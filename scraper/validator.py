"""Data validator for validating scraped data against official website"""
import time
from datetime import datetime
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from storage.models import SchemeData, SchemeMetadata
from scraper.url_validator import validate_url


class DataValidator:
    """Validates scraped data against official website"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
        })
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def _fetch_validation_data(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch data from official URL for validation"""
        try:
            response = self.session.get(url, timeout=config.VALIDATION_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            print(f"Validation fetch error for {url}: {e}")
            return None
    
    def validate_scheme(self, scheme_data: SchemeData) -> Dict[str, Any]:
        """Validate scheme data against official website"""
        if not config.VALIDATION_ENABLED:
            return {'status': 'skipped', 'reason': 'validation_disabled'}
        
        validation_result = {
            'status': 'pending',
            'validated_at': datetime.now().isoformat(),
            'checks': {}
        }
        
        source_url = str(scheme_data.metadata.source_url)
        soup = self._fetch_validation_data(source_url)
        
        if not soup:
            validation_result['status'] = 'error'
            validation_result['error'] = 'Could not fetch validation page'
            return validation_result
        
        # Validate scheme name
        validation_result['checks']['scheme_name'] = self._validate_scheme_name(
            scheme_data.metadata.scheme_name,
            soup
        )
        
        # Validate NAV
        if scheme_data.current_nav:
            validation_result['checks']['nav'] = self._validate_nav(
                scheme_data.current_nav,
                soup
            )
        
        # Validate scheme type
        validation_result['checks']['scheme_type'] = self._validate_scheme_type(
            scheme_data.metadata.scheme_type,
            soup
        )
        
        # Determine overall status
        checks = validation_result['checks']
        if all(check.get('valid', False) for check in checks.values()):
            validation_result['status'] = 'valid'
        elif any(check.get('valid', False) for check in checks.values()):
            validation_result['status'] = 'partial'
        else:
            validation_result['status'] = 'invalid'
        
        return validation_result
    
    def _validate_scheme_name(self, stored_name: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """Validate scheme name"""
        page_text = soup.get_text().lower()
        stored_lower = stored_name.lower()
        
        # Check if stored name appears in page
        name_found = stored_lower in page_text or any(
            word in page_text for word in stored_lower.split() if len(word) > 3
        )
        
        return {
            'valid': name_found,
            'stored': stored_name,
            'found_on_page': name_found
        }
    
    def _validate_nav(self, stored_nav: float, soup: BeautifulSoup) -> Dict[str, Any]:
        """Validate NAV value"""
        import re
        
        page_text = soup.get_text()
        # Look for NAV values on page
        nav_patterns = [
            r'NAV[:\s]*₹?\s*([\d,]+\.?\d*)',
            r'Net Asset Value[:\s]*₹?\s*([\d,]+\.?\d*)',
        ]
        
        found_navs = []
        for pattern in nav_patterns:
            matches = re.findall(pattern, page_text, re.I)
            for match in matches:
                try:
                    nav_value = float(match.replace(',', ''))
                    found_navs.append(nav_value)
                except ValueError:
                    pass
        
        if not found_navs:
            return {
                'valid': False,
                'stored': stored_nav,
                'found_on_page': None,
                'reason': 'No NAV found on page'
            }
        
        # Check if stored NAV is close to any found NAV (within 1%)
        for found_nav in found_navs:
            if abs(stored_nav - found_nav) / max(stored_nav, found_nav) < 0.01:
                return {
                    'valid': True,
                    'stored': stored_nav,
                    'found_on_page': found_nav
                }
        
        return {
            'valid': False,
            'stored': stored_nav,
            'found_on_page': found_navs[0] if found_navs else None,
            'reason': 'NAV mismatch'
        }
    
    def _validate_scheme_type(self, stored_type: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """Validate scheme type"""
        page_text = soup.get_text().lower()
        stored_lower = stored_type.lower()
        
        # Check if scheme type keywords appear
        type_found = stored_lower in page_text
        
        return {
            'valid': type_found,
            'stored': stored_type,
            'found_on_page': type_found
        }
    
    def update_validation_status(self, scheme_data: SchemeData, validation_result: Dict[str, Any]):
        """Update scheme data with validation results"""
        scheme_data.metadata.validation_status = validation_result['status']
        scheme_data.metadata.last_validated = datetime.fromisoformat(
            validation_result['validated_at']
        )

