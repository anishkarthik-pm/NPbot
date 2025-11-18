"""Main entry point for NPbot"""
import argparse
import sys
import os
from datetime import datetime

import config
from scraper.nippon_scraper import NipponScraper
from scraper.validator import DataValidator
from storage.data_store import DataStore
from scheduler.refresh_job import RefreshScheduler
from query.query_interface import QueryInterface


def scrape_data():
    """Scrape and store all mutual fund data"""
    print("=" * 60)
    print("NPbot - Data Scraping and Storage")
    print("=" * 60)
    print(f"Started at: {datetime.now()}\n")
    
    scraper = NipponScraper()
    validator = DataValidator()
    data_store = DataStore()
    
    # Scrape all schemes
    print("Step 1: Scraping scheme pages...")
    schemes = scraper.scrape_all_schemes()
    print(f"Scraped {len(schemes)} schemes\n")
    
    # Validate and store schemes
    print("Step 2: Validating and storing schemes...")
    for i, scheme in enumerate(schemes, 1):
        print(f"Processing scheme {i}/{len(schemes)}: {scheme.metadata.scheme_name}")
        
        # Validate
        if config.VALIDATION_ENABLED:
            validation_result = validator.validate_scheme(scheme)
            validator.update_validation_status(scheme, validation_result)
            print(f"  Validation: {validation_result['status']}")
        
        # Store scheme
        data_store.store_scheme(scheme)
        
        # Create and store text chunks
        scheme_text = _generate_scheme_text(scheme)
        chunks = data_store.create_text_chunks(
            scheme_code=scheme.metadata.scheme_code,
            content=scheme_text,
            chunk_type="scheme",
            source_url=str(scheme.metadata.source_url),
            metadata={
                'scheme_name': scheme.metadata.scheme_name,
                'scheme_type': scheme.metadata.scheme_type
            }
        )
        data_store.store_text_chunks(chunks)
        print(f"  Stored {len(chunks)} text chunks")
    
    # Scrape factsheets
    print("\nStep 3: Scraping factsheets...")
    factsheets = scraper.scrape_all_factsheets(schemes)
    print(f"Scraped {len(factsheets)} factsheets\n")
    
    # Store factsheets
    print("Step 4: Storing factsheets...")
    for i, factsheet in enumerate(factsheets, 1):
        print(f"Processing factsheet {i}/{len(factsheets)}: {factsheet.scheme_name}")
        data_store.store_factsheet(factsheet)
        
        # Create and store text chunks
        chunks = data_store.create_text_chunks(
            scheme_code=factsheet.scheme_code,
            content=factsheet.raw_text,
            chunk_type="factsheet",
            source_url=str(factsheet.source_url),
            metadata={
                'scheme_name': factsheet.scheme_name
            }
        )
        data_store.store_text_chunks(chunks)
        print(f"  Stored {len(chunks)} text chunks")
    
    # Update metadata
    data_store.update_refresh_timestamp(nav_only=False)
    
    # Print summary
    metadata = data_store.get_metadata()
    print("\n" + "=" * 60)
    print("Scraping Complete!")
    print("=" * 60)
    print(f"Total schemes stored: {metadata.total_schemes}")
    print(f"Total factsheets stored: {metadata.total_factsheets}")
    print(f"Total text chunks: {metadata.total_chunks}")
    print(f"Completed at: {datetime.now()}")


def _generate_scheme_text(scheme):
    """Generate text representation of scheme data"""
    from storage.models import SchemeData
    
    text_parts = [
        f"Scheme Name: {scheme.metadata.scheme_name}",
        f"Scheme Code: {scheme.metadata.scheme_code}",
        f"Scheme Type: {scheme.metadata.scheme_type}",
    ]
    
    if scheme.metadata.category:
        text_parts.append(f"Category: {scheme.metadata.category}")
    
    if scheme.current_nav:
        text_parts.append(f"Current NAV: ₹{scheme.current_nav}")
        if scheme.nav_date:
            text_parts.append(f"NAV Date: {scheme.nav_date}")
    
    if scheme.aum:
        text_parts.append(f"AUM: ₹{scheme.aum} Cr")
    
    if scheme.expense_ratio:
        text_parts.append(f"Expense Ratio: {scheme.expense_ratio}%")
    
    if scheme.fund_manager:
        text_parts.append(f"Fund Manager: {scheme.fund_manager}")
    
    if scheme.launch_date:
        text_parts.append(f"Inception Date: {scheme.launch_date}")
    
    if scheme.benchmark:
        text_parts.append(f"Benchmark: {scheme.benchmark}")
    
    if scheme.risk_level:
        text_parts.append(f"Risk Level: {scheme.risk_level}")
    
    if scheme.min_investment:
        text_parts.append(f"Minimum Investment: ₹{scheme.min_investment}")
    
    if scheme.sip_min_investment:
        text_parts.append(f"SIP Minimum: ₹{scheme.sip_min_investment}")
    
    if scheme.performance:
        for period, value in scheme.performance.items():
            text_parts.append(f"{period} Return: {value}%")
    
    if scheme.portfolio:
        text_parts.append(f"Portfolio: {scheme.portfolio}")
    
    return "\n".join(text_parts)


