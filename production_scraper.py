#!/usr/bin/env python3
"""
Production Sneaker Image Scraper
Combines ScrapeNinja and BrowseAI for optimal coverage
"""

import os
import sqlite3
import requests
import time
import hashlib
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from google_drive import GoogleDriveManager

# Setup logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ProductionScraper:
    def __init__(self):
        # API credentials
        self.scrapeninja_key = "aed6d6ba061f3f5bdb457d1ef0ae46bcf9193423fa8bba6b7e9d391bf911721f"
        self.scrapeninja_url = "https://scrapeninja.apiroad.net/scrape"
        self.browseai_key = "c6639012-5b3b-4f11-a0c4-3e5804a82c1d:dd38b1a2-9ee9-487c-a595-dfc8bde92168"
        self.browseai_url = "https://api.browse.ai/v2"
        
        # Database and storage
        self.db_path = "sneakers.db"
        self.image_dir = "data/production_images"
        os.makedirs(self.image_dir, exist_ok=True)
        
        # Initialize database schema
        self.init_database()
        
        # Google Drive integration
        try:
            self.drive_manager = GoogleDriveManager()
            logging.info("Google Drive integration enabled")
        except:
            self.drive_manager = None
            logging.warning("Google Drive integration disabled")
        
        # Rate limiting
        self.scrapeninja_requests = 0
        self.browseai_requests = 0
        self.scrapeninja_limit = 100
        self.browseai_limit = 50
        self.last_request_time = 0
        self.min_delay = 2
        
        # Success tracking
        self.stats = {
            'sneakers_processed': 0,
            'images_found': 0,
            'images_downloaded': 0,
            'images_uploaded': 0,
            'scrapeninja_success': 0,
            'browseai_success': 0,
            'errors': []
        }
        
        # Known working product URL patterns
        self.url_patterns = {
            'nike': [
                'https://www.nike.com/t/{model}-{colorway}',
                'https://www.nike.com/w?q={brand}%20{model}'
            ],
            'adidas': [
                'https://www.adidas.com/us/{model}-shoes/{sku}.html',
                'https://www.adidas.com/us/search?q={brand}%20{model}'
            ],
            'stockx': [
                'https://stockx.com/{brand}-{model}-{colorway}',
                'https://stockx.com/search?s={brand}-{model}'
            ],
            'goat': [
                'https://www.goat.com/sneakers/{model}-{colorway}-{sku}',
                'https://www.goat.com/search?query={brand}%20{model}'
            ]
        }
    
    def init_database(self):
        """Initialize database schema if needed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create images table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sneaker_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                local_path TEXT,
                drive_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sneaker_id) REFERENCES sneakers (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_priority_sneakers(self, limit=50):
        """Get sneakers that need images, prioritizing popular brands"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT s.id, s.brand, s.model, s.colorway, s.sku,
               COUNT(i.id) as image_count
        FROM sneakers s
        LEFT JOIN images i ON s.id = i.sneaker_id
        WHERE s.brand IN ('Nike', 'Jordan', 'Adidas', 'Yeezy')
        GROUP BY s.id
        HAVING image_count < 3
        ORDER BY 
            CASE s.brand 
                WHEN 'Nike' THEN 1 
                WHEN 'Jordan' THEN 2 
                WHEN 'Adidas' THEN 3 
                WHEN 'Yeezy' THEN 4 
                ELSE 5 
            END,
            image_count ASC,
            RANDOM()
        LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        sneakers = cursor.fetchall()
        conn.close()
        
        return [{
            'id': s[0], 'brand': s[1], 'model': s[2], 
            'colorway': s[3], 'sku': s[4], 'image_count': s[5]
        } for s in sneakers]
    
    def rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def scrape_with_scrapeninja(self, url):
        """Scrape URL using ScrapeNinja API"""
        if self.scrapeninja_requests >= self.scrapeninja_limit:
            return None
        
        self.rate_limit()
        
        payload = {
            "url": url,
            "headers": [
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            ],
            "geo": "us",
            "retryNum": 1,
            "timeout": 20
        }
        
        headers = {
            "x-apiroad-key": self.scrapeninja_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.scrapeninja_url, json=payload, headers=headers, timeout=30)
            self.scrapeninja_requests += 1
            
            if response.status_code == 200:
                result = response.json()
                body = result.get('body', '')
                if body and len(body) > 5000:
                    self.stats['scrapeninja_success'] += 1
                    return body
            
            return None
            
        except Exception as e:
            self.stats['errors'].append(f"ScrapeNinja error for {url[:50]}: {e}")
            return None
    
    def extract_images_from_html(self, html, base_url):
        """Extract high-quality product images from HTML"""
        if not html:
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            image_urls = set()
            
            # Priority selectors for different sites
            priority_selectors = [
                'img[data-sub-type="product"]',  # Nike
                'img[data-testid="product-detail-image"]',  # StockX
                '.ProductMedia__image img',  # GOAT
                'img[data-automation-id="pdp-image"]',  # Adidas
                'img.product-image',
                'img[alt*="product"]',
                'img[alt*="shoe"]',
                'img[alt*="sneaker"]'
            ]
            
            # Try priority selectors first
            for selector in priority_selectors:
                imgs = soup.select(selector)
                for img in imgs:
                    src = self.get_image_src(img)
                    if src and self.is_high_quality_image(src):
                        image_urls.add(self.normalize_url(src, base_url))
            
            # If no priority images found, try general approach
            if not image_urls:
                all_imgs = soup.find_all('img')
                for img in all_imgs:
                    src = self.get_image_src(img)
                    if src and self.is_product_image(src, img):
                        image_urls.add(self.normalize_url(src, base_url))
            
            # Look for JSON-LD structured data
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        self.extract_images_from_json(data, image_urls, base_url)
                except:
                    continue
            
            return list(image_urls)[:10]  # Limit to 10 images per page
            
        except Exception as e:
            logging.error(f"Error parsing HTML: {e}")
            return []
    
    def get_image_src(self, img):
        """Get the best image source from img tag"""
        return (img.get('src') or 
                img.get('data-src') or 
                img.get('data-lazy-src') or
                img.get('data-original') or
                img.get('srcset', '').split(',')[0].split(' ')[0])
    
    def normalize_url(self, url, base_url):
        """Convert relative URLs to absolute"""
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return urljoin(base_url, url)
        return url
    
    def is_high_quality_image(self, url):
        """Check if image is likely high quality"""
        url_lower = url.lower()
        
        # Look for size indicators
        quality_indicators = [
            '800', '1000', '1200', '1600', 'large', 'xl', 'zoom', 
            'detail', 'hero', 'main', 'primary'
        ]
        
        return any(indicator in url_lower for indicator in quality_indicators)
    
    def is_product_image(self, url, img_tag=None):
        """Check if URL is likely a product image"""
        if not url or len(url) < 10:
            return False
        
        url_lower = url.lower()
        
        # Skip non-product images
        skip_patterns = [
            'logo', 'icon', 'avatar', 'banner', 'header', 'footer',
            'nav', 'menu', 'button', 'arrow', 'social', 'placeholder',
            'loading', 'spinner', '1x1', 'pixel', 'badge', 'star'
        ]
        
        if any(pattern in url_lower for pattern in skip_patterns):
            return False
        
        # Look for product indicators
        product_patterns = [
            'product', 'shoe', 'sneaker', 'nike', 'adidas', 'jordan',
            'item', 'catalog', 'gallery', 'pdp', 'colorway'
        ]
        
        score = sum(1 for pattern in product_patterns if pattern in url_lower)
        
        # Check img tag attributes
        if img_tag:
            alt_text = (img_tag.get('alt', '') or '').lower()
            score += sum(1 for pattern in product_patterns if pattern in alt_text)
        
        return score >= 1
    
    def extract_images_from_json(self, data, image_urls, base_url):
        """Extract images from JSON-LD structured data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key.lower() in ['image', 'images', 'photo', 'photos']:
                    if isinstance(value, str) and value.startswith('http'):
                        image_urls.add(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and item.startswith('http'):
                                image_urls.add(item)
                elif isinstance(value, (dict, list)):
                    self.extract_images_from_json(value, image_urls, base_url)
        elif isinstance(data, list):
            for item in data:
                self.extract_images_from_json(item, image_urls, base_url)
    
    def download_image(self, url, filename):
        """Download and save an image with validation"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, timeout=15, stream=True, headers=headers)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                return False
            
            # Validate file size
            content_length = response.headers.get('content-length')
            if content_length:
                size = int(content_length)
                if size < 15000 or size > 15000000:  # 15KB to 15MB
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
            logging.error(f"Error downloading {url}: {e}")
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
                
            # Check if file is not empty and has some content
            with open(image_path, 'rb') as f:
                header = f.read(10)
                if len(header) < 10:
                    return False
                    
            # Try to open with PIL to verify it's a valid image
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    # Just check if we can get basic info without full verification
                    width, height = img.size
                    if width < 50 or height < 50:  # Too small to be useful
                        return False
            except Exception:
                # If PIL fails, check if it's at least a valid file with image-like content
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
    
    def save_image_to_database(self, sneaker_id, image_url, local_path, drive_url=None):
        """Save image information to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if image already exists
            cursor.execute("""
                SELECT id FROM images 
                WHERE sneaker_id = ? AND url = ?
            """, (sneaker_id, image_url))
            
            if cursor.fetchone():
                conn.close()
                return False
            
            # Insert new image record
            cursor.execute("""
                INSERT INTO images (sneaker_id, url, local_path, drive_url, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (sneaker_id, image_url, local_path, drive_url))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Error saving image to database: {e}")
            return False
    
    def upload_to_drive(self, local_path, sneaker_id):
        """Upload image to Google Drive"""
        if not self.drive_manager:
            return None
        
        try:
            filename = os.path.basename(local_path)
            drive_url = self.drive_manager.upload_image(local_path, filename)
            if drive_url:
                self.stats['images_uploaded'] += 1
                logging.info(f"Uploaded to Drive: {filename}")
            return drive_url
        except Exception as e:
            logging.error(f"Error uploading to Drive: {e}")
            return None
    
    def generate_product_urls(self, sneaker):
        """Generate potential product URLs for a sneaker"""
        brand = sneaker['brand'].lower()
        model = sneaker['model'].lower().replace(' ', '-')
        colorway = (sneaker['colorway'] or '').lower().replace(' ', '-')
        sku = sneaker['sku'] or ''
        
        urls = []
        
        # Nike direct URLs
        if brand in ['nike', 'jordan']:
            urls.extend([
                f"https://www.nike.com/t/{model}-{colorway}",
                f"https://www.nike.com/w?q={sneaker['brand']}%20{sneaker['model']}"
            ])
        
        # Adidas direct URLs
        elif brand == 'adidas':
            urls.extend([
                f"https://www.adidas.com/us/{model}-shoes/{sku}.html",
                f"https://www.adidas.com/us/search?q={sneaker['brand']}%20{sneaker['model']}"
            ])
        
        # Marketplace URLs (work for all brands)
        search_term = f"{sneaker['brand']}-{sneaker['model']}".lower().replace(' ', '-')
        urls.extend([
            f"https://stockx.com/{search_term}",
            f"https://stockx.com/search?s={search_term}",
            f"https://www.goat.com/search?query={sneaker['brand']}%20{sneaker['model']}"
        ])
        
        return urls[:5]  # Limit to 5 URLs per sneaker
    
    def process_sneaker(self, sneaker):
        """Process a single sneaker to collect images"""
        sneaker_id = sneaker['id']
        brand = sneaker['brand']
        model = sneaker['model']
        
        logging.info(f"Processing: {brand} {model} (ID: {sneaker_id})")
        
        urls = self.generate_product_urls(sneaker)
        images_found = 0
        images_downloaded = 0
        
        for url in urls:
            if self.scrapeninja_requests >= self.scrapeninja_limit:
                break
            
            # Scrape the page
            html = self.scrape_with_scrapeninja(url)
            if not html:
                continue
            
            # Extract images
            image_urls = self.extract_images_from_html(html, url)
            images_found += len(image_urls)
            
            # Download up to 3 images per URL
            for i, img_url in enumerate(image_urls[:3]):
                if images_downloaded >= 5:  # Max 5 images per sneaker
                    break
                
                # Generate filename
                url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                filename = f"{sneaker_id}_{url_hash}_{i+1}.jpg"
                
                # Download image
                local_path = self.download_image(img_url, filename)
                if local_path:
                    images_downloaded += 1
                    
                    # Upload to Google Drive
                    drive_url = self.upload_to_drive(local_path, sneaker_id)
                    
                    # Save to database
                    self.save_image_to_database(sneaker_id, img_url, local_path, drive_url)
                    
                    logging.info(f"Downloaded: {filename}")
            
            if images_downloaded >= 5:
                break
        
        self.stats['sneakers_processed'] += 1
        self.stats['images_found'] += images_found
        self.stats['images_downloaded'] += images_downloaded
        
        return {
            'sneaker_id': sneaker_id,
            'images_found': images_found,
            'images_downloaded': images_downloaded
        }
    
    def run_production_collection(self, limit=30):
        """Run the production image collection process"""
        logging.info("Starting Production Image Collection")
        logging.info(f"Limits: ScrapeNinja {self.scrapeninja_limit}, BrowseAI {self.browseai_limit}")
        
        start_time = time.time()
        sneakers = self.get_priority_sneakers(limit)
        
        logging.info(f"Processing {len(sneakers)} sneakers...")
        
        # Process sneakers sequentially to respect rate limits
        for sneaker in sneakers:
            if self.scrapeninja_requests >= self.scrapeninja_limit:
                logging.warning("Reached ScrapeNinja daily limit")
                break
            
            result = self.process_sneaker(sneaker)
            
            # Log progress
            if self.stats['sneakers_processed'] % 5 == 0:
                logging.info(f"Progress: {self.stats['sneakers_processed']}/{len(sneakers)} sneakers processed")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate final report
        success_rate = (self.stats['images_downloaded'] / max(1, self.stats['images_found'])) * 100
        
        report = f"""
        Production Collection Complete!
        ================================
        Time: {duration:.1f} seconds
        Sneakers processed: {self.stats['sneakers_processed']}
        Images found: {self.stats['images_found']}
        Images downloaded: {self.stats['images_downloaded']}
        Images uploaded to Drive: {self.stats['images_uploaded']}
        
        API Usage:
        - ScrapeNinja: {self.scrapeninja_requests}/{self.scrapeninja_limit}
        - BrowseAI: {self.browseai_requests}/{self.browseai_limit}
        
        Success Rates:
        - Download success: {success_rate:.1f}%
        - ScrapeNinja success: {self.stats['scrapeninja_success']}
        
        Errors: {len(self.stats['errors'])}
        """
        
        logging.info(report)
        
        # Save detailed report
        report_data = {
            'timestamp': time.time(),
            'duration': duration,
            'stats': self.stats,
            'api_usage': {
                'scrapeninja': f"{self.scrapeninja_requests}/{self.scrapeninja_limit}",
                'browseai': f"{self.browseai_requests}/{self.browseai_limit}"
            }
        }
        
        with open('production_scraper_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return report_data

if __name__ == "__main__":
    scraper = ProductionScraper()
    scraper.run_production_collection(limit=25)  # Process 25 sneakers