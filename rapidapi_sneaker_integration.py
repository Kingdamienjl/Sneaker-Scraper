#!/usr/bin/env python3
"""
RapidAPI Sneaker Database Integration
Uses the Sneaker Database API to collect comprehensive sneaker data
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
from urllib.parse import urljoin
import threading

class RapidAPISneakerIntegration:
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
        self.logger = logging.getLogger('rapidapi_sneaker')
        self.logger.setLevel(logging.INFO)
        
        # File handler with UTF-8 encoding
        log_file = os.path.join(log_dir, f"rapidapi_sneaker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
        self.image_dir = os.path.join("data", "rapidapi_images")
        os.makedirs(self.image_dir, exist_ok=True)
        
    def setup_database(self):
        """Setup database connection with proper handling"""
        self.db_path = "sneakers.db"
        self.db_lock = threading.Lock()
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for RapidAPI data"""
        with self.db_lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                # Create enhanced sneaker data table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rapidapi_sneakers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        api_id TEXT UNIQUE,
                        name TEXT,
                        brand TEXT,
                        colorway TEXT,
                        description TEXT,
                        release_date TEXT,
                        retail_price REAL,
                        image_url TEXT,
                        product_url TEXT,
                        stockx_url TEXT,
                        goat_url TEXT,
                        flightclub_url TEXT,
                        stadium_goods_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create price data table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rapidapi_prices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sneaker_id INTEGER,
                        platform TEXT,
                        price REAL,
                        size TEXT,
                        condition TEXT,
                        currency TEXT DEFAULT 'USD',
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sneaker_id) REFERENCES rapidapi_sneakers (id)
                    )
                """)
                
                # Create images table for RapidAPI
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rapidapi_images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sneaker_id INTEGER,
                        url TEXT,
                        local_path TEXT,
                        image_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sneaker_id) REFERENCES rapidapi_sneakers (id)
                    )
                """)
                
                conn.commit()
                conn.close()
                self.logger.info("RapidAPI database tables initialized successfully")
                
            except Exception as e:
                self.logger.error(f"Database initialization error: {e}")
                
    def setup_apis(self):
        """Setup API configurations"""
        # RapidAPI configuration
        self.rapidapi_key = "ea9e679331msha2742f4c3daa0c5p1925fcjsn69b27669a85c"
        self.rapidapi_host = "the-sneaker-database.p.rapidapi.com"
        
        self.headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": self.rapidapi_host
        }
        
        # API endpoints
        self.base_url = "https://the-sneaker-database.p.rapidapi.com"
        
    def setup_stats(self):
        """Initialize statistics tracking"""
        self.stats = {
            'start_time': time.time(),
            'api_requests': 0,
            'sneakers_found': 0,
            'sneakers_saved': 0,
            'images_downloaded': 0,
            'prices_collected': 0,
            'errors': []
        }
        
    def get_database_connection(self):
        """Get a database connection with proper timeout"""
        return sqlite3.connect(self.db_path, timeout=30.0)
    
    def search_sneakers(self, brand, limit=10):
        """Search for sneakers using the RapidAPI"""
        try:
            url = f"{self.base_url}/sneakers"
            params = {
                "brand": brand.lower(),
                "limit": limit
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.stats['api_requests'] += 1
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', data) if isinstance(data, dict) else data
                self.logger.info(f"Found {len(results)} sneakers for brand: {brand}")
                return results
            else:
                self.logger.warning(f"Search failed for '{brand}': {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error searching for '{brand}': {e}")
            self.stats['errors'].append(f"Search error for '{brand}': {str(e)}")
            return []
    
    def get_sneaker_details(self, sneaker_id):
        """Get detailed information for a specific sneaker"""
        try:
            url = f"{self.base_url}/getproduct"
            params = {"productid": sneaker_id}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.stats['api_requests'] += 1
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Retrieved details for sneaker ID: {sneaker_id}")
                return data
            else:
                self.logger.warning(f"Details failed for ID '{sneaker_id}': {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting details for ID '{sneaker_id}': {e}")
            return None
    
    def get_sneaker_prices(self, sneaker_id):
        """Get price information for a sneaker"""
        try:
            url = f"{self.base_url}/getprices"
            params = {"productid": sneaker_id}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.stats['api_requests'] += 1
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Retrieved prices for sneaker ID: {sneaker_id}")
                return data.get('prices', [])
            else:
                self.logger.warning(f"Prices failed for ID '{sneaker_id}': {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting prices for ID '{sneaker_id}': {e}")
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
    
    def save_sneaker_to_database(self, sneaker_data):
        """Save sneaker data to database"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                # Check if sneaker already exists
                api_id = sneaker_data.get('id') or sneaker_data.get('sku')
                cursor.execute("SELECT id FROM rapidapi_sneakers WHERE api_id = ?", (api_id,))
                existing = cursor.fetchone()
                
                if existing:
                    conn.close()
                    return existing[0]
                
                # Insert new sneaker
                cursor.execute("""
                    INSERT INTO rapidapi_sneakers (
                        api_id, name, brand, colorway, description, release_date,
                        retail_price, image_url, product_url, stockx_url, goat_url,
                        flightclub_url, stadium_goods_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    api_id,
                    sneaker_data.get('name', ''),
                    sneaker_data.get('brand', ''),
                    sneaker_data.get('colorway', ''),
                    sneaker_data.get('description', ''),
                    sneaker_data.get('releaseDate', ''),
                    sneaker_data.get('retailPrice', 0),
                    sneaker_data.get('image', {}).get('original') if isinstance(sneaker_data.get('image'), dict) else sneaker_data.get('image', ''),
                    sneaker_data.get('links', {}).get('stockX', ''),
                    sneaker_data.get('links', {}).get('stockX', ''),
                    sneaker_data.get('links', {}).get('goat', ''),
                    sneaker_data.get('links', {}).get('flightClub', ''),
                    sneaker_data.get('links', {}).get('stadiumGoods', '')
                ))
                
                sneaker_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                self.stats['sneakers_saved'] += 1
                return sneaker_id
                
        except Exception as e:
            self.logger.error(f"Error saving sneaker to database: {e}")
            return None
    
    def save_prices_to_database(self, sneaker_id, prices):
        """Save price data to database"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                for price_data in prices:
                    cursor.execute("""
                        INSERT INTO rapidapi_prices (
                            sneaker_id, platform, price, size, condition, currency
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        sneaker_id,
                        price_data.get('platform', ''),
                        price_data.get('price', 0),
                        price_data.get('size', ''),
                        price_data.get('condition', ''),
                        price_data.get('currency', 'USD')
                    ))
                
                conn.commit()
                conn.close()
                self.stats['prices_collected'] += len(prices)
                
        except Exception as e:
            self.logger.error(f"Error saving prices to database: {e}")
    
    def save_image_to_database(self, sneaker_id, image_url, local_path, image_type="product"):
        """Save image information to database"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO rapidapi_images (sneaker_id, url, local_path, image_type)
                    VALUES (?, ?, ?, ?)
                """, (sneaker_id, image_url, local_path, image_type))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving image to database: {e}")
            return False
    
    def process_sneaker(self, sneaker_data):
        """Process a single sneaker from search results"""
        try:
            # Save basic sneaker data
            sneaker_id = self.save_sneaker_to_database(sneaker_data)
            if not sneaker_id:
                return False
            
            api_id = sneaker_data.get('id') or sneaker_data.get('sku')
            name = sneaker_data.get('name', 'Unknown')
            
            self.logger.info(f"Processing: {name} (API ID: {api_id})")
            
            # Download main image
            image_data = sneaker_data.get('image', {})
            image_url = None
            
            if isinstance(image_data, dict):
                image_url = image_data.get('original') or image_data.get('small') or image_data.get('thumbnail')
            elif isinstance(image_data, str):
                image_url = image_data
            
            if image_url:
                filename = f"rapidapi_{sneaker_id}_{hashlib.md5(image_url.encode()).hexdigest()[:8]}.jpg"
                local_path = self.download_image(image_url, filename)
                
                if local_path:
                    self.save_image_to_database(sneaker_id, image_url, local_path)
                    self.stats['images_downloaded'] += 1
                    self.logger.info(f"Downloaded image: {filename}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing sneaker: {e}")
            self.stats['errors'].append(f"Processing error: {str(e)}")
            return False
    
    def update_sneaker_details(self, sneaker_id, details):
        """Update sneaker with detailed information"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE rapidapi_sneakers 
                    SET description = ?, updated_at = datetime('now')
                    WHERE id = ?
                """, (details.get('description', ''), sneaker_id))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error updating sneaker details: {e}")
    
    def collect_popular_brands(self):
        """Collect data for popular sneaker brands"""
        popular_brands = [
            "nike",
            "adidas", 
            "jordan",
            "new-balance",
            "converse",
            "vans",
            "puma",
            "reebok"
        ]
        
        for brand in popular_brands:
            self.logger.info(f"Searching for: {brand}")
            
            # Search for sneakers
            results = self.search_sneakers(brand, limit=50)
            self.stats['sneakers_found'] += len(results)
            
            # Process each sneaker
            for sneaker in results:
                self.process_sneaker(sneaker)
                time.sleep(0.5)  # Rate limiting
            
            time.sleep(2)  # Delay between brand searches
    
    def generate_report(self):
        """Generate collection report"""
        duration = time.time() - self.stats['start_time']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': round(duration, 1),
            'api_requests': self.stats['api_requests'],
            'sneakers_found': self.stats['sneakers_found'],
            'sneakers_saved': self.stats['sneakers_saved'],
            'images_downloaded': self.stats['images_downloaded'],
            'prices_collected': self.stats['prices_collected'],
            'success_rate': f"{(self.stats['sneakers_saved'] / max(1, self.stats['sneakers_found']) * 100):.1f}%",
            'errors': self.stats['errors'][-10:]  # Last 10 errors
        }
        
        # Save report
        with open('rapidapi_sneaker_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\nRapidAPI Sneaker Collection Report")
        print(f"==================================")
        print(f"Duration: {duration:.1f} seconds")
        print(f"API requests: {self.stats['api_requests']}")
        print(f"Sneakers found: {self.stats['sneakers_found']}")
        print(f"Sneakers saved: {self.stats['sneakers_saved']}")
        print(f"Images downloaded: {self.stats['images_downloaded']}")
        print(f"Prices collected: {self.stats['prices_collected']}")
        print(f"Success rate: {(self.stats['sneakers_saved'] / max(1, self.stats['sneakers_found']) * 100):.1f}%")
        
        return report
    
    def run(self):
        """Run the RapidAPI sneaker collection"""
        self.logger.info("Starting RapidAPI Sneaker Collection")
        
        try:
            # Collect popular brands
            self.collect_popular_brands()
            
            # Generate final report
            report = self.generate_report()
            self.logger.info("RapidAPI Sneaker Collection completed")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Collection failed: {e}")
            return None

def main():
    """Main function"""
    collector = RapidAPISneakerIntegration()
    
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