def run_scheduler():
    """Start the periodic refresh scheduler"""
    print("=" * 60)
    print("NPbot - Periodic Refresh Scheduler")
    print("=" * 60)
    print(f"Started at: {datetime.now()}\n")
    
    scheduler = RefreshScheduler()
    scheduler.start_scheduler()


def query_data():
    """Interactive query interface"""
    print("=" * 60)
    print("NPbot - Query Interface")
    print("=" * 60)
    
    query = QueryInterface()
    
    # Print statistics
    stats = query.get_statistics()
    print("\nStorage Statistics:")
    print(f"  Total Schemes: {stats['total_schemes']}")
    print(f"  Total Factsheets: {stats['total_factsheets']}")
    print(f"  Total Chunks: {stats['total_chunks']}")
    print(f"  Last Full Refresh: {stats['last_full_refresh']}")
    print(f"  Last NAV Update: {stats['last_nav_update']}")
    
    if stats['schemes_by_type']:
        print("\nSchemes by Type:")
        for scheme_type, count in stats['schemes_by_type'].items():
            print(f"  {scheme_type}: {count}")
    
    # Example queries
    print("\nExample: Searching for 'equity' schemes...")
    results = query.search_schemes(query="equity")
    print(f"Found {len(results)} schemes")
    for scheme in results[:5]:  # Show first 5
        print(f"  - {scheme.metadata.scheme_name} ({scheme.metadata.scheme_code})")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NPbot - Nippon India Mutual Fund Data System')
    parser.add_argument(
        '--scrape',
        action='store_true',
        help='Scrape and store all mutual fund data'
    )
    parser.add_argument(
        '--scheduler',
        action='store_true',
        help='Start periodic refresh scheduler'
    )
    parser.add_argument(
        '--query',
        action='store_true',
        help='Run query interface (show statistics)'
    )
    parser.add_argument(
        '--nav-refresh',
        action='store_true',
        help='Run NAV-only refresh (faster)'
    )
    parser.add_argument(
        '--server',
        action='store_true',
        help='Start API server'
    )
    
    args = parser.parse_args()
    
    if args.scrape:
        scrape_data()
    elif args.scheduler:
        run_scheduler()
    elif args.query:
        query_data()
    elif args.nav_refresh:
        scheduler = RefreshScheduler()
        scheduler.run_once(nav_only=True)
    elif args.server:
        import uvicorn
        from api_server import app
        print("Starting NPbot API server...")
        print("API will be available at http://localhost:8000")
        print("API docs at http://localhost:8000/docs")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        parser.print_help()
        sys.exit(1)


async def call_llm(prompt: str) -> str:
    """Call OpenRouter API using OpenAI-compatible client"""
    from openai import OpenAI
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    completion = client.chat.completions.create(
        model="google/gemini-2.0-flash-thinking-exp:free",
        messages=[{"role": "user", "content": prompt}],
    )
    
    return completion.choices[0].message.content


def rag(query: str) -> str:
    """Retrieve context from RAG system for a query"""
    from backend.rag_system import RAGSystem
    
    try:
        rag_system = RAGSystem()
        search_results = rag_system.search(query, n_results=5)
        
        if not search_results:
            return "No relevant information found in the database."
        
        # Build context from search results
        context_parts = []
        for result in search_results[:3]:  # Use top 3 results
            context_parts.append(result['document'])
        
        return "\n\n".join(context_parts)
    except Exception as e:
        print(f"Error in RAG retrieval: {e}")
        return f"Error retrieving context: {str(e)}"


if __name__ == "__main__":
    main()

