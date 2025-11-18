"""FastAPI server for NPbot query answering"""
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from main import call_llm, rag

app = FastAPI(title="NPbot API", description="Nippon India Mutual Fund Query API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """Request model for query"""
    query: str


class QueryResponse(BaseModel):
    """Response model for query"""
    answer: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "NPbot API - Nippon India Mutual Fund Query Service",
        "endpoints": {
            "/ask": "POST - Answer queries about mutual fund schemes",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    # Check if required environment variables are set
    api_key_set = bool(os.getenv("OPENROUTER_API_KEY"))
    
    return {
        "status": "healthy" if api_key_set else "degraded",
        "openrouter_api_key_set": api_key_set,
        "message": "API is operational" if api_key_set else "OPENROUTER_API_KEY not set"
    }


@app.post("/ask", response_model=QueryResponse)
async def ask_query(request: QueryRequest):
    """
    Answer a query about Nippon India Mutual Fund schemes.
    
    Example:
    {
        "query": "Tell me the latest NAV and date of Nippon India Small Cap Fund?"
    }
    """
    if not request.query or len(request.query.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Query must be at least 3 characters long"
        )
    
    query = request.query.strip()
    
    try:
        # Get context from RAG system
        context = rag(query)
        
        # Create prompt
        prompt = f"""You are a Mutual Fund FAQ assistant for Nippon AMC.

Question: {query}

Use only the following data:
{context}

Answer clearly and concisely.
"""
        
        # Call LLM
        response = await call_llm(prompt)
        
        return {"answer": response}
    
    except ValueError as e:
        # Missing API key or configuration error
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        # Other errors
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    # Check for required environment variables
    if not os.getenv("OPENROUTER_API_KEY"):
        print("WARNING: OPENROUTER_API_KEY environment variable is not set")
        print("The API will not function properly without it.")
        print("Set it with: export OPENROUTER_API_KEY=your_key")
        print()
    
    # Run the server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

