"""Query answerer that uses RAG to answer factual queries"""
from typing import Dict, Any, Optional
import re

from backend.rag_system import RAGSystem
from backend.data_loader import DataLoader
from scraper.url_validator import validate_url


class QueryAnswerer:
    """Answers queries about Nippon India Mutual Fund schemes using RAG"""
    
    def __init__(self):
        self.rag_system = RAGSystem()
        self.data_loader = DataLoader()
    
    def answer_query(self, query: str) -> Dict[str, Any]:
        """
        Answer a factual query about mutual fund schemes.
        
        Returns:
            {
                'answer': str,  # Factual answer
                'source_url': str,  # Official source URL
                'scheme_code': str,  # Scheme code if applicable
                'confidence': str  # 'high', 'medium', 'low'
            }
        """
        # Validate query
        if not query or len(query.strip()) < 3:
            return {
                'answer': "Please provide a valid query about Nippon India Mutual Fund schemes.",
                'source_url': "",
                'scheme_code': "",
                'confidence': 'low'
            }
        
        query = query.strip()
        
        # Search for relevant documents
        search_results = self.rag_system.search(query, n_results=5)
        
        if not search_results:
            return {
                'answer': "I don't have information about that in my database. Please ensure the data has been scraped from the official Nippon India Mutual Fund website.",
                'source_url': "",
                'scheme_code': "",
                'confidence': 'low'
            }
        
        # Extract source URL from top result
        top_result = search_results[0]
        source_url = top_result['metadata'].get('source_url', '')
        
        # Validate source URL
        if not source_url or not validate_url(source_url):
            # Try to find a valid source URL from results
            for result in search_results:
                candidate_url = result['metadata'].get('source_url', '')
                if candidate_url and validate_url(candidate_url):
                    source_url = candidate_url
                    break
        
        if not source_url or not validate_url(source_url):
            return {
                'answer': "I cannot provide an answer as the source URL is invalid. This may indicate data integrity issues.",
                'source_url': "",
                'scheme_code': "",
                'confidence': 'low'
            }
        
        # Get scheme code if available
        scheme_code = top_result['metadata'].get('scheme_code', '')
        
        # Try to find specific scheme if query mentions a scheme name
        scheme_name = self._extract_scheme_name(query)
        if scheme_name:
            scheme = self.data_loader.get_scheme_by_name(scheme_name)
            if scheme:
                scheme_code = scheme.metadata.scheme_code
                # Use scheme's source URL if available
                if scheme.field_sources:
                    # Try to get most relevant field source
                    for field in ['nav', 'scheme_page', 'category']:
                        if field in scheme.field_sources:
                            candidate_url = scheme.field_sources[field]
                            if validate_url(candidate_url):
                                source_url = candidate_url
                                break
                else:
                    source_url = str(scheme.metadata.source_url)
        
        # Generate answer using RAG
        try:
            answer = self.rag_system.generate_answer(
                query=query,
                context_documents=search_results,
                source_url=source_url
            )
        except Exception as e:
            print(f"Error generating answer: {e}")
            # Fallback: construct answer from search results
            answer = self._construct_fallback_answer(query, search_results, source_url)
        
        # Validate answer doesn't contain fake data
        if self._contains_fake_data(answer):
            return {
                'answer': "I cannot provide an answer as the data may not be from official sources. Please verify the data has been scraped from the official Nippon India Mutual Fund website.",
                'source_url': "",
                'scheme_code': scheme_code,
                'confidence': 'low'
            }
        
        # Ensure source URL is included in answer
        if not self._has_source_url(answer):
            answer += f"\n\nSource: {source_url}"
        
        # Determine confidence
        confidence = self._determine_confidence(search_results, answer)
        
        return {
            'answer': answer,
            'source_url': source_url,
            'scheme_code': scheme_code,
            'confidence': confidence
        }
    
    def _extract_scheme_name(self, query: str) -> Optional[str]:
        """Extract scheme name from query"""
        # Look for "Nippon India" followed by scheme name
        pattern = r'Nippon\s+India\s+([A-Za-z\s]+?)(?:\s+Fund|\?|$)'
        match = re.search(pattern, query, re.I)
        if match:
            return f"Nippon India {match.group(1).strip()} Fund"
        
        # Look for scheme name patterns
        scheme_keywords = ['fund', 'scheme', 'plan']
        words = query.split()
        for i, word in enumerate(words):
            if word.lower() in scheme_keywords and i > 0:
                # Try to extract scheme name
                potential_name = ' '.join(words[max(0, i-3):i+1])
                if 'nippon' in potential_name.lower():
                    return potential_name
        
        return None
    
    def _construct_fallback_answer(
        self,
        query: str,
        search_results: list,
        source_url: str
    ) -> str:
        """Construct answer from search results without LLM"""
        top_doc = search_results[0]['document']
        
        # Try to extract relevant information
        answer_parts = []
        
        # Check if query is about NAV
        if 'nav' in query.lower() or 'net asset value' in query.lower():
            nav_match = re.search(r'Latest NAV: ₹?([\d,]+\.?\d*)', top_doc, re.I)
            date_match = re.search(r'NAV Date: ([\d/-]+)', top_doc, re.I)
            if nav_match:
                nav_value = nav_match.group(1)
                nav_date = date_match.group(1) if date_match else "latest available date"
                answer_parts.append(f"The latest NAV is ₹{nav_value} as of {nav_date}.")
        
        # Check if query is about scheme name
        if 'name' in query.lower() or 'what is' in query.lower():
            name_match = re.search(r'Scheme Name: ([^\n]+)', top_doc)
            if name_match:
                answer_parts.append(f"The scheme name is {name_match.group(1).strip()}.")
        
        # Generic answer
        if not answer_parts:
            # Extract first relevant sentence
            sentences = top_doc.split('.')
            for sentence in sentences[:2]:
                if any(keyword in sentence.lower() for keyword in query.lower().split()):
                    answer_parts.append(sentence.strip() + '.')
                    break
        
        if not answer_parts:
            answer_parts.append("Based on the available data from the official website:")
        
        answer = ' '.join(answer_parts)
        answer += f"\n\nSource: {source_url}"
        
        return answer
    
    def _contains_fake_data(self, answer: str) -> bool:
        """Check if answer contains fake or demo data"""
        fake_indicators = [
            'demo',
            'example',
            'sample',
            'test data',
            'placeholder',
            'xxx',
            '000.00',
            'not available',
            'n/a',
            'tbd'
        ]
        
        answer_lower = answer.lower()
        for indicator in fake_indicators:
            if indicator in answer_lower:
                # Check context - might be legitimate "not available"
                if indicator == 'not available' or indicator == 'n/a':
                    # Only flag if it seems like placeholder data
                    if 'demo' in answer_lower or 'example' in answer_lower:
                        return True
                else:
                    return True
        
        return False
    
    def _has_source_url(self, answer: str) -> bool:
        """Check if answer includes a source URL"""
        url_pattern = r'https?://[^\s]+'
        return bool(re.search(url_pattern, answer))
    
    def _determine_confidence(
        self,
        search_results: list,
        answer: str
    ) -> str:
        """Determine confidence level of answer"""
        if not search_results:
            return 'low'
        
        top_result = search_results[0]
        distance = top_result.get('distance')
        
        # High confidence: low distance, clear answer, valid source
        if distance is not None and distance < 0.3:
            if self._has_source_url(answer) and not self._contains_fake_data(answer):
                return 'high'
        
        # Medium confidence: moderate distance or multiple results
        if len(search_results) >= 2:
            return 'medium'
        
        # Low confidence: high distance or unclear answer
        if distance is not None and distance > 0.7:
            return 'low'
        
        return 'medium'

