"""Data storage system for structured JSON + text chunks + source URLs"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from .models import (
    SchemeData,
    SchemeMetadata,
    FactsheetData,
    TextChunk,
    StorageMetadata,
    NAVData
)
import config


class DataStore:
    """Manages storage of scheme data, factsheets, and text chunks"""
    
    def __init__(self):
        self.schemes_dir = config.SCHEMES_DIR
        self.factsheets_dir = config.FACTSHEETS_DIR
        self.chunks_dir = config.CHUNKS_DIR
        self.metadata_file = config.METADATA_FILE
        self._metadata: Optional[StorageMetadata] = None
    
    def _load_metadata(self) -> StorageMetadata:
        """Load metadata from file"""
        if self._metadata is not None:
            return self._metadata
        
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert datetime strings back to datetime objects
                if data.get('last_full_refresh'):
                    data['last_full_refresh'] = datetime.fromisoformat(data['last_full_refresh'])
                if data.get('last_nav_update'):
                    data['last_nav_update'] = datetime.fromisoformat(data['last_nav_update'])
                self._metadata = StorageMetadata(**data)
        else:
            self._metadata = StorageMetadata()
        
        return self._metadata
    
    def _save_metadata(self):
        """Save metadata to file"""
        if self._metadata is None:
            return
        
        data = self._metadata.model_dump()
        # Convert datetime objects to ISO format strings
        if data.get('last_full_refresh'):
            data['last_full_refresh'] = data['last_full_refresh'].isoformat()
        if data.get('last_nav_update'):
            data['last_nav_update'] = data['last_nav_update'].isoformat()
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def store_scheme(self, scheme_data: SchemeData) -> bool:
        """Store scheme data as JSON"""
        try:
            scheme_code = scheme_data.metadata.scheme_code
            filename = f"{scheme_code}.json"
            filepath = self.schemes_dir / filename
            
            # Convert to dict and handle datetime serialization
            data = scheme_data.model_dump()
            data['metadata']['last_updated'] = data['metadata']['last_updated'].isoformat()
            if data['metadata'].get('last_validated'):
                data['metadata']['last_validated'] = data['metadata']['last_validated'].isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Update metadata
            metadata = self._load_metadata()
            # Check if scheme already exists
            existing = next(
                (s for s in metadata.schemes if s.get('scheme_code') == scheme_code),
                None
            )
            if not existing:
                metadata.schemes.append({
                    'scheme_code': scheme_code,
                    'scheme_name': scheme_data.metadata.scheme_name,
                    'source_url': str(scheme_data.metadata.source_url)
                })
                metadata.total_schemes += 1
            else:
                # Update existing entry
                existing['scheme_name'] = scheme_data.metadata.scheme_name
                existing['source_url'] = str(scheme_data.metadata.source_url)
            
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error storing scheme {scheme_data.metadata.scheme_code}: {e}")
            return False
    
    def store_factsheet(self, factsheet_data: FactsheetData) -> bool:
        """Store factsheet data as JSON"""
        try:
            scheme_code = factsheet_data.scheme_code
            filename = f"{scheme_code}_factsheet.json"
            filepath = self.factsheets_dir / filename
            
            data = factsheet_data.model_dump()
            data['last_updated'] = data['last_updated'].isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Update metadata
            metadata = self._load_metadata()
            metadata.total_factsheets += 1
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error storing factsheet {factsheet_data.scheme_code}: {e}")
            return False
    
    def store_text_chunks(self, chunks: List[TextChunk]) -> bool:
        """Store text chunks for search/retrieval"""
        try:
            for chunk in chunks:
                filename = f"{chunk.chunk_id}.json"
                filepath = self.chunks_dir / filename
                
                data = chunk.model_dump()
                data['created_at'] = data['created_at'].isoformat()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Update metadata
            metadata = self._load_metadata()
            metadata.total_chunks += len(chunks)
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error storing text chunks: {e}")
            return False
    
    def create_text_chunks(
        self,
        scheme_code: str,
        content: str,
        chunk_type: str,
        source_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """Create text chunks from content"""
        chunks = []
        chunk_size = config.CHUNK_SIZE
        overlap = config.CHUNK_OVERLAP
        
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = start + chunk_size
            chunk_content = content[start:end]
            
            # Create chunk ID
            chunk_id = hashlib.md5(
                f"{scheme_code}_{chunk_type}_{chunk_index}".encode()
            ).hexdigest()
            
            chunk = TextChunk(
                chunk_id=chunk_id,
                scheme_code=scheme_code,
                chunk_type=chunk_type,
                content=chunk_content,
                metadata=metadata or {},
                source_url=source_url,
                created_at=datetime.now()
            )
            chunks.append(chunk)
            
            start = end - overlap
            chunk_index += 1
        
        return chunks
    
    def get_scheme(self, scheme_code: str) -> Optional[SchemeData]:
        """Retrieve scheme data"""
        filename = f"{scheme_code}.json"
        filepath = self.schemes_dir / filename
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert ISO strings back to datetime
            data['metadata']['last_updated'] = datetime.fromisoformat(data['metadata']['last_updated'])
            if data['metadata'].get('last_validated'):
                data['metadata']['last_validated'] = datetime.fromisoformat(data['metadata']['last_validated'])
            
            return SchemeData(**data)
        except Exception as e:
            print(f"Error loading scheme {scheme_code}: {e}")
            return None
    
    def get_factsheet(self, scheme_code: str) -> Optional[FactsheetData]:
        """Retrieve factsheet data"""
        filename = f"{scheme_code}_factsheet.json"
        filepath = self.factsheets_dir / filename
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
            return FactsheetData(**data)
        except Exception as e:
            print(f"Error loading factsheet {scheme_code}: {e}")
            return None
    
    def get_all_chunks(self, scheme_code: Optional[str] = None) -> List[TextChunk]:
        """Retrieve all text chunks, optionally filtered by scheme_code"""
        chunks = []
        
        for chunk_file in self.chunks_dir.glob("*.json"):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if scheme_code and data.get('scheme_code') != scheme_code:
                    continue
                
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                chunks.append(TextChunk(**data))
            except Exception as e:
                print(f"Error loading chunk {chunk_file}: {e}")
        
        return chunks
    
    def get_all_schemes(self) -> List[SchemeData]:
        """Retrieve all stored schemes"""
        schemes = []
        
        for scheme_file in self.schemes_dir.glob("*.json"):
            try:
                scheme_code = scheme_file.stem
                scheme = self.get_scheme(scheme_code)
                if scheme:
                    schemes.append(scheme)
            except Exception as e:
                print(f"Error loading scheme from {scheme_file}: {e}")
        
        return schemes
    
    def update_refresh_timestamp(self, nav_only: bool = False):
        """Update refresh timestamp in metadata"""
        metadata = self._load_metadata()
        now = datetime.now()
        
        if nav_only:
            metadata.last_nav_update = now
        else:
            metadata.last_full_refresh = now
            metadata.last_nav_update = now
        
        self._save_metadata()
    
    def get_metadata(self) -> StorageMetadata:
        """Get current storage metadata"""
        return self._load_metadata()

