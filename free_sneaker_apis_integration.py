#!/usr/bin/env python3
"""
Free Sneaker APIs Integration
Combines multiple free APIs to collect comprehensive sneaker data
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import logging
import requests
from datetime import datetime
from urllib.parse import urljoin, quote
import threading

class FreeSneakerAPIsIntegration:
    def __init__(self):
        self.setup_logging()
        self.setup_directories()
        self.setup_database()
        self.setup_apis()
        self.setup_stats()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('free_sneaker_apis')
        self.logger.setLevel(logging.INFO)
        
        # File handler with UTF-8 encoding
        log_file = os.path.join(log_dir, f"free_sneaker_apis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def setup_directories(self):
        """Setup required directories"""
        self.image_dir = os.path.join("data", "free_api_images")
        os.makedirs(self.image_dir, exist_ok=True)
        
    def setup_database(self):
        """Setup database connection with proper handling"""
        self.db_path = "sneakers.db"
        self.db_lock = threading.Lock()
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for free API data"""
        with self.db_lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                # Create free API sneaker data table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS free_api_sneakers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        api_source TEXT,
                        api_id TEXT,
                        name TEXT,
                        brand TEXT,
                        model TEXT,
                        colorway TEXT,
                        description TEXT,
                        release_date TEXT,
                        retail_price REAL,
                        image_url TEXT,
                        thumbnail_url TEXT,
                        product_url TEXT,
                        stockx_url TEXT,
                        goat_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(api_source, api_id)
                    )
                """)
                
                # Create free API images table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS free_api_images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sneaker_id INTEGER,
                        url TEXT,
                        local_path TEXT,
                        image_type TEXT,
                        api_source TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sneaker_id) REFERENCES free_api_sneakers (id)
                    )
                """)
                
                conn.commit()
                conn.close()
                self.logger.info("Free API database tables initialized successfully")
                
            except Exception as e:
                self.logger.error(f"Database initialization error: {e}")
                
    def setup_apis(self):
        """Setup API configurations for free services"""
        self.apis = {
            'sneaker_database': {
                'base_url': 'https://api.thesneakerdatabase.com/v2',
                'rate_limit': 5,  # 5 requests per second
                'headers': {
                    'User-Agent': 'SoleID-Scraper/1.0'
                }
            },
            'sneaker_api_io': {
                'base_url': 'https://www.sneakerapi.io/api',
                'rate_limit': 2,  # Conservative rate limit
                'headers': {
                    'User-Agent': 'SoleID-Scraper/1.0'
                }
            }
        }
        
    def setup_stats(self):
        """Initialize statistics tracking"""
        self.stats = {
            'start_time': time.time(),
            'api_requests': 0,
            'sneakers_found': 0,
            'sneakers_saved': 0,
            'images_downloaded': 0,
            'errors': [],
            'api_stats': {}
        }
        
        for api_name in self.apis.keys():
            self.stats['api_stats'][api_name] = {
                'requests': 0,
                'sneakers': 0,
                'errors': 0
            }
    
    def get_database_connection(self):
        """Get a database connection with proper timeout"""
        return sqlite3.connect(self.db_path, timeout=30.0)
    
    def search_sneaker_database_api(self, brand, limit=50):
        """Search using The Sneaker Database API (free tier)"""
        try:
            api_config = self.apis['sneaker_database']
            url = f"{api_config['base_url']}/sneakers"
            
            params = {
                'brand': brand.lower(),
                'limit': limit
            }
            
            response = requests.get(
                url, 
                headers=api_config['headers'], 
                params=params, 
                timeout=30
            )
            
            self.stats['api_requests'] += 1
            self.stats['api_stats']['sneaker_database']['requests'] += 1
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                self.logger.info(f"Sneaker Database API: Found {len(results)} sneakers for brand: {brand}")
                self.stats['api_stats']['sneaker_database']['sneakers'] += len(results)
                return results
            else:
                self.logger.warning(f"Sneaker Database API failed for '{brand}': {response.status_code}")
                self.stats['api_stats']['sneaker_database']['errors'] += 1
                return []
                
        except Exception as e:
            self.logger.error(f"Sneaker Database API error for '{brand}': {e}")
            self.stats['api_stats']['sneaker_database']['errors'] += 1
            return []
    
    def search_sneaker_api_io(self, brand, limit=50):
        """Search using SneakerAPI.io (free service)"""
        try:
            api_config = self.apis['sneaker_api_io']
            url = f"{api_config['base_url']}/sneakers"
            
            params = {
                'brand': brand,
                'limit': limit
            }
            
            response = requests.get(
                url, 
                headers=api_config['headers'], 
                params=params, 
                timeout=30
            )
            
            self.stats['api_requests'] += 1
            self.stats['api_stats']['sneaker_api_io']['requests'] += 1
            
            if response.status_code == 200:
                data = response.json()
                results = data if isinstance(data, list) else data.get('results', [])
                self.logger.info(f"SneakerAPI.io: Found {len(results)} sneakers for brand: {brand}")
                self.stats['api_stats']['sneaker_api_io']['sneakers'] += len(results)
                return results
            else:
                self.logger.warning(f"SneakerAPI.io failed for '{brand}': {response.status_code}")
                self.stats['api_stats']['sneaker_api_io']['errors'] += 1
                return []
                
        except Exception as e:
            self.logger.error(f"SneakerAPI.io error for '{brand}': {e}")
            self.stats['api_stats']['sneaker_api_io']['errors'] += 1
            return []
    
    def download_image(self, url, filename):
        """Download image from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'webp']):
                return False
            
            # Save file
            filepath = os.path.join(self.image_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Validate downloaded image
            if self.validate_image(filepath):
                return filepath
            else:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return False
                
        except Exception as e:
            self.logger.error(f"Error downloading {url}: {e}")
            return False
    
    def validate_image(self, image_path):
        """Validate downloaded image"""
        try:
            if not os.path.exists(image_path):
                return False
                
            # Check file size
            file_size = os.path.getsize(image_path)
            if file_size < 500:  # Less than 500 bytes
                return False
                
            # Check if file has image-like content
            with open(image_path, 'rb') as f:
                content = f.read(20)
                # Check for common image file signatures
                if not (content.startswith(b'\xff\xd8\xff') or  # JPEG
                       content.startswith(b'\x89PNG') or        # PNG
                       content.startswith(b'GIF8') or           # GIF
                       content.startswith(b'RIFF')):            # WebP
                    return False
                
            return True
        except Exception as e:
            self.logger.error(f"Image validation failed: {e}")
            return False
    
    def save_sneaker_to_database(self, sneaker_data, api_source):
        """Save sneaker data to database"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                # Extract API ID based on source
                if api_source == 'sneaker_database':
                    api_id = sneaker_data.get('id') or sneaker_data.get('sku')
                elif api_source == 'sneaker_api_io':
                    api_id = sneaker_data.get('id') or sneaker_data.get('_id')
                else:
                    api_id = str(hash(str(sneaker_data)))
                
                # Check if sneaker already exists
                cursor.execute(
                    "SELECT id FROM free_api_sneakers WHERE api_source = ? AND api_id = ?", 
                    (api_source, api_id)
                )
                existing = cursor.fetchone()
                
                if existing:
                    conn.close()
                    return existing[0]
                
                # Extract data based on API source
                name = sneaker_data.get('name', '')
                brand = sneaker_data.get('brand', '')
                model = sneaker_data.get('model', '')
                colorway = sneaker_data.get('colorway', '')
                description = sneaker_data.get('description', '')
                release_date = sneaker_data.get('releaseDate', '') or sneaker_data.get('release_date', '')
                retail_price = sneaker_data.get('retailPrice', 0) or sneaker_data.get('retail_price', 0)
                
                # Handle image URLs
                image_url = ''
                thumbnail_url = ''
                
                if api_source == 'sneaker_database':
                    image_data = sneaker_data.get('image', {})
                    if isinstance(image_data, dict):
                        image_url = image_data.get('original', '')
                        thumbnail_url = image_data.get('small', '')
                    elif isinstance(image_data, str):
                        image_url = image_data
                elif api_source == 'sneaker_api_io':
                    image_url = sneaker_data.get('image', '') or sneaker_data.get('imageUrl', '')
                    thumbnail_url = sneaker_data.get('thumbnail', '')
                
                # Handle product URLs
                product_url = sneaker_data.get('productUrl', '') or sneaker_data.get('url', '')
                stockx_url = ''
                goat_url = ''
                
                if 'links' in sneaker_data:
                    links = sneaker_data['links']
                    stockx_url = links.get('stockX', '') or links.get('stockx', '')
                    goat_url = links.get('goat', '') or links.get('GOAT', '')
                
                # Insert new sneaker
                cursor.execute("""
                    INSERT INTO free_api_sneakers (
                        api_source, api_id, name, brand, model, colorway, description,
                        release_date, retail_price, image_url, thumbnail_url,
                        product_url, stockx_url, goat_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    api_source, api_id, name, brand, model, colorway, description,
                    release_date, retail_price, image_url, thumbnail_url,
                    product_url, stockx_url, goat_url
                ))
                
                sneaker_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                self.stats['sneakers_saved'] += 1
                return sneaker_id
                
        except Exception as e:
            self.logger.error(f"Error saving sneaker to database: {e}")
            return None
    
    def save_image_to_database(self, sneaker_id, image_url, local_path, image_type, api_source):
        """Save image information to database"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO free_api_images (sneaker_id, url, local_path, image_type, api_source)
                    VALUES (?, ?, ?, ?, ?)
                """, (sneaker_id, image_url, local_path, image_type, api_source))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving image to database: {e}")
            return False
    
    def process_sneaker(self, sneaker_data, api_source):
        """Process a single sneaker from API results"""
        try:
            # Save basic sneaker data
            sneaker_id = self.save_sneaker_to_database(sneaker_data, api_source)
            if not sneaker_id:
                return False
            
            name = sneaker_data.get('name', 'Unknown')
            self.logger.info(f"Processing: {name} (Source: {api_source})")
            
            # Download main image
            image_url = None
            
            if api_source == 'sneaker_database':
                image_data = sneaker_data.get('image', {})
                if isinstance(image_data, dict):
                    image_url = image_data.get('original') or image_data.get('small')
                elif isinstance(image_data, str):
                    image_url = image_data
            elif api_source == 'sneaker_api_io':
                image_url = sneaker_data.get('image', '') or sneaker_data.get('imageUrl', '')
            
            if image_url:
                filename = f"{api_source}_{sneaker_id}_{hashlib.md5(image_url.encode()).hexdigest()[:8]}.jpg"
                local_path = self.download_image(image_url, filename)
                
                if local_path:
                    self.save_image_to_database(sneaker_id, image_url, local_path, "product", api_source)
                    self.stats['images_downloaded'] += 1
                    self.logger.info(f"Downloaded image: {filename}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing sneaker: {e}")
            self.stats['errors'].append(f"Processing error: {str(e)}")
            return False
    
    def collect_from_all_apis(self):
        """Collect data from all available free APIs"""
        popular_brands = [
            "nike", "adidas", "jordan", "new-balance", "converse", 
            "vans", "puma", "reebok", "asics", "saucony"
        ]
        
        for brand in popular_brands:
            self.logger.info(f"Collecting data for brand: {brand}")
            
            # Try Sneaker Database API
            try:
                results = self.search_sneaker_database_api(brand, limit=30)
                self.stats['sneakers_found'] += len(results)
                
                for sneaker in results:
                    self.process_sneaker(sneaker, 'sneaker_database')
                    time.sleep(0.2)  # Rate limiting
                    
                time.sleep(1)  # Delay between API calls
            except Exception as e:
                self.logger.error(f"Error with Sneaker Database API for {brand}: {e}")
            
            # Try SneakerAPI.io
            try:
                results = self.search_sneaker_api_io(brand, limit=30)
                self.stats['sneakers_found'] += len(results)
                
                for sneaker in results:
                    self.process_sneaker(sneaker, 'sneaker_api_io')
                    time.sleep(0.5)  # Conservative rate limiting
                    
                time.sleep(2)  # Delay between brands
            except Exception as e:
                self.logger.error(f"Error with SneakerAPI.io for {brand}: {e}")
    
    def generate_report(self):
        """Generate collection report"""
        duration = time.time() - self.stats['start_time']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': round(duration, 1),
            'total_api_requests': self.stats['api_requests'],
            'sneakers_found': self.stats['sneakers_found'],
            'sneakers_saved': self.stats['sneakers_saved'],
            'images_downloaded': self.stats['images_downloaded'],
            'success_rate': f"{(self.stats['sneakers_saved'] / max(1, self.stats['sneakers_found']) * 100):.1f}%",
            'api_breakdown': self.stats['api_stats'],
            'errors': self.stats['errors'][-10:]  # Last 10 errors
        }
        
        # Save report
        with open('free_sneaker_apis_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\nFree Sneaker APIs Collection Report")
        print(f"===================================")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Total API requests: {self.stats['api_requests']}")
        print(f"Sneakers found: {self.stats['sneakers_found']}")
        print(f"Sneakers saved: {self.stats['sneakers_saved']}")
        print(f"Images downloaded: {self.stats['images_downloaded']}")
        print(f"Success rate: {(self.stats['sneakers_saved'] / max(1, self.stats['sneakers_found']) * 100):.1f}%")
        
        print(f"\nAPI Breakdown:")
        for api_name, stats in self.stats['api_stats'].items():
            print(f"  {api_name}: {stats['requests']} requests, {stats['sneakers']} sneakers, {stats['errors']} errors")
        
        return report
    
    def run(self):
        """Run the free APIs sneaker collection"""
        self.logger.info("Starting Free Sneaker APIs Collection")
        
        try:
            # Collect from all available APIs
            self.collect_from_all_apis()
            
            # Generate final report
            report = self.generate_report()
            self.logger.info("Free Sneaker APIs Collection completed")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Collection failed: {e}")
            return None

def main():
    """Main function"""
    collector = FreeSneakerAPIsIntegration()
    
    try:
        # Run the collection
        report = collector.run()
        
        if report and report['sneakers_saved'] > 0:
            print(f"\nSuccess! Collected {report['sneakers_saved']} sneakers with {report['images_downloaded']} images")
        else:
            print(f"\nCollection completed. Check the logs for details.")
            
    except KeyboardInterrupt:
        print("\nCollection interrupted by user")
    except Exception as e:
        print(f"Collection failed: {e}")
        logging.error(f"Collection failed: {e}")

if __name__ == "__main__":
    main()