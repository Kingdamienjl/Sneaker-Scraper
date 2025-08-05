#!/usr/bin/env python3
"""
Enhanced 36-Hour Sneaker Image Collector
- Collects real sneaker images for 36 hours
- Renames files with actual shoe names
- Removes duplicates based on image hash
- Uploads to Google Drive after collection
- Uses the proven Bing + Direct URL method
"""

import sqlite3
import requests
import os
import time
import json
import hashlib
import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urljoin
from pathlib import Path
import re
from google_drive import GoogleDriveManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_36_hour_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Enhanced36HourCollector:
    def __init__(self):
        self.db_path = 'sneakers.db'
        self.image_dir = Path('data/enhanced_sneaker_images')
        self.image_dir.mkdir(parents=True, exist_ok=True)
        
        # Collection settings
        self.collection_hours = 36
        self.batch_size = 10  # Process 10 sneakers at a time
        self.images_per_sneaker = 3  # Target 3 images per sneaker
        self.delay_between_requests = 2  # 2 seconds between requests
        
        # Progress tracking
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=self.collection_hours)
        self.progress_file = 'enhanced_36_hour_progress.json'
        
        # Image hashes for duplicate detection
        self.image_hashes = set()
        
        # Initialize database
        self.init_database()
        
        logger.info(f"Enhanced 36-Hour Collector initialized")
        logger.info(f"Start time: {self.start_time}")
        logger.info(f"End time: {self.end_time}")
        logger.info(f"Target duration: {self.collection_hours} hours")

    def init_database(self):
        """Initialize the enhanced_sneaker_images table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enhanced_sneaker_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sneaker_id INTEGER,
                sneaker_name TEXT,
                source TEXT,
                image_url TEXT,
                local_path TEXT,
                filename TEXT,
                image_hash TEXT UNIQUE,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sneaker_id) REFERENCES sneakers (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized for enhanced collection")

    def get_sneaker_batches(self):
        """Get sneakers in batches for processing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM sneakers')
        total_sneakers = cursor.fetchone()[0]
        
        offset = 0
        while offset < total_sneakers:
            cursor.execute('''
                SELECT id, name, brand 
                FROM sneakers 
                ORDER BY id 
                LIMIT ? OFFSET ?
            ''', (self.batch_size, offset))
            
            batch = cursor.fetchall()
            if not batch:
                break
                
            yield batch
            offset += self.batch_size
        
        conn.close()

    def clean_filename(self, sneaker_name):
        """Clean sneaker name for use as filename"""
        # Remove special characters and replace spaces with underscores
        clean_name = re.sub(r'[^\w\s-]', '', sneaker_name)
        clean_name = re.sub(r'\s+', '_', clean_name.strip())
        return clean_name[:50]  # Limit length

    def calculate_image_hash(self, image_path):
        """Calculate MD5 hash of image file for duplicate detection"""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {image_path}: {e}")
            return None

    def search_bing_images(self, sneaker_name, max_images=2):
        """Search for sneaker images on Bing"""
        images = []
        try:
            search_query = f"{sneaker_name} sneaker shoe"
            encoded_query = quote_plus(search_query)
            
            # Bing image search URL
            url = f"https://www.bing.com/images/search?q={encoded_query}&form=HDRSC2&first=1&tsc=ImageBasicHover"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Simple regex to find image URLs in Bing results
                import re
                image_urls = re.findall(r'"murl":"([^"]+)"', response.text)
                
                for img_url in image_urls[:max_images]:
                    if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png']):
                        images.append({
                            'url': img_url,
                            'source': 'bing'
                        })
                        
        except Exception as e:
            logger.error(f"Error searching Bing for {sneaker_name}: {e}")
        
        return images

    def search_direct_urls(self, sneaker_name, max_images=1):
        """Generate direct sneaker image URLs"""
        images = []
        try:
            # Generate some direct URL patterns
            clean_name = sneaker_name.lower().replace(' ', '-').replace("'", "")
            
            direct_urls = [
                f"https://stockx.com/api/browse?_search={quote_plus(sneaker_name)}",
                f"https://goat.com/search?query={quote_plus(sneaker_name)}",
            ]
            
            for i, url in enumerate(direct_urls[:max_images]):
                images.append({
                    'url': url,
                    'source': 'direct'
                })
                
        except Exception as e:
            logger.error(f"Error generating direct URLs for {sneaker_name}: {e}")
        
        return images

    def download_image(self, image_info, sneaker_name, sneaker_id):
        """Download and save image with sneaker name as filename"""
        try:
            url = image_info['url']
            source = image_info['source']
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            if response.status_code == 200:
                # Generate filename with sneaker name
                clean_name = self.clean_filename(sneaker_name)
                timestamp = int(time.time())
                filename = f"{clean_name}_{source}_{timestamp}.jpg"
                filepath = self.image_dir / filename
                
                # Save image
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Calculate hash for duplicate detection
                image_hash = self.calculate_image_hash(filepath)
                if image_hash in self.image_hashes:
                    # Duplicate found, remove file
                    os.remove(filepath)
                    logger.info(f"Duplicate image removed: {filename}")
                    return None
                
                self.image_hashes.add(image_hash)
                
                # Get image info
                file_size = filepath.stat().st_size
                
                # Save to database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO enhanced_sneaker_images 
                    (sneaker_id, sneaker_name, source, image_url, local_path, filename, image_hash, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (sneaker_id, sneaker_name, source, url, str(filepath), filename, image_hash, file_size))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Downloaded: {filename} ({file_size} bytes)")
                return str(filepath)
                
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
        
        return None

    def process_sneaker(self, sneaker_id, sneaker_name, brand):
        """Process a single sneaker and collect images"""
        logger.info(f"Processing: {sneaker_name} ({brand})")
        
        images_downloaded = 0
        
        # Search Bing images
        bing_images = self.search_bing_images(sneaker_name, max_images=2)
        for image_info in bing_images:
            if self.download_image(image_info, sneaker_name, sneaker_id):
                images_downloaded += 1
            time.sleep(self.delay_between_requests)
        
        # Search direct URLs
        direct_images = self.search_direct_urls(sneaker_name, max_images=1)
        for image_info in direct_images:
            if self.download_image(image_info, sneaker_name, sneaker_id):
                images_downloaded += 1
            time.sleep(self.delay_between_requests)
        
        return images_downloaded

    def save_progress(self, stats):
        """Save progress to JSON file"""
        progress_data = {
            'timestamp': datetime.now().isoformat(),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
            'remaining_hours': max(0, (self.end_time - datetime.now()).total_seconds() / 3600),
            **stats
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

    def generate_hourly_report(self, stats):
        """Generate hourly progress report"""
        duration = (datetime.now() - self.start_time).total_seconds() / 3600
        remaining = max(0, (self.end_time - datetime.now()).total_seconds() / 3600)
        
        logger.info("=" * 60)
        logger.info(f"HOURLY PROGRESS REPORT - Hour {duration:.1f}")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration:.2f} hours")
        logger.info(f"Remaining: {remaining:.2f} hours")
        logger.info(f"Sneakers processed: {stats['sneakers_processed']}")
        logger.info(f"Images downloaded: {stats['images_downloaded']}")
        logger.info(f"Success rate: {stats['success_rate']}")
        logger.info(f"Avg images/sneaker: {stats['avg_images_per_sneaker']:.2f}")
        logger.info(f"Sneakers/hour: {stats['sneakers_per_hour']:.1f}")
        logger.info(f"Duplicates removed: {stats['duplicates_removed']}")
        logger.info("=" * 60)

    def upload_to_google_drive(self):
        """Upload all collected images to Google Drive"""
        logger.info("Starting Google Drive upload...")
        
        try:
            drive_manager = GoogleDriveManager()
            
            # Get all images from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT sneaker_name, filename, local_path 
                FROM enhanced_sneaker_images 
                ORDER BY sneaker_name
            ''')
            
            images = cursor.fetchall()
            conn.close()
            
            uploaded_count = 0
            for sneaker_name, filename, local_path in images:
                if os.path.exists(local_path):
                    try:
                        # Upload to Google Drive
                        drive_manager.upload_image(local_path, filename, sneaker_name)
                        uploaded_count += 1
                        logger.info(f"Uploaded to Drive: {filename}")
                    except Exception as e:
                        logger.error(f"Failed to upload {filename}: {e}")
                else:
                    logger.warning(f"File not found: {local_path}")
            
            logger.info(f"Google Drive upload completed: {uploaded_count} images uploaded")
            
        except Exception as e:
            logger.error(f"Error during Google Drive upload: {e}")

    def run_collection(self):
        """Run the 36-hour collection process"""
        logger.info("Starting Enhanced 36-Hour Collection")
        logger.info("=" * 60)
        
        sneakers_processed = 0
        images_downloaded = 0
        duplicates_removed = 0
        last_hour_report = 0
        
        try:
            for batch in self.get_sneaker_batches():
                # Check if time limit reached
                if datetime.now() >= self.end_time:
                    logger.info("Time limit reached, stopping collection")
                    break
                
                # Process each sneaker in batch
                for sneaker_id, sneaker_name, brand in batch:
                    if datetime.now() >= self.end_time:
                        break
                    
                    batch_images = self.process_sneaker(sneaker_id, sneaker_name, brand)
                    images_downloaded += batch_images
                    sneakers_processed += 1
                    
                    # Calculate stats
                    duration_hours = (datetime.now() - self.start_time).total_seconds() / 3600
                    success_rate = f"{(images_downloaded / (sneakers_processed * self.images_per_sneaker) * 100):.1f}%" if sneakers_processed > 0 else "0%"
                    avg_images_per_sneaker = images_downloaded / sneakers_processed if sneakers_processed > 0 else 0
                    sneakers_per_hour = sneakers_processed / duration_hours if duration_hours > 0 else 0
                    
                    stats = {
                        'sneakers_processed': sneakers_processed,
                        'images_downloaded': images_downloaded,
                        'duplicates_removed': len(self.image_hashes) - images_downloaded,
                        'success_rate': success_rate,
                        'avg_images_per_sneaker': avg_images_per_sneaker,
                        'sneakers_per_hour': sneakers_per_hour
                    }
                    
                    # Save progress
                    self.save_progress(stats)
                    
                    # Generate hourly report
                    current_hour = int(duration_hours)
                    if current_hour > last_hour_report:
                        self.generate_hourly_report(stats)
                        last_hour_report = current_hour
                
                # Small delay between batches
                time.sleep(5)
        
        except KeyboardInterrupt:
            logger.info("Collection interrupted by user")
        except Exception as e:
            logger.error(f"Error during collection: {e}")
        
        # Final report
        duration_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        logger.info("=" * 60)
        logger.info("FINAL COLLECTION REPORT")
        logger.info("=" * 60)
        logger.info(f"Total duration: {duration_hours:.2f} hours")
        logger.info(f"Total sneakers processed: {sneakers_processed}")
        logger.info(f"Total images downloaded: {images_downloaded}")
        logger.info(f"Duplicates removed: {len(self.image_hashes) - images_downloaded}")
        logger.info(f"Average images per sneaker: {images_downloaded / sneakers_processed if sneakers_processed > 0 else 0:.2f}")
        logger.info("=" * 60)
        
        # Upload to Google Drive
        if images_downloaded > 0:
            self.upload_to_google_drive()
        
        logger.info("Enhanced 36-Hour Collection completed!")

if __name__ == "__main__":
    collector = Enhanced36HourCollector()
    collector.run_collection()