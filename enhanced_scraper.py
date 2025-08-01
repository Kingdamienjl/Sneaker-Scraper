import os
import time
import logging
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
import requests
from PIL import Image
import io

from scrapers import StockXScraper, EbayScraper
from google_drive import GoogleDriveManager
from database import SessionLocal, get_db
from models import Sneaker, SneakerImage, PriceHistory, ScrapingLog
from config import Config

logger = logging.getLogger(__name__)

class EnhancedSneakerScraper:
    """Enhanced scraper for building comprehensive sneaker database"""
    
    def __init__(self):
        self.google_drive = GoogleDriveManager()
        self.scrapers = {
            'stockx': StockXScraper(delay=2.0),
            'ebay': EbayScraper(delay=1.5)
        }
        self.image_folder = "data/images"
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories"""
        os.makedirs(self.image_folder, exist_ok=True)
        os.makedirs("data/temp", exist_ok=True)
    
    def build_sneaker_database(self, popular_sneakers: List[str], max_per_sneaker: int = 50):
        """
        Build comprehensive sneaker database by scraping popular models
        
        Args:
            popular_sneakers: List of popular sneaker names to scrape
            max_per_sneaker: Maximum number of listings per sneaker model
        """
        logger.info(f"Starting database build for {len(popular_sneakers)} sneaker models")
        
        total_scraped = 0
        total_images = 0
        
        for sneaker_name in popular_sneakers:
            logger.info(f"Processing: {sneaker_name}")
            
            try:
                # Scrape from all platforms
                all_data = []
                for platform, scraper in self.scrapers.items():
                    logger.info(f"Scraping {platform} for {sneaker_name}")
                    platform_data = scraper.scrape_sneaker_data(sneaker_name)
                    all_data.extend(platform_data[:max_per_sneaker])
                    time.sleep(3)  # Be respectful to servers
                
                # Process and save data
                processed_count, image_count = self.process_scraped_data(all_data, sneaker_name)
                total_scraped += processed_count
                total_images += image_count
                
                logger.info(f"Completed {sneaker_name}: {processed_count} items, {image_count} images")
                
            except Exception as e:
                logger.error(f"Error processing {sneaker_name}: {str(e)}")
                continue
        
        logger.info(f"Database build complete: {total_scraped} items, {total_images} images")
        return {"total_items": total_scraped, "total_images": total_images}
    
    def process_scraped_data(self, scraped_data: List[Dict], search_term: str) -> tuple:
        """Process scraped data and save to database with images"""
        db = SessionLocal()
        processed_count = 0
        image_count = 0
        
        try:
            for item in scraped_data:
                try:
                    # Check if sneaker already exists
                    existing_sneaker = db.query(Sneaker).filter(
                        Sneaker.name == item['name'],
                        Sneaker.brand == item['brand']
                    ).first()
                    
                    if not existing_sneaker:
                        # Create new sneaker record
                        sneaker = Sneaker(
                            name=item['name'],
                            brand=item['brand'],
                            model=self.extract_model(item['name']),
                            colorway=self.extract_colorway(item['name']),
                            sku=item.get('sku'),
                            retail_price=item.get('retail_price'),
                            release_date=self.parse_release_date(item.get('release_date')),
                            description=f"Scraped from {item['platform']}"
                        )
                        db.add(sneaker)
                        db.flush()  # Get the ID
                        sneaker_id = sneaker.id
                    else:
                        sneaker_id = existing_sneaker.id
                    
                    # Process main image
                    if item.get('image_url'):
                        image_saved = self.save_sneaker_image(
                            sneaker_id, 
                            item['image_url'], 
                            'main', 
                            db,
                            is_primary=True
                        )
                        if image_saved:
                            image_count += 1
                    
                    # Process additional images
                    for idx, img_url in enumerate(item.get('additional_images', [])):
                        image_saved = self.save_sneaker_image(
                            sneaker_id, 
                            img_url, 
                            f'detail_{idx}', 
                            db
                        )
                        if image_saved:
                            image_count += 1
                    
                    # Save price data
                    if item.get('current_price'):
                        price_record = PriceHistory(
                            sneaker_id=sneaker_id,
                            size='Unknown',  # Most scraped data doesn't have size
                            price=item['current_price'],
                            condition='new',
                            platform=item['platform'],
                            listing_type='current',
                            sale_date=datetime.utcnow()
                        )
                        db.add(price_record)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing item {item.get('name', 'Unknown')}: {str(e)}")
                    continue
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            db.rollback()
        finally:
            db.close()
        
        return processed_count, image_count
    
    def save_sneaker_image(self, sneaker_id: int, image_url: str, image_type: str, 
                          db, is_primary: bool = False) -> bool:
        """Download image, save to Google Drive, and record in database"""
        try:
            # Check if image already exists
            existing_image = db.query(SneakerImage).filter(
                SneakerImage.sneaker_id == sneaker_id,
                SneakerImage.image_url == image_url
            ).first()
            
            if existing_image:
                return False
            
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Validate image
            try:
                img = Image.open(io.BytesIO(response.content))
                img.verify()
            except:
                logger.warning(f"Invalid image format: {image_url}")
                return False
            
            # Generate unique filename
            image_hash = hashlib.md5(response.content).hexdigest()
            file_extension = self.get_image_extension(image_url)
            filename = f"sneaker_{sneaker_id}_{image_type}_{image_hash}{file_extension}"
            local_path = os.path.join(self.image_folder, filename)
            
            # Save locally first
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Upload to Google Drive
            google_drive_id = self.google_drive.upload_image(
                local_path, 
                filename,
                folder_name="SoleID_Images"
            )
            
            if google_drive_id:
                # Save to database
                sneaker_image = SneakerImage(
                    sneaker_id=sneaker_id,
                    image_url=image_url,
                    google_drive_id=google_drive_id,
                    image_type=image_type,
                    is_primary=is_primary
                )
                db.add(sneaker_image)
                
                # Clean up local file
                try:
                    os.remove(local_path)
                except:
                    pass
                
                logger.info(f"Saved image: {filename} -> Google Drive: {google_drive_id}")
                return True
            
        except Exception as e:
            logger.error(f"Error saving image {image_url}: {str(e)}")
        
        return False
    
    def get_image_extension(self, url: str) -> str:
        """Extract file extension from URL"""
        if '.jpg' in url.lower():
            return '.jpg'
        elif '.jpeg' in url.lower():
            return '.jpeg'
        elif '.png' in url.lower():
            return '.png'
        elif '.webp' in url.lower():
            return '.webp'
        else:
            return '.jpg'  # Default
    
    def extract_model(self, name: str) -> str:
        """Extract sneaker model from name"""
        # Simple extraction - can be enhanced with ML
        common_models = [
            'Air Jordan 1', 'Air Jordan 4', 'Air Jordan 11', 'Air Max 90', 
            'Air Max 1', 'Dunk Low', 'Dunk High', 'Yeezy 350', 'Yeezy 700',
            'Stan Smith', 'Ultraboost', 'NMD'
        ]
        
        name_lower = name.lower()
        for model in common_models:
            if model.lower() in name_lower:
                return model
        
        # Fallback: take first few words
        words = name.split()[:3]
        return ' '.join(words)
    
    def extract_colorway(self, name: str) -> str:
        """Extract colorway from name"""
        # Look for color words
        colors = [
            'black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 
            'purple', 'pink', 'brown', 'gray', 'grey', 'navy', 'royal',
            'bred', 'chicago', 'shadow', 'cement', 'infrared'
        ]
        
        name_lower = name.lower()
        found_colors = [color for color in colors if color in name_lower]
        
        if found_colors:
            return ' '.join(found_colors[:2])  # Max 2 colors
        
        return 'Unknown'
    
    def parse_release_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse release date string to datetime"""
        if not date_str:
            return None
        
        try:
            # Try common formats
            for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%B %d, %Y']:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
        except:
            pass
        
        return None
    
    def get_popular_sneakers(self) -> List[str]:
        """Get list of popular sneakers to scrape"""
        return [
            # Nike Jordan
            "Air Jordan 1 Retro High",
            "Air Jordan 4 Retro",
            "Air Jordan 11 Retro",
            "Air Jordan 3 Retro",
            "Air Jordan 6 Retro",
            
            # Nike Air Max
            "Nike Air Max 90",
            "Nike Air Max 1",
            "Nike Air Max 97",
            "Nike Air Max 270",
            
            # Nike Dunk
            "Nike Dunk Low",
            "Nike Dunk High",
            "Nike SB Dunk Low",
            
            # Yeezy
            "Adidas Yeezy Boost 350 V2",
            "Adidas Yeezy 700",
            "Adidas Yeezy 500",
            
            # Other Popular
            "Nike Air Force 1",
            "Adidas Stan Smith",
            "Adidas Ultraboost",
            "New Balance 550",
            "Travis Scott Jordan 1"
        ]

# Quick start function
def start_database_building():
    """Start building the sneaker database"""
    scraper = EnhancedSneakerScraper()
    popular_sneakers = scraper.get_popular_sneakers()
    
    logger.info("🚀 Starting SoleID Database Building...")
    logger.info(f"📊 Will scrape {len(popular_sneakers)} popular sneaker models")
    logger.info("💾 Images will be saved to Google Drive")
    logger.info("🗄️ Data will be stored in local database")
    
    results = scraper.build_sneaker_database(popular_sneakers, max_per_sneaker=30)
    
    logger.info("✅ Database building completed!")
    logger.info(f"📈 Total items: {results['total_items']}")
    logger.info(f"🖼️ Total images: {results['total_images']}")
    
    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_database_building()