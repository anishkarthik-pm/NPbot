"""Query interface for retrieving stored data (no live scraping)"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from storage.data_store import DataStore
from storage.models import SchemeData, FactsheetData, TextChunk


class QueryInterface:
    """Interface for querying stored mutual fund data"""
    
    def __init__(self):
        self.data_store = DataStore()
    
    def search_schemes(
        self,
        query: Optional[str] = None,
        scheme_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[SchemeData]:
        """Search schemes by query, type, or category"""
        all_schemes = self.data_store.get_all_schemes()
        
        if not query and not scheme_type and not category:
            return all_schemes
        
        results = []
        query_lower = query.lower() if query else None
        
        for scheme in all_schemes:
            # Filter by query
            if query_lower:
                matches = (
                    query_lower in scheme.metadata.scheme_name.lower() or
                    query_lower in scheme.metadata.scheme_type.lower() or
                    (scheme.metadata.category and query_lower in scheme.metadata.category.lower())
                )
                if not matches:
                    continue
            
            # Filter by scheme type
            if scheme_type and scheme.metadata.scheme_type.lower() != scheme_type.lower():
                continue
            
            # Filter by category
            if category and scheme.metadata.category and \
               scheme.metadata.category.lower() != category.lower():
                continue
            
            results.append(scheme)
        
        return results
    
    def get_scheme(self, scheme_code: str) -> Optional[SchemeData]:
        """Get specific scheme by code"""
        return self.data_store.get_scheme(scheme_code)
    
    def get_scheme_by_name(self, scheme_name: str) -> Optional[SchemeData]:
        """Get scheme by name (exact or partial match)"""
        all_schemes = self.data_store.get_all_schemes()
        name_lower = scheme_name.lower()
        
        # Try exact match first
        for scheme in all_schemes:
            if scheme.metadata.scheme_name.lower() == name_lower:
                return scheme
        
        # Try partial match
        for scheme in all_schemes:
            if name_lower in scheme.metadata.scheme_name.lower():
                return scheme
        
        return None
    
    def get_factsheet(self, scheme_code: str) -> Optional[FactsheetData]:
        """Get factsheet for a scheme"""
        return self.data_store.get_factsheet(scheme_code)
    
    def search_chunks(
        self,
        query: str,
        scheme_code: Optional[str] = None,
        chunk_type: Optional[str] = None
    ) -> List[TextChunk]:
        """Search text chunks by query"""
        all_chunks = self.data_store.get_all_chunks(scheme_code=scheme_code)
        query_lower = query.lower()
        
        results = []
        for chunk in all_chunks:
            # Filter by chunk type
            if chunk_type and chunk.chunk_type != chunk_type:
                continue
            
            # Simple text search in chunk content
            if query_lower in chunk.content.lower():
                results.append(chunk)
        
        return results
    
    def get_nav_data(self, scheme_code: str) -> Optional[Dict[str, Any]]:
        """Get NAV data for a scheme"""
        scheme = self.get_scheme(scheme_code)
        if not scheme:
            return None
        
        return {
            'scheme_code': scheme.metadata.scheme_code,
            'scheme_name': scheme.metadata.scheme_name,
            'current_nav': scheme.current_nav,
            'nav_date': scheme.nav_date,
            'nav_history': [
                {
                    'date': nav.date,
                    'nav': nav.nav
                }
                for nav in (scheme.nav_data or [])
            ] if scheme.nav_data else [],
            'last_updated': scheme.metadata.last_updated.isoformat()
        }
    
    def get_all_nav_data(self) -> List[Dict[str, Any]]:
        """Get NAV data for all schemes"""
        all_schemes = self.data_store.get_all_schemes()
        nav_data = []
        
        for scheme in all_schemes:
            nav_info = self.get_nav_data(scheme.metadata.scheme_code)
            if nav_info:
                nav_data.append(nav_info)
        
        return nav_data
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored data"""
        metadata = self.data_store.get_metadata()
        all_schemes = self.data_store.get_all_schemes()
        
        # Count by scheme type
        scheme_types = {}
        for scheme in all_schemes:
            scheme_type = scheme.metadata.scheme_type
            scheme_types[scheme_type] = scheme_types.get(scheme_type, 0) + 1
        
        return {
            'total_schemes': metadata.total_schemes,
            'total_factsheets': metadata.total_factsheets,
            'total_chunks': metadata.total_chunks,
            'schemes_by_type': scheme_types,
            'last_full_refresh': metadata.last_full_refresh.isoformat() if metadata.last_full_refresh else None,
            'last_nav_update': metadata.last_nav_update.isoformat() if metadata.last_nav_update else None
        }
    
    def get_schemes_by_type(self, scheme_type: str) -> List[SchemeData]:
        """Get all schemes of a specific type"""
        return self.search_schemes(scheme_type=scheme_type)
    
    def get_recent_updates(self, days: int = 7) -> List[SchemeData]:
        """Get schemes updated in the last N days"""
        all_schemes = self.data_store.get_all_schemes()
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        
        recent = []
        for scheme in all_schemes:
            if scheme.metadata.last_updated >= cutoff_date:
                recent.append(scheme)
        
        return sorted(recent, key=lambda s: s.metadata.last_updated, reverse=True)

