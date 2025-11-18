"""Data models for storing mutual fund information"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class SchemeMetadata(BaseModel):
    """Metadata for a mutual fund scheme"""
    scheme_code: str
    scheme_name: str
    scheme_type: str
    category: Optional[str] = None
    source_url: HttpUrl
    factsheet_url: Optional[HttpUrl] = None
    last_updated: datetime
    last_validated: Optional[datetime] = None
    validation_status: str = "pending"  # pending, valid, invalid, error


class NAVData(BaseModel):
    """NAV (Net Asset Value) data"""
    date: str
    nav: float
    repurchase_price: Optional[float] = None
    sale_price: Optional[float] = None


class SchemeData(BaseModel):
    """Complete scheme data structure"""
    metadata: SchemeMetadata
    nav_data: Optional[List[NAVData]] = None
    current_nav: Optional[float] = None
    nav_date: Optional[str] = None
    aum: Optional[float] = None  # Assets Under Management
    expense_ratio: Optional[float] = None
    fund_manager: Optional[str] = None
    launch_date: Optional[str] = None  # Inception Date
    benchmark: Optional[str] = None
    risk_level: Optional[str] = None
    min_investment: Optional[float] = None
    sip_min_investment: Optional[float] = None  # SIP minimum investment
    exit_load: Optional[str] = None
    performance: Optional[Dict[str, Any]] = None  # 1Y, 3Y, 5Y returns
    portfolio: Optional[Dict[str, Any]] = None
    notices: Optional[List[Dict[str, Any]]] = None  # Official notices
    field_sources: Optional[Dict[str, str]] = None  # Source URL for each field
    raw_data: Optional[Dict[str, Any]] = None  # Store raw scraped data


class FactsheetData(BaseModel):
    """Factsheet data structure"""
    scheme_code: str
    scheme_name: str
    source_url: HttpUrl
    last_updated: datetime
    content: Dict[str, Any]  # Structured factsheet content
    raw_text: str  # Full text content for chunking


class TextChunk(BaseModel):
    """Text chunk for search/retrieval"""
    chunk_id: str
    scheme_code: str
    chunk_type: str  # "scheme" or "factsheet"
    content: str
    metadata: Dict[str, Any]
    source_url: HttpUrl
    created_at: datetime


class StorageMetadata(BaseModel):
    """Overall storage metadata"""
    total_schemes: int = 0
    total_factsheets: int = 0
    total_chunks: int = 0
    last_full_refresh: Optional[datetime] = None
    last_nav_update: Optional[datetime] = None
    schemes: List[Dict[str, str]] = []  # List of {scheme_code, scheme_name, source_url}

