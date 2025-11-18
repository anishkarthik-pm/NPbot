"""Standalone script to scrape Nippon India Multi Asset Allocation Fund page"""
import csv
import re
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def fetch_page(url: str) -> BeautifulSoup:
    """Fetch and parse the webpage"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'lxml')
    except Exception as e:
        print(f"Error fetching page: {e}")
        raise


def extract_fund_name(soup: BeautifulSoup) -> str:
    """Extract fund name"""
    # Try multiple selectors
    selectors = ['h1', '.fund-name', '.scheme-name', 'title']
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(strip=True)
            if text and len(text) > 3:
                # Clean up title if needed
                text = re.sub(r'\s*-\s*Nippon.*$', '', text, flags=re.I)
                return text
    return "Unknown Fund"


def extract_nav(soup: BeautifulSoup) -> dict:
    """Extract NAV information"""
    nav_info = {'nav': None, 'nav_date': None}
    text = soup.get_text()
    
    # Look for NAV patterns
    nav_patterns = [
        r'NAV[:\s]*₹?\s*([\d,]+\.?\d*)\s*(?:as\s*of|dated|on)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})?',
        r'Latest\s*NAV[:\s]*₹?\s*([\d,]+\.?\d*)',
        r'Net\s*Asset\s*Value[:\s]*₹?\s*([\d,]+\.?\d*)',
    ]
    
    for pattern in nav_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                nav_value = float(match.group(1).replace(',', ''))
                nav_info['nav'] = nav_value
                if len(match.groups()) > 1 and match.group(2):
                    nav_info['nav_date'] = match.group(2)
                else:
                    # Try to find date nearby
                    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text[max(0, match.start()-50):match.end()+50])
                    if date_match:
                        nav_info['nav_date'] = date_match.group(1)
                break
            except (ValueError, IndexError):
                continue
    
    return nav_info


def extract_fund_details(soup: BeautifulSoup) -> dict:
    """Extract fund details from tables and text"""
    details = {}
    text = soup.get_text()
    
    # Extract from tables
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                
                # Map common fields
                if 'aum' in key or ('assets' in key and 'management' in key):
                    details['aum'] = _parse_amount(value)
                elif 'expense' in key:
                    details['expense_ratio'] = _parse_percentage(value)
                elif 'fund manager' in key or 'manager' in key:
                    details['fund_manager'] = value
                elif 'launch' in key or 'inception' in key:
                    details['inception_date'] = value
                elif 'benchmark' in key:
                    details['benchmark'] = value
                elif 'risk' in key:
                    details['risk_level'] = value
                elif 'minimum' in key and 'investment' in key and 'sip' not in key:
                    details['min_investment'] = _parse_amount(value)
                elif 'sip' in key and 'minimum' in key:
                    details['sip_min'] = _parse_amount(value)
                elif 'category' in key:
                    details['category'] = value
    
    return details


def extract_returns(soup: BeautifulSoup) -> dict:
    """Extract returns data (1Y, 3Y, 5Y)"""
    returns = {}
    text = soup.get_text()
    
    # Look for return patterns
    return_patterns = [
        (r'(?:1\s*Year|1Y)[:\s]+([\d.]+)\s*%', '1Y'),
        (r'(?:3\s*Year|3Y)[:\s]+([\d.]+)\s*%', '3Y'),
        (r'(?:5\s*Year|5Y)[:\s]+([\d.]+)\s*%', '5Y'),
    ]
    
    for pattern, period in return_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                returns[period] = float(match.group(1))
            except ValueError:
                pass
    
    # Also check tables
    tables = soup.find_all('table')
    for table in tables:
        table_text = table.get_text().lower()
        if 'return' in table_text or 'performance' in table_text:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if re.search(r'1\s*(?:year|y)', key):
                        ret_match = re.search(r'([\d.]+)', value)
                        if ret_match:
                            try:
                                returns['1Y'] = float(ret_match.group(1))
                            except ValueError:
                                pass
                    elif re.search(r'3\s*(?:year|y)', key):
                        ret_match = re.search(r'([\d.]+)', value)
                        if ret_match:
                            try:
                                returns['3Y'] = float(ret_match.group(1))
                            except ValueError:
                                pass
                    elif re.search(r'5\s*(?:year|y)', key):
                        ret_match = re.search(r'([\d.]+)', value)
                        if ret_match:
                            try:
                                returns['5Y'] = float(ret_match.group(1))
                            except ValueError:
                                pass
    
    return returns


def extract_key_facts(soup: BeautifulSoup) -> dict:
    """Extract key facts about the fund"""
    facts = {}
    text = soup.get_text()
    
    # Extract scheme code if available
    code_match = re.search(r'(?:scheme\s*code|fund\s*code)[:\s]*(\d{6})', text, re.I)
    if code_match:
        facts['scheme_code'] = code_match.group(1)
    
    # Extract fund type/category
    if 'equity' in text.lower():
        facts['fund_type'] = 'Equity'
    elif 'debt' in text.lower() or 'bond' in text.lower():
        facts['fund_type'] = 'Debt'
    elif 'hybrid' in text.lower() or 'multi-asset' in text.lower():
        facts['fund_type'] = 'Hybrid'
    else:
        facts['fund_type'] = 'Other'
    
    return facts


def _parse_amount(text: str) -> float:
    """Parse amount from text"""
    match = re.search(r'([\d,]+\.?\d*)', text.replace(',', ''))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def _parse_percentage(text: str) -> float:
    """Parse percentage from text"""
    match = re.search(r'([\d.]+)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def save_to_csv(data: dict, filepath: Path):
    """Save extracted data to CSV file"""
    # Ensure directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare CSV row
    row = {
        'fund_name': data.get('fund_name', ''),
        'scheme_code': data.get('scheme_code', ''),
        'fund_type': data.get('fund_type', ''),
        'category': data.get('category', ''),
        'nav': data.get('nav', ''),
        'nav_date': data.get('nav_date', ''),
        'aum_cr': data.get('aum', ''),
        'expense_ratio': data.get('expense_ratio', ''),
        'fund_manager': data.get('fund_manager', ''),
        'inception_date': data.get('inception_date', ''),
        'benchmark': data.get('benchmark', ''),
        'risk_level': data.get('risk_level', ''),
        'min_investment': data.get('min_investment', ''),
        'sip_min': data.get('sip_min', ''),
        'return_1y': data.get('returns', {}).get('1Y', ''),
        'return_3y': data.get('returns', {}).get('3Y', ''),
        'return_5y': data.get('returns', {}).get('5Y', ''),
        'source_url': data.get('source_url', ''),
        'scraped_at': data.get('scraped_at', ''),
    }
    
    # Check if file exists to determine if we need headers
    file_exists = filepath.exists()
    
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        fieldnames = [
            'fund_name', 'scheme_code', 'fund_type', 'category',
            'nav', 'nav_date', 'aum_cr', 'expense_ratio',
            'fund_manager', 'inception_date', 'benchmark', 'risk_level',
            'min_investment', 'sip_min',
            'return_1y', 'return_3y', 'return_5y',
            'source_url', 'scraped_at'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(row)
    
    print(f"✓ Data saved to {filepath}")


def main():
    """Main scraping function"""
    url = "https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Multi-Asset-Allocation-F"
    
    print("=" * 60)
    print("Nippon India Fund Scraper")
    print("=" * 60)
    print(f"URL: {url}\n")
    
    # Fetch page
    print("Step 1: Fetching page...")
    soup = fetch_page(url)
    print("✓ Page fetched successfully\n")
    
    # Extract data
    print("Step 2: Extracting data...")
    
    fund_name = extract_fund_name(soup)
    print(f"  Fund Name: {fund_name}")
    
    nav_info = extract_nav(soup)
    print(f"  NAV: ₹{nav_info['nav']}" if nav_info['nav'] else "  NAV: Not found")
    print(f"  NAV Date: {nav_info['nav_date']}" if nav_info['nav_date'] else "  NAV Date: Not found")
    
    fund_details = extract_fund_details(soup)
    print(f"  AUM: ₹{fund_details.get('aum', 'N/A')} Cr" if fund_details.get('aum') else "  AUM: Not found")
    print(f"  Expense Ratio: {fund_details.get('expense_ratio', 'N/A')}%" if fund_details.get('expense_ratio') else "  Expense Ratio: Not found")
    print(f"  Fund Manager: {fund_details.get('fund_manager', 'N/A')}" if fund_details.get('fund_manager') else "  Fund Manager: Not found")
    
    returns = extract_returns(soup)
    if returns:
        print(f"  Returns: {returns}")
    else:
        print("  Returns: Not found")
    
    key_facts = extract_key_facts(soup)
    print(f"  Fund Type: {key_facts.get('fund_type', 'N/A')}")
    print(f"  Scheme Code: {key_facts.get('scheme_code', 'N/A')}")
    
    # Combine all data
    all_data = {
        'fund_name': fund_name,
        'scheme_code': key_facts.get('scheme_code', ''),
        'fund_type': key_facts.get('fund_type', ''),
        'category': fund_details.get('category', ''),
        'nav': nav_info['nav'],
        'nav_date': nav_info['nav_date'],
        'aum': fund_details.get('aum'),
        'expense_ratio': fund_details.get('expense_ratio'),
        'fund_manager': fund_details.get('fund_manager', ''),
        'inception_date': fund_details.get('inception_date', ''),
        'benchmark': fund_details.get('benchmark', ''),
        'risk_level': fund_details.get('risk_level', ''),
        'min_investment': fund_details.get('min_investment'),
        'sip_min': fund_details.get('sip_min'),
        'returns': returns,
        'source_url': url,
        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    print("\nStep 3: Saving to CSV...")
    
    # Save to CSV
    data_dir = Path('data')
    csv_file = data_dir / 'nippon_fund_facts.csv'
    save_to_csv(all_data, csv_file)
    
    print("\n" + "=" * 60)
    print("Scraping Complete!")
    print("=" * 60)
    print(f"Data saved to: {csv_file}")


if __name__ == "__main__":
    main()

