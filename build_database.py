#!/usr/bin/env python3
"""
SoleID Database Builder
Start scraping sneaker data and building the comprehensive database
"""

import sys
import os
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_scraper import start_database_building
from database import create_tables

def setup_logging():
    """Setup logging configuration"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = f"database_build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_path

def main():
    """Main function to start database building"""
    print("🚀 SoleID Database Builder Starting...")
    print("=" * 50)
    
    # Setup logging
    log_path = setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("SoleID Database Builder Started")
    logger.info(f"Log file: {log_path}")
    
    try:
        # Ensure database tables exist
        print("📊 Setting up database tables...")
        create_tables()
        logger.info("Database tables created/verified")
        
        # Start the scraping process
        print("🔍 Starting sneaker data collection...")
        print("📱 This will scrape popular sneakers from multiple platforms")
        print("🖼️ Images will be saved to Google Drive")
        print("💾 Data will be stored in the local database")
        print("⏱️ This process may take 30-60 minutes...")
        print()
        
        # Confirm before starting
        response = input("Do you want to start the database building process? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Database building cancelled")
            return
        
        print("\n🎯 Starting data collection...")
        results = start_database_building()
        
        print("\n" + "=" * 50)
        print("✅ DATABASE BUILDING COMPLETED!")
        print(f"📈 Total sneaker items collected: {results['total_items']}")
        print(f"🖼️ Total images saved: {results['total_images']}")
        print(f"📝 Log file saved: {log_path}")
        print("=" * 50)
        
        logger.info("Database building completed successfully")
        logger.info(f"Results: {results}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        logger.warning("Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during database building: {str(e)}")
        logger.error(f"Error during database building: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()