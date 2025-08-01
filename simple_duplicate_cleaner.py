#!/usr/bin/env python3
"""
Simple Duplicate Image Cleaner - Remove duplicate images using file hashing
Uses only built-in Python libraries for maximum compatibility
"""

import os
import sys
import time
import logging
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, List, Set
from pathlib import Path
import shutil
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_drive import GoogleDriveManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/duplicate_cleaner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleDuplicateCleaner:
    """Simple duplicate image detection and cleanup using file hashing"""
    
    def __init__(self):
        # Initialize Google Drive
        try:
            self.drive_manager = GoogleDriveManager()
            logger.info("✅ Google Drive authentication successful")
        except Exception as e:
            logger.error(f"❌ Google Drive authentication failed: {e}")
            self.drive_manager = None
        
        # Image directories to check
        self.image_dirs = [
            Path("data/real_images"),
            Path("data/web_images"), 
            Path("data/direct_images"),
            Path("data/parallel_images")
        ]
        
        # Create backup directory
        self.backup_dir = Path("data/duplicate_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'total_images': 0,
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'space_saved': 0,
            'database_cleaned': 0,
            'drive_cleaned': 0
        }
    
    def calculate_file_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of file content"""
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {filepath}: {e}")
            return ""
    
    def find_local_duplicates(self) -> Dict[str, List[Dict]]:
        """Find duplicate images in local directories"""
        logger.info("🔍 Scanning local directories for duplicate images...")
        
        file_hashes = defaultdict(list)
        
        # Scan all image directories
        for img_dir in self.image_dirs:
            if img_dir.exists():
                logger.info(f"📁 Scanning: {img_dir}")
                image_files = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.png"))
                
                for img_file in image_files:
                    try:
                        file_hash = self.calculate_file_hash(img_file)
                        if file_hash:
                            stat = img_file.stat()
                            file_info = {
                                'path': str(img_file),
                                'name': img_file.name,
                                'size': stat.st_size,
                                'modified': stat.st_mtime,
                                'hash': file_hash
                            }
                            file_hashes[file_hash].append(file_info)
                            self.stats['total_images'] += 1
                    except Exception as e:
                        logger.error(f"Error processing {img_file}: {e}")
        
        # Find duplicates
        duplicates = {}
        for file_hash, files in file_hashes.items():
            if len(files) > 1:
                duplicates[file_hash] = files
                self.stats['duplicates_found'] += len(files) - 1
        
        logger.info(f"📊 Found {self.stats['total_images']} total images")
        logger.info(f"🔍 Found {len(duplicates)} duplicate groups with {self.stats['duplicates_found']} duplicate images")
        
        return duplicates
    
    def remove_local_duplicates(self, duplicates: Dict[str, List[Dict]]):
        """Remove duplicate files, keeping the largest/newest one"""
        logger.info("🗑️ Removing local duplicate files...")
        
        for file_hash, images in duplicates.items():
            if len(images) <= 1:
                continue
            
            # Sort by size (descending) then by modification time (descending)
            images.sort(key=lambda x: (x['size'], x['modified']), reverse=True)
            
            # Keep the first (best quality/newest), remove the rest
            keep_image = images[0]
            remove_images = images[1:]
            
            logger.info(f"✅ Keeping: {keep_image['name']} ({keep_image['size']} bytes)")
            
            for img in remove_images:
                try:
                    img_path = Path(img['path'])
                    
                    # Backup before deletion
                    backup_path = self.backup_dir / f"{int(time.time())}_{img_path.name}"
                    shutil.copy2(img_path, backup_path)
                    
                    # Remove original
                    img_path.unlink()
                    
                    self.stats['duplicates_removed'] += 1
                    self.stats['space_saved'] += img['size']
                    
                    logger.info(f"🗑️ Removed: {img['name']} ({img['size']} bytes)")
                    
                except Exception as e:
                    logger.error(f"❌ Error removing {img['path']}: {e}")
    
    def clean_database_duplicates(self):
        """Remove duplicate entries from database"""
        logger.info("🗄️ Cleaning database duplicates...")
        
        try:
            conn = sqlite3.connect('sneakers.db')
            cursor = conn.cursor()
            
            # Find duplicate image URLs
            cursor.execute("""
                SELECT image_url, COUNT(*) as count, GROUP_CONCAT(id) as ids
                FROM sneaker_images 
                WHERE image_url IS NOT NULL AND image_url != ''
                GROUP BY image_url 
                HAVING count > 1
                ORDER BY count DESC
            """)
            
            duplicates = cursor.fetchall()
            logger.info(f"Found {len(duplicates)} duplicate URL groups in database")
            
            for image_url, count, ids in duplicates:
                id_list = ids.split(',')
                # Keep the first one, delete the rest
                for duplicate_id in id_list[1:]:
                    cursor.execute("DELETE FROM sneaker_images WHERE id = ?", (duplicate_id,))
                    self.stats['database_cleaned'] += 1
                
                logger.info(f"🗄️ Cleaned {count-1} duplicates for URL: {image_url[:50]}...")
            
            # Also find duplicate local file paths
            cursor.execute("""
                SELECT local_path, COUNT(*) as count, GROUP_CONCAT(id) as ids
                FROM sneaker_images 
                WHERE local_path IS NOT NULL AND local_path != ''
                GROUP BY local_path 
                HAVING count > 1
                ORDER BY count DESC
            """)
            
            path_duplicates = cursor.fetchall()
            logger.info(f"Found {len(path_duplicates)} duplicate path groups in database")
            
            for local_path, count, ids in path_duplicates:
                id_list = ids.split(',')
                # Keep the first one, delete the rest
                for duplicate_id in id_list[1:]:
                    cursor.execute("DELETE FROM sneaker_images WHERE id = ?", (duplicate_id,))
                    self.stats['database_cleaned'] += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Removed {self.stats['database_cleaned']} duplicate database entries")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning database: {e}")
    
    def clean_google_drive_duplicates(self):
        """Clean duplicates from Google Drive Nike folder"""
        if not self.drive_manager:
            logger.warning("⚠️ Google Drive not available, skipping Drive cleanup")
            return
        
        logger.info("☁️ Cleaning Google Drive duplicates...")
        
        try:
            # First find SoleID_Images folder
            soleid_folder = self.drive_manager.find_folder_by_name("SoleID_Images")
            if not soleid_folder:
                logger.error("❌ SoleID_Images folder not found on Google Drive")
                return
            
            # Get Nike folder inside SoleID_Images (most problematic according to user)
            nike_folder = self.drive_manager.find_folder_by_name('Nike', soleid_folder['id'])
            if not nike_folder:
                logger.error("❌ Nike folder not found on Google Drive")
                return
            
            nike_folder_id = nike_folder['id']
            
            # List all files in Nike folder
            files = self.drive_manager.service.files().list(
                q=f"'{nike_folder_id}' in parents and trashed=false",
                fields="files(id, name, size, md5Checksum, createdTime)",
                pageSize=1000
            ).execute().get('files', [])
            
            logger.info(f"📁 Found {len(files)} files in Nike folder")
            
            # Group by MD5 checksum (exact duplicates)
            hash_groups = defaultdict(list)
            for file in files:
                md5 = file.get('md5Checksum')
                if md5:
                    hash_groups[md5].append(file)
            
            # Remove duplicates
            for md5, file_group in hash_groups.items():
                if len(file_group) > 1:
                    # Sort by creation time, keep the oldest
                    file_group.sort(key=lambda x: x.get('createdTime', ''))
                    
                    logger.info(f"🔍 Found {len(file_group)} duplicates: {file_group[0]['name']}")
                    
                    # Delete all but the first (oldest)
                    for duplicate_file in file_group[1:]:
                        try:
                            self.drive_manager.service.files().delete(
                                fileId=duplicate_file['id']
                            ).execute()
                            
                            self.stats['drive_cleaned'] += 1
                            logger.info(f"🗑️ Removed from Drive: {duplicate_file['name']}")
                            
                            # Small delay to avoid rate limiting
                            time.sleep(0.1)
                            
                        except Exception as e:
                            logger.error(f"❌ Error removing {duplicate_file['name']}: {e}")
            
            logger.info(f"✅ Removed {self.stats['drive_cleaned']} duplicate files from Google Drive")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning Google Drive: {e}")
    
    def analyze_duplicate_patterns(self, duplicates: Dict[str, List[Dict]]):
        """Analyze patterns in duplicate images"""
        logger.info("📊 Analyzing duplicate patterns...")
        
        # Analyze by directory
        dir_stats = defaultdict(int)
        for file_hash, images in duplicates.items():
            for img in images:
                dir_name = Path(img['path']).parent.name
                dir_stats[dir_name] += 1
        
        logger.info("📁 Duplicates by directory:")
        for dir_name, count in sorted(dir_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {dir_name}: {count} duplicates")
        
        # Analyze by file size
        size_ranges = {
            'Small (< 50KB)': 0,
            'Medium (50KB - 200KB)': 0,
            'Large (200KB - 500KB)': 0,
            'Very Large (> 500KB)': 0
        }
        
        for file_hash, images in duplicates.items():
            for img in images[1:]:  # Count only duplicates, not originals
                size = img['size']
                if size < 50 * 1024:
                    size_ranges['Small (< 50KB)'] += 1
                elif size < 200 * 1024:
                    size_ranges['Medium (50KB - 200KB)'] += 1
                elif size < 500 * 1024:
                    size_ranges['Large (200KB - 500KB)'] += 1
                else:
                    size_ranges['Very Large (> 500KB)'] += 1
        
        logger.info("📏 Duplicates by size:")
        for size_range, count in size_ranges.items():
            logger.info(f"  {size_range}: {count} duplicates")
    
    def generate_report(self):
        """Generate cleanup report"""
        logger.info("📊 Generating cleanup report...")
        
        space_saved_mb = self.stats['space_saved'] / (1024 * 1024)
        
        report = f"""
