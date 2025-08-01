#!/usr/bin/env python3
"""
Simple script to clean up empty Google Drive folders
"""

from google_drive import GoogleDriveManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_empty_folders():
    """Clean up empty brand folders on Google Drive"""
    try:
        drive_manager = GoogleDriveManager()
        
        # Get the SoleID_Images folder
        soleid_folder = drive_manager.find_folder_by_name("SoleID_Images")
        if not soleid_folder:
            logger.error("Could not find SoleID_Images folder")
            return
            
        logger.info(f"Found SoleID_Images folder: {soleid_folder['id']}")
        
        # List all folders in SoleID_Images
        folders = drive_manager.service.files().list(
            q=f"'{soleid_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        empty_folders = []
        non_empty_folders = []
        
        for folder in folders.get('files', []):
            # Check if folder has any files
            files = drive_manager.service.files().list(
                q=f"'{folder['id']}' in parents and trashed=false",
                fields="files(id, name)"
            ).execute()
            
            file_count = len(files.get('files', []))
            if file_count == 0:
                empty_folders.append(folder)
            else:
                non_empty_folders.append((folder, file_count))
        
        logger.info(f"\n📊 DRIVE ANALYSIS:")
        logger.info(f"   • Total folders: {len(folders.get('files', []))}")
        logger.info(f"   • Empty folders: {len(empty_folders)}")
        logger.info(f"   • Non-empty folders: {len(non_empty_folders)}")
        
        if non_empty_folders:
            logger.info(f"\n✅ FOLDERS WITH DATA:")
            for folder, count in non_empty_folders:
                logger.info(f"   • {folder['name']}: {count} files")
        
        # Delete empty folders
        if empty_folders:
            logger.info(f"\n🗑️ DELETING EMPTY FOLDERS:")
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
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    logger.info("🧹 CLEANING UP EMPTY GOOGLE DRIVE FOLDERS")
    logger.info("=" * 50)
    cleanup_empty_folders()
    logger.info("=" * 50)
    logger.info("🎯 CLEANUP COMPLETE!")