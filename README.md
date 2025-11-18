# NPbot - Nippon India Mutual Fund Data Precomputation System

A system for precomputing and storing Nippon India Mutual Fund data from official sources.

## Features

- **Web Scraping**: Scrapes all official Nippon India Mutual Fund scheme pages and factsheets
- **Data Validation**: Validates each field using the official website
- **Structured Storage**: Stores data as structured JSON + text chunks + source URL
- **Periodic Refresh**: Daily refresh job for NAV updates and data synchronization
- **Query Interface**: Query-time retrieval from stored data (no live scraping)

## Project Structure

```
NPbot/
├── scraper/
│   ├── __init__.py
│   ├── nippon_scraper.py      # Main scraper for scheme pages and factsheets
│   └── validator.py            # Data validation against official website
├── storage/
│   ├── __init__.py
│   ├── data_store.py           # Storage system for JSON + text chunks
│   └── models.py               # Data models/schemas
├── scheduler/
│   ├── __init__.py
│   └── refresh_job.py          # Periodic refresh job scheduler
├── query/
│   ├── __init__.py
│   └── query_interface.py     # Query interface for stored data
├── config.py                   # Configuration settings
├── main.py                     # Main entry point
└── requirements.txt
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure settings in `config.py` or via environment variables

3. Run initial data collection:
```bash
python main.py --scrape
```

4. Start the periodic refresh scheduler:
```bash
python main.py --scheduler
```

## Usage

### Scrape Data
```bash
python main.py --scrape
```

### Run Scheduler
```bash
python main.py --scheduler
```

### Query Stored Data
```python
from query.query_interface import QueryInterface

query = QueryInterface()
results = query.search("equity fund")
```

## Data Storage

Data is stored in the `data/` directory:
- `schemes/` - Individual scheme JSON files
- `factsheets/` - Factsheet JSON files
- `chunks/` - Text chunks for search
- `metadata.json` - Index of all stored data with source URLs

