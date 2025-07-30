import os
import logging
import schedule
import time
from datetime import datetime
from typing import List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from config import Config
from models import Base, Sneaker, SneakerImage, PriceHistory, ScrapingLog
from scrapers import StockXScraper, GOATScraper, EbayScraper
from google_drive import GoogleDriveManager
from image_processor import ImageProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScraperManager:
    def __init__(self):
        # Database setup
        self.engine = create_engine(Config.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        
        # Initialize scrapers
        self.scrapers = {
            'stockx': StockXScraper(delay=Config.REQUEST_DELAY),
            'goat': GOATScraper(delay=Config.REQUEST_DELAY),
            'ebay': EbayScraper(delay=Config.REQUEST_DELAY)
        }
        
        # Initialize Google Drive and image processor
        self.drive_manager = GoogleDriveManager()
        self.image_processor = ImageProcessor()
        
        # Create necessary directories
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.IMAGES_DIR, exist_ok=True)
        os.makedirs(Config.LOGS_DIR, exist_ok=True)
        
        # Popular sneaker search terms
        self.default_search_terms = [
            "Air Jordan 1", "Air Jordan 4", "Air Jordan 11",
            "Nike Dunk Low", "Nike Dunk High", "Nike Air Force 1",
            "Yeezy 350", "Yeezy 700", "Yeezy 500",
            "Adidas Ultraboost", "Adidas NMD", "Adidas Stan Smith",
            "New Balance 550", "New Balance 990", "New Balance 2002R",
            "Travis Scott Jordan", "Off-White Nike", "Fragment Jordan"
        ]
    
    def scrape_all_platforms(self, search_terms: List[str] = None, platforms: List[str] = None):
        """Scrape data from all specified platforms"""
        if search_terms is None:
            search_terms = self.default_search_terms
        
        if platforms is None:
            platforms = list(self.scrapers.keys())
        
        logger.info(f"Starting scraping for {len(search_terms)} search terms across {len(platforms)} platforms")
        
        for platform in platforms:
            if platform not in self.scrapers:
                logger.warning(f"Unknown platform: {platform}")
                continue
            
            self._scrape_platform(platform, search_terms)
        
        logger.info("Scraping completed for all platforms")
    
    def _scrape_platform(self, platform: str, search_terms: List[str]):
        """Scrape data from a specific platform"""
        scraper = self.scrapers[platform]
        start_time = datetime.utcnow()
        items_scraped = 0
        errors_count = 0
        error_messages = []
        
        logger.info(f"Starting {platform} scraping")
        
        db = self.SessionLocal()
        
        try:
            for search_term in search_terms:
                try:
                    logger.info(f"Scraping {platform} for: {search_term}")
                    sneaker_data_list = scraper.scrape_sneaker_data(search_term)
                    
                    for sneaker_data in sneaker_data_list:
                        try:
                            self._process_sneaker_data(sneaker_data, db)
                            items_scraped += 1
                        except Exception as e:
                            errors_count += 1
                            error_msg = f"Error processing sneaker data: {str(e)}"
                            error_messages.append(error_msg)
                            logger.error(error_msg)
                    
                    # Small delay between search terms
                    time.sleep(2)
                
                except Exception as e:
                    errors_count += 1
                    error_msg = f"Error scraping {search_term} on {platform}: {str(e)}"
                    error_messages.append(error_msg)
                    logger.error(error_msg)
            
            # Log scraping results
            end_time = datetime.utcnow()
            status = "success" if errors_count == 0 else ("partial" if items_scraped > 0 else "error")
            
            scraping_log = ScrapingLog(
                platform=platform,
                status=status,
                items_scraped=items_scraped,
                errors_count=errors_count,
                start_time=start_time,
                end_time=end_time,
                error_message="; ".join(error_messages[:5])  # Store first 5 errors
            )
            
            db.add(scraping_log)
            db.commit()
            
            logger.info(f"Completed {platform} scraping: {items_scraped} items, {errors_count} errors")
        
        except Exception as e:
            logger.error(f"Critical error in {platform} scraping: {str(e)}")
            db.rollback()
        
        finally:
            db.close()
    
    def _process_sneaker_data(self, sneaker_data: dict, db):
        """Process and store sneaker data"""
        # Check if sneaker already exists
        existing_sneaker = None
        if sneaker_data.get('sku'):
            existing_sneaker = db.query(Sneaker).filter(Sneaker.sku == sneaker_data['sku']).first()
        
        if not existing_sneaker and sneaker_data.get('name'):
            existing_sneaker = db.query(Sneaker).filter(
                Sneaker.name.ilike(f"%{sneaker_data['name']}%")
            ).first()
        
        if existing_sneaker:
            sneaker = existing_sneaker
            logger.info(f"Updating existing sneaker: {sneaker.name}")
        else:
            # Create new sneaker
            sneaker = Sneaker(
                name=sneaker_data.get('name', ''),
                brand=sneaker_data.get('brand', 'Unknown'),
                model=self._extract_model(sneaker_data.get('name', '')),
                colorway=sneaker_data.get('colorway'),
                sku=sneaker_data.get('sku'),
                retail_price=sneaker_data.get('retail_price'),
                release_date=self._parse_date(sneaker_data.get('release_date')),
                description=sneaker_data.get('description')
            )
            db.add(sneaker)
            db.flush()  # Get the ID
            logger.info(f"Created new sneaker: {sneaker.name}")
        
        # Process main image
        if sneaker_data.get('image_url'):
            self._process_image(sneaker, sneaker_data['image_url'], 'main', True, db)
        
        # Process additional images
        for i, img_url in enumerate(sneaker_data.get('additional_images', [])):
            self._process_image(sneaker, img_url, f'detail_{i}', False, db)
        
        # Process price data
        if sneaker_data.get('current_price'):
            price_history = PriceHistory(
                sneaker_id=sneaker.id,
                size='Unknown',  # Size info would need to be extracted from detailed scraping
                price=sneaker_data['current_price'],
                condition='new',
                platform=sneaker_data.get('platform', 'Unknown'),
                listing_type='current',
                sale_date=datetime.utcnow()
            )
            db.add(price_history)
        
        db.commit()
    
    def _process_image(self, sneaker: Sneaker, image_url: str, image_type: str, is_primary: bool, db):
        """Download, process, and store image"""
        try:
            # Check if image already exists
            existing_image = db.query(SneakerImage).filter(
                SneakerImage.sneaker_id == sneaker.id,
                SneakerImage.image_url == image_url
            ).first()
            
            if existing_image:
                return
            
            # Download image
            image_filename = f"{sneaker.id}_{image_type}_{int(time.time())}.jpg"
            local_path = os.path.join(Config.IMAGES_DIR, image_filename)
            
            if self.scrapers['stockx'].download_image(image_url, local_path):
                # Process image
                processed_path = self.image_processor.process_image(local_path)
                
                # Upload to Google Drive
                drive_result = self.drive_manager.upload_image(
                    processed_path,
                    image_filename,
                    self.drive_manager.folder_id
                )
                
                if drive_result:
                    # Store image info in database
                    sneaker_image = SneakerImage(
                        sneaker_id=sneaker.id,
                        image_url=image_url,
                        google_drive_id=drive_result['id'],
                        image_type=image_type,
                        is_primary=is_primary
                    )
                    db.add(sneaker_image)
                    
                    logger.info(f"Processed and uploaded image: {image_filename}")
                
                # Clean up local files
                if os.path.exists(local_path):
                    os.remove(local_path)
                if os.path.exists(processed_path) and processed_path != local_path:
                    os.remove(processed_path)
        
        except Exception as e:
            logger.error(f"Error processing image {image_url}: {str(e)}")
    
    def _extract_model(self, name: str) -> str:
        """Extract model from sneaker name"""
        # Simple model extraction logic
        words = name.split()
        if len(words) >= 2:
            return ' '.join(words[:2])
        return name
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except:
            pass
        
        return None
    
    def schedule_scraping(self):
        """Schedule automatic scraping"""
        schedule.every(Config.SCRAPE_INTERVAL_HOURS).hours.do(self.scrape_all_platforms)
        
        logger.info(f"Scheduled scraping every {Config.SCRAPE_INTERVAL_HOURS} hours")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    manager = ScraperManager()
    
    # Run initial scraping
    manager.scrape_all_platforms()
    
    # Start scheduled scraping
    manager.schedule_scraping()