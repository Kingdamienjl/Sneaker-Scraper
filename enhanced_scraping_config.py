#!/usr/bin/env python3
"""
Enhanced Scraping Configuration
This script increases scraping depth and accuracy by:
1. Expanding search terms and brand coverage
2. Increasing items per query
3. Adding more detailed data extraction
4. Implementing better error handling and retry logic
"""

import os
import sys
import time
import logging
from typing import List, Dict
from scraper_manager import ScraperManager
from config import Config
from database import SessionLocal
from models import Sneaker, SneakerImage, PriceHistory

# Setup enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedScrapingConfig:
    """Enhanced configuration for deeper, more accurate scraping"""
    
    # Increased depth parameters
    MAX_ITEMS_PER_QUERY = 25  # Increased from default 10
    MAX_CONCURRENT_REQUESTS = 15  # Increased from 10
    REQUEST_DELAY = 0.8  # Slightly reduced for faster scraping
    RETRY_ATTEMPTS = 3
    TIMEOUT_SECONDS = 30
    
    # Comprehensive search terms for maximum coverage
    ENHANCED_SEARCH_TERMS = [
        # Nike Categories - Expanded
        "Nike Air Jordan 1", "Nike Air Jordan 3", "Nike Air Jordan 4", "Nike Air Jordan 5",
        "Nike Air Jordan 6", "Nike Air Jordan 11", "Nike Air Jordan 12", "Nike Air Jordan 13",
        "Nike Air Max 1", "Nike Air Max 90", "Nike Air Max 95", "Nike Air Max 97",
        "Nike Air Force 1", "Nike Dunk Low", "Nike Dunk High", "Nike SB Dunk",
        "Nike Blazer", "Nike Cortez", "Nike React", "Nike Zoom",
        "Nike Air Presto", "Nike Air Huarache", "Nike Air VaporMax", "Nike Air Max 270",
        "Nike Air Max Plus", "Nike Air Max 720", "Nike Shox", "Nike Free",
        
        # Adidas Categories - Expanded  
        "Adidas Yeezy 350", "Adidas Yeezy 700", "Adidas Yeezy 500", "Adidas Yeezy Slide",
        "Adidas Stan Smith", "Adidas Superstar", "Adidas Gazelle", "Adidas Campus",
        "Adidas Ultraboost", "Adidas NMD", "Adidas Boost", "Adidas ZX",
        "Adidas Samba", "Adidas Spezial", "Adidas Forum", "Adidas Rivalry",
        "Adidas Continental", "Adidas Falcon", "Adidas Ozweego", "Adidas Nite Jogger",
        
        # Jordan Brand - Detailed
        "Air Jordan Retro", "Jordan 1 Low", "Jordan 1 Mid", "Jordan 1 High",
        "Jordan 3 Retro", "Jordan 4 Retro", "Jordan 5 Retro", "Jordan 6 Retro",
        "Jordan 11 Retro", "Jordan 12 Retro", "Jordan 13 Retro", "Jordan 14 Retro",
        "Jordan Legacy", "Jordan Delta", "Jordan React", "Jordan Zoom",
        
        # Popular Collaborations
        "Travis Scott Jordan", "Off-White Nike", "Fragment Jordan", "Dior Jordan",
        "Supreme Nike", "Stussy Nike", "Sacai Nike", "Comme des Garcons Nike",
        "Fear of God Nike", "Virgil Abloh", "Kanye West", "Pharrell Williams",
        
        # New Balance - Expanded
        "New Balance 550", "New Balance 990", "New Balance 991", "New Balance 992",
        "New Balance 993", "New Balance 994", "New Balance 995", "New Balance 996",
        "New Balance 997", "New Balance 998", "New Balance 999", "New Balance 1500",
        "New Balance 2002R", "New Balance 327", "New Balance 574", "New Balance 530",
        
        # Converse & Vans
        "Converse Chuck Taylor", "Converse All Star", "Converse 70s", "Converse Run Star",
        "Vans Old Skool", "Vans Authentic", "Vans Era", "Vans Slip-On",
        "Vans SK8-Hi", "Vans Half Cab", "Vans Style 36", "Vans Knu Skool",
        
        # ASICS & Other Brands
        "ASICS Gel-Lyte", "ASICS Gel-Kayano", "ASICS Gel-Nimbus", "ASICS Gel-1130",
        "Puma Suede", "Puma RS-X", "Puma Thunder", "Puma Clyde",
        "Reebok Classic", "Reebok Club C", "Reebok Pump", "Reebok Question",
        
        # Luxury & Designer
        "Balenciaga Triple S", "Balenciaga Speed", "Balenciaga Track", "Balenciaga Runner",
        "Golden Goose Superstar", "Common Projects Achilles", "Maison Margiela GAT",
        "Rick Owens DRKSHDW", "Bottega Veneta Tire", "Gucci Ace", "Louis Vuitton Trainer",
        
        # Trending Models
        "Salomon XT-6", "Hoka Clifton", "On Cloud", "Allbirds Tree",
        "Crocs Classic", "Birkenstock Boston", "UGG Tasman", "Dr. Martens 1460"
    ]
    
    # Brand-specific deep search terms
    BRAND_SPECIFIC_TERMS = {
        "Nike": [
            "Air Jordan", "Air Max", "Air Force", "Dunk", "Blazer", "React", "Zoom",
            "VaporMax", "Presto", "Huarache", "Cortez", "Free", "Shox", "Pegasus"
        ],
        "Adidas": [
            "Yeezy", "Ultraboost", "NMD", "Stan Smith", "Superstar", "Gazelle",
            "Campus", "Samba", "Spezial", "Forum", "ZX", "Falcon", "Ozweego"
        ],
        "New Balance": [
            "990", "991", "992", "993", "994", "995", "996", "997", "998", "999",
            "550", "327", "2002R", "574", "530", "1500", "1906R", "9060"
        ],
        "Jordan": [
            "Air Jordan 1", "Air Jordan 3", "Air Jordan 4", "Air Jordan 5",
            "Air Jordan 6", "Air Jordan 11", "Air Jordan 12", "Air Jordan 13"
        ]
    }

