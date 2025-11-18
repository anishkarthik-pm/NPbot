"""Configuration settings for NPbot"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SCHEMES_DIR = DATA_DIR / "schemes"
FACTSHEETS_DIR = DATA_DIR / "factsheets"
CHUNKS_DIR = DATA_DIR / "chunks"
METADATA_FILE = DATA_DIR / "metadata.json"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
SCHEMES_DIR.mkdir(exist_ok=True)
FACTSHEETS_DIR.mkdir(exist_ok=True)
CHUNKS_DIR.mkdir(exist_ok=True)

# Nippon India Mutual Fund URLs - Official domains only
NIPPON_BASE_URL = "https://mf.nipponindiaim.com"
NIPPON_MAIN_URL = "https://www.nipponindiaim.com"
SCHEMES_LIST_URL = f"{NIPPON_BASE_URL}/FundsAndPerformance/Pages/Fund-Listing.aspx"
FACTSHEET_BASE_URL = f"{NIPPON_BASE_URL}/FundsAndPerformance/Pages"

# Official domains allowed for validation
ALLOWED_DOMAINS = [
    "mf.nipponindiaim.com",
    "nipponindiaim.com",
    "amfiindia.com",
    "sebi.gov.in"
]

# Scraping settings
REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Scheduler settings
REFRESH_HOUR = int(os.getenv("REFRESH_HOUR", "2"))  # 2 AM default
REFRESH_MINUTE = int(os.getenv("REFRESH_MINUTE", "0"))
NAV_UPDATE_INTERVAL_HOURS = 24

# Storage settings
CHUNK_SIZE = 1000  # characters per text chunk
CHUNK_OVERLAP = 200  # characters overlap between chunks

# Validation settings
VALIDATION_ENABLED = True
VALIDATION_TIMEOUT = 10

# Backend/RAG settings
CHROMA_DB_PATH = DATA_DIR / "chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # ChromaDB default
MAX_SEARCH_RESULTS = 5

