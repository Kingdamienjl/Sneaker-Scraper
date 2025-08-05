#!/usr/bin/env python3
"""
Working Sneaker Image Collector - Gets REAL sneaker photos from free sources
Uses multiple working APIs and scraping methods for actual sneaker images
"""

import os
import sqlite3
import requests
import json
import time
import logging
import hashlib
import signal
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote, urlencode
import threading
import random
import re
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('working_sneaker_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class WorkingSneakerCollector:
    def __init__(self):
        self.db_path = "sneakers.db"
        self.image_dir = "data/real_sneaker_images"
        os.makedirs(self.image_dir, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # 6-hour collection parameters
        self.start_time = time.time()
        self.end_time = self.start_time + (6 * 60 * 60)  # 6 hours
        self.running = True
        
        # Statistics
        self.stats = {
            'start_time': self.start_time,
            'target_end_time': self.end_time,
            'sneakers_processed': 0,
            'images_found': 0,
            'images_downloaded': 0,
            'api_requests': 0,
            'cycles_completed': 0,
            'source_stats': {'bing': 0, 'duckduckgo': 0, 'yahoo': 0, 'direct': 0},
            'errors': [],
            'hourly_reports': []
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
        
        # Progress tracking
        self.last_report_time = time.time()
        self.report_interval = 3600  # 1 hour reports
        
        # Initialize database
        self.init_database()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.logger.info(f"Working Sneaker Image Collector initialized")
        self.logger.info(f"Start time: {datetime.fromtimestamp(self.start_time)}")
        self.logger.info(f"Target end time: {datetime.fromtimestamp(self.end_time)}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def init_database(self):
        """Initialize database schema for real sneaker images"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create real_sneaker_images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS real_sneaker_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sneaker_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                image_url TEXT NOT NULL,
                local_path TEXT,
                image_type TEXT DEFAULT 'product',
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sneaker_id) REFERENCES sneakers (id)
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("Real sneaker images database initialized")
    
    def rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_bing_images(self, query, count=8):
        """Search Bing Images for real sneaker photos"""
        try:
            self.rate_limit()
            
            # Bing Image Search (no API key needed)
            search_url = "https://www.bing.com/images/search"
            params = {
                'q': f"{query} sneakers shoes",
                'form': 'HDRSC2',
                'first': 1,
                'count': count,
                'qft': '+filterui:imagesize-large+filterui:aspect-wide'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Parse Bing results
                soup = BeautifulSoup(response.content, 'html.parser')
                images = []
                
                # Find image elements
                img_elements = soup.find_all('img', {'class': 'mimg'})
                
                for img in img_elements[:count]:
                    src = img.get('src')
                    if src and src.startswith('http'):
                        images.append({
                            'url': src,
                            'source': 'bing',
                            'width': 800,
                            'height': 600,
                            'tags': query,
                            'description': f"Bing image for {query}"
                        })
                
                self.stats['api_requests'] += 1
                self.logger.info(f"Found {len(images)} Bing images for: {query}")
                return images
            else:
                self.logger.warning(f"Bing search failed: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Bing search error: {e}")
            return []
    
    def search_duckduckgo_images(self, query, count=8):
        """Search DuckDuckGo Images for real sneaker photos"""
        try:
            self.rate_limit()
            
            # DuckDuckGo Image Search
            search_url = "https://duckduckgo.com/"
            params = {
                'q': f"{query} sneakers shoes",
                'iax': 'images',
                'ia': 'images'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # First get the search page
            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Try to extract image URLs from DuckDuckGo
                # This is simplified - real implementation would need more complex parsing
                images = []
                
                # For now, return empty to focus on working sources
                self.logger.debug(f"DuckDuckGo parsing not fully implemented")
                return []
                
        except Exception as e:
            self.logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    def search_direct_sneaker_images(self, query, count=5):
        """Search for direct sneaker images from known patterns"""
        try:
            images = []
            
            # Common sneaker image patterns
            brand = query.split()[0].lower() if query else "nike"
            model = query.replace(brand, "").strip().replace(" ", "-").lower()
            
            # Generate some common sneaker image URLs
            patterns = [
                f"https://images.stockx.com/images/{brand}-{model}-product.jpg",
                f"https://images.footlocker.com/is/image/FLEU/{brand}_{model}",
                f"https://static.nike.com/a/images/t_PDP_1728_v1/f_auto/{model}.jpg",
                f"https://assets.adidas.com/images/h_840,f_auto,q_auto/{model}.jpg"
            ]
            
            for i, pattern in enumerate(patterns[:count]):
                images.append({
                    'url': pattern,
                    'source': 'direct',
                    'width': 800,
                    'height': 600,
                    'tags': query,
                    'description': f"Direct URL for {query}"
                })
            
            self.logger.info(f"Generated {len(images)} direct URLs for: {query}")
            return images
            
        except Exception as e:
            self.logger.error(f"Direct search error: {e}")
            return []
    
    def search_free_stock_photos(self, query, count=5):
        """Search free stock photo sites for sneaker images"""
        try:
            images = []
            
            # Unsplash (free tier)
            unsplash_urls = [
                f"https://source.unsplash.com/800x600/?{quote(query)},sneakers",
                f"https://source.unsplash.com/800x600/?{quote(query)},shoes",
                f"https://source.unsplash.com/800x600/?sneakers,{quote(query.split()[0])}",
                f"https://source.unsplash.com/800x600/?footwear,{quote(query)}"
            ]
            
            for i, url in enumerate(unsplash_urls[:count]):
                images.append({
                    'url': url,
                    'source': 'unsplash_free',
                    'width': 800,
                    'height': 600,
                    'tags': query,
                    'description': f"Unsplash free image for {query}"
                })
            
            self.logger.info(f"Generated {len(images)} Unsplash free URLs for: {query}")
            return images
            
        except Exception as e:
            self.logger.error(f"Free stock photo search error: {e}")
            return []
    
    def search_all_sources(self, query, per_source=3):
        """Search all available sources for real sneaker images"""
        all_images = []
        
        try:
            # Bing Images (most reliable)
            bing_images = self.search_bing_images(query, per_source)
            all_images.extend(bing_images)
            
            # Free stock photos
            stock_images = self.search_free_stock_photos(query, per_source)
            all_images.extend(stock_images)
            
            # Direct URLs (as backup)
            direct_images = self.search_direct_sneaker_images(query, 2)
            all_images.extend(direct_images)
            
            self.logger.info(f"Found {len(all_images)} total images for: {query}")
            return all_images
            
        except Exception as e:
            self.logger.error(f"Error in search_all_sources for {query}: {e}")
            return []
    
    def download_image(self, image_data, sneaker_id):
        """Download and save real sneaker image"""
        try:
            url = image_data['url']
            source = image_data['source']
            
            # Generate filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{source}_{sneaker_id}_{url_hash}.jpg"
            filepath = os.path.join(self.image_dir, filename)
            
            # Skip if already exists
            if os.path.exists(filepath):
                return filepath
            
            # Download image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=20, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            # Check if it's actually an image
            content_type = response.headers.get('content-type', '')
            if not any(img_type in content_type.lower() for img_type in ['image/', 'jpeg', 'jpg', 'png', 'webp']):
                self.logger.warning(f"Not an image: {content_type} for {url}")
                return None
            
            # Save file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Validate image
            if self.validate_image(filepath):
                self.stats['source_stats'][source] = self.stats['source_stats'].get(source, 0) + 1
                self.logger.info(f"Successfully downloaded: {filename}")
                return filepath
            else:
                if os.path.exists(filepath):
                    os.remove(filepath)
                self.logger.warning(f"Invalid image removed: {filename}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error downloading image from {url}: {e}")
            return None
    
    def validate_image(self, image_path):
        """Validate downloaded image is real and good quality"""
        try:
            if not os.path.exists(image_path):
                return False
                
            # Check file size (must be reasonable for a real photo)
            file_size = os.path.getsize(image_path)
            if file_size < 1000:  # Less than 1KB is suspicious
                return False
            if file_size > 15 * 1024 * 1024:  # More than 15MB is too big
                return False
                
            # Check basic image signatures
            with open(image_path, 'rb') as f:
                header = f.read(20)
                
            # JPEG signature
            if header.startswith(b'\xff\xd8\xff'):
                return True
            # PNG signature  
            elif header.startswith(b'\x89PNG\r\n\x1a\n'):
                return True
            # GIF signature
            elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
                return True
            # WebP signature
            elif b'WEBP' in header:
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Image validation failed: {e}")
            return False
    
    def save_image_to_database(self, sneaker_id, image_data, local_path):
        """Save real sneaker image information to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            file_size = os.path.getsize(local_path) if local_path and os.path.exists(local_path) else 0
            
            cursor.execute("""
                INSERT INTO real_sneaker_images (
                    sneaker_id, source, image_url, local_path, 
                    width, height, file_size, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sneaker_id,
                image_data['source'],
                image_data['url'],
                local_path,
                image_data.get('width', 0),
                image_data.get('height', 0),
                file_size,
                image_data.get('tags', '')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving image to database: {e}")
            return False
    
    def collect_images_for_sneaker(self, sneaker_id, name, brand):
        """Collect real images for a single sneaker"""
        try:
            self.logger.info(f"Collecting REAL images for: {name} ({brand})")
            
            # Create search query
            query = f"{brand} {name}".strip()
            if not query:
                query = "sneaker"
            
            # Get images from real sources only
            all_images = self.search_all_sources(query, per_source=4)
            self.stats['images_found'] += len(all_images)
            
            # Download and save images
            downloaded_count = 0
            for image_data in all_images[:8]:  # Max 8 images per sneaker
                local_path = self.download_image(image_data, sneaker_id)
                
                if local_path:
                    if self.save_image_to_database(sneaker_id, image_data, local_path):
                        downloaded_count += 1
                        self.stats['images_downloaded'] += 1
                
                time.sleep(1)  # Pause between downloads
            
            self.logger.info(f"Downloaded {downloaded_count} REAL images for {name}")
            return downloaded_count
            
        except Exception as e:
            self.logger.error(f"Error collecting images for {name}: {e}")
            self.stats['errors'].append(f"Collection error for {name}: {str(e)}")
            return 0
    
    def get_sneakers_batch(self, offset=0, limit=20):
        """Get a batch of sneakers for processing"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get sneakers with fewer real images (prioritize those with 0-2 images)
            cursor.execute("""
                SELECT s.id, s.name, s.brand, COUNT(ri.id) as image_count
                FROM sneakers s
                LEFT JOIN real_sneaker_images ri ON s.id = ri.sneaker_id
                GROUP BY s.id, s.name, s.brand
                HAVING image_count < 3
                ORDER BY image_count ASC, s.id
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            sneakers = cursor.fetchall()
            conn.close()
            
            return sneakers
            
        except Exception as e:
            self.logger.error(f"Error getting sneakers batch: {e}")
            return []
    
    def generate_hourly_report(self):
        """Generate hourly progress report"""
        current_time = time.time()
        duration = current_time - self.stats['start_time']
        remaining_time = self.stats['target_end_time'] - current_time
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_hours': round(duration / 3600, 2),
            'remaining_hours': round(remaining_time / 3600, 2),
            'sneakers_processed': self.stats['sneakers_processed'],
            'images_found': self.stats['images_found'],
            'images_downloaded': self.stats['images_downloaded'],
            'api_requests': self.stats['api_requests'],
            'cycles_completed': self.stats['cycles_completed'],
            'source_breakdown': self.stats['source_stats'],
            'success_rate': f"{(self.stats['images_downloaded'] / max(1, self.stats['images_found']) * 100):.1f}%",
            'avg_images_per_sneaker': round(self.stats['images_downloaded'] / max(1, self.stats['sneakers_processed']), 2),
            'sneakers_per_hour': round(self.stats['sneakers_processed'] / max(0.1, duration / 3600), 1)
        }
        
        self.stats['hourly_reports'].append(report)
        
        # Save report to file
        with open('working_sneaker_progress.json', 'w') as f:
            json.dump({
                'current_report': report,
                'all_reports': self.stats['hourly_reports']
            }, f, indent=2)
        
        # Print progress
        print(f"\n=== REAL SNEAKER IMAGES HOURLY REPORT ===")
        print(f"Time: {report['duration_hours']:.1f}h / 6.0h ({report['remaining_hours']:.1f}h remaining)")
        print(f"Sneakers processed: {report['sneakers_processed']} ({report['sneakers_per_hour']}/hour)")
        print(f"REAL images downloaded: {report['images_downloaded']} (avg {report['avg_images_per_sneaker']}/sneaker)")
        print(f"Success rate: {report['success_rate']}")
        print(f"Source breakdown: {report['source_breakdown']}")
        print("=" * 40)
        
        self.logger.info(f"Hourly report generated - {report['images_downloaded']} REAL images collected")
        
        return report
    
    def run_collection(self):
        """Run the continuous real sneaker image collection"""
        self.logger.info("Starting Working Sneaker Image Collection")
        
        try:
            offset = 0
            batch_size = 12
            
            while self.running and time.time() < self.stats['target_end_time']:
                # Get batch of sneakers
                sneakers = self.get_sneakers_batch(offset, batch_size)
                
                if not sneakers:
                    # No more sneakers, start new cycle
                    self.stats['cycles_completed'] += 1
                    offset = 0
                    self.logger.info(f"Completed cycle {self.stats['cycles_completed']}, starting over...")
                    time.sleep(120)  # 2 minute pause between cycles
                    continue
                
                self.logger.info(f"Processing batch: {len(sneakers)} sneakers (offset: {offset})")
                
                # Process each sneaker in batch
                for sneaker_id, name, brand, current_image_count in sneakers:
                    if not self.running or time.time() >= self.stats['target_end_time']:
                        break
                    
                    self.collect_images_for_sneaker(sneaker_id, name or "Unknown", brand or "Unknown")
                    self.stats['sneakers_processed'] += 1
                    
                    # Longer pause between sneakers to be respectful
                    time.sleep(5)
                
                offset += batch_size
                
                # Generate hourly report
                if time.time() - self.last_report_time >= self.report_interval:
                    self.generate_hourly_report()
                    self.last_report_time = time.time()
                
                # Pause between batches
                time.sleep(15)
            
            # Final report
            self.generate_final_report()
            
        except Exception as e:
            self.logger.error(f"Collection failed: {e}")
            self.generate_final_report()
    
    def generate_final_report(self):
        """Generate final collection report"""
        duration = time.time() - self.stats['start_time']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_duration_hours': round(duration / 3600, 2),
            'target_duration_hours': 6.0,
            'completed_early': duration < (6 * 3600 - 300),
            'sneakers_processed': self.stats['sneakers_processed'],
            'images_found': self.stats['images_found'],
            'images_downloaded': self.stats['images_downloaded'],
            'api_requests': self.stats['api_requests'],
            'cycles_completed': self.stats['cycles_completed'],
            'source_breakdown': self.stats['source_stats'],
            'success_rate': f"{(self.stats['images_downloaded'] / max(1, self.stats['images_found']) * 100):.1f}%",
            'avg_images_per_sneaker': round(self.stats['images_downloaded'] / max(1, self.stats['sneakers_processed']), 2),
            'sneakers_per_hour': round(self.stats['sneakers_processed'] / max(0.1, duration / 3600), 1),
            'errors': self.stats['errors'][-20:],
            'hourly_reports': self.stats['hourly_reports']
        }
        
        # Save final report
        with open('working_sneaker_final_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print final summary
        print(f"\n" + "=" * 60)
        print(f"WORKING SNEAKER IMAGE COLLECTION FINAL REPORT")
        print(f"=" * 60)
        print(f"Duration: {report['total_duration_hours']:.2f} hours")
        print(f"Sneakers processed: {report['sneakers_processed']} ({report['sneakers_per_hour']}/hour)")
        print(f"REAL images downloaded: {report['images_downloaded']}")
        print(f"Average images per sneaker: {report['avg_images_per_sneaker']}")
        print(f"Success rate: {report['success_rate']}")
        print(f"Source breakdown: {report['source_breakdown']}")
        print(f"=" * 60)
        
        self.logger.info("Working Sneaker Image Collection completed")
        return report

def main():
    """Main function"""
    collector = WorkingSneakerCollector()
    
    try:
        # Run collection
        collector.run_collection()
        
    except KeyboardInterrupt:
        print("\nCollection interrupted by user")
        collector.running = False
        collector.generate_final_report()
    except Exception as e:
        print(f"Collection failed: {e}")
        logging.error(f"Collection failed: {e}")
        collector.generate_final_report()

if __name__ == "__main__":
    main()