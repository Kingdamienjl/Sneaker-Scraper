import uvicorn
from api import app
from scraper_manager import ScraperManager
import threading
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_scheduled_scraping():
    """Start the scheduled scraping in a separate thread"""
    manager = ScraperManager()
    manager.schedule_scraping()

if __name__ == "__main__":
    # Start scheduled scraping in background
    scraping_thread = threading.Thread(target=start_scheduled_scraping, daemon=True)
    scraping_thread.start()
    
    logger.info("Starting Sneaker Data API server...")
    
    # Start the API server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable reload in production
    )