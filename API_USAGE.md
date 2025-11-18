# NPbot API Usage Guide

## Overview

The NPbot API provides an `/ask` endpoint for answering queries about Nippon India Mutual Fund schemes using RAG (Retrieval-Augmented Generation).

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export OPENROUTER_API_KEY=your_openrouter_api_key
```

Or create a `.env` file:
```
OPENROUTER_API_KEY=your_openrouter_api_key
```

### 3. Ensure Data is Scraped

Before using the API, ensure you have scraped data:

```bash
python main.py --scrape
```

## Starting the Server

### Option 1: Using main.py

```bash
python main.py --server
```

### Option 2: Direct API Server

```bash
python api_server.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### GET `/`

Root endpoint with API information.

**Response:**
```json
{
  "message": "NPbot API - Nippon India Mutual Fund Query Service",
  "endpoints": {
    "/ask": "POST - Answer queries about mutual fund schemes",
    "/health": "GET - Health check"
  }
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "openrouter_api_key_set": true,
  "message": "API is operational"
}
```

### POST `/ask`

Answer a query about Nippon India Mutual Fund schemes.

**Request Body:**
```json
{
  "query": "Tell me the latest NAV and date of Nippon India Small Cap Fund?"
}
```

**Response:**
```json
{
  "answer": "The latest NAV for Nippon India Small Cap Fund is ₹125.45 as of 15-01-2024."
}
```

## Usage Examples

### Using cURL

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me the latest NAV and date of Nippon India Small Cap Fund?"}'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={"query": "Tell me the latest NAV and date of Nippon India Small Cap Fund?"}
)

print(response.json()["answer"])
```

### Using JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/ask', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'Tell me the latest NAV and date of Nippon India Small Cap Fund?'
  })
});

const data = await response.json();
console.log(data.answer);
```

## How It Works

1. **Query Received**: The `/ask` endpoint receives a query
2. **RAG Retrieval**: The `rag(query)` function searches ChromaDB for relevant context
3. **Prompt Construction**: A prompt is created with the query and retrieved context
4. **LLM Call**: The `call_llm(prompt)` function calls OpenRouter API with Gemini model
5. **Response**: The answer is returned to the client

## Example Queries

- "Tell me the latest NAV and date of Nippon India Small Cap Fund?"
- "What is the expense ratio of Nippon India Large Cap Fund?"
- "Who is the fund manager of Nippon India Multi Asset Allocation Fund?"
- "What is the AUM of Nippon India Equity Hybrid Fund?"
- "What is the risk level of Nippon India Debt Fund?"

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid query)
- `500`: Internal Server Error (configuration or processing error)

## Configuration

The API uses:
- **Model**: `google/gemini-2.0-flash-thinking-exp:free` (via OpenRouter)
- **RAG Results**: Top 3 most relevant documents
- **Context**: Retrieved from pre-scraped ChromaDB embeddings

## Notes

- All answers are based on pre-scraped data from official Nippon India Mutual Fund website
- The system uses RAG to retrieve relevant context before generating answers
- Answers are concise and factual (no investment advice)
- Source URLs are included in the context data

