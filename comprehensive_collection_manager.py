#!/usr/bin/env python3
"""
Comprehensive Collection Manager
Scrapes 2000+ shoe metadata entries and 1000+ individual shoe images
with advanced duplicate prevention and non-shoe image filtering
"""

import os
import sys
import time
import json
import sqlite3
import hashlib
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import imagehash
from PIL import Image
import cv2
import numpy as np
import io
import re

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_drive import GoogleDriveManager
from database import SessionLocal
from models import Sneaker, SneakerImage, PriceHistory

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_collection.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ComprehensiveCollectionManager:
    """Advanced collection manager with duplicate prevention and quality filtering"""
    
    def __init__(self):
        # API credentials
        self.scrapeninja_key = "aed6d6ba061f3f5bdb457d1ef0ae46bcf9193423fa8bba6b7e9d391bf911721f"
        self.scrapeninja_url = "https://scrapeninja.apiroad.net/scrape"
        self.browseai_key = "c6639012-5b3b-4f11-a0c4-3e5804a82c1d:dd38b1a2-9ee9-487c-a595-dfc8bde92168"
        
        # Database and storage
        self.db_path = "sneakers.db"
        self.image_dir = "data/comprehensive_images"
        os.makedirs(self.image_dir, exist_ok=True)
        
        # Initialize Google Drive
        try:
            self.drive_manager = GoogleDriveManager()
            logger.info("✅ Google Drive integration enabled")
        except Exception as e:
            self.drive_manager = None
            logger.warning(f"⚠️ Google Drive integration disabled: {e}")
        
        # Rate limiting and quotas
        self.api_requests = 0
        self.api_limit = 200  # Conservative limit
        self.last_request_time = 0
        self.min_delay = 1.5
        
        # Collection targets
        self.metadata_target = 2000
        self.image_target = 1000
        
        # Statistics tracking
        self.stats = {
            'start_time': datetime.now(),
            'metadata_collected': 0,
            'images_collected': 0,
            'duplicates_prevented': 0,
            'non_shoe_filtered': 0,
            'api_requests_used': 0,
            'errors': 0,
            'quality_filtered': 0
        }
        
        # Duplicate prevention
        self.processed_hashes = set()
        self.processed_urls = set()
        self.processed_names = set()
        
        # Load existing data to prevent duplicates
        self._load_existing_data()
        
        # Enhanced search terms for comprehensive coverage
        self.search_terms = [
            # Nike Categories
            "Nike Air Jordan 1", "Nike Air Jordan 4", "Nike Air Jordan 11", "Nike Air Jordan 3",
            "Nike Air Max 90", "Nike Air Max 1", "Nike Air Max 97", "Nike Air Force 1",
            "Nike Dunk Low", "Nike Dunk High", "Nike SB Dunk", "Nike Blazer",
            "Nike React", "Nike Zoom", "Nike Air Presto", "Nike Cortez",
            
            # Adidas Categories
            "Adidas Yeezy 350", "Adidas Yeezy 700", "Adidas Yeezy 500", "Adidas Ultraboost",
            "Adidas NMD", "Adidas Stan Smith", "Adidas Superstar", "Adidas Gazelle",
            "Adidas Forum", "Adidas Continental", "Adidas Ozweego", "Adidas ZX",
            
            # Other Popular Brands
            "New Balance 550", "New Balance 990", "New Balance 2002R", "New Balance 327",
            "Converse Chuck Taylor", "Converse One Star", "Vans Old Skool", "Vans Sk8-Hi",
            "Puma Suede", "Puma RS-X", "Reebok Classic", "ASICS Gel-Lyte",
            
            # Collaborations and Limited Editions
            "Travis Scott Jordan", "Off-White Nike", "Fragment Jordan", "Dior Jordan",
            "Supreme Nike", "Stussy Nike", "Union Jordan", "Chicago Jordan",
            "Bred Jordan", "Royal Jordan", "Shadow Jordan", "Shattered Backboard"
        ]
        
        # Quality filters for images
        self.min_resolution = (300, 300)
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.min_file_size = 5 * 1024  # 5KB
        
        # Non-shoe detection keywords
        self.non_shoe_keywords = [
            'person', 'people', 'model', 'wearing', 'outfit', 'fashion',
            'lifestyle', 'street', 'portrait', 'face', 'body', 'legs',
            'feet', 'socks', 'pants', 'jeans', 'shorts', 'dress'
        ]
        
        # Shoe-specific keywords for validation
        self.shoe_keywords = [
            'sneaker', 'shoe', 'jordan', 'nike', 'adidas', 'yeezy',
            'dunk', 'air max', 'force', 'boost', 'sole', 'laces',
            'upper', 'midsole', 'outsole', 'toe box', 'heel'
        ]
    
    def _load_existing_data(self):
        """Load existing data to prevent duplicates"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load existing sneaker names and SKUs
            cursor.execute("SELECT name, sku FROM sneakers WHERE name IS NOT NULL")
            for name, sku in cursor.fetchall():
                if name:
                    self.processed_names.add(name.lower().strip())
                if sku:
                    self.processed_names.add(sku.lower().strip())
            
            # Load existing image URLs
            cursor.execute("SELECT url FROM images WHERE url IS NOT NULL")
            for (url,) in cursor.fetchall():
                if url:
                    self.processed_urls.add(url)
            
            conn.close()
            logger.info(f"📊 Loaded {len(self.processed_names)} existing names, {len(self.processed_urls)} existing URLs")
            
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    def run_comprehensive_collection(self):
        """Run the comprehensive collection process"""
        logger.info("🚀 Starting Comprehensive Collection Manager")
        logger.info("=" * 60)
        logger.info(f"🎯 Targets: {self.metadata_target} metadata entries, {self.image_target} images")
        logger.info(f"🕐 Started: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        try:
            # Phase 1: Metadata Collection
            logger.info("\n📊 Phase 1: Metadata Collection")
            self._collect_metadata()
            
            # Phase 2: Image Collection
            logger.info("\n🖼️ Phase 2: Image Collection")
            self._collect_images()
            
            # Phase 3: Quality Analysis and Cleanup
            logger.info("\n🔍 Phase 3: Quality Analysis")
            self._analyze_and_cleanup()
            
            # Final report
            self._generate_final_report()
            
        except Exception as e:
            logger.error(f"Critical error in collection: {e}")
            self.stats['errors'] += 1
    
    def _collect_metadata(self):
        """Collect sneaker metadata from multiple sources"""
        collected = 0
        
        for i, search_term in enumerate(self.search_terms):
            if collected >= self.metadata_target:
                break
            
            logger.info(f"🔍 Searching: {search_term} ({i+1}/{len(self.search_terms)})")
            
            try:
                # Try multiple collection methods
                methods = [
                    self._scrape_stockx_search,
                    self._scrape_goat_search,
                    self._scrape_nike_search,
                    self._scrape_adidas_search
                ]
                
                for method in methods:
                    if collected >= self.metadata_target:
                        break
                    
                    try:
                        results = method(search_term)
                        for result in results:
                            if self._save_metadata(result):
                                collected += 1
                                self.stats['metadata_collected'] = collected
                                
                                if collected % 50 == 0:
                                    logger.info(f"   ✅ Collected {collected}/{self.metadata_target} metadata entries")
                                
                                if collected >= self.metadata_target:
                                    break
                    
                    except Exception as e:
                        logger.error(f"Error in method {method.__name__}: {e}")
                        self.stats['errors'] += 1
                
                # Rate limiting between search terms
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing search term '{search_term}': {e}")
                self.stats['errors'] += 1
        
        logger.info(f"📊 Metadata collection complete: {collected}/{self.metadata_target}")
    
    def _collect_images(self):
        """Collect high-quality shoe images"""
        # Get sneakers that need images
        sneakers = self._get_sneakers_needing_images()
        logger.info(f"🎯 Found {len(sneakers)} sneakers needing images")
        
        collected = 0
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            for sneaker in sneakers:
                if collected >= self.image_target:
                    break
                
                future = executor.submit(self._collect_sneaker_images, sneaker)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    images_found = future.result()
                    collected += images_found
                    self.stats['images_collected'] = collected
                    
                    if collected % 25 == 0:
                        logger.info(f"   🖼️ Collected {collected}/{self.image_target} images")
                    
                except Exception as e:
                    logger.error(f"Error in image collection future: {e}")
                    self.stats['errors'] += 1
        
        logger.info(f"🖼️ Image collection complete: {collected}/{self.image_target}")
    
    def _collect_sneaker_images(self, sneaker: Dict) -> int:
        """Collect images for a specific sneaker"""
        images_found = 0
        
        try:
            search_query = f"{sneaker['brand']} {sneaker['model']}"
            if sneaker.get('colorway'):
                search_query += f" {sneaker['colorway']}"
            
            # Try multiple image sources
            sources = [
                self._search_google_images,
                self._search_bing_images,
                self._scrape_product_images
            ]
            
            for source in sources:
                if images_found >= 3:  # Limit per sneaker
                    break
                
                try:
                    image_urls = source(search_query, sneaker)
                    
                    for url in image_urls:
                        if images_found >= 3:
                            break
                        
                        if self._is_valid_image_url(url) and self._download_and_validate_image(url, sneaker):
                            images_found += 1
                
                except Exception as e:
                    logger.error(f"Error in image source {source.__name__}: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting images for {sneaker.get('name', 'Unknown')}: {e}")
        
        return images_found
    
    def _download_and_validate_image(self, url: str, sneaker: Dict) -> bool:
        """Download and validate image quality and content"""
        try:
            # Check for duplicates
            if url in self.processed_urls:
                self.stats['duplicates_prevented'] += 1
                return False
            
            # Download image
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code != 200:
                return False
            
            # Size validation
            if len(response.content) < self.min_file_size or len(response.content) > self.max_file_size:
                self.stats['quality_filtered'] += 1
                return False
            
            # Image validation
            try:
                image = Image.open(io.BytesIO(response.content))
                
                # Resolution check
                if image.size[0] < self.min_resolution[0] or image.size[1] < self.min_resolution[1]:
                    self.stats['quality_filtered'] += 1
                    return False
                
                # Duplicate hash check
                img_hash = str(imagehash.phash(image))
                if img_hash in self.processed_hashes:
                    self.stats['duplicates_prevented'] += 1
                    return False
                
                # Non-shoe content detection
                if self._is_non_shoe_image(url, image):
                    self.stats['non_shoe_filtered'] += 1
                    return False
                
                # Save image
                filename = f"sneaker_{sneaker['id']}_{int(time.time())}_{hashlib.md5(url.encode()).hexdigest()[:8]}.jpg"
                filepath = os.path.join(self.image_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                # Save to database
                self._save_image_record(sneaker['id'], url, filepath)
                
                # Upload to Google Drive if available
                if self.drive_manager:
                    try:
                        drive_url = self.drive_manager.upload_image(filepath, filename)
                        if drive_url:
                            self._update_image_drive_url(sneaker['id'], url, drive_url)
                    except Exception as e:
                        logger.warning(f"Drive upload failed: {e}")
                
                # Track processed
                self.processed_urls.add(url)
                self.processed_hashes.add(img_hash)
                
                return True
                
            except Exception as e:
                logger.error(f"Image processing error: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return False
    
    def _is_non_shoe_image(self, url: str, image: Image.Image) -> bool:
        """Detect if image contains non-shoe content"""
        try:
            # URL-based detection
            url_lower = url.lower()
            for keyword in self.non_shoe_keywords:
                if keyword in url_lower:
                    return True
            
            # Check for shoe keywords in URL
            has_shoe_keyword = any(keyword in url_lower for keyword in self.shoe_keywords)
            if not has_shoe_keyword:
                # Additional validation needed
                pass
            
            # Basic image analysis
            img_array = np.array(image.convert('RGB'))
            
            # Check aspect ratio (shoes are typically wider than tall)
            aspect_ratio = image.width / image.height
            if aspect_ratio < 0.5 or aspect_ratio > 3.0:
                return True  # Likely not a shoe
            
            # Color analysis - shoes typically have consistent color regions
            # This is a simplified check
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_ratio = np.sum(edges > 0) / edges.size
            
            # Too many edges might indicate complex scenes with people
            if edge_ratio > 0.3:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Non-shoe detection error: {e}")
            return False  # Default to keeping the image
    
    def _scrape_stockx_search(self, search_term: str) -> List[Dict]:
        """Scrape StockX search results"""
        results = []
        
        try:
            if self.api_requests >= self.api_limit:
                return results
            
            search_url = f"https://stockx.com/search?s={search_term.replace(' ', '%20')}"
            html = self._scrape_with_api(search_url)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract product data from StockX
                products = soup.find_all('div', class_='browse-tile')
                
                for product in products[:10]:  # Limit per search
                    try:
                        name_elem = product.find('p', class_='tile-name')
                        price_elem = product.find('div', class_='tile-price')
                        
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            
                            # Extract brand and model
                            brand = self._extract_brand(name)
                            model = self._extract_model(name, brand)
                            
                            result = {
                                'name': name,
                                'brand': brand,
                                'model': model,
                                'colorway': self._extract_colorway(name),
                                'price': self._extract_price(price_elem.get_text(strip=True) if price_elem else ''),
                                'platform': 'StockX',
                                'source_url': search_url
                            }
                            
                            results.append(result)
                    
                    except Exception as e:
                        logger.error(f"Error parsing StockX product: {e}")
        
        except Exception as e:
            logger.error(f"Error scraping StockX: {e}")
        
        return results
    
    def _scrape_with_api(self, url: str) -> Optional[str]:
        """Scrape URL using ScrapeNinja API with rate limiting"""
        if self.api_requests >= self.api_limit:
            return None
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        
        try:
            payload = {
                "url": url,
                "headers": [
                    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                ],
                "geo": "us",
                "retryNum": 1,
                "timeout": 15
            }
            
            headers = {
                "x-apiroad-key": self.scrapeninja_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.scrapeninja_url, json=payload, headers=headers, timeout=30)
            self.api_requests += 1
            self.stats['api_requests_used'] = self.api_requests
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                return result.get('body', '')
            
            return None
            
        except Exception as e:
            logger.error(f"API scraping error for {url}: {e}")
            return None
    
    def _save_metadata(self, data: Dict) -> bool:
        """Save metadata to database with duplicate prevention"""
        try:
            # Check for duplicates
            name_key = data['name'].lower().strip()
            if name_key in self.processed_names:
                self.stats['duplicates_prevented'] += 1
                return False
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sneakers (name, brand, model, colorway, retail_price, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data['name'],
                data['brand'],
                data['model'],
                data.get('colorway', ''),
                data.get('price'),
                f"Collected from {data.get('platform', 'Unknown')}",
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            # Track processed
            self.processed_names.add(name_key)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            return False
    
    def _generate_final_report(self):
        """Generate comprehensive final report"""
        duration = datetime.now() - self.stats['start_time']
        
        report = f"""
