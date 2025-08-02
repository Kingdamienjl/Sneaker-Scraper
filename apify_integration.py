#!/usr/bin/env python3
"""
Apify Integration for Sneaker Scraping
Manages Apify actors for comprehensive sneaker data collection
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

try:
    from apify_client import ApifyClient
except ImportError:
    print("❌ apify-client not installed. Install with: pip install apify-client")
    sys.exit(1)

class ApifyIntegration:
    def __init__(self, api_key, time_limit_hours=2):
        self.api_key = api_key
        self.time_limit_hours = time_limit_hours
        self.setup_logging()
        self.setup_directories()
        self.setup_database()
        self.setup_apify_client()
        self.setup_stats()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('apify_integration')
        self.logger.setLevel(logging.INFO)
        
        # File handler with UTF-8 encoding
        log_file = os.path.join(log_dir, f"apify_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
        self.image_dir = os.path.join("data", "apify_images")
        os.makedirs(self.image_dir, exist_ok=True)
        
    def setup_database(self):
        """Setup database connection with proper handling"""
        self.db_path = "sneakers.db"
        self.db_lock = threading.Lock()
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for Apify data"""
        with self.db_lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                # Create Apify runs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS apify_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT UNIQUE,
                        actor_id TEXT,
                        scraper_type TEXT,
                        status TEXT,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        items_count INTEGER DEFAULT 0,
                        error_message TEXT
                    )
                """)
                
                # Create Apify items table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS apify_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT,
                        item_data TEXT,
                        processed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (run_id) REFERENCES apify_runs (run_id)
                    )
                """)
                
                # Create Apify images table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS apify_images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT,
                        url TEXT,
                        local_path TEXT,
                        image_hash TEXT,
                        drive_path TEXT,
                        drive_id TEXT,
                        drive_status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (run_id) REFERENCES apify_runs (run_id)
                    )
                """)
                
                conn.commit()
                conn.close()
                self.logger.info("Apify database tables initialized successfully")
                
            except Exception as e:
                self.logger.error(f"Database initialization error: {e}")
                
    def setup_apify_client(self):
        """Setup Apify client"""
        try:
            self.client = ApifyClient(self.api_key)
            self.logger.info("Apify client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Apify client: {e}")
            raise
            
    def setup_stats(self):
        """Initialize statistics tracking"""
        self.stats = {
            'start_time': time.time(),
            'runs_started': 0,
            'runs_completed': 0,
            'items_scraped': 0,
            'images_downloaded': 0,
            'drive_uploads': 0,
            'duplicates_removed': 0,
            'scrapers': {},
            'errors': []
        }
        
    def get_database_connection(self):
        """Get a database connection with proper timeout"""
        return sqlite3.connect(self.db_path, timeout=30.0)
    
    def check_time_limit(self):
        """Check if we're within the time limit"""
        elapsed = time.time() - self.stats['start_time']
        return elapsed < (self.time_limit_hours * 3600)
    
    def run_nike_scraper(self, max_items=100):
        """Run Nike sneaker scraper"""
        try:
            self.logger.info(f"Starting Nike scraper (max {max_items} items)")
            
            # Nike scraper configuration
            run_input = {
                "startUrls": [
                    {"url": "https://www.nike.com/w/mens-shoes-nik1zy7ok"},
                    {"url": "https://www.nike.com/w/womens-shoes-5e1x6zy7ok"},
                    {"url": "https://www.nike.com/w/jordan-37eefznik1"}
                ],
                "maxItems": max_items,
                "proxyConfiguration": {"useApifyProxy": True}
            }
            
            # Start the run
            run = self.client.actor("apify/web-scraper").call(run_input=run_input)
            run_id = run["id"]
            
            # Save run to database
            self.save_run_to_database(run_id, "apify/web-scraper", "nike")
            self.stats['runs_started'] += 1
            
            if "nike" not in self.stats['scrapers']:
                self.stats['scrapers']['nike'] = {'runs': 0, 'items': 0, 'images': 0}
            self.stats['scrapers']['nike']['runs'] += 1
            
            self.logger.info(f"Nike scraper started with run ID: {run_id}")
            return run_id
            
        except Exception as e:
            self.logger.error(f"Failed to start Nike scraper: {e}")
            self.stats['errors'].append(f"Nike scraper start error: {str(e)}")
            return None
    
    def run_general_sneakers_scraper(self, max_items=100):
        """Run general sneakers scraper"""
        try:
            self.logger.info(f"Starting general sneakers scraper (max {max_items} items)")
            
            # General sneaker sites
            run_input = {
                "startUrls": [
                    {"url": "https://www.footlocker.com/category/mens/shoes.html"},
                    {"url": "https://www.finishline.com/store/men/shoes"},
                    {"url": "https://www.eastbay.com/category/mens/shoes.html"}
                ],
                "maxItems": max_items,
                "proxyConfiguration": {"useApifyProxy": True}
            }
            
            # Start the run
            run = self.client.actor("apify/web-scraper").call(run_input=run_input)
            run_id = run["id"]
            
            # Save run to database
            self.save_run_to_database(run_id, "apify/web-scraper", "general_sneakers")
            self.stats['runs_started'] += 1
            
            if "general_sneakers" not in self.stats['scrapers']:
                self.stats['scrapers']['general_sneakers'] = {'runs': 0, 'items': 0, 'images': 0}
            self.stats['scrapers']['general_sneakers']['runs'] += 1
            
            self.logger.info(f"General sneakers scraper started with run ID: {run_id}")
            return run_id
            
        except Exception as e:
            self.logger.error(f"Failed to start general sneakers scraper: {e}")
            self.stats['errors'].append(f"General sneakers scraper start error: {str(e)}")
            return None
    
    def save_run_to_database(self, run_id, actor_id, scraper_type):
        """Save run information to database"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO apify_runs (run_id, actor_id, scraper_type, status)
                    VALUES (?, ?, ?, ?)
                """, (run_id, actor_id, scraper_type, "running"))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error saving run to database: {e}")
    
    def wait_for_run_completion(self, run_id, timeout_minutes=30):
        """Wait for a run to complete"""
        try:
            self.logger.info(f"Waiting for run {run_id} to complete (timeout: {timeout_minutes} min)")
            
            start_time = time.time()
            timeout_seconds = timeout_minutes * 60
            
            while time.time() - start_time < timeout_seconds:
                if not self.check_time_limit():
                    self.logger.warning("Time limit reached, stopping wait")
                    return False
                
                try:
                    run_info = self.client.run(run_id).get()
                    status = run_info.get("status")
                    
                    if status == "SUCCEEDED":
                        self.logger.info(f"Run {run_id} completed successfully")
                        self.update_run_status(run_id, "completed")
                        return True
                    elif status == "FAILED":
                        self.logger.error(f"Run {run_id} failed")
                        self.update_run_status(run_id, "failed", error_message="Run failed")
                        return False
                    elif status in ["RUNNING", "READY"]:
                        self.logger.info(f"Run {run_id} status: {status}")
                        time.sleep(30)  # Wait 30 seconds before checking again
                    else:
                        self.logger.warning(f"Unknown status for run {run_id}: {status}")
                        time.sleep(30)
                        
                except Exception as e:
                    self.logger.error(f"Error checking run status: {e}")
                    time.sleep(30)
            
            self.logger.warning(f"Run {run_id} timed out after {timeout_minutes} minutes")
            self.update_run_status(run_id, "timeout", error_message="Timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for run completion: {e}")
            return False
    
    def process_run_results(self, run_id, scraper_type):
        """Process results from a completed run"""
        try:
            self.logger.info(f"Processing results for run {run_id} ({scraper_type})")
            
            # Get run results
            dataset_client = self.client.run(run_id).dataset()
            items = list(dataset_client.iterate_items())
            
            self.logger.info(f"Retrieved {len(items)} items from run {run_id}")
            
            # Process each item
            for item in items:
                self.process_item(run_id, item, scraper_type)
                
            # Update statistics
            self.stats['items_scraped'] += len(items)
            self.stats['runs_completed'] += 1
            
            if scraper_type in self.stats['scrapers']:
                self.stats['scrapers'][scraper_type]['items'] += len(items)
            
            self.update_run_status(run_id, "processed", len(items))
            self.logger.info(f"Processed {len(items)} items from run {run_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing run results: {e}")
            self.stats['errors'].append(f"Process results error for {run_id}: {str(e)}")
    
    def process_item(self, run_id, item, scraper_type):
        """Process a single scraped item"""
        try:
            # Save item to database
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO apify_items (run_id, item_data)
                    VALUES (?, ?)
                """, (run_id, json.dumps(item)))
                
                conn.commit()
                conn.close()
            
            # Extract and download images
            self.extract_and_download_images(run_id, item, scraper_type)
            
        except Exception as e:
            self.logger.error(f"Error processing item: {e}")
    
    def extract_and_download_images(self, run_id, item, scraper_type):
        """Extract and download images from an item"""
        try:
            image_urls = []
            
            # Extract image URLs based on scraper type
            if scraper_type == "nike":
                # Nike-specific image extraction
                if "images" in item:
                    image_urls.extend(item["images"])
                if "productImages" in item:
                    image_urls.extend(item["productImages"])
            else:
                # General image extraction
                for key, value in item.items():
                    if isinstance(value, str) and any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        image_urls.append(value)
                    elif isinstance(value, list):
                        for v in value:
                            if isinstance(v, str) and any(ext in v.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                                image_urls.append(v)
            
            # Download images
            for url in image_urls[:5]:  # Limit to 5 images per item
                if self.check_time_limit():
                    self.download_image(run_id, url, scraper_type)
                else:
                    break
                    
        except Exception as e:
            self.logger.error(f"Error extracting images: {e}")
    
    def download_image(self, run_id, url, scraper_type):
        """Download a single image"""
        try:
            if not url or not url.startswith(('http://', 'https://')):
                return
                
            # Generate filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"{scraper_type}_{url_hash}.jpg"
            local_path = os.path.join(self.image_dir, filename)
            
            # Skip if already exists
            if os.path.exists(local_path):
                return
            
            # Download image
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Calculate image hash
            with open(local_path, 'rb') as f:
                image_hash = hashlib.md5(f.read()).hexdigest()
            
            # Save to database
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO apify_images (run_id, url, local_path, image_hash)
                    VALUES (?, ?, ?, ?)
                """, (run_id, url, local_path, image_hash))
                
                conn.commit()
                conn.close()
            
            self.stats['images_downloaded'] += 1
            
            # Update scraper stats
            scraper_key = scraper_type
            if scraper_key in self.stats['scrapers']:
                self.stats['scrapers'][scraper_key]['images'] += 1
            
            self.logger.info(f"Downloaded image: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error downloading image {url}: {e}")
    
    def update_run_status(self, run_id, status, items_count=0, error_message=None):
        """Update run status in database"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE apify_runs 
                    SET status = ?, items_count = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE run_id = ?
                """, (status, items_count, error_message, run_id))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error updating run status: {e}")
    
    def generate_report(self):
        """Generate comprehensive report"""
        duration = time.time() - self.stats['start_time']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_hours': round(duration / 3600, 2),
            'time_limit_hours': self.time_limit_hours,
            'runs_started': self.stats['runs_started'],
            'runs_completed': self.stats['runs_completed'],
            'items_scraped': self.stats['items_scraped'],
            'images_downloaded': self.stats['images_downloaded'],
            'drive_uploads': self.stats['drive_uploads'],
            'duplicates_removed': self.stats['duplicates_removed'],
            'scraper_breakdown': self.stats['scrapers'],
            'errors': self.stats['errors'][-20:]  # Last 20 errors
        }
        
        # Save report
        with open('apify_integration_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\nApify Integration Report")
        print(f"========================")
        print(f"Duration: {duration/3600:.1f} hours (Limit: {self.time_limit_hours} hours)")
        print(f"Runs started: {self.stats['runs_started']}")
        print(f"Runs completed: {self.stats['runs_completed']}")
        print(f"Items scraped: {self.stats['items_scraped']}")
        print(f"Images downloaded: {self.stats['images_downloaded']}")
        print(f"Drive uploads: {self.stats['drive_uploads']}")
        print(f"Duplicates removed: {self.stats['duplicates_removed']}")
        
        print(f"\nScraper Breakdown:")
        for scraper, stats in self.stats['scrapers'].items():
            print(f"  {scraper}: {stats['runs']} runs, {stats['items']} items, {stats['images']} images")
        
        return report
        
    def run(self):
        """Run the complete Apify integration process"""
        self.logger.info(f"Starting Apify Integration (Time limit: {self.time_limit_hours} hours)")
        
        try:
            run_ids = []
            
            # Start all scrapers
            if self.check_time_limit():
                nike_run = self.run_nike_scraper(max_items=150)
                if nike_run:
                    run_ids.append((nike_run, "nike"))
                    
            if self.check_time_limit():
                general_run = self.run_general_sneakers_scraper(max_items=100)
                if general_run:
                    run_ids.append((general_run, "general_sneakers"))
            
            # Wait for runs to complete and process results
            for run_id, scraper_type in run_ids:
                if not self.check_time_limit():
                    break
                    
                if self.wait_for_run_completion(run_id, timeout_minutes=45):
                    self.process_run_results(run_id, scraper_type)
                    
            # Generate final report
            report = self.generate_report()
            self.logger.info("Apify Integration completed successfully")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Integration failed: {e}")
            return None

def main():
    """Main function"""
    # Get API key from environment variable
    api_key = os.getenv('APIFY_API_KEY')
    if not api_key:
        print("❌ APIFY_API_KEY environment variable not set!")
        print("Please set your Apify API key in the environment variables")
        return
    
    # Initialize integration with 2-hour time limit
    integration = ApifyIntegration(api_key, time_limit_hours=2)
    
    try:
        # Run the integration
        report = integration.run()
        
        if report and report['items_scraped'] > 0:
            print(f"\nSuccess! Scraped {report['items_scraped']} items with {report['images_downloaded']} images")
            print(f"Uploaded {report['drive_uploads']} images to Google Drive")
            print(f"Removed {report['duplicates_removed']} duplicate images")
        else:
            print(f"\nIntegration completed. Check the logs for details.")
            
    except KeyboardInterrupt:
        print("\nIntegration interrupted by user")
    except Exception as e:
        print(f"Integration failed: {e}")

if __name__ == "__main__":
    main()