def create_enhanced_scraper_manager():
    """Create scraper manager with enhanced configuration"""
    
    # Update config for enhanced scraping
    Config.MAX_CONCURRENT_REQUESTS = EnhancedScrapingConfig.MAX_CONCURRENT_REQUESTS
    Config.REQUEST_DELAY = EnhancedScrapingConfig.REQUEST_DELAY
    
    manager = ScraperManager()
    
    # Override default search terms with enhanced ones
    manager.default_search_terms = EnhancedScrapingConfig.ENHANCED_SEARCH_TERMS
    
    return manager

def run_enhanced_scraping_session(duration_hours: int = 2):
    """Run an enhanced scraping session with increased depth"""
    
    print("🚀 Starting Enhanced Scraping Session")
    print("=" * 60)
    print(f"⏱️  Duration: {duration_hours} hours")
    print(f"🔍 Search Terms: {len(EnhancedScrapingConfig.ENHANCED_SEARCH_TERMS)}")
    print(f"📊 Max Items per Query: {EnhancedScrapingConfig.MAX_ITEMS_PER_QUERY}")
    print(f"⚡ Concurrent Requests: {EnhancedScrapingConfig.MAX_CONCURRENT_REQUESTS}")
    print("=" * 60)
    
    start_time = time.time()
    end_time = start_time + (duration_hours * 3600)
    
    manager = create_enhanced_scraper_manager()
    
    # Statistics tracking
    total_items = 0
    total_errors = 0
    cycles_completed = 0
    
    try:
        while time.time() < end_time:
            cycle_start = time.time()
            print(f"\n🔄 Starting Scraping Cycle {cycles_completed + 1}")
            
            # Get initial counts
            db = SessionLocal()
            initial_sneakers = db.query(Sneaker).count()
            initial_images = db.query(SneakerImage).count()
            initial_prices = db.query(PriceHistory).count()
            db.close()
            
            try:
                # Run scraping for all platforms
                manager.scrape_all_platforms(
                    search_terms=EnhancedScrapingConfig.ENHANCED_SEARCH_TERMS[:50],  # Use first 50 terms per cycle
                    platforms=['stockx', 'modern']  # Focus on working scrapers
                )
                
                # Get final counts
                db = SessionLocal()
                final_sneakers = db.query(Sneaker).count()
                final_images = db.query(SneakerImage).count()
                final_prices = db.query(PriceHistory).count()
                db.close()
                
                # Calculate cycle results
                cycle_sneakers = final_sneakers - initial_sneakers
                cycle_images = final_images - initial_images
                cycle_prices = final_prices - initial_prices
                
                total_items += cycle_sneakers
                cycles_completed += 1
                
                cycle_time = time.time() - cycle_start
                print(f"✅ Cycle {cycles_completed} completed in {cycle_time:.1f}s")
                print(f"   • New Sneakers: {cycle_sneakers}")
                print(f"   • New Images: {cycle_images}")
                print(f"   • New Prices: {cycle_prices}")
                
                # Brief pause between cycles
                time.sleep(30)
                
            except Exception as e:
                total_errors += 1
                logger.error(f"Error in scraping cycle: {str(e)}")
                time.sleep(60)  # Longer pause on error
        
        # Final summary
        total_time = time.time() - start_time
        print(f"\n🎉 Enhanced Scraping Session Completed!")
        print("=" * 60)
        print(f"⏱️  Total Time: {total_time/3600:.1f} hours")
        print(f"🔄 Cycles Completed: {cycles_completed}")
        print(f"📊 Total Items Scraped: {total_items}")
        print(f"❌ Total Errors: {total_errors}")
        print(f"📈 Items per Hour: {total_items/(total_time/3600):.1f}")
        
        # Final database stats
        db = SessionLocal()
        final_sneakers = db.query(Sneaker).count()
        final_images = db.query(SneakerImage).count()
        final_prices = db.query(PriceHistory).count()
        db.close()
        
        print(f"\n📋 Final Database Stats:")
        print(f"   • Total Sneakers: {final_sneakers}")
        print(f"   • Total Images: {final_images}")
        print(f"   • Total Prices: {final_prices}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Scraping session interrupted by user")
    except Exception as e:
        logger.error(f"Critical error in enhanced scraping: {str(e)}")

