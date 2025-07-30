import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///sneakers.db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Google Drive
    GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    
    # API Keys
    STOCKX_API_KEY = os.getenv("STOCKX_API_KEY")
    GOAT_API_KEY = os.getenv("GOAT_API_KEY")
    EBAY_API_KEY = os.getenv("EBAY_API_KEY")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    
    # Scraping Settings
    SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24))
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", 10))
    REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 1.0))
    
    # Image Processing
    MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", 1024))
    IMAGE_QUALITY = int(os.getenv("IMAGE_QUALITY", 85))
    
    # Directories
    DATA_DIR = "data"
    IMAGES_DIR = "data/images"
    LOGS_DIR = "logs"