"""Example usage of NPbot query interface"""
from query.query_interface import QueryInterface

# Initialize query interface
query = QueryInterface()

# Get statistics
print("=== Storage Statistics ===")
stats = query.get_statistics()
print(f"Total Schemes: {stats['total_schemes']}")
print(f"Total Factsheets: {stats['total_factsheets']}")
print(f"Total Chunks: {stats['total_chunks']}")
print(f"Last Full Refresh: {stats['last_full_refresh']}")
print(f"Last NAV Update: {stats['last_nav_update']}")
print()

# Search for schemes
print("=== Searching for 'Equity' schemes ===")
equity_schemes = query.search_schemes(query="equity")
print(f"Found {len(equity_schemes)} equity schemes")
for scheme in equity_schemes[:5]:  # Show first 5
    print(f"  - {scheme.metadata.scheme_name} ({scheme.metadata.scheme_code})")
    if scheme.current_nav:
        print(f"    NAV: ₹{scheme.current_nav} (as of {scheme.nav_date})")
print()

# Get NAV data for all schemes
print("=== NAV Data ===")
nav_data = query.get_all_nav_data()
print(f"Retrieved NAV data for {len(nav_data)} schemes")
for nav in nav_data[:3]:  # Show first 3
    print(f"  {nav['scheme_name']}: ₹{nav['current_nav']} (as of {nav['nav_date']})")
print()

# Get schemes by type
print("=== Schemes by Type ===")
if stats['schemes_by_type']:
    for scheme_type, count in stats['schemes_by_type'].items():
        print(f"{scheme_type}: {count} schemes")
print()

# Search text chunks
print("=== Searching Text Chunks ===")
chunks = query.search_chunks("NAV", chunk_type="scheme")
print(f"Found {len(chunks)} chunks containing 'NAV'")
for chunk in chunks[:3]:  # Show first 3
    print(f"  Chunk from {chunk.scheme_code}: {chunk.content[:100]}...")

