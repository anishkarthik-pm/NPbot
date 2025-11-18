# Nippon India Mutual Fund Scraping Guide

## Overview

The scraper has been updated to extract all required fields from the official Nippon India Mutual Fund website (`mf.nipponindiaim.com`). All data is validated and tied to official source URLs.

## Extracted Fields

The scraper extracts the following fields from each scheme page:

1. **Fund Name** - Full name of the mutual fund scheme
2. **Fund Category** - Equity/Debt/Hybrid/ELSS etc.
3. **Scheme Code** - Unique scheme identifier
4. **Latest NAV & NAV Date** - Current Net Asset Value and date
5. **AUM** - Assets Under Management (in Crores)
6. **Expense Ratio** - Total Expense Ratio percentage
7. **Benchmark** - Benchmark index name
8. **Inception Date** - Fund launch date
9. **Fund Manager(s)** - Name(s) of fund manager(s)
10. **SIP & Minimum Investment** - Minimum investment amounts
11. **Risk Level** - Risk profile (Low/Medium/High)
12. **Latest Factsheet URL** - PDF or HTML factsheet link
13. **Scheme Webpage URL** - Official scheme page URL
14. **Performance** - 1Y, 3Y, 5Y returns
15. **Official Notices** - Any notices or announcements
16. **Last Updated Timestamp** - When data was scraped

## URL Validation

All URLs are validated to ensure they come from official domains only:
- `mf.nipponindiaim.com`
- `nipponindiaim.com`
- `amfiindia.com`
- `sebi.gov.in`

**No fake or demo URLs are allowed.** The system will reject any URL not from these domains.

## Field Source Tracking

Each field is tracked with its source URL in the `field_sources` dictionary:
```python
{
    'scheme_page': 'https://mf.nipponindiaim.com/...',
    'category': 'https://mf.nipponindiaim.com/...',
    'nav': 'https://mf.nipponindiaim.com/...',
    'factsheet': 'https://mf.nipponindiaim.com/.../factsheet.pdf',
    ...
}
```

## Data Validation

All scraped data is validated against the official website:
- Scheme name is checked against page content
- NAV values are verified (within 1% tolerance)
- Scheme type is cross-checked
- Validation status is stored: `valid`, `partial`, `invalid`, or `error`

## Usage

### Test Single Scheme Scraping

Test the scraper with the example URL:
```bash
python test_scraper.py
```

This will:
1. Scrape the example scheme page
2. Extract all fields
3. Validate data against official website
4. Store the data with source URLs
5. Display extracted information

### Scrape All Schemes

Scrape all available schemes:
```bash
python main.py --scrape
```

### Run Periodic Refresh

Start the scheduler for daily NAV updates:
```bash
python main.py --scheduler
```

### Query Stored Data

Query stored data (no live scraping):
```bash
python main.py --query
```

## Example Output

When scraping a scheme, you'll see:
```
Extracted Fields:
  Fund Name: Nippon India Multi Asset Allocation Fund
  Fund Category: Hybrid
  Scheme Code: 123456
  Latest NAV: ₹25.45
  NAV Date: 15-01-2024
  AUM: ₹1250.50 Cr
  Expense Ratio: 1.25%
  Benchmark: NIFTY 50
  Inception Date: 01-01-2020
  Fund Manager: John Doe
  Minimum Investment: ₹5000
  SIP Minimum: ₹1000
  Risk Level: Medium
  Factsheet URL: https://mf.nipponindiaim.com/.../factsheet.pdf
  Scheme Webpage URL: https://mf.nipponindiaim.com/...

Field Sources (all validated from official website):
  scheme_page: https://mf.nipponindiaim.com/...
  category: https://mf.nipponindiaim.com/...
  nav: https://mf.nipponindiaim.com/...
  ...
```

## Data Storage

All data is stored in the `data/` directory:
- `schemes/` - Individual scheme JSON files with all fields
- `factsheets/` - Factsheet data
- `chunks/` - Text chunks for search
- `metadata.json` - Index of all schemes with source URLs

Each scheme JSON includes:
- All extracted fields
- `field_sources` - Source URL for each field
- `validation_status` - Validation result
- `last_updated` - Timestamp
- `raw_data` - HTML snippet for validation

## Validation Requirements

As per requirements:
- **All data must be validated directly from the website**
- **Every stored value is tied to its source URL**
- **No invalid or demo URLs allowed**
- **Only official pages from allowed domains**

Example validation message:
> "As per the actual website, the latest NAV for XYZ Fund matches the values displayed on the official Nippon India MF website."

## Troubleshooting

### Scheme Discovery Issues

If the scraper can't find schemes automatically:
1. Check the `SCHEMES_LIST_URL` in `config.py`
2. Verify the website structure hasn't changed
3. Manually provide scheme URLs if needed

### Extraction Issues

If fields are not being extracted:
1. Check the website HTML structure
2. Update extraction patterns in `scraper/nippon_scraper.py`
3. Verify the page is accessible

### Validation Failures

If validation fails:
1. Check internet connection
2. Verify the official website is accessible
3. Check if the page structure has changed
4. Review validation results in stored data

## Next Steps

1. **Test with example URL**: Run `python test_scraper.py`
2. **Scrape all schemes**: Run `python main.py --scrape`
3. **Set up scheduler**: Run `python main.py --scheduler` for daily updates
4. **Query data**: Use `QueryInterface` to retrieve stored data

All data is precomputed and stored, so queries are fast and don't require live scraping!

