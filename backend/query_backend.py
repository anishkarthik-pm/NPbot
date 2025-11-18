"""Backend script for answering queries about Nippon India Mutual Fund schemes"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.query_answerer import QueryAnswerer
import config


def answer_query(query: str) -> dict:
    """
    Main function to answer a query about Nippon India Mutual Fund schemes.
    
    Args:
        query: User's question (e.g., "Tell me the latest NAV and date of Nippon India Small Cap Fund?")
    
    Returns:
        Dictionary with answer, source_url, scheme_code, and confidence
    """
    try:
        answerer = QueryAnswerer()
        result = answerer.answer_query(query)
        return result
    except Exception as e:
        return {
            'answer': f"Error processing query: {str(e)}",
            'source_url': "",
            'scheme_code': "",
            'confidence': 'low'
        }


def main():
    """CLI interface for query answering"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NPbot Query Backend')
    parser.add_argument(
        '--query',
        type=str,
        help='Query to answer (e.g., "Tell me the latest NAV and date of Nippon India Small Cap Fund?")'
    )
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='Refresh ChromaDB embeddings'
    )
    
    args = parser.parse_args()
    
    if args.refresh:
        print("Refreshing ChromaDB embeddings...")
        from backend.rag_system import RAGSystem
        rag = RAGSystem()
        rag.refresh_embeddings()
        print("✓ Embeddings refreshed")
        return
    
    if not args.query:
        # Interactive mode
        print("=" * 60)
        print("NPbot Query Backend")
        print("=" * 60)
        print("Enter queries about Nippon India Mutual Fund schemes.")
        print("Type 'exit' to quit.\n")
        
        answerer = QueryAnswerer()
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() in ['exit', 'quit', 'q']:
                    break
                
                if not query:
                    continue
                
                print("\nProcessing query...")
                result = answerer.answer_query(query)
                
                print(f"\nAnswer ({result['confidence']} confidence):")
                print(result['answer'])
                if result['source_url']:
                    print(f"\nSource URL: {result['source_url']}")
                if result['scheme_code']:
                    print(f"Scheme Code: {result['scheme_code']}")
                
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    else:
        # Single query mode
        result = answer_query(args.query)
        print(result['answer'])
        if result['source_url']:
            print(f"\nSource: {result['source_url']}")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY environment variable is required")
        print("Set it with: export OPENROUTER_API_KEY=your_key")
        sys.exit(1)
    
    main()

