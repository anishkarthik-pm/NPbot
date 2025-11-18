# NPbot Backend - Query Answering System

## Overview

The backend system answers factual queries about Nippon India Mutual Fund schemes using RAG (Retrieval-Augmented Generation) with ChromaDB embeddings and OpenRouter API.

## Features

- ✅ Loads pre-scraped JSON scheme data
- ✅ Creates ChromaDB embeddings for all schemes
- ✅ Uses RAG for answering queries
- ✅ Integrates with OpenRouter API
- ✅ Ensures every answer includes exactly one official source URL
- ✅ Rejects answers with fake/demo data
- ✅ Returns short factual answers only (no advice)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file or set environment variables:

```bash
export OPENROUTER_API_KEY=your_openrouter_api_key
export OPENROUTER_MODEL=openai/gpt-4o-mini  # Optional, defaults to gpt-4o-mini
```

### 3. Ensure Data is Scraped

Before using the backend, ensure you have scraped data:

```bash
python main.py --scrape
```

## Usage

### Command Line Interface

#### Interactive Mode

```bash
python backend/query_backend.py
```

Then enter queries like:
- "Tell me the latest NAV and date of Nippon India Small Cap Fund?"
- "What is the expense ratio of Nippon India Large Cap Fund?"
- "Who is the fund manager of Nippon India Multi Asset Allocation Fund?"

#### Single Query Mode

```bash
python backend/query_backend.py --query "Tell me the latest NAV and date of Nippon India Small Cap Fund?"
```

#### Refresh Embeddings

After scraping new data, refresh embeddings:

```bash
python backend/query_backend.py --refresh
```

### Python API

```python
from backend.query_answerer import QueryAnswerer

answerer = QueryAnswerer()
result = answerer.answer_query("Tell me the latest NAV and date of Nippon India Small Cap Fund?")

print(result['answer'])
print(f"Source: {result['source_url']}")
print(f"Confidence: {result['confidence']}")
```

## Response Format

Every response includes:

```python
{
    'answer': str,        # Factual answer with source URL
    'source_url': str,    # Official source URL (validated)
    'scheme_code': str,   # Scheme code if applicable
    'confidence': str      # 'high', 'medium', or 'low'
}
```

## Source URL Validation

- All source URLs are validated against official domains:
  - `mf.nipponindiaim.com`
  - `nipponindiaim.com`
  - `amfiindia.com`
  - `sebi.gov.in`
- Answers without valid source URLs are rejected
- Every answer includes exactly one official source URL

## Fake Data Detection

The system rejects answers containing:
- Demo/test data
- Placeholder values
- Example data
- Invalid indicators

## Architecture

```
Query → RAG System → ChromaDB Search → OpenRouter API → Validated Answer
         ↓
    Data Loader → Pre-scraped JSON → Formatted Context
```

### Components

1. **DataLoader** (`backend/data_loader.py`)
   - Loads pre-scraped JSON scheme data
   - Formats data for embedding
   - Provides source URL tracking

2. **RAGSystem** (`backend/rag_system.py`)
   - Manages ChromaDB collection
   - Creates embeddings for schemes
   - Searches relevant documents
   - Generates answers using OpenRouter API

3. **QueryAnswerer** (`backend/query_answerer.py`)
   - Main interface for answering queries
   - Validates source URLs
   - Detects fake data
   - Ensures factual answers only

## Example Queries

### NAV Query
**Query:** "Tell me the latest NAV and date of Nippon India Small Cap Fund?"

**Response:**
```
The latest NAV for Nippon India Small Cap Fund is ₹125.45 as of 15-01-2024.

Source: https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Small-Cap-Fund
```

### Expense Ratio Query
**Query:** "What is the expense ratio of Nippon India Large Cap Fund?"

**Response:**
```
The expense ratio of Nippon India Large Cap Fund is 1.25%.

Source: https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Large-Cap-Fund
```

### Fund Manager Query
**Query:** "Who manages Nippon India Multi Asset Allocation Fund?"

**Response:**
```
Nippon India Multi Asset Allocation Fund is managed by John Doe.

Source: https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-Multi-Asset-Allocation-F
```

## Error Handling

- **No data:** Returns message asking to scrape data first
- **Invalid source URL:** Rejects answer and reports data integrity issue
- **OpenRouter API error:** Falls back to constructing answer from search results
- **Fake data detected:** Rejects answer and asks to verify data source

## Configuration

Edit `config.py` to adjust:
- ChromaDB storage path
- Number of search results
- OpenRouter model (via environment variable)

## Notes

- Answers are kept brief (max 2-3 sentences)
- No investment advice is provided
- All data comes from pre-scraped official sources
- Source URLs are always validated before inclusion

