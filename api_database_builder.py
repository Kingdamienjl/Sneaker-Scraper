#!/usr/bin/env python3
"""
Enhanced API-Based Database Builder
Leverages multiple sneaker APIs to build a comprehensive database:
1. Sneaks-API (druv5319) - StockX, GOAT, FlightClub, Stadium Goods data
2. Sneaker-API (HoseaCodes) - Popular sneakers with descriptions and images
3. Our existing scrapers as fallback
"""

import os
import sys
import time
import json
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime

from database import SessionLocal
from models import Sneaker, SneakerImage, PriceHistory, ScrapingLog
from google_drive import GoogleDriveManager
from image_processor import ImageProcessor
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_database_builder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SneaksAPIClient:
    """Client for Sneaks-API (druv5319/Sneaks-API)"""
    
    def __init__(self):
        # Using the public Vercel deployment
        self.base_url = "https://sneaksapi.vercel.app"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SoleID-Database-Builder/1.0'
        })
    
    def search_products(self, query: str, limit: int = 25) -> List[Dict]:
        """Search for sneaker products"""
        try:
            # Clean and format query
            clean_query = query.replace(' ', '%20')
            url = f"{self.base_url}/search/{clean_query}"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data[:limit] if isinstance(data, list) else []
            else:
                logger.warning(f"SneaksAPI search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"SneaksAPI search error: {str(e)}")
            return []
    
    def get_product_details(self, style_id: str) -> Optional[Dict]:
        """Get detailed product information including prices"""
        try:
            url = f"{self.base_url}/id/{style_id}"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"SneaksAPI details failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"SneaksAPI details error: {str(e)}")
            return None
    
    def get_most_popular(self, limit: int = 50) -> List[Dict]:
        """Get most popular sneakers from StockX"""
        try:
            url = f"{self.base_url}/mostpopular"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data[:limit] if isinstance(data, list) else []
            else:
                logger.warning(f"SneaksAPI popular failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"SneaksAPI popular error: {str(e)}")
            return []

class SneakerAPIClient:
    """Client for Sneaker-API (HoseaCodes/Sneaker-Api)"""
    
    def __init__(self):
        self.base_url = "https://sneakerapi.io"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SoleID-Database-Builder/1.0'
        })
    
    def get_all_sneakers(self, limit: int = 100) -> List[Dict]:
        """Get all sneakers from the API"""
        try:
            url = f"{self.base_url}/api/sneakers"
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                # Handle different response formats
                if isinstance(data, dict) and 'sneakers' in data:
                    return data['sneakers'][:limit]
                elif isinstance(data, list):
                    return data[:limit]
                else:
                    return []
            else:
                logger.warning(f"SneakerAPI failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"SneakerAPI error: {str(e)}")
            return []
    
    def search_sneakers(self, brand: str = None, model: str = None) -> List[Dict]:
        """Search sneakers by brand or model"""
        try:
            params = {}
            if brand:
                params['brand'] = brand
            if model:
                params['model'] = model
            
            url = f"{self.base_url}/api/sneakers"
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'sneakers' in data:
                    return data['sneakers']
                elif isinstance(data, list):
                    return data
                else:
                    return []
            else:
                logger.warning(f"SneakerAPI search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"SneakerAPI search error: {str(e)}")
            return []

class APIBasedDatabaseBuilder:
    """Enhanced database builder using multiple APIs"""
    
    def __init__(self):
        self.sneaks_api = SneaksAPIClient()
        self.sneaker_api = SneakerAPIClient()
        self.drive_manager = GoogleDriveManager()
        self.image_processor = ImageProcessor()
        
        # Ensure directories exist
        os.makedirs(Config.IMAGES_DIR, exist_ok=True)
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'sneaks_api_items': 0,
            'sneaker_api_items': 0,
            'images_downloaded': 0,
            'errors': 0,
            'duplicates_skipped': 0
        }
    
    def build_comprehensive_database(self, max_items: int = 1000):
        """Build database using all available APIs"""
        print("🚀 Building Comprehensive Sneaker Database")
        print("=" * 60)
        print(f"🎯 Target: {max_items} sneakers")
        print(f"📡 Sources: Sneaks-API + Sneaker-API + Enhanced Search")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Phase 1: Get popular sneakers from Sneaks-API
            print("\n📈 Phase 1: Popular Sneakers (Sneaks-API)")
            popular_sneakers = self.sneaks_api.get_most_popular(limit=100)
            self._process_sneaks_data(popular_sneakers, "popular")
            
            # Phase 2: Get curated sneakers from Sneaker-API
            print("\n🎨 Phase 2: Curated Collection (Sneaker-API)")
            curated_sneakers = self.sneaker_api.get_all_sneakers(limit=200)
            self._process_sneaker_api_data(curated_sneakers)
            
            # Phase 3: Enhanced search for specific brands
            print("\n🔍 Phase 3: Brand-Specific Search")
            self._enhanced_brand_search(max_items - self.stats['total_processed'])
            
            # Phase 4: Fill gaps with trending searches
            print("\n🌟 Phase 4: Trending Searches")
            self._trending_search_fill(max_items - self.stats['total_processed'])
            
            # Final statistics
            total_time = time.time() - start_time
            self._print_final_stats(total_time)
            
        except Exception as e:
            logger.error(f"Database building error: {str(e)}")
            print(f"❌ Error: {str(e)}")
    
    def _process_sneaks_data(self, sneakers: List[Dict], source: str):
        """Process data from Sneaks-API"""
        db = SessionLocal()
        
        try:
            for sneaker_data in sneakers:
                try:
                    # Get detailed information if style_id available
                    style_id = sneaker_data.get('styleID') or sneaker_data.get('style_id')
                    if style_id:
                        detailed_data = self.sneaks_api.get_product_details(style_id)
                        if detailed_data:
                            sneaker_data.update(detailed_data)
                    
                    # Process and save sneaker
                    if self._save_sneaker_from_sneaks(db, sneaker_data, source):
                        self.stats['sneaks_api_items'] += 1
                        self.stats['total_processed'] += 1
                        
                        if self.stats['total_processed'] % 10 == 0:
                            print(f"   ✅ Processed {self.stats['total_processed']} sneakers...")
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Error processing sneaker: {str(e)}")
                    
        finally:
            db.close()
    
    def _process_sneaker_api_data(self, sneakers: List[Dict]):
        """Process data from Sneaker-API"""
        db = SessionLocal()
        
        try:
            for sneaker_data in sneakers:
                try:
                    if self._save_sneaker_from_sneaker_api(db, sneaker_data):
                        self.stats['sneaker_api_items'] += 1
                        self.stats['total_processed'] += 1
                        
                        if self.stats['total_processed'] % 10 == 0:
                            print(f"   ✅ Processed {self.stats['total_processed']} sneakers...")
                    
                    time.sleep(0.3)  # Rate limiting
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Error processing sneaker: {str(e)}")
                    
        finally:
            db.close()
    
    def _enhanced_brand_search(self, remaining_items: int):
        """Enhanced search for specific brands"""
        if remaining_items <= 0:
            return
        
        brands = ["Nike", "Adidas", "Jordan", "New Balance", "Yeezy", "Off-White", "Travis Scott"]
        models = ["Air Jordan 1", "Air Max", "Ultraboost", "Dunk", "Yeezy 350", "Air Force 1"]
        
        search_terms = []
        for brand in brands:
            search_terms.append(brand)
            for model in models:
                search_terms.append(f"{brand} {model}")
        
        db = SessionLocal()
        try:
            for term in search_terms[:remaining_items//5]:  # Limit searches
                try:
                    results = self.sneaks_api.search_products(term, limit=5)
                    for sneaker_data in results:
                        if self._save_sneaker_from_sneaks(db, sneaker_data, "search"):
                            self.stats['total_processed'] += 1
                            
                            if self.stats['total_processed'] % 10 == 0:
                                print(f"   🔍 Searched: {self.stats['total_processed']} sneakers...")
                    
                    time.sleep(1.0)  # Rate limiting for searches
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Search error for {term}: {str(e)}")
                    
        finally:
            db.close()
    
    def _trending_search_fill(self, remaining_items: int):
        """Fill remaining slots with trending searches"""
        if remaining_items <= 0:
            return
        
        trending_terms = [
            "Jordan 4", "Dunk Low", "Air Max 90", "Yeezy 700", "New Balance 550",
            "Travis Scott", "Fragment", "Off-White", "Supreme", "Stussy",
            "Balenciaga", "Golden Goose", "Common Projects", "Rick Owens"
        ]
        
        db = SessionLocal()
        try:
            for term in trending_terms:
                if self.stats['total_processed'] >= remaining_items:
                    break
                    
                try:
                    results = self.sneaks_api.search_products(term, limit=3)
                    for sneaker_data in results:
                        if self._save_sneaker_from_sneaks(db, sneaker_data, "trending"):
                            self.stats['total_processed'] += 1
                    
                    time.sleep(0.8)
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Trending search error for {term}: {str(e)}")
                    
        finally:
            db.close()
    
    def _save_sneaker_from_sneaks(self, db, data: Dict, source: str) -> bool:
        """Save sneaker data from Sneaks-API format"""
        try:
            # Extract basic info
            name = data.get('shoeName') or data.get('name', '')
            brand = data.get('brand', '')
            style_id = data.get('styleID') or data.get('style_id', '')
            
            if not name:
                return False
            
            # Check for duplicates
            existing = db.query(Sneaker).filter(
                Sneaker.name.ilike(f"%{name}%")
            ).first()
            
            if existing:
                self.stats['duplicates_skipped'] += 1
                return False
            
            # Create sneaker
            sneaker = Sneaker(
                name=name,
                brand=brand or self._extract_brand_from_name(name),
                model=self._extract_model_from_name(name),
                colorway=data.get('colorway', ''),
                sku=style_id,
                retail_price=self._parse_price(data.get('retailPrice')),
                release_date=self._parse_date(data.get('releaseDate')),
                description=data.get('description', '')
            )
            
            db.add(sneaker)
            db.flush()
            
            # Process images
            self._process_images_from_sneaks(db, sneaker, data)
            
            # Process prices
            self._process_prices_from_sneaks(db, sneaker, data)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving Sneaks data: {str(e)}")
            return False
    
    def _save_sneaker_from_sneaker_api(self, db, data: Dict) -> bool:
        """Save sneaker data from Sneaker-API format"""
        try:
            name = data.get('name', '')
            brand = data.get('brand', '')
            
            if not name:
                return False
            
            # Check for duplicates
            existing = db.query(Sneaker).filter(
                Sneaker.name.ilike(f"%{name}%")
            ).first()
            
            if existing:
                self.stats['duplicates_skipped'] += 1
                return False
            
            # Create sneaker
            sneaker = Sneaker(
                name=name,
                brand=brand or self._extract_brand_from_name(name),
                model=data.get('model', ''),
                colorway=data.get('colorway', ''),
                sku=data.get('sku', ''),
                retail_price=self._parse_price(data.get('retailPrice')),
                release_date=self._parse_date(data.get('releaseDate')),
                description=data.get('description', '')
            )
            
            db.add(sneaker)
            db.flush()
            
            # Process images
            if data.get('image'):
                self._save_image(db, sneaker, data['image'], 'main', True)
            
            # Process price
            if data.get('price'):
                price_history = PriceHistory(
                    sneaker_id=sneaker.id,
                    size='Unknown',
                    price=self._parse_price(data['price']),
                    condition='new',
                    platform='SneakerAPI',
                    listing_type='current',
                    sale_date=datetime.utcnow()
                )
                db.add(price_history)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving SneakerAPI data: {str(e)}")
            return False
    
    def _process_images_from_sneaks(self, db, sneaker: Sneaker, data: Dict):
        """Process images from Sneaks-API data"""
        # Main image
        if data.get('thumbnail'):
            self._save_image(db, sneaker, data['thumbnail'], 'main', True)
        
        # Additional images
        if data.get('imageLinks'):
            for i, img_url in enumerate(data['imageLinks'][:5]):  # Limit to 5 images
                self._save_image(db, sneaker, img_url, f'detail_{i}', False)
    
    def _process_prices_from_sneaks(self, db, sneaker: Sneaker, data: Dict):
        """Process price data from Sneaks-API"""
        # StockX prices
        if data.get('lowestResellPrice', {}).get('stockX'):
            price_history = PriceHistory(
                sneaker_id=sneaker.id,
                size='Unknown',
                price=self._parse_price(data['lowestResellPrice']['stockX']),
                condition='new',
                platform='StockX',
                listing_type='current',
                sale_date=datetime.utcnow()
            )
            db.add(price_history)
        
        # GOAT prices
        if data.get('lowestResellPrice', {}).get('goat'):
            price_history = PriceHistory(
                sneaker_id=sneaker.id,
                size='Unknown',
                price=self._parse_price(data['lowestResellPrice']['goat']),
                condition='new',
                platform='GOAT',
                listing_type='current',
                sale_date=datetime.utcnow()
            )
            db.add(price_history)
    
    def _save_image(self, db, sneaker: Sneaker, image_url: str, image_type: str, is_primary: bool):
        """Download and save image"""
        try:
            # Check if image already exists
            existing = db.query(SneakerImage).filter(
                SneakerImage.sneaker_id == sneaker.id,
                SneakerImage.image_url == image_url
            ).first()
            
            if existing:
                return
            
            # Download and process image
            image_filename = f"{sneaker.id}_{image_type}_{int(time.time())}.jpg"
            local_path = os.path.join(Config.IMAGES_DIR, image_filename)
            
            # Download image
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # Process image
                processed_path = self.image_processor.process_image(local_path)
                
                # Upload to Google Drive
                drive_result = self.drive_manager.upload_image(
                    processed_path,
                    image_filename,
                    self.drive_manager.folder_id
                )
                
                if drive_result:
                    # Save to database
                    sneaker_image = SneakerImage(
                        sneaker_id=sneaker.id,
                        image_url=image_url,
                        google_drive_id=drive_result['id'],
                        image_type=image_type,
                        is_primary=is_primary
                    )
                    db.add(sneaker_image)
                    self.stats['images_downloaded'] += 1
                
                # Cleanup
                if os.path.exists(local_path):
                    os.remove(local_path)
                if os.path.exists(processed_path) and processed_path != local_path:
                    os.remove(processed_path)
                    
        except Exception as e:
            logger.error(f"Error saving image {image_url}: {str(e)}")
    
    def _extract_brand_from_name(self, name: str) -> str:
        """Extract brand from sneaker name"""
        name_lower = name.lower()
        brands = ['nike', 'adidas', 'jordan', 'new balance', 'puma', 'reebok', 'converse', 'vans']
        
        for brand in brands:
            if brand in name_lower:
                return brand.title()
        
        return 'Unknown'
    
    def _extract_model_from_name(self, name: str) -> str:
        """Extract model from sneaker name"""
        words = name.split()
        if len(words) >= 2:
            return ' '.join(words[:3])  # Take first 3 words as model
        return name
    
    def _parse_price(self, price_str) -> Optional[float]:
        """Parse price string to float"""
        if not price_str:
            return None
        
        try:
            # Remove currency symbols and convert
            price_clean = str(price_str).replace('$', '').replace(',', '').strip()
            return float(price_clean)
        except:
            return None
    
    def _parse_date(self, date_str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(str(date_str), fmt)
                except:
                    continue
            return None
        except:
            return None
    
    def _print_final_stats(self, total_time: float):
        """Print final statistics"""
        print("\n" + "=" * 60)
        print("🎉 DATABASE BUILDING COMPLETED!")
        print("=" * 60)
        print(f"⏱️  Total Time: {total_time/60:.1f} minutes")
        print(f"📊 Total Processed: {self.stats['total_processed']}")
        print(f"🔥 Sneaks-API Items: {self.stats['sneaks_api_items']}")
        print(f"🎨 Sneaker-API Items: {self.stats['sneaker_api_items']}")
        print(f"🖼️  Images Downloaded: {self.stats['images_downloaded']}")
        print(f"⚠️  Duplicates Skipped: {self.stats['duplicates_skipped']}")
        print(f"❌ Errors: {self.stats['errors']}")
        
        # Database stats
        db = SessionLocal()
        try:
            total_sneakers = db.query(Sneaker).count()
            total_images = db.query(SneakerImage).count()
            total_prices = db.query(PriceHistory).count()
            
            print(f"\n📋 Final Database Stats:")
            print(f"   • Total Sneakers: {total_sneakers}")
            print(f"   • Total Images: {total_images}")
            print(f"   • Total Prices: {total_prices}")
            
        finally:
            db.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API-Based Database Builder")
    parser.add_argument("--max-items", type=int, default=1000,
                       help="Maximum number of sneakers to process")
    parser.add_argument("--test", action="store_true",
                       help="Run in test mode with limited items")
    
    args = parser.parse_args()
    
    if args.test:
        max_items = 50
        print("🧪 Running in TEST MODE")
    else:
        max_items = args.max_items
    
    builder = APIBasedDatabaseBuilder()
    builder.build_comprehensive_database(max_items)

if __name__ == "__main__":
    main()