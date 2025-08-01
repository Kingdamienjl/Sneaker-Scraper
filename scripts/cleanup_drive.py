#!/usr/bin/env python3
"""
Clean up empty folders on Google Drive and check for actual scraped data
"""

import os
from google_drive import GoogleDriveManager
from database import SessionLocal
from models import Sneaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_empty_folders():
    """Clean up empty brand folders on Google Drive"""
    try:
        drive_manager = GoogleDriveManager()
        
        # Get the SoleID_Images folder
        soleid_folder = drive_manager.get_or_create_folder("SoleID_Images")
        if not soleid_folder:
            logger.error("Could not find SoleID_Images folder")
            return
            
        logger.info(f"Found SoleID_Images folder: {soleid_folder['id']}")
        
        # List all folders in SoleID_Images
        folders = drive_manager.service.files().list(
            q=f"'{soleid_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)"
        ).execute()
        
        empty_folders = []
        non_empty_folders = []
        
        for folder in folders.get('files', []):
            # Check if folder has any files
            files = drive_manager.service.files().list(
                q=f"'{folder['id']}' in parents",
                fields="files(id, name)"
            ).execute()
            
            file_count = len(files.get('files', []))
            if file_count == 0:
                empty_folders.append(folder)
                logger.info(f"Empty folder: {folder['name']}")
            else:
                non_empty_folders.append((folder, file_count))
                logger.info(f"Folder {folder['name']} has {file_count} files")
        
        logger.info(f"\n📊 DRIVE ANALYSIS:")
        logger.info(f"   • Total folders: {len(folders.get('files', []))}")
        logger.info(f"   • Empty folders: {len(empty_folders)}")
        logger.info(f"   • Non-empty folders: {len(non_empty_folders)}")
        
        if non_empty_folders:
            logger.info(f"\n✅ FOLDERS WITH DATA:")
            for folder, count in non_empty_folders:
                logger.info(f"   • {folder['name']}: {count} files")
        
        # Ask user if they want to delete empty folders
        if empty_folders:
            logger.info(f"\n🗑️ EMPTY FOLDERS TO DELETE:")
            for folder in empty_folders:
                logger.info(f"   • {folder['name']}")
            
            # Delete empty folders
            deleted_count = 0
            for folder in empty_folders:
                try:
                    drive_manager.service.files().delete(fileId=folder['id']).execute()
                    logger.info(f"   ✅ Deleted: {folder['name']}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"   ❌ Failed to delete {folder['name']}: {e}")
            
            logger.info(f"\n🎯 CLEANUP COMPLETE: Deleted {deleted_count} empty folders")
        else:
            logger.info(f"\n✅ No empty folders found!")
            
        return non_empty_folders
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return []

def check_database_data():
    """Check what data we have in the database"""
    try:
        db = SessionLocal()
        
        # Get sneaker count
        sneakers = db.query(Sneaker).all()
        logger.info(f"\n📊 DATABASE ANALYSIS:")
        logger.info(f"   • Total sneakers: {len(sneakers)}")
        
        if sneakers:
            # Group by brand
            brands = {}
            for sneaker in sneakers:
                brand = sneaker.brand or 'Unknown'
                if brand not in brands:
                    brands[brand] = 0
                brands[brand] += 1
            
            logger.info(f"   • Brands with data: {len(brands)}")
            logger.info(f"\n✅ BRANDS IN DATABASE:")
            for brand, count in sorted(brands.items()):
                logger.info(f"   • {brand}: {count} sneakers")
                
            # Show sample sneaker
            sample = sneakers[0]
            logger.info(f"\n📝 SAMPLE SNEAKER:")
            logger.info(f"   • Name: {sample.name}")
            logger.info(f"   • Brand: {sample.brand}")
            logger.info(f"   • Price: ${sample.retail_price}")
            logger.info(f"   • Images: {len(sample.images)}")
        else:
            logger.info(f"   ❌ No sneakers found in database")
            
        db.close()
            
    except Exception as e:
        logger.error(f"Error checking database: {e}")

if __name__ == "__main__":
    logger.info("🧹 STARTING DRIVE CLEANUP AND DATA CHECK")
    logger.info("=" * 50)
    
    # Clean up empty folders
    non_empty_folders = cleanup_empty_folders()
    
    # Check database data
    check_database_data()
    
    logger.info("\n" + "=" * 50)
    logger.info("🎯 CLEANUP AND CHECK COMPLETE!")