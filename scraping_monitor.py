#!/usr/bin/env python3
"""
Real-time Scraping Session Monitor
Tracks progress of ongoing scraping operations and Google Drive uploads
"""

import time
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import logging

# Add current directory to path for imports
sys.path.append('.')

from models import Sneaker, SneakerImage, PriceHistory, ScrapingLog
from config import Config
from google_drive import GoogleDriveManager

class ScrapingMonitor:
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.start_time = datetime.now()
        self.drive_manager = GoogleDriveManager()
        
    def get_session_stats(self):
        """Get current session statistics"""
        db = self.SessionLocal()
        try:
            # Get total counts
            total_sneakers = db.query(Sneaker).count()
            total_images = db.query(SneakerImage).count()
            total_prices = db.query(PriceHistory).count()
            
            # Get recent additions (last hour)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_sneakers = db.query(Sneaker).filter(
                Sneaker.created_at >= one_hour_ago
            ).count()
            
            recent_images = db.query(SneakerImage).filter(
                SneakerImage.created_at >= one_hour_ago
            ).count()
            
            # Get brand distribution
            brand_stats = db.query(
                Sneaker.brand, 
                func.count(Sneaker.id).label('count')
            ).group_by(Sneaker.brand).order_by(func.count(Sneaker.id).desc()).limit(10).all()
            
            return {
                'total_sneakers': total_sneakers,
                'total_images': total_images,
                'total_prices': total_prices,
                'recent_sneakers': recent_sneakers,
                'recent_images': recent_images,
                'brand_stats': brand_stats
            }
        finally:
            db.close()
    
    def get_drive_stats(self):
        """Get Google Drive statistics"""
        try:
            files = self.drive_manager.list_files()
            folders = [f for f in files if 'folder' in f.get('mimeType', '')]
            images = [f for f in files if 'image' in f.get('mimeType', '')]
            
            return {
                'total_files': len(files),
                'folders': len(folders),
                'images': len(images)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def display_status(self):
        """Display comprehensive status"""
        elapsed = datetime.now() - self.start_time
        stats = self.get_session_stats()
        drive_stats = self.get_drive_stats()
        
        # Clear screen and display header
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🚀 SoleID Scraping Session Monitor")
        print("=" * 60)
        print(f"⏱️  Session Duration: {elapsed}")
        print(f"🕐 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Database Statistics
        print("\n📊 DATABASE STATISTICS")
        print("-" * 30)
        print(f"👟 Total Sneakers: {stats['total_sneakers']:,}")
        print(f"🖼️  Total Images: {stats['total_images']:,}")
        print(f"💰 Total Prices: {stats['total_prices']:,}")
        print(f"🆕 Recent Sneakers (1h): {stats['recent_sneakers']:,}")
        print(f"🆕 Recent Images (1h): {stats['recent_images']:,}")
        
        # Brand Distribution
        print("\n🏷️  TOP BRANDS")
        print("-" * 20)
        for brand, count in stats['brand_stats']:
            print(f"   {brand}: {count:,}")
        
        # Google Drive Statistics
        print("\n☁️  GOOGLE DRIVE STATUS")
        print("-" * 25)
        if 'error' in drive_stats:
            print(f"❌ Error: {drive_stats['error']}")
        else:
            print(f"📁 Total Files: {drive_stats['total_files']:,}")
            print(f"📂 Folders: {drive_stats['folders']:,}")
            print(f"🖼️  Images: {drive_stats['images']:,}")
        
        # Performance Metrics
        if elapsed.total_seconds() > 0:
            sneakers_per_hour = (stats['recent_sneakers'] / elapsed.total_seconds()) * 3600
            images_per_hour = (stats['recent_images'] / elapsed.total_seconds()) * 3600
            
            print("\n⚡ PERFORMANCE METRICS")
            print("-" * 25)
            print(f"👟 Sneakers/Hour: {sneakers_per_hour:.1f}")
            print(f"🖼️  Images/Hour: {images_per_hour:.1f}")
        
        # Progress Indicators
        print("\n🎯 SESSION PROGRESS")
        print("-" * 20)
        target_sneakers = 500  # From our scraping target
        progress = min(100, (stats['recent_sneakers'] / target_sneakers) * 100)
        progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
        print(f"Progress: [{progress_bar}] {progress:.1f}%")
        print(f"Target: {target_sneakers:,} sneakers")
        
        print("\n" + "=" * 60)
        print("Press Ctrl+C to stop monitoring")
        print("=" * 60)

def main():
    """Main monitoring loop"""
    monitor = ScrapingMonitor()
    
    try:
        while True:
            monitor.display_status()
            time.sleep(30)  # Update every 30 seconds
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        print("📊 Final session statistics displayed above")

if __name__ == "__main__":
    main()