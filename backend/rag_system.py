"""RAG system using ChromaDB embeddings and OpenRouter API"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
import requests
from dotenv import load_dotenv

import config
from backend.data_loader import DataLoader
from storage.models import SchemeData, TextChunk

load_dotenv()


class RAGSystem:
    """RAG system for answering queries about mutual fund schemes"""
    
    def __init__(self, collection_name: str = "nippon_schemes"):
        self.data_loader = DataLoader()
        self.collection_name = collection_name
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.openrouter_base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        # Initialize ChromaDB
        chroma_db_path = config.CHROMA_DB_PATH
        chroma_db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(chroma_db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = None
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize or get existing ChromaDB collection"""
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            print(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Nippon India Mutual Fund schemes"}
            )
            print(f"Created new collection: {self.collection_name}")
            # Populate with embeddings
            self._populate_embeddings()
    
    def _populate_embeddings(self):
        """Populate ChromaDB with scheme embeddings"""
        print("Populating ChromaDB with scheme embeddings...")
        
        schemes = self.data_loader.load_all_schemes()
        chunks = self.data_loader.load_all_chunks()
        
        documents = []
        metadatas = []
        ids = []
        
        # Add scheme data
        for scheme in schemes:
            scheme_text = self.data_loader.format_scheme_for_embedding(scheme)
            documents.append(scheme_text)
            metadatas.append({
                "scheme_code": scheme.metadata.scheme_code,
                "scheme_name": scheme.metadata.scheme_name,
                "scheme_type": scheme.metadata.scheme_type,
                "category": scheme.metadata.category or "",
                "source_url": str(scheme.metadata.source_url),
                "type": "scheme"
            })
            ids.append(f"scheme_{scheme.metadata.scheme_code}")
        
        # Add text chunks
        for chunk in chunks:
            documents.append(chunk.content)
            metadatas.append({
                "scheme_code": chunk.scheme_code,
                "chunk_type": chunk.chunk_type,
                "source_url": str(chunk.source_url),
                "type": "chunk"
            })
            ids.append(f"chunk_{chunk.chunk_id}")
        
        if documents:
            print(f"Adding {len(documents)} documents to ChromaDB...")
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"✓ Successfully added {len(documents)} documents")
        else:
            print("No documents to add. Run scraper first to populate data.")
    
    def _get_embeddings(self, query: str) -> List[float]:
        """Get embeddings for a query using OpenRouter API"""
        # For now, we'll use ChromaDB's default embedding function
        # In production, you might want to use OpenRouter's embedding API
        # For simplicity, we'll let ChromaDB handle embeddings
        return None  # ChromaDB will handle this
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents using ChromaDB"""
        try:
            count = self.collection.count()
            if count == 0:
                print("Warning: ChromaDB collection is empty. Run scraper first.")
                return []
        except Exception as e:
            print(f"Warning: Could not check collection count: {e}")
            return []
        
        try:
            query_count = min(n_results, count) if count > 0 else n_results
            results = self.collection.query(
                query_texts=[query],
                n_results=query_count
            )
        except Exception as e:
            print(f"Error querying ChromaDB: {e}")
            return []
        
        # Format results
        formatted_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def _call_openrouter(self, messages: List[Dict[str, str]]) -> str:
        """Call OpenRouter API for LLM completion"""
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional
            "X-Title": "NPbot"  # Optional
        }
        
        data = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": 0.1,  # Low temperature for factual answers
            "max_tokens": 200  # Short answers only
        }
        
        try:
            response = requests.post(
                self.openrouter_base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"Error calling OpenRouter API: {e}")
            raise
    
    def generate_answer(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        source_url: str
    ) -> str:
        """Generate answer using RAG with OpenRouter API"""
        
        # Build context from documents
        context_parts = []
        for doc in context_documents[:3]:  # Use top 3 results
            context_parts.append(doc['document'])
        
        context = "\n\n".join(context_parts)
        
        # Create prompt
        system_prompt = """You are a factual assistant for Nippon India Mutual Fund information.
Your role is to provide short, factual answers based ONLY on the provided context.
Rules:
1. Answer ONLY using information from the provided context
2. Include the source URL in your answer
3. If information is not in the context, say "I don't have that information in my database"
4. Keep answers brief and factual (max 2-3 sentences)
5. Do NOT provide investment advice
6. Do NOT use fake or demo data
7. Always include the source URL at the end: "Source: [URL]"
"""
        
        user_prompt = f"""Context from official Nippon India Mutual Fund website:
{context}

Question: {query}

Provide a short factual answer based on the context above. Include the source URL."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        answer = self._call_openrouter(messages)
        
        # Ensure source URL is included
        if "source:" not in answer.lower() and "source url" not in answer.lower():
            answer += f"\n\nSource: {source_url}"
        
        return answer
    
    def refresh_embeddings(self):
        """Refresh embeddings (re-populate ChromaDB)"""
        print("Refreshing embeddings...")
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        
        self._initialize_collection()

