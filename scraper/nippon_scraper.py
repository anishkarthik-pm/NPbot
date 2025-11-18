"""Scraper for Nippon India Mutual Fund pages"""
import re
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from storage.models import SchemeData, SchemeMetadata, FactsheetData, NAVData
from scraper.url_validator import validate_url, normalize_url


class NipponScraper:
    """Scrapes Nippon India Mutual Fund scheme pages and factsheets"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.base_url = config.NIPPON_BASE_URL
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage"""
        try:
            # Validate URL before fetching
            if not validate_url(url):
                print(f"Invalid URL (not from official domain): {url}")
                return None
            
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _extract_scheme_code(self, url: str, soup: Optional[BeautifulSoup] = None) -> Optional[str]:
        """Extract scheme code from URL or page content"""
        # Try to extract from URL pattern (e.g., scheme code in URL)
        match = re.search(r'/(\d{6})', url)
        if match:
            return match.group(1)
        
        # Try to extract from page content
        if soup:
            # Look for scheme code in various formats
            text = soup.get_text()
            # Pattern: Scheme Code: 123456
            code_match = re.search(r'(?:scheme\s*code|fund\s*code)[:\s]*(\d{6})', text, re.I)
            if code_match:
                return code_match.group(1)
            
            # Look in meta tags or data attributes
            meta_code = soup.find('meta', {'name': re.compile(r'scheme.*code', re.I)})
            if meta_code and meta_code.get('content'):
                code = re.search(r'(\d{6})', meta_code.get('content'))
                if code:
                    return code.group(1)
        
        return None
    
    def get_all_schemes_list(self) -> List[Dict[str, str]]:
        """Get list of all available schemes from official listing page"""
        schemes = []
        
        # Try to find schemes listing page
        soup = self._fetch_page(config.SCHEMES_LIST_URL)
        if not soup:
            print("Could not fetch schemes listing page. Trying alternative method...")
            # Alternative: Try to discover schemes from main page
            return self._discover_schemes_alternative()
        
        # Look for scheme links in various formats
        # Pattern 1: Links to FundsAndPerformance/Pages/
        scheme_links = soup.find_all('a', href=re.compile(r'FundsAndPerformance/Pages', re.I))
        
        for link in scheme_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Make URL absolute
            if href.startswith('/'):
                full_url = urljoin(self.base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(config.SCHEMES_LIST_URL, href)
            
            # Validate URL
            full_url = normalize_url(full_url, self.base_url)
            if not full_url:
                continue
            
            scheme_name = link.get_text(strip=True)
            if not scheme_name or len(scheme_name) < 3:
                # Try to get name from title or data attributes
                scheme_name = link.get('title', '') or link.get('data-title', '')
            
            if scheme_name:
                scheme_code = self._extract_scheme_code(full_url) or f"SCHEME_{len(schemes)}"
                schemes.append({
                    'scheme_code': scheme_code,
                    'scheme_name': scheme_name,
                    'url': full_url
                })
        
        # Remove duplicates
        seen_urls = set()
        unique_schemes = []
        for scheme in schemes:
            if scheme['url'] not in seen_urls:
                seen_urls.add(scheme['url'])
                unique_schemes.append(scheme)
        
        return unique_schemes
    
    def _discover_schemes_alternative(self) -> List[Dict[str, str]]:
        """Alternative method to discover schemes"""
        # This would need to be implemented based on actual website structure
        # For now, return empty list
        return []
    
    def scrape_scheme_page(self, scheme_url: str, scheme_code: Optional[str] = None) -> Optional[SchemeData]:
        """Scrape individual scheme page and extract all required fields"""
        # Validate and normalize URL
        scheme_url = normalize_url(scheme_url, self.base_url)
        if not scheme_url:
            print(f"Invalid scheme URL: {scheme_url}")
            return None
        
        soup = self._fetch_page(scheme_url)
        if not soup:
            return None
        
        # Extract scheme code
        if not scheme_code:
            scheme_code = self._extract_scheme_code(scheme_url, soup) or "UNKNOWN"
        
        # Track source URLs for each field
        field_sources = {'scheme_page': scheme_url}
        
        # Extract Fund Name
        fund_name = self._extract_fund_name(soup)
        
        # Extract Fund Category
        category = self._extract_fund_category(soup)
        field_sources['category'] = scheme_url
        
        # Extract Latest NAV & NAV Date
        nav_data = self._extract_nav_data(soup)
        current_nav = nav_data[0].nav if nav_data else None
        nav_date = nav_data[0].date if nav_data else None
        field_sources['nav'] = scheme_url
        
        # Extract AUM
        aum = self._extract_aum(soup)
        field_sources['aum'] = scheme_url
        
        # Extract Expense Ratio
        expense_ratio = self._extract_expense_ratio(soup)
        field_sources['expense_ratio'] = scheme_url
        
        # Extract Benchmark
        benchmark = self._extract_benchmark(soup)
        field_sources['benchmark'] = scheme_url
        
        # Extract Inception Date
        inception_date = self._extract_inception_date(soup)
        field_sources['inception_date'] = scheme_url
        
        # Extract Fund Manager(s)
        fund_manager = self._extract_fund_manager(soup)
        field_sources['fund_manager'] = scheme_url
        
        # Extract SIP & Minimum Investment details
        sip_details = self._extract_sip_details(soup)
        min_investment = sip_details.get('min_investment')
        sip_min_investment = sip_details.get('sip_min_investment')
        field_sources['investment_details'] = scheme_url
        
        # Extract Risk Level
        risk_level = self._extract_risk_level(soup)
        field_sources['risk_level'] = scheme_url
        
        # Extract Latest Factsheet URL (PDF)
        factsheet_url = self._extract_factsheet_url(soup, scheme_url)
        if factsheet_url:
            field_sources['factsheet'] = factsheet_url
        
        # Extract Performance (1Y, 3Y, 5Y)
        performance = self._extract_performance(soup)
        field_sources['performance'] = scheme_url
        
        # Extract Official Notices
        notices = self._extract_notices(soup, scheme_url)
        if notices:
            field_sources['notices'] = scheme_url
        
        # Determine scheme type from category
        scheme_type = self._determine_scheme_type(category)
        
        metadata = SchemeMetadata(
            scheme_code=scheme_code,
            scheme_name=fund_name or "Unknown Scheme",
            scheme_type=scheme_type,
            category=category,
            source_url=scheme_url,
            factsheet_url=factsheet_url,
            last_updated=datetime.now(),
            validation_status='pending'
        )
        
        scheme_data = SchemeData(
            metadata=metadata,
            nav_data=nav_data if nav_data else None,
            current_nav=current_nav,
            nav_date=nav_date,
            aum=aum,
            expense_ratio=expense_ratio,
            fund_manager=fund_manager,
            launch_date=inception_date,
            benchmark=benchmark,
            risk_level=risk_level,
            min_investment=min_investment,
            sip_min_investment=sip_min_investment,
            performance=performance,
            notices=notices,
            field_sources=field_sources,
            raw_data={'html_snippet': str(soup)[:10000]}  # Store first 10KB for validation
        )
        
        return scheme_data
    
    def _extract_fund_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract fund name from page"""
        # Try multiple selectors
        selectors = [
            'h1',
            '.fund-name',
            '.scheme-name',
            '[class*="fund-name"]',
            '[class*="scheme-name"]',
            '[id*="fund-name"]',
            '[id*="scheme-name"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 3:
                    return text
        
        # Try title tag
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Remove common suffixes
            title_text = re.sub(r'\s*-\s*Nippon.*$', '', title_text, flags=re.I)
            if title_text:
                return title_text
        
        return None
    
    def _extract_fund_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract fund category (Equity/Debt/Hybrid/ELSS etc.)"""
        text = soup.get_text()
        
        # Look for category in various formats
        category_patterns = [
            r'(?:category|fund\s*category)[:\s]*([A-Za-z\s]+?)(?:\n|$)',
            r'(equity|debt|hybrid|elss|liquid|arbitrage|balanced)',
            r'(large\s*cap|mid\s*cap|small\s*cap|multi\s*cap)',
        ]
        
        for pattern in category_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                category = match.group(1).strip()
                # Capitalize properly
                category = category.title()
                return category
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'category' in key:
                        return value
        
        return None
    
    def _extract_nav_data(self, soup: BeautifulSoup) -> List[NAVData]:
        """Extract NAV data from page"""
        nav_data = []
        
        # Look for NAV in various formats
        text = soup.get_text()
        
        # Pattern 1: NAV: ₹123.45 (as of DD-MM-YYYY)
        nav_patterns = [
            r'NAV[:\s]*₹?\s*([\d,]+\.?\d*)\s*(?:as\s*of|dated|on)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})?',
            r'Net\s*Asset\s*Value[:\s]*₹?\s*([\d,]+\.?\d*)',
            r'Latest\s*NAV[:\s]*₹?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in nav_patterns:
            matches = re.finditer(pattern, text, re.I)
            for match in matches:
                try:
                    nav_value = float(match.group(1).replace(',', ''))
                    nav_date = None
                    if len(match.groups()) > 1 and match.group(2):
                        nav_date = match.group(2)
                    else:
                        # Try to find date nearby
                        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text[max(0, match.start()-50):match.end()+50])
                        if date_match:
                            nav_date = date_match.group(1)
                    
                    if not nav_date:
                        nav_date = datetime.now().strftime('%d-%m-%Y')
                    
                    nav_data.append(NAVData(
                        date=nav_date,
                        nav=nav_value
                    ))
                    break  # Take first match
                except (ValueError, IndexError):
                    continue
        
        # Also look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'nav' in key:
                        nav_match = re.search(r'([\d,]+\.?\d*)', value.replace(',', ''))
                        if nav_match:
                            try:
                                nav_value = float(nav_match.group(1))
                                nav_data.append(NAVData(
                                    date=datetime.now().strftime('%d-%m-%Y'),
                                    nav=nav_value
                                ))
                            except ValueError:
                                pass
        
        return nav_data
    
    def _extract_aum(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract AUM (Assets Under Management)"""
        text = soup.get_text()
        
        # Look for AUM patterns
        aum_patterns = [
            r'AUM[:\s]*₹?\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|Lakh|L)',
            r'Assets\s*Under\s*Management[:\s]*₹?\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
            r'Fund\s*Size[:\s]*₹?\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
        ]
        
        for pattern in aum_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    aum_value = float(match.group(1).replace(',', ''))
                    # Check if in Crore or Lakh
                    if 'lakh' in match.group(0).lower():
                        aum_value = aum_value / 100  # Convert lakh to crore
                    return aum_value
                except ValueError:
                    continue
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'aum' in key or ('assets' in key and 'management' in key):
                        aum_match = re.search(r'([\d,]+\.?\d*)', value.replace(',', ''))
                        if aum_match:
                            try:
                                aum_value = float(aum_match.group(1))
                                if 'lakh' in value.lower():
                                    aum_value = aum_value / 100
                                return aum_value
                            except ValueError:
                                pass
        
        return None
    
    def _extract_expense_ratio(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract expense ratio"""
        text = soup.get_text()
        
        # Look for expense ratio patterns
        expense_patterns = [
            r'Expense\s*Ratio[:\s]*([\d.]+)\s*%?',
            r'Total\s*Expense\s*Ratio[:\s]*([\d.]+)\s*%?',
            r'TER[:\s]*([\d.]+)\s*%?',
        ]
        
        for pattern in expense_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'expense' in key:
                        exp_match = re.search(r'([\d.]+)', value)
                        if exp_match:
                            try:
                                return float(exp_match.group(1))
                            except ValueError:
                                pass
        
        return None
    
    def _extract_benchmark(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract benchmark"""
        text = soup.get_text()
        
        # Look for benchmark patterns
        benchmark_patterns = [
            r'Benchmark[:\s]+([^\n]+)',
            r'Benchmark\s*Index[:\s]+([^\n]+)',
        ]
        
        for pattern in benchmark_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                benchmark = match.group(1).strip()
                # Clean up
                benchmark = re.sub(r'\s+', ' ', benchmark)
                return benchmark[:200]  # Limit length
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'benchmark' in key:
                        return value.strip()
        
        return None
    
    def _extract_inception_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract inception/launch date"""
        text = soup.get_text()
        
        # Look for date patterns
        date_patterns = [
            r'(?:Inception|Launch|Inception\s*Date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Date\s*of\s*Inception[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1)
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'inception' in key or 'launch' in key:
                        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', value)
                        if date_match:
                            return date_match.group(1)
        
        return None
    
    def _extract_fund_manager(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract fund manager(s)"""
        text = soup.get_text()
        
        # Look for fund manager patterns
        manager_patterns = [
            r'Fund\s*Manager[:\s]+([^\n]+)',
            r'Fund\s*Managers?[:\s]+([^\n]+)',
            r'Managed\s*by[:\s]+([^\n]+)',
        ]
        
        for pattern in manager_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                manager = match.group(1).strip()
                # Clean up
                manager = re.sub(r'\s+', ' ', manager)
                return manager[:200]  # Limit length
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'manager' in key:
                        return value.strip()
        
        return None
    
    def _extract_sip_details(self, soup: BeautifulSoup) -> Dict[str, Optional[float]]:
        """Extract SIP and minimum investment details"""
        details = {'min_investment': None, 'sip_min_investment': None}
        text = soup.get_text()
        
        # Look for minimum investment
        min_inv_patterns = [
            r'Minimum\s*Investment[:\s]*₹?\s*([\d,]+)',
            r'Min\s*Investment[:\s]*₹?\s*([\d,]+)',
            r'Initial\s*Investment[:\s]*₹?\s*([\d,]+)',
        ]
        
        for pattern in min_inv_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    details['min_investment'] = float(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        # Look for SIP minimum
        sip_patterns = [
            r'SIP\s*Minimum[:\s]*₹?\s*([\d,]+)',
            r'Minimum\s*SIP[:\s]*₹?\s*([\d,]+)',
            r'Systematic\s*Investment\s*Plan[:\s]*₹?\s*([\d,]+)',
        ]
        
        for pattern in sip_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    details['sip_min_investment'] = float(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'minimum' in key and 'investment' in key and 'sip' not in key:
                        inv_match = re.search(r'([\d,]+)', value.replace(',', ''))
                        if inv_match:
                            try:
                                details['min_investment'] = float(inv_match.group(1))
                            except ValueError:
                                pass
                    elif 'sip' in key and 'minimum' in key:
                        sip_match = re.search(r'([\d,]+)', value.replace(',', ''))
                        if sip_match:
                            try:
                                details['sip_min_investment'] = float(sip_match.group(1))
                            except ValueError:
                                pass
        
        return details
    
    def _extract_risk_level(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract risk level"""
        text = soup.get_text()
        
        # Look for risk level patterns
        risk_patterns = [
            r'Risk\s*Level[:\s]+([^\n]+)',
            r'Risk\s*Profile[:\s]+([^\n]+)',
            r'Riskometer[:\s]+([^\n]+)',
        ]
        
        for pattern in risk_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                risk = match.group(1).strip()
                # Common risk levels
                if re.search(r'low', risk, re.I):
                    return 'Low'
                elif re.search(r'medium|moderate', risk, re.I):
                    return 'Medium'
                elif re.search(r'high', risk, re.I):
                    return 'High'
                return risk[:50]  # Limit length
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'risk' in key:
                        return value.strip()
        
        return None
    
    def _extract_factsheet_url(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract factsheet PDF URL"""
        # Look for PDF links
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf|factsheet', re.I))
        
        for link in pdf_links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True).lower()
            
            # Check if it's a factsheet link
            if 'factsheet' in link_text or 'fact sheet' in link_text or href.endswith('.pdf'):
                full_url = normalize_url(href, base_url)
                if full_url:
                    return full_url
        
        # Also look for factsheet in text and find nearby links
        text = soup.get_text()
        if 'factsheet' in text.lower():
            # Find the factsheet text and look for nearby links
            factsheet_elements = soup.find_all(string=re.compile(r'factsheet', re.I))
            for element in factsheet_elements:
                parent = element.find_parent()
                if parent:
                    link = parent.find('a', href=re.compile(r'\.pdf'))
                    if link:
                        href = link.get('href', '')
                        full_url = normalize_url(href, base_url)
                        if full_url:
                            return full_url
        
        return None
    
    def _extract_performance(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract performance data (1Y, 3Y, 5Y returns)"""
        performance = {}
        text = soup.get_text()
        
        # Look for performance table or section
        # Pattern: 1 Year: 12.34% or 1Y: 12.34%
        perf_patterns = [
            r'(?:1\s*Year|1Y)[:\s]+([\d.]+)\s*%',
            r'(?:3\s*Year|3Y)[:\s]+([\d.]+)\s*%',
            r'(?:5\s*Year|5Y)[:\s]+([\d.]+)\s*%',
        ]
        
        for i, pattern in enumerate(perf_patterns):
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    years = ['1Y', '3Y', '5Y'][i]
                    performance[years] = float(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        # Look in performance tables
        tables = soup.find_all('table')
        for table in tables:
            # Check if this looks like a performance table
            table_text = table.get_text().lower()
            if 'return' in table_text or 'performance' in table_text:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        # Match year patterns
                        if re.search(r'1\s*(?:year|y)', key):
                            perf_match = re.search(r'([\d.]+)', value)
                            if perf_match:
                                try:
                                    performance['1Y'] = float(perf_match.group(1))
                                except ValueError:
                                    pass
                        elif re.search(r'3\s*(?:year|y)', key):
                            perf_match = re.search(r'([\d.]+)', value)
                            if perf_match:
                                try:
                                    performance['3Y'] = float(perf_match.group(1))
                                except ValueError:
                                    pass
                        elif re.search(r'5\s*(?:year|y)', key):
                            perf_match = re.search(r'([\d.]+)', value)
                            if perf_match:
                                try:
                                    performance['5Y'] = float(perf_match.group(1))
                                except ValueError:
                                    pass
        
        return performance if performance else None
    
    def _extract_notices(self, soup: BeautifulSoup, base_url: str) -> Optional[List[Dict[str, Any]]]:
        """Extract official notices"""
        notices = []
        
        # Look for notice sections
        notice_sections = soup.find_all(['div', 'section'], class_=re.compile(r'notice|announcement', re.I))
        
        for section in notice_sections:
            notice_text = section.get_text(strip=True)
            notice_links = section.find_all('a', href=True)
            
            for link in notice_links:
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                notice_url = normalize_url(href, base_url)
                
                if notice_url:
                    notices.append({
                        'title': link_text or 'Notice',
                        'url': notice_url,
                        'text': notice_text[:500] if notice_text else ''
                    })
        
        # Also look for notice links in main content
        notice_links = soup.find_all('a', href=re.compile(r'notice|announcement', re.I))
        for link in notice_links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            notice_url = normalize_url(href, base_url)
            
            if notice_url and link_text:
                notices.append({
                    'title': link_text,
                    'url': notice_url,
                    'text': ''
                })
        
        return notices if notices else None
    
    def _determine_scheme_type(self, category: Optional[str]) -> str:
        """Determine scheme type from category"""
        if not category:
            return 'Unknown'
        
        category_lower = category.lower()
        
        if 'equity' in category_lower or 'elss' in category_lower:
            return 'Equity'
        elif 'debt' in category_lower or 'bond' in category_lower or 'gilt' in category_lower:
            return 'Debt'
        elif 'hybrid' in category_lower or 'balanced' in category_lower or 'multi-asset' in category_lower:
            return 'Hybrid'
        elif 'liquid' in category_lower or 'money market' in category_lower:
            return 'Liquid'
        else:
            return 'Other'
    
    def scrape_factsheet(self, factsheet_url: str, scheme_code: str, scheme_name: str) -> Optional[FactsheetData]:
        """Scrape factsheet page (PDF or HTML)"""
        # Validate URL
        factsheet_url = normalize_url(factsheet_url, self.base_url)
        if not factsheet_url:
            return None
        
        # If PDF, we can't parse it with BeautifulSoup, so we'll store the URL
        if factsheet_url.endswith('.pdf'):
            # For PDFs, we'll just store metadata
            factsheet_data = FactsheetData(
                scheme_code=scheme_code,
                scheme_name=scheme_name,
                source_url=factsheet_url,
                last_updated=datetime.now(),
                content={'type': 'pdf', 'url': factsheet_url},
                raw_text=f"PDF Factsheet: {factsheet_url}"
            )
            return factsheet_data
        
        # If HTML, scrape it
        soup = self._fetch_page(factsheet_url)
        if not soup:
            return None
        
        # Extract factsheet content
        content = {}
        raw_text = soup.get_text(separator=' ', strip=True)
        
        # Try to extract structured data from tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        content[key] = value
        
        factsheet_data = FactsheetData(
            scheme_code=scheme_code,
            scheme_name=scheme_name,
            source_url=factsheet_url,
            last_updated=datetime.now(),
            content=content,
            raw_text=raw_text
        )
        
        return factsheet_data
    
    def scrape_all_schemes(self) -> List[SchemeData]:
        """Scrape all available schemes"""
        schemes_list = self.get_all_schemes_list()
        scraped_schemes = []
        
        print(f"Found {len(schemes_list)} schemes to scrape")
        
        for i, scheme_info in enumerate(schemes_list, 1):
            print(f"Scraping scheme {i}/{len(schemes_list)}: {scheme_info['scheme_name']}")
            
            scheme_data = self.scrape_scheme_page(
                scheme_info['url'],
                scheme_info['scheme_code']
            )
            
            if scheme_data:
                scraped_schemes.append(scheme_data)
            else:
                print(f"  Failed to scrape: {scheme_info['scheme_name']}")
            
            # Be respectful with rate limiting
            time.sleep(1)
        
        return scraped_schemes
    
    def scrape_all_factsheets(self, schemes: List[SchemeData]) -> List[FactsheetData]:
        """Scrape factsheets for all schemes"""
        factsheets = []
        
        for scheme in schemes:
            if scheme.metadata.factsheet_url:
                print(f"Scraping factsheet for {scheme.metadata.scheme_name}")
                
                factsheet = self.scrape_factsheet(
                    str(scheme.metadata.factsheet_url),
                    scheme.metadata.scheme_code,
                    scheme.metadata.scheme_name
                )
                
                if factsheet:
                    factsheets.append(factsheet)
                
                time.sleep(1)
        
        return factsheets
