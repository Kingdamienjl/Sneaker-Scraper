#!/usr/bin/env python3
"""
Enhanced Scraper Manager with API Integration
Combines Sneaks-API, Sneaker-API, and existing scrapers for comprehensive data collection
"""

import os
import sys
import time
import logging
from typing import List, Dict
from datetime import datetime
import asyncio

from database import SessionLocal
from models import Sneaker, SneakerImage, PriceHistory, ScrapingLog
from api_database_builder import APIBasedDatabaseBuilder, SneaksAPIClient, SneakerAPIClient
from modern_scrapers import SneaksAPIScraper, StaticDataScraper, MultiSourceScraper
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_scraper_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedScraperManager:
    """Enhanced scraper manager with multiple API sources"""
    
    def __init__(self):
        self.api_builder = APIBasedDatabaseBuilder()
        self.sneaks_client = SneaksAPIClient()
        self.sneaker_client = SneakerAPIClient()
        self.legacy_scrapers = MultiSourceScraper()
        
        # Statistics
        self.session_stats = {
            'start_time': datetime.now(),
            'total_processed': 0,
            'api_items': 0,
            'scraper_items': 0,
            'images_processed': 0,
            'errors': 0,
            'duplicates_skipped': 0
        }
    
    def run_comprehensive_collection(self, target_items: int = 500, mode: str = "balanced"):
        """
        Run comprehensive data collection
        
        Modes:
        - balanced: Mix of APIs and scrapers
        - api_focused: Primarily use APIs
        - scraper_focused: Primarily use scrapers
        - popular_only: Focus on popular/trending sneakers
        """
        print("🚀 Enhanced SoleID Data Collection")
        print("=" * 60)
        print(f"🎯 Target: {target_items} sneakers")
        print(f"📊 Mode: {mode}")
        print(f"🕐 Started: {self.session_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        try:
            if mode == "api_focused":
                self._api_focused_collection(target_items)
            elif mode == "scraper_focused":
                self._scraper_focused_collection(target_items)
            elif mode == "popular_only":
                self._popular_focused_collection(target_items)
            else:  # balanced
                self._balanced_collection(target_items)
            
            self._print_session_summary()
            
        except Exception as e:
            logger.error(f"Collection error: {str(e)}")
            print(f"❌ Error: {str(e)}")
    
    def _api_focused_collection(self, target_items: int):
        """API-focused collection strategy"""
        print("\n📡 API-Focused Collection Strategy")
        
        # 70% from APIs, 30% from scrapers
        api_target = int(target_items * 0.7)
        scraper_target = target_items - api_target
        
        # Phase 1: Popular sneakers from Sneaks-API
        print(f"\n🔥 Phase 1: Popular Sneakers ({api_target//3} items)")
        self._collect_popular_sneakers(api_target // 3)
        
        # Phase 2: Curated collection from Sneaker-API
        print(f"\n🎨 Phase 2: Curated Collection ({api_target//3} items)")
        self._collect_curated_sneakers(api_target // 3)
        
        # Phase 3: Enhanced search
        print(f"\n🔍 Phase 3: Enhanced Search ({api_target//3} items)")
        self._collect_search_results(api_target // 3)
        
        # Phase 4: Scraper fallback
        print(f"\n🕷️ Phase 4: Scraper Fallback ({scraper_target} items)")
        self._collect_scraper_data(scraper_target)
    
    def _balanced_collection(self, target_items: int):
        """Balanced collection strategy"""
        print("\n⚖️ Balanced Collection Strategy")
        
        # 50% APIs, 50% scrapers
        api_target = target_items // 2
        scraper_target = target_items - api_target
        
        # Interleave API and scraper collection
        phases = [
            ("Popular API", api_target // 3, self._collect_popular_sneakers),
            ("Legacy Scrapers", scraper_target // 2, self._collect_scraper_data),
            ("Curated API", api_target // 3, self._collect_curated_sneakers),
            ("Enhanced Scrapers", scraper_target // 2, self._collect_scraper_data),
            ("Search API", api_target // 3, self._collect_search_results)
        ]
        
        for phase_name, phase_target, phase_func in phases:
            print(f"\n📊 {phase_name}: {phase_target} items")
            phase_func(phase_target)
    
    def _popular_focused_collection(self, target_items: int):
        """Focus on popular and trending sneakers"""
        print("\n🌟 Popular-Focused Collection Strategy")
        
        # Get popular sneakers from multiple sources
        popular_sources = [
            ("Sneaks-API Popular", target_items // 3, self._collect_popular_sneakers),
            ("Trending Searches", target_items // 3, self._collect_trending_searches),
            ("Static Popular", target_items // 3, self._collect_static_popular)
        ]
        
        for source_name, source_target, source_func in popular_sources:
            print(f"\n⭐ {source_name}: {source_target} items")
            source_func(source_target)
    
    def _collect_popular_sneakers(self, target: int):
        """Collect popular sneakers from Sneaks-API"""
        try:
            popular_data = self.sneaks_client.get_most_popular(limit=target)
            
            db = SessionLocal()
            try:
                for sneaker_data in popular_data:
                    if self._save_sneaker_data(db, sneaker_data, "sneaks_popular"):
                        self.session_stats['api_items'] += 1
                        self.session_stats['total_processed'] += 1
                        
                        if self.session_stats['total_processed'] % 10 == 0:
                            print(f"   ✅ Processed {self.session_stats['total_processed']} items...")
                    
                    time.sleep(0.5)  # Rate limiting
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error collecting popular sneakers: {str(e)}")
            self.session_stats['errors'] += 1
    
    def _collect_curated_sneakers(self, target: int):
        """Collect curated sneakers from Sneaker-API"""
        try:
            curated_data = self.sneaker_client.get_all_sneakers(limit=target)
            
            db = SessionLocal()
            try:
                for sneaker_data in curated_data:
                    if self._save_sneaker_data(db, sneaker_data, "sneaker_api"):
                        self.session_stats['api_items'] += 1
                        self.session_stats['total_processed'] += 1
                        
                        if self.session_stats['total_processed'] % 10 == 0:
                            print(f"   ✅ Processed {self.session_stats['total_processed']} items...")
                    
                    time.sleep(0.3)
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error collecting curated sneakers: {str(e)}")
            self.session_stats['errors'] += 1
    
    def _collect_search_results(self, target: int):
        """Collect sneakers through enhanced search"""
        search_terms = [
            "Nike Air Jordan", "Adidas Yeezy", "Nike Dunk", "Air Max",
            "New Balance 550", "Travis Scott", "Off-White", "Fragment",
            "Jordan 4", "Jordan 1", "Air Force 1", "Ultraboost"
        ]
        
        db = SessionLocal()
        try:
            items_per_search = max(1, target // len(search_terms))
            
            for term in search_terms:
                if self.session_stats['total_processed'] >= target:
                    break
                
                try:
                    results = self.sneaks_client.search_products(term, limit=items_per_search)
                    
                    for sneaker_data in results:
                        if self._save_sneaker_data(db, sneaker_data, "sneaks_search"):
                            self.session_stats['api_items'] += 1
                            self.session_stats['total_processed'] += 1
                    
                    time.sleep(1.0)  # Rate limiting for searches
                    
                except Exception as e:
                    logger.error(f"Search error for {term}: {str(e)}")
                    self.session_stats['errors'] += 1
                    
        finally:
            db.close()
    
    def _collect_trending_searches(self, target: int):
        """Collect trending sneaker searches"""
        trending_terms = [
            "Jordan 4 Black Cat", "Dunk Low Panda", "Yeezy 350 Zebra",
            "Air Max 90 White", "New Balance 2002R", "Jordan 1 Chicago",
            "Travis Scott Jordan 1", "Off-White Air Jordan", "Fragment Jordan 1"
        ]
        
        db = SessionLocal()
        try:
            items_per_search = max(1, target // len(trending_terms))
            
            for term in trending_terms:
                if self.session_stats['total_processed'] >= target:
                    break
                
                try:
                    results = self.sneaks_client.search_products(term, limit=items_per_search)
                    
                    for sneaker_data in results:
                        if self._save_sneaker_data(db, sneaker_data, "trending"):
                            self.session_stats['api_items'] += 1
                            self.session_stats['total_processed'] += 1
                    
                    time.sleep(0.8)
                    
                except Exception as e:
                    logger.error(f"Trending search error for {term}: {str(e)}")
                    self.session_stats['errors'] += 1
                    
        finally:
            db.close()
    
    def _collect_scraper_data(self, target: int):
        """Collect data using legacy scrapers"""
        try:
            search_terms = ["Jordan", "Nike", "Adidas", "Yeezy", "Dunk"]
            
            db = SessionLocal()
            try:
                items_per_search = max(1, target // len(search_terms))
                
                for term in search_terms:
                    if self.session_stats['total_processed'] >= target:
                        break
                    
                    try:
                        # Use SneaksAPI scraper (most reliable)
                        sneaks_scraper = SneaksAPIScraper()
                        results = sneaks_scraper.search_sneakers(term, max_results=items_per_search)
                        
                        for sneaker_data in results:
                            if self._save_sneaker_data(db, sneaker_data, "scraper"):
                                self.session_stats['scraper_items'] += 1
                                self.session_stats['total_processed'] += 1
                        
                        time.sleep(2.0)  # Longer delay for scrapers
                        
                    except Exception as e:
                        logger.error(f"Scraper error for {term}: {str(e)}")
                        self.session_stats['errors'] += 1
                        
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in scraper collection: {str(e)}")
            self.session_stats['errors'] += 1
    
    def _collect_static_popular(self, target: int):
        """Collect from static popular data"""
        try:
            static_scraper = StaticDataScraper()
            results = static_scraper.search_sneakers("", max_results=target)
            
            db = SessionLocal()
            try:
                for sneaker_data in results:
                    if self._save_sneaker_data(db, sneaker_data, "static"):
                        self.session_stats['scraper_items'] += 1
                        self.session_stats['total_processed'] += 1
                        
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error collecting static data: {str(e)}")
            self.session_stats['errors'] += 1
    
    def _save_sneaker_data(self, db, data: Dict, source: str) -> bool:
        """Save sneaker data to database"""
        try:
            # Extract name and check for duplicates
            name = data.get('name') or data.get('shoeName', '')
            if not name:
                return False
            
            # Check for duplicates
            existing = db.query(Sneaker).filter(
                Sneaker.name.ilike(f"%{name}%")
            ).first()
            
            if existing:
                self.session_stats['duplicates_skipped'] += 1
                return False
            
            # Create sneaker record
            sneaker = Sneaker(
                name=name,
                brand=data.get('brand', '') or self._extract_brand(name),
                model=data.get('model', '') or self._extract_model(name),
                colorway=data.get('colorway', ''),
                sku=data.get('sku') or data.get('styleID', ''),
                retail_price=self._parse_price(data.get('retail_price') or data.get('retailPrice')),
                release_date=self._parse_date(data.get('release_date') or data.get('releaseDate')),
                description=data.get('description', '')
            )
            
            db.add(sneaker)
            db.flush()
            
            # Save price information
            price = self._parse_price(data.get('price'))
            if price:
                price_history = PriceHistory(
                    sneaker_id=sneaker.id,
                    size='Unknown',
                    price=price,
                    condition='new',
                    platform=data.get('platform', source),
                    listing_type='current',
                    sale_date=datetime.utcnow()
                )
                db.add(price_history)
            
            # Save image if available
            image_url = data.get('image_url') or data.get('thumbnail')
            if image_url:
                sneaker_image = SneakerImage(
                    sneaker_id=sneaker.id,
                    image_url=image_url,
                    image_type='main',
                    is_primary=True
                )
                db.add(sneaker_image)
                self.session_stats['images_processed'] += 1
            
            # Log scraping activity
            scraping_log = ScrapingLog(
                platform=data.get('platform', source),
                items_found=1,
                items_saved=1,
                errors=0,
                scrape_date=datetime.utcnow()
            )
            db.add(scraping_log)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving sneaker data: {str(e)}")
            self.session_stats['errors'] += 1
            return False
    
    def _extract_brand(self, name: str) -> str:
        """Extract brand from sneaker name"""
        name_lower = name.lower()
        brands = ['nike', 'adidas', 'jordan', 'new balance', 'puma', 'reebok', 'converse', 'vans']
        
        for brand in brands:
            if brand in name_lower:
                return brand.title()
        
        return 'Unknown'
    
    def _extract_model(self, name: str) -> str:
        """Extract model from sneaker name"""
        words = name.split()
        if len(words) >= 2:
            return ' '.join(words[:3])
        return name
    
    def _parse_price(self, price_str) -> float:
        """Parse price string to float"""
        if not price_str:
            return None
        
        try:
            import re
            price_clean = str(price_str).replace('$', '').replace(',', '').strip()
            return float(price_clean)
        except:
            return None
    
    def _parse_date(self, date_str):
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        try:
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(str(date_str), fmt)
                except:
                    continue
            return None
        except:
            return None
    
    def _print_session_summary(self):
        """Print session summary"""
        duration = datetime.now() - self.session_stats['start_time']
        
        print("\n" + "=" * 60)
        print("🎉 ENHANCED COLLECTION COMPLETED!")
        print("=" * 60)
        print(f"⏱️  Duration: {duration.total_seconds()/60:.1f} minutes")
        print(f"📊 Total Processed: {self.session_stats['total_processed']}")
        print(f"📡 API Items: {self.session_stats['api_items']}")
        print(f"🕷️ Scraper Items: {self.session_stats['scraper_items']}")
        print(f"🖼️  Images Processed: {self.session_stats['images_processed']}")
        print(f"⚠️  Duplicates Skipped: {self.session_stats['duplicates_skipped']}")
        print(f"❌ Errors: {self.session_stats['errors']}")
        
        # Database stats
        db = SessionLocal()
        try:
            total_sneakers = db.query(Sneaker).count()
            total_images = db.query(SneakerImage).count()
            total_prices = db.query(PriceHistory).count()
            
            print(f"\n📋 Current Database Stats:")
            print(f"   • Total Sneakers: {total_sneakers}")
            print(f"   • Total Images: {total_images}")
            print(f"   • Total Prices: {total_prices}")
            
        finally:
            db.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Scraper Manager")
    parser.add_argument("--target", type=int, default=500,
                       help="Target number of sneakers to collect")
    parser.add_argument("--mode", choices=["balanced", "api_focused", "scraper_focused", "popular_only"],
                       default="balanced", help="Collection mode")
    parser.add_argument("--test", action="store_true",
                       help="Run in test mode with limited items")
    
    args = parser.parse_args()
    
    if args.test:
        target = 25
        print("🧪 Running in TEST MODE")
    else:
        target = args.target
    
    manager = EnhancedScraperManager()
    manager.run_comprehensive_collection(target, args.mode)

if __name__ == "__main__":
    main()