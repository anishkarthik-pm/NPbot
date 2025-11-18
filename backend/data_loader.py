"""Data loader for pre-scraped JSON scheme data"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import config
from storage.models import SchemeData, SchemeMetadata, TextChunk
from storage.data_store import DataStore


class DataLoader:
    """Loads pre-scraped JSON scheme data for RAG system"""
    
    def __init__(self):
        self.data_store = DataStore()
        self.schemes_dir = config.SCHEMES_DIR
        self.chunks_dir = config.CHUNKS_DIR
    
    def load_all_schemes(self) -> List[SchemeData]:
        """Load all stored schemes from JSON files"""
        schemes = []
        
        for scheme_file in self.schemes_dir.glob("*.json"):
            try:
                scheme = self.data_store.get_scheme(scheme_file.stem)
                if scheme:
                    schemes.append(scheme)
            except Exception as e:
                print(f"Error loading scheme from {scheme_file}: {e}")
        
        return schemes
    
    def load_all_chunks(self) -> List[TextChunk]:
        """Load all text chunks from JSON files"""
        chunks = []
        
        for chunk_file in self.chunks_dir.glob("*.json"):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                chunk = TextChunk(**data)
                chunks.append(chunk)
            except Exception as e:
                print(f"Error loading chunk from {chunk_file}: {e}")
        
        return chunks
    
    def get_scheme_by_name(self, scheme_name: str) -> Optional[SchemeData]:
        """Get scheme by name (fuzzy match)"""
        all_schemes = self.load_all_schemes()
        scheme_name_lower = scheme_name.lower()
        
        # Try exact match first
        for scheme in all_schemes:
            if scheme.metadata.scheme_name.lower() == scheme_name_lower:
                return scheme
        
        # Try partial match
        for scheme in all_schemes:
            if scheme_name_lower in scheme.metadata.scheme_name.lower():
                return scheme
        
        # Try word-by-word match
        query_words = set(scheme_name_lower.split())
        for scheme in all_schemes:
            scheme_words = set(scheme.metadata.scheme_name.lower().split())
            if query_words.issubset(scheme_words) or len(query_words & scheme_words) >= 2:
                return scheme
        
        return None
    
    def format_scheme_for_embedding(self, scheme: SchemeData) -> str:
        """Format scheme data as text for embedding"""
        text_parts = [
            f"Scheme Name: {scheme.metadata.scheme_name}",
            f"Scheme Code: {scheme.metadata.scheme_code}",
            f"Scheme Type: {scheme.metadata.scheme_type}",
        ]
        
        if scheme.metadata.category:
            text_parts.append(f"Category: {scheme.metadata.category}")
        
        if scheme.current_nav:
            text_parts.append(f"Latest NAV: ₹{scheme.current_nav}")
            if scheme.nav_date:
                text_parts.append(f"NAV Date: {scheme.nav_date}")
        
        if scheme.aum:
            text_parts.append(f"AUM: ₹{scheme.aum} Crores")
        
        if scheme.expense_ratio:
            text_parts.append(f"Expense Ratio: {scheme.expense_ratio}%")
        
        if scheme.fund_manager:
            text_parts.append(f"Fund Manager: {scheme.fund_manager}")
        
        if scheme.launch_date:
            text_parts.append(f"Inception Date: {scheme.launch_date}")
        
        if scheme.benchmark:
            text_parts.append(f"Benchmark: {scheme.benchmark}")
        
        if scheme.risk_level:
            text_parts.append(f"Risk Level: {scheme.risk_level}")
        
        if scheme.min_investment:
            text_parts.append(f"Minimum Investment: ₹{scheme.min_investment}")
        
        if scheme.sip_min_investment:
            text_parts.append(f"SIP Minimum Investment: ₹{scheme.sip_min_investment}")
        
        if scheme.performance:
            perf_text = "Performance: "
            perf_parts = []
            for period, value in scheme.performance.items():
                perf_parts.append(f"{period}: {value}%")
            text_parts.append(perf_text + ", ".join(perf_parts))
        
        # Add source URL for reference
        text_parts.append(f"Source URL: {scheme.metadata.source_url}")
        
        return "\n".join(text_parts)
    
    def get_source_url(self, scheme: SchemeData, field: Optional[str] = None) -> str:
        """Get source URL for a scheme or specific field"""
        if field and scheme.field_sources and field in scheme.field_sources:
            return scheme.field_sources[field]
        return str(scheme.metadata.source_url)