🎉 COMPREHENSIVE COLLECTION COMPLETE
{'=' * 60}
📊 COLLECTION SUMMARY:
   • Metadata Collected: {self.stats['metadata_collected']}/{self.metadata_target}
   • Images Collected: {self.stats['images_collected']}/{self.image_target}
   • Duration: {duration}
   
🛡️ QUALITY CONTROL:
   • Duplicates Prevented: {self.stats['duplicates_prevented']}
   • Non-shoe Images Filtered: {self.stats['non_shoe_filtered']}
   • Quality Filtered: {self.stats['quality_filtered']}
   
📡 API USAGE:
   • Requests Used: {self.stats['api_requests_used']}/{self.api_limit}
   • Errors: {self.stats['errors']}
   
💾 STORAGE:
   • Local Images: {self.image_dir}
   • Database: {self.db_path}
   • Google Drive: {'✅ Enabled' if self.drive_manager else '❌ Disabled'}
{'=' * 60}
        """
        
        logger.info(report)
        
        # Save detailed report
        report_data = {
            'timestamp': time.time(),
            'duration_seconds': duration.total_seconds(),
            'stats': self.stats,
            'targets': {
                'metadata': self.metadata_target,
                'images': self.image_target
            },
            'completion_rates': {
                'metadata': (self.stats['metadata_collected'] / self.metadata_target) * 100,
                'images': (self.stats['images_collected'] / self.image_target) * 100
            }
        }
        
        with open('comprehensive_collection_report.json', 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info("📄 Detailed report saved to comprehensive_collection_report.json")
    
    def _get_sneakers_needing_images(self) -> List[Dict]:
        """Get sneakers that need images from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
            SELECT s.id, s.name, s.brand, s.model, s.colorway,
                   COUNT(i.id) as image_count
            FROM sneakers s
            LEFT JOIN images i ON s.id = i.sneaker_id
            GROUP BY s.id
            HAVING image_count < 3
            ORDER BY s.created_at DESC
            LIMIT 500
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            
            return [{
                'id': r[0], 'name': r[1], 'brand': r[2], 
                'model': r[3], 'colorway': r[4], 'image_count': r[5]
            } for r in results]
            
        except Exception as e:
            logger.error(f"Error getting sneakers needing images: {e}")
            return []
    
    def _scrape_goat_search(self, search_term: str) -> List[Dict]:
        """Scrape GOAT search results"""
        results = []
        try:
            if self.api_requests >= self.api_limit:
                return results
            
            search_url = f"https://www.goat.com/search?query={search_term.replace(' ', '%20')}"
            html = self._scrape_with_api(search_url)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                products = soup.find_all('div', class_='ProductTile')
                
                for product in products[:8]:
                    try:
                        name_elem = product.find('h3')
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            brand = self._extract_brand(name)
                            
                            results.append({
                                'name': name,
                                'brand': brand,
                                'model': self._extract_model(name, brand),
                                'colorway': self._extract_colorway(name),
                                'platform': 'GOAT',
                                'source_url': search_url
                            })
                    except Exception as e:
                        logger.error(f"Error parsing GOAT product: {e}")
        except Exception as e:
            logger.error(f"Error scraping GOAT: {e}")
        
        return results
    
    def _scrape_nike_search(self, search_term: str) -> List[Dict]:
        """Scrape Nike search results"""
        results = []
        try:
            if self.api_requests >= self.api_limit:
                return results
            
            search_url = f"https://www.nike.com/w?q={search_term.replace(' ', '%20')}"
            html = self._scrape_with_api(search_url)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                products = soup.find_all('div', class_='product-card')
                
                for product in products[:8]:
                    try:
                        name_elem = product.find('div', class_='product-card__title')
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            
                            results.append({
                                'name': name,
                                'brand': 'Nike',
                                'model': self._extract_model(name, 'Nike'),
                                'colorway': self._extract_colorway(name),
                                'platform': 'Nike',
                                'source_url': search_url
                            })
                    except Exception as e:
                        logger.error(f"Error parsing Nike product: {e}")
        except Exception as e:
            logger.error(f"Error scraping Nike: {e}")
        
        return results
    
    def _scrape_adidas_search(self, search_term: str) -> List[Dict]:
        """Scrape Adidas search results"""
        results = []
        try:
            if self.api_requests >= self.api_limit:
                return results
            
            search_url = f"https://www.adidas.com/us/search?q={search_term.replace(' ', '%20')}"
            html = self._scrape_with_api(search_url)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                products = soup.find_all('div', class_='glass-product-card')
                
                for product in products[:8]:
                    try:
                        name_elem = product.find('h5')
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            
                            results.append({
                                'name': name,
                                'brand': 'Adidas',
                                'model': self._extract_model(name, 'Adidas'),
                                'colorway': self._extract_colorway(name),
                                'platform': 'Adidas',
                                'source_url': search_url
                            })
                    except Exception as e:
                        logger.error(f"Error parsing Adidas product: {e}")
        except Exception as e:
            logger.error(f"Error scraping Adidas: {e}")
        
        return results
    
    def _search_google_images(self, query: str, sneaker: Dict) -> List[str]:
        """Search Google Images for sneaker photos"""
        image_urls = []
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&tbm=isch"
            html = self._scrape_with_api(search_url)
            
            if html:
                # Extract image URLs from Google Images
                import re
                img_pattern = r'"ou":"([^"]+)"'
                matches = re.findall(img_pattern, html)
                
                for match in matches[:5]:
                    if self._is_valid_image_url(match):
                        image_urls.append(match)
        
        except Exception as e:
            logger.error(f"Error searching Google Images: {e}")
        
        return image_urls
    
    def _search_bing_images(self, query: str, sneaker: Dict) -> List[str]:
        """Search Bing Images for sneaker photos"""
        image_urls = []
        try:
            search_url = f"https://www.bing.com/images/search?q={query.replace(' ', '+')}"
            html = self._scrape_with_api(search_url)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                img_elements = soup.find_all('img', class_='mimg')
                
                for img in img_elements[:5]:
                    src = img.get('src')
                    if src and self._is_valid_image_url(src):
                        image_urls.append(src)
        
        except Exception as e:
            logger.error(f"Error searching Bing Images: {e}")
        
        return image_urls
    
    def _scrape_product_images(self, query: str, sneaker: Dict) -> List[str]:
        """Scrape product images from sneaker websites"""
        image_urls = []
        
        # Try brand-specific product pages
        brand_urls = {
            'Nike': f"https://www.nike.com/w?q={query.replace(' ', '%20')}",
            'Adidas': f"https://www.adidas.com/us/search?q={query.replace(' ', '%20')}",
            'Jordan': f"https://www.nike.com/jordan/w?q={query.replace(' ', '%20')}"
        }
        
        brand = sneaker.get('brand', '').lower()
        for brand_key, url in brand_urls.items():
            if brand in brand_key.lower():
                try:
                    html = self._scrape_with_api(url)
                    if html:
                        soup = BeautifulSoup(html, 'html.parser')
                        img_elements = soup.find_all('img')
                        
                        for img in img_elements[:3]:
                            src = img.get('src') or img.get('data-src')
                            if src and self._is_valid_image_url(src):
                                image_urls.append(src)
                                if len(image_urls) >= 3:
                                    break
                except Exception as e:
                    logger.error(f"Error scraping {brand_key}: {e}")
        
        return image_urls
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image URL"""
        if not url or len(url) < 10:
            return False
        
        # Check for image extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        url_lower = url.lower()
        
        # Direct extension check
        if any(ext in url_lower for ext in image_extensions):
            return True
        
        # Check for image-related patterns
        image_patterns = ['image', 'img', 'photo', 'pic', 'thumb']
        if any(pattern in url_lower for pattern in image_patterns):
            return True
        
        return False
    
    def _save_image_record(self, sneaker_id: int, url: str, filepath: str):
        """Save image record to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO images (sneaker_id, url, local_path, created_at)
                VALUES (?, ?, ?, ?)
            """, (sneaker_id, url, filepath, datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving image record: {e}")
    
    def _update_image_drive_url(self, sneaker_id: int, url: str, drive_url: str):
        """Update image record with Google Drive URL"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE images SET drive_url = ? 
                WHERE sneaker_id = ? AND url = ?
            """, (drive_url, sneaker_id, url))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating Drive URL: {e}")
    
    def _extract_brand(self, name: str) -> str:
        """Extract brand from sneaker name"""
        name_lower = name.lower()
        
        brands = {
            'nike': ['nike', 'air jordan', 'jordan'],
            'adidas': ['adidas', 'yeezy'],
            'new balance': ['new balance'],
            'converse': ['converse'],
            'vans': ['vans'],
            'puma': ['puma'],
            'reebok': ['reebok'],
            'asics': ['asics']
        }
        
        for brand, keywords in brands.items():
            if any(keyword in name_lower for keyword in keywords):
                return brand.title()
        
        return 'Unknown'
    
    def _extract_model(self, name: str, brand: str) -> str:
        """Extract model from sneaker name"""
        name_clean = name.replace(brand, '').strip()
        
        # Common model patterns
        models = [
            'Air Jordan 1', 'Air Jordan 4', 'Air Jordan 11', 'Air Max 90',
            'Air Max 1', 'Air Force 1', 'Dunk Low', 'Dunk High',
            'Yeezy 350', 'Yeezy 700', 'Ultraboost', 'NMD',
            'Stan Smith', 'Superstar', 'Chuck Taylor', 'Old Skool'
        ]
        
        name_lower = name.lower()
        for model in models:
            if model.lower() in name_lower:
                return model
        
        # Extract first few words as model
        words = name_clean.split()[:3]
        return ' '.join(words) if words else 'Unknown'
    
    def _extract_colorway(self, name: str) -> str:
        """Extract colorway from sneaker name"""
        # Look for quoted colorways
        quote_match = re.search(r'"([^"]+)"', name)
        if quote_match:
            return quote_match.group(1)
        
        # Look for color words at the end
        color_words = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'grey', 'gray', 'brown', 'pink', 'purple', 'orange']
        words = name.lower().split()
        
        colorway_words = []
        for word in reversed(words):
            if any(color in word for color in color_words):
                colorway_words.insert(0, word.title())
            else:
                break
        
        return ' '.join(colorway_words) if colorway_words else ''
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract price from text"""
        try:
            # Remove currency symbols and extract numbers
            price_clean = re.sub(r'[^\d.]', '', price_text)
            if price_clean:
                return float(price_clean)
        except:
            pass
        return None
    
    def _analyze_and_cleanup(self):
        """Analyze collected data and perform cleanup"""
        logger.info("🔍 Analyzing collected data...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count current data
            cursor.execute("SELECT COUNT(*) FROM sneakers")
            total_sneakers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM images")
            total_images = cursor.fetchone()[0]
            
            logger.info(f"📊 Analysis complete:")
            logger.info(f"   • Total sneakers in database: {total_sneakers}")
            logger.info(f"   • Total images in database: {total_images}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}")

if __name__ == "__main__":
    manager = ComprehensiveCollectionManager()
    manager.run_comprehensive_collection()