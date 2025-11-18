"""Test script for backend query answering"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.query_answerer import QueryAnswerer


def test_backend():
    """Test the backend query answering system"""
    print("=" * 60)
    print("NPbot Backend Test")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("\nERROR: OPENROUTER_API_KEY environment variable is required")
        print("Set it with: export OPENROUTER_API_KEY=your_key")
        print("\nOr create a .env file with:")
        print("OPENROUTER_API_KEY=your_key")
        return
    
    print("\nInitializing Query Answerer...")
    try:
        answerer = QueryAnswerer()
        print("✓ Query Answerer initialized")
    except Exception as e:
        print(f"✗ Error initializing: {e}")
        print("\nMake sure you have:")
        print("1. Scraped data (run: python main.py --scrape)")
        print("2. Set OPENROUTER_API_KEY environment variable")
        return
    
    # Test queries
    test_queries = [
        "Tell me the latest NAV and date of Nippon India Small Cap Fund?",
        "What is the expense ratio of Nippon India Large Cap Fund?",
        "Who is the fund manager of Nippon India Multi Asset Allocation Fund?",
    ]
    
    print("\n" + "=" * 60)
    print("Testing Queries")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query}")
        print("-" * 60)
        
        try:
            result = answerer.answer_query(query)
            
            print(f"\nAnswer ({result['confidence']} confidence):")
            print(result['answer'])
            
            if result['source_url']:
                print(f"\nSource URL: {result['source_url']}")
            
            if result['scheme_code']:
                print(f"Scheme Code: {result['scheme_code']}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_backend()

