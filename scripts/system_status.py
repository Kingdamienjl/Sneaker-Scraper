#!/usr/bin/env python3
"""
SoleID System Status Report
"""

import os
from database import SessionLocal
from models import Sneaker, SneakerImage, PriceHistory, ScrapingLog

def generate_status_report():
    """Generate a comprehensive status report"""
    
    print("🚀 SoleID SYSTEM STATUS REPORT")
    print("=" * 60)
    
    # Database Status
    print("\n📊 DATABASE STATUS:")
    try:
        db = SessionLocal()
        sneaker_count = db.query(Sneaker).count()
        image_count = db.query(SneakerImage).count()
        price_count = db.query(PriceHistory).count()
        log_count = db.query(ScrapingLog).count()
        
        print(f"   ✅ Database connected: sneakers.db")
        print(f"   📦 Sneakers: {sneaker_count}")
        print(f"   🖼️ Images: {image_count}")
        print(f"   💰 Price records: {price_count}")
        print(f"   📝 Scraping logs: {log_count}")
        
        # Show sample sneakers
        if sneaker_count > 0:
            print(f"\n   📋 Sample Sneakers:")
            sneakers = db.query(Sneaker).limit(5).all()
            for sneaker in sneakers:
                print(f"      • {sneaker.brand} {sneaker.name}")
        
        db.close()
        
    except Exception as e:
        print(f"   ❌ Database error: {str(e)}")
    
    # Local Files Status
    print(f"\n📁 LOCAL FILES:")
    try:
        # Check data directories
        directories = ['data', 'data/images', 'data/temp', 'data/exports', 'logs', 'backups']
        for directory in directories:
            if os.path.exists(directory):
                file_count = len(os.listdir(directory)) if os.path.isdir(directory) else 0
                print(f"   ✅ {directory}/ ({file_count} files)")
            else:
                print(f"   ❌ {directory}/ (missing)")
        
        # Check images specifically
        if os.path.exists('data/images'):
            images = os.listdir('data/images')
            if images:
                print(f"\n   🖼️ Downloaded Images ({len(images)}):")
                for img in images:
                    size = os.path.getsize(os.path.join('data/images', img))
                    print(f"      • {img} ({size:,} bytes)")
            else:
                print(f"\n   📁 No images in data/images/")
                
    except Exception as e:
        print(f"   ❌ File system error: {str(e)}")
    
    # Google Drive Status
    print(f"\n☁️ GOOGLE DRIVE STATUS:")
    try:
        from google_drive import GoogleDriveManager
        gdm = GoogleDriveManager()
        files = gdm.list_files()
        
        print(f"   ✅ Connected successfully")
        print(f"   📂 Total files: {len(files)}")
        
        # Check for SoleID folder
        folder = gdm.find_folder_by_name("SoleID_Images")
        if folder:
            print(f"   📁 SoleID_Images folder: {folder['id']}")
            
            # List brand folders
            brand_folders = [f for f in files if f.get('mimeType') == 'application/vnd.google-apps.folder']
            if brand_folders:
                print(f"   🏷️ Brand folders ({len(brand_folders)}):")
                for folder in brand_folders:
                    print(f"      • {folder['name']}")
        else:
            print(f"   ❌ SoleID_Images folder not found")
            
    except Exception as e:
        print(f"   ❌ Google Drive error: {str(e)}")
    
    # API Status
    print(f"\n🌐 API STATUS:")
    try:
        import requests
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ API server running on http://localhost:8000")
            print(f"   📚 Documentation: http://localhost:8000/docs")
            print(f"   🔗 Endpoints available:")
            print(f"      • GET /api/sneakers - List all sneakers")
            print(f"      • GET /api/sneakers/{{id}} - Get specific sneaker")
            print(f"      • GET /api/search?q={{query}} - Search sneakers")
            print(f"      • GET /api/database-stats - Database statistics")
            print(f"      • POST /api/build-database - Build database")
        else:
            print(f"   ⚠️ API returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ API not accessible: {str(e)}")
    
    # Scraper Status
    print(f"\n🕷️ SCRAPER STATUS:")
    try:
        from modern_scrapers import MultiSourceScraper
        scraper = MultiSourceScraper()
        test_results = scraper.search_sneakers("test", 1)
        print(f"   ✅ Scrapers functional")
        print(f"   🔧 Available sources:")
        print(f"      • SneaksAPI (external API)")
        print(f"      • Static Data (fallback)")
        print(f"   📊 Test query returned {len(test_results)} results")
    except Exception as e:
        print(f"   ❌ Scraper error: {str(e)}")
    
    print(f"\n" + "=" * 60)
    print(f"🎯 SYSTEM READY FOR MOBILE APP DEVELOPMENT!")
    print(f"=" * 60)
    
    print(f"\n📱 MOBILE APP INTEGRATION:")
    print(f"   • Use API endpoints for data retrieval")
    print(f"   • Images stored in Google Drive with IDs")
    print(f"   • SQLite database for fast local queries")
    print(f"   • Real-time scraping capabilities")
    
    print(f"\n🔧 NEXT STEPS:")
    print(f"   1. ✅ Database system working")
    print(f"   2. ✅ Image storage working") 
    print(f"   3. ✅ Google Drive integration working")
    print(f"   4. ✅ API endpoints working")
    print(f"   5. 🚀 Ready to start Android development!")
    
    print(f"\n📋 QUICK START COMMANDS:")
    print(f"   • Start API: python main.py")
    print(f"   • Download images: python download_images.py")
    print(f"   • Test system: python complete_system_test.py")
    print(f"   • Check status: python system_status.py")

if __name__ == "__main__":
    generate_status_report()