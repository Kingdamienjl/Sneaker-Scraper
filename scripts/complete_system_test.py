#!/usr/bin/env python3
"""
Complete SoleID System Test - Downloads real images and tests all components
"""

import sys
import os
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modern_scrapers import MultiSourceScraper
from google_drive import GoogleDriveManager
from database import SessionLocal
from models import Sneaker, SneakerImage, PriceHistory, ScrapingLog

class CompleteSoleIDTest:
    """Complete system test with real image downloads"""
    
    def __init__(self):
        self.scraper = MultiSourceScraper()
        self.drive_manager = None
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Initialize Google Drive (optional)
        try:
            self.drive_manager = GoogleDriveManager()
            self.logger.info("✅ Google Drive initialized successfully")
        except Exception as e:
            self.logger.warning(f"⚠️ Google Drive initialization failed: {str(e)}")
    
    def test_complete_system(self) -> Dict:
        """Test the complete system with real data"""
        print("🚀 SoleID Complete System Test")
        print("=" * 50)
        
        results = {
            'database_test': False,
            'scraper_test': False,
            'image_download_test': False,
            'google_drive_test': False,
            'api_test': False,
            'total_sneakers': 0,
            'total_images': 0,
            'errors': []
        }
        
        # Test 1: Database Connection
        print("🔍 Testing database connection...")
        try:
            db = SessionLocal()
            count = db.query(Sneaker).count()
            print(f"   ✅ Database connected - {count} sneakers found")
            results['database_test'] = True
            results['total_sneakers'] = count
            db.close()
        except Exception as e:
            print(f"   ❌ Database test failed: {str(e)}")
            results['errors'].append(f"Database: {str(e)}")
        
        # Test 2: Scraper
        print("\n🕷️ Testing scrapers...")
        try:
            test_data = self.scraper.search_sneakers("Air Jordan", 2)
            print(f"   ✅ Scrapers working - found {len(test_data)} items")
            results['scraper_test'] = True
        except Exception as e:
            print(f"   ❌ Scraper test failed: {str(e)}")
            results['errors'].append(f"Scraper: {str(e)}")
        
        # Test 3: Image Download with Real URLs
        print("\n🖼️ Testing image downloads...")
        try:
            # Use real sneaker image URLs for testing
            test_images = [
                {
                    'name': 'Air Jordan 1 Test',
                    'brand': 'Nike',
                    'image_url': 'https://images.stockx.com/images/Air-Jordan-1-Retro-High-OG-Bred-Toe.jpg?fit=fill&bg=FFFFFF&w=700&h=500&fm=webp&auto=compress&q=90&dpr=2&trim=color&updated_at=1606325713'
                },
                {
                    'name': 'Nike Dunk Test',
                    'brand': 'Nike', 
                    'image_url': 'https://images.stockx.com/images/Nike-Dunk-Low-White-Black-2021.jpg?fit=fill&bg=FFFFFF&w=700&h=500&fm=webp&auto=compress&q=90&dpr=2&trim=color&updated_at=1609439600'
                }
            ]
            
            downloaded_count = 0
            for img_data in test_images:
                if self.download_test_image(img_data):
                    downloaded_count += 1
            
            print(f"   ✅ Downloaded {downloaded_count}/{len(test_images)} test images")
            results['image_download_test'] = downloaded_count > 0
            results['total_images'] = downloaded_count
            
        except Exception as e:
            print(f"   ❌ Image download test failed: {str(e)}")
            results['errors'].append(f"Image Download: {str(e)}")
        
        # Test 4: Google Drive
        print("\n☁️ Testing Google Drive...")
        if self.drive_manager:
            try:
                # Try to list files in the drive
                files = self.drive_manager.list_files()
                print(f"   ✅ Google Drive connected - {len(files)} files found")
                results['google_drive_test'] = True
            except Exception as e:
                print(f"   ❌ Google Drive test failed: {str(e)}")
                results['errors'].append(f"Google Drive: {str(e)}")
        else:
            print("   ⚠️ Google Drive not initialized")
        
        # Test 5: API (if server is running)
        print("\n🌐 Testing API...")
        try:
            response = requests.get("http://localhost:8000/api/sneakers", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ API working - {len(data)} sneakers via API")
                results['api_test'] = True
            else:
                print(f"   ⚠️ API returned status {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ API test failed (server may not be running): {str(e)}")
        
        return results
    
    def download_test_image(self, img_data: Dict) -> bool:
        """Download a test image"""
        try:
            image_url = img_data['image_url']
            
            # Download image
            response = requests.get(image_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                # Save to local directory
                file_name = f"test_{img_data['name'].replace(' ', '_').lower()}_{int(time.time())}.jpg"
                local_path = os.path.join("data/images", file_name)
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"      📁 Saved: {file_name} ({len(response.content)} bytes)")
                
                # Try Google Drive upload
                if self.drive_manager:
                    try:
                        drive_id = self.drive_manager.upload_image(
                            local_path, 
                            file_name,
                            folder_name=img_data['brand']
                        )
                        if drive_id:
                            print(f"      ☁️ Uploaded to Google Drive: {drive_id}")
                    except Exception as e:
                        print(f"      ⚠️ Google Drive upload failed: {str(e)}")
                
                return True
            else:
                print(f"      ❌ Failed to download: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"      ❌ Download error: {str(e)}")
            return False
    
    def show_system_status(self, results: Dict):
        """Show complete system status"""
        print("\n" + "=" * 50)
        print("📊 SYSTEM STATUS REPORT")
        print("=" * 50)
        
        # Test Results
        tests = [
            ("Database Connection", results['database_test']),
            ("Scraper Functionality", results['scraper_test']),
            ("Image Downloads", results['image_download_test']),
            ("Google Drive", results['google_drive_test']),
            ("API Endpoint", results['api_test'])
        ]
        
        for test_name, passed in tests:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:.<30} {status}")
        
        print(f"\n📈 DATA SUMMARY:")
        print(f"   • Sneakers in database: {results['total_sneakers']}")
        print(f"   • Test images downloaded: {results['total_images']}")
        
        if results['errors']:
            print(f"\n⚠️ ERRORS ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"   • {error}")
        
        print(f"\n🔍 WHERE TO FIND YOUR DATA:")
        print(f"   • Database: sneakers.db")
        print(f"   • Local Images: data/images/")
        print(f"   • Google Drive: SoleID_Images folder")
        print(f"   • API: http://localhost:8000/api/sneakers")
        print(f"   • Logs: logs/ directory")
        
        # Check actual files
        print(f"\n📁 LOCAL FILES:")
        try:
            images = os.listdir("data/images")
            if images:
                print(f"   • Images found: {len(images)}")
                for img in images[:3]:  # Show first 3
                    print(f"     - {img}")
                if len(images) > 3:
                    print(f"     ... and {len(images) - 3} more")
            else:
                print(f"   • No images in data/images/")
        except:
            print(f"   • Could not access data/images/")

def main():
    """Run the complete system test"""
    tester = CompleteSoleIDTest()
    results = tester.test_complete_system()
    tester.show_system_status(results)
    
    print(f"\n🎯 NEXT STEPS:")
    if not results['api_test']:
        print(f"   1. Start the API server: python main.py")
    if not results['google_drive_test']:
        print(f"   2. Fix Google Drive authentication")
    if results['image_download_test']:
        print(f"   3. ✅ System ready for mobile app development!")
    else:
        print(f"   3. Fix image download issues")

if __name__ == "__main__":
    main()