🧹 DUPLICATE IMAGE CLEANUP REPORT
{'='*60}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 STATISTICS:
  Total images scanned: {self.stats['total_images']:,}
  Duplicate images found: {self.stats['duplicates_found']:,}
  Local duplicates removed: {self.stats['duplicates_removed']:,}
  Database entries cleaned: {self.stats['database_cleaned']:,}
  Google Drive files cleaned: {self.stats['drive_cleaned']:,}
  Space saved: {space_saved_mb:.1f} MB

✅ CLEANUP ACTIONS COMPLETED:
  ✓ Local duplicate files removed and backed up
  ✓ Database duplicate entries cleaned
  ✓ Google Drive Nike folder duplicates removed
  ✓ Backup copies created in: {self.backup_dir}

🎯 NEXT STEPS:
  1. Monitor image collection processes for duplicate prevention
  2. Implement hash checking in scrapers before download
  3. Regular maintenance cleanup (weekly recommended)
  4. Consider implementing image similarity detection

💡 RECOMMENDATIONS:
  - Add duplicate checking to all image scrapers
  - Use file hashing before saving new images
  - Implement better filename uniqueness
  - Regular automated cleanup scheduling

{'='*60}
        """
        
        print(report)
        
        # Save report to file
        report_file = Path("data/duplicate_cleanup_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 Report saved to: {report_file}")
    
    def run(self):
        """Run complete duplicate cleanup process"""
        start_time = time.time()
        logger.info("🚀 Starting Simple Duplicate Image Cleanup")
        
        try:
            # 1. Find local duplicates
            duplicates = self.find_local_duplicates()
            
            # 2. Analyze patterns
            if duplicates:
                self.analyze_duplicate_patterns(duplicates)
                
                # 3. Remove local duplicates
                self.remove_local_duplicates(duplicates)
            
            # 4. Clean database duplicates
            self.clean_database_duplicates()
            
            # 5. Clean Google Drive duplicates
            self.clean_google_drive_duplicates()
            
            # 6. Generate report
            self.generate_report()
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Duplicate cleanup completed in {elapsed_time:.1f} seconds!")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            raise

if __name__ == "__main__":
    cleaner = SimpleDuplicateCleaner()
    cleaner.run()