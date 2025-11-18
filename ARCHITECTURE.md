# NPbot Architecture

## Overview

NPbot is a data precomputation system for Nippon India Mutual Fund data. It scrapes, validates, stores, and serves mutual fund information without performing live scraping during query time.

## System Components

### 1. Scraper Module (`scraper/`)

**Purpose**: Scrapes official Nippon India Mutual Fund pages

**Components**:
- `nippon_scraper.py`: Main scraper for scheme pages and factsheets
  - `get_all_schemes_list()`: Discovers all available schemes
  - `scrape_scheme_page()`: Scrapes individual scheme pages
  - `scrape_factsheet()`: Scrapes factsheet pages
  - Extracts: NAV, AUM, expense ratio, fund manager, returns, portfolio, etc.

- `validator.py`: Validates scraped data against official website
  - `validate_scheme()`: Cross-validates scheme data
  - Checks: scheme name, NAV values, scheme type
  - Updates validation status in stored data

### 2. Storage Module (`storage/`)

**Purpose**: Manages structured data storage

**Components**:
- `models.py`: Pydantic models for data structures
  - `SchemeData`: Complete scheme information
  - `SchemeMetadata`: Scheme metadata with source URLs
  - `FactsheetData`: Factsheet content
  - `TextChunk`: Text chunks for search/retrieval
  - `StorageMetadata`: Overall storage statistics

- `data_store.py`: Storage operations
  - `store_scheme()`: Stores scheme as JSON
  - `store_factsheet()`: Stores factsheet as JSON
  - `store_text_chunks()`: Stores text chunks
  - `create_text_chunks()`: Splits content into searchable chunks
  - `get_scheme()`: Retrieves stored scheme
  - `get_all_schemes()`: Retrieves all schemes

**Storage Structure**:
```
data/
├── schemes/          # Individual scheme JSON files
├── factsheets/       # Factsheet JSON files
├── chunks/           # Text chunk JSON files
└── metadata.json     # Index and statistics
```

### 3. Scheduler Module (`scheduler/`)

**Purpose**: Manages periodic data refresh

**Components**:
- `refresh_job.py`: Periodic refresh scheduler
  - `full_refresh()`: Complete data refresh (all schemes + factsheets)
  - `nav_refresh()`: Fast NAV-only update
  - `start_scheduler()`: Runs scheduled jobs
    - Daily NAV refresh at configured time (default: 2 AM)
    - Weekly full refresh on Sunday

**Schedule**:
- **Daily**: NAV updates (lightweight, fast)
- **Weekly**: Full refresh (comprehensive, slower)

### 4. Query Module (`query/`)

**Purpose**: Query interface for stored data (no live scraping)

**Components**:
- `query_interface.py`: Query operations
  - `search_schemes()`: Search by query, type, category
  - `get_scheme()`: Get specific scheme by code
  - `get_factsheet()`: Get factsheet for scheme
  - `search_chunks()`: Search text chunks
  - `get_nav_data()`: Get NAV information
  - `get_statistics()`: Get storage statistics

**Key Feature**: All queries operate on precomputed stored data only.

### 5. Configuration (`config.py`)

**Settings**:
- URLs: Nippon India Mutual Fund base URLs
- Scraping: Timeouts, retries, user agent
- Storage: Chunk size, overlap
- Scheduler: Refresh times
- Validation: Enable/disable validation

## Data Flow

### Initial Scraping
1. `main.py --scrape` triggers scraping
2. Scraper discovers all schemes
3. For each scheme:
   - Scrape scheme page
   - Validate data (optional)
   - Store as JSON
   - Generate text chunks
   - Store chunks
4. Scrape factsheets
5. Store factsheets and chunks
6. Update metadata

### Periodic Refresh
1. Scheduler runs at configured time
2. **NAV Refresh** (daily):
   - Load all stored schemes
   - Re-scrape NAV data only
   - Update stored schemes
3. **Full Refresh** (weekly):
   - Complete re-scraping of all data
   - Re-validation
   - Update all stored data

### Query Time
1. User queries via `QueryInterface`
2. System retrieves from stored JSON files
3. No live scraping performed
4. Fast response times

## Data Validation

Validation process:
1. Scraper extracts data from official page
2. Validator fetches same page
3. Cross-checks:
   - Scheme name presence
   - NAV value accuracy (within 1%)
   - Scheme type consistency
4. Updates validation status in stored data

## Text Chunking

Text chunks enable semantic search:
- **Chunk Size**: 1000 characters (configurable)
- **Overlap**: 200 characters between chunks
- **Types**: "scheme" or "factsheet"
- **Metadata**: Includes scheme code, type, source URL

## Storage Format

### Scheme JSON Structure
```json
{
  "metadata": {
    "scheme_code": "123456",
    "scheme_name": "Scheme Name",
    "scheme_type": "Equity",
    "category": "Large Cap",
    "source_url": "https://...",
    "factsheet_url": "https://...",
    "last_updated": "2024-01-01T00:00:00",
    "validation_status": "valid"
  },
  "current_nav": 123.45,
  "nav_date": "01-01-2024",
  "aum": 1000.5,
  "expense_ratio": 1.2,
  ...
}
```

### Text Chunk Structure
```json
{
  "chunk_id": "abc123...",
  "scheme_code": "123456",
  "chunk_type": "scheme",
  "content": "Scheme Name: ...",
  "metadata": {...},
  "source_url": "https://...",
  "created_at": "2024-01-01T00:00:00"
}
```

## Usage Examples

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Scrape all data
python main.py --scrape
```

### Run Scheduler
```bash
# Start periodic refresh scheduler
python main.py --scheduler
```

### Query Data
```python
from query.query_interface import QueryInterface

query = QueryInterface()
schemes = query.search_schemes(query="equity")
nav_data = query.get_nav_data("123456")
```

## Error Handling

- **Retry Logic**: Automatic retries with exponential backoff
- **Graceful Degradation**: Continues processing if individual items fail
- **Validation Errors**: Tracked in validation_status field
- **Storage Errors**: Logged but don't stop batch processing

## Performance Considerations

- **Rate Limiting**: 1 second delay between requests
- **Caching**: All data stored locally, no repeated scraping
- **Incremental Updates**: NAV refresh only updates changed data
- **Parallel Processing**: Can be extended for concurrent scraping

## Future Enhancements

- Vector embeddings for semantic search
- Database backend (PostgreSQL/MongoDB)
- API server for remote queries
- Webhook notifications for NAV updates
- Advanced analytics and reporting