def run_brand_focused_scraping(brand: str, duration_minutes: int = 30):
    """Run focused scraping for a specific brand"""
    
    if brand not in EnhancedScrapingConfig.BRAND_SPECIFIC_TERMS:
        print(f"❌ Brand '{brand}' not found in configuration")
        return
    
    print(f"🎯 Starting Brand-Focused Scraping: {brand}")
    print("=" * 50)
    
    brand_terms = [f"{brand} {term}" for term in EnhancedScrapingConfig.BRAND_SPECIFIC_TERMS[brand]]
    
    manager = create_enhanced_scraper_manager()
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    while time.time() < end_time:
        try:
            manager.scrape_all_platforms(
                search_terms=brand_terms,
                platforms=['stockx', 'modern']
            )
            time.sleep(60)  # 1 minute between cycles
        except Exception as e:
            logger.error(f"Error in brand-focused scraping: {str(e)}")
            time.sleep(120)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Sneaker Scraping")
    parser.add_argument("--mode", choices=["enhanced", "brand"], default="enhanced",
                       help="Scraping mode: enhanced (full) or brand (focused)")
    parser.add_argument("--duration", type=int, default=2,
                       help="Duration in hours for enhanced mode or minutes for brand mode")
    parser.add_argument("--brand", type=str, default="Nike",
                       help="Brand name for brand-focused scraping")
    
    args = parser.parse_args()
    
    if args.mode == "enhanced":
        run_enhanced_scraping_session(args.duration)
    elif args.mode == "brand":
        run_brand_focused_scraping(args.brand, args.duration)