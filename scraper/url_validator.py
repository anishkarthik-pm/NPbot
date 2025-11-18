"""URL validator to ensure only official domains are used"""
from urllib.parse import urlparse
from typing import Optional

import config


def validate_url(url: str) -> bool:
    """Validate that URL is from an official domain"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check if domain matches any allowed domain
        for allowed_domain in config.ALLOWED_DOMAINS:
            if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                return True
        
        return False
    except Exception:
        return False


def normalize_url(url: str, base_url: Optional[str] = None) -> Optional[str]:
    """Normalize and validate URL"""
    from urllib.parse import urljoin
    
    if not url:
        return None
    
    # If relative URL, make it absolute
    if base_url and not url.startswith('http'):
        url = urljoin(base_url, url)
    
    # Validate URL
    if not validate_url(url):
        print(f"Warning: URL not from official domain: {url}")
        return None
    
    return url

