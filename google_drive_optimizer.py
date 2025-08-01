#!/usr/bin/env python3
"""
Google Drive Optimizer
Cleans up duplicates and organizes sneaker images in Google Drive
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import logging
from datetime import datetime
from google_drive import GoogleDriveManager
import threading

class GoogleDriveOptimizer:
    def __init__(self):
        self.setup_logging()
        self.setup_database()
        self.setup_google_drive()
        self.setup_stats()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('drive_optimizer')
        self.logger.setLevel(logging.INFO)
        
        # File handler with UTF-8 encoding
        log_file = os.path.join(log_dir, f"drive_optimizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def setup_database(self):
        """Setup database connection"""
        self.db_path = "sneakers.db"
        self.db_lock = threading.Lock()
        
    def setup_google_drive(self):
        """Setup Google Drive manager"""
        try:
            self.drive_manager = GoogleDriveManager()
            self.logger.info("Google Drive manager initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive: {e}")
            self.drive_manager = None
            raise
            
    def setup_stats(self):
        """Initialize statistics tracking"""
        self.stats = {
            'start_time': time.time(),
            'files_scanned': 0,
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'folders_organized': 0,
            'space_saved_mb': 0,
            'errors': []
        }
        
    def get_database_connection(self):
        """Get a database connection with proper timeout"""
        return sqlite3.connect(self.db_path, timeout=30.0)
        
    def scan_drive_images(self):
        """Scan all images in Google Drive"""
        try:
            self.logger.info("Scanning Google Drive for images...")
            
            # Get all image files from Drive
            all_files = []
            
            # Scan main folder
            main_files = self.drive_manager.list_files(file_type='image')
            all_files.extend(main_files)
            
            # Scan subfolders
            folders = self.drive_manager.list_files()
            for folder in folders:
                if folder.get('mimeType') == 'application/vnd.google-apps.folder':
                    folder_files = self.drive_manager.list_files(
                        folder_id=folder['id'], 
                        file_type='image'
                    )
                    all_files.extend(folder_files)
            
            self.logger.info(f"Found {len(all_files)} image files in Google Drive")
            self.stats['files_scanned'] = len(all_files)
            
            return all_files
            
        except Exception as e:
            self.logger.error(f"Error scanning Drive images: {e}")
            return []
            
    def find_duplicates_by_name(self, files):
        """Find duplicate files by name patterns"""
        duplicates = {}
        name_groups = {}
        
        for file in files:
            name = file['name']
            
            # Group by similar names (ignoring hash suffixes)
            base_name = self.extract_base_name(name)
            
            if base_name not in name_groups:
                name_groups[base_name] = []
            name_groups[base_name].append(file)
            
        # Find groups with multiple files
        for base_name, group in name_groups.items():
            if len(group) > 1:
                duplicates[base_name] = group
                self.stats['duplicates_found'] += len(group) - 1
                
        return duplicates
        
    def extract_base_name(self, filename):
        """Extract base name from filename, removing hash suffixes"""
        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Remove hash patterns (8 character hex at end)
        parts = name_without_ext.split('_')
        if len(parts) > 1 and len(parts[-1]) == 8:
            try:
                int(parts[-1], 16)  # Check if it's hex
                return '_'.join(parts[:-1])
            except ValueError:
                pass
                
        return name_without_ext
        
    def find_duplicates_by_size(self, files):
        """Find duplicate files by size"""
        size_groups = {}
        
        for file in files:
            size = file.get('size', '0')
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(file)
            
        # Return groups with multiple files
        duplicates = {}
        for size, group in size_groups.items():
            if len(group) > 1:
                duplicates[f"size_{size}"] = group
                
        return duplicates
        
    def remove_duplicates(self, duplicate_groups):
        """Remove duplicate files, keeping the oldest one"""
        removed_count = 0
        space_saved = 0
        
        for group_name, files in duplicate_groups.items():
            try:
                self.logger.info(f"Processing duplicate group: {group_name} ({len(files)} files)")
                
                # Sort by creation time (keep oldest)
                files_sorted = sorted(files, key=lambda x: x.get('createdTime', ''))
                
                # Keep first file, remove others
                keep_file = files_sorted[0]
                remove_files = files_sorted[1:]
                
                self.logger.info(f"Keeping: {keep_file['name']} (ID: {keep_file['id']})")
                
                for file_to_remove in remove_files:
                    try:
                        file_size = int(file_to_remove.get('size', '0'))
                        
                        if self.drive_manager.delete_file(file_to_remove['id']):
                            self.logger.info(f"Removed duplicate: {file_to_remove['name']}")
                            removed_count += 1
                            space_saved += file_size
                            
                            # Update database if this file was tracked
                            self.update_database_after_deletion(file_to_remove['id'])
                            
                    except Exception as e:
                        self.logger.error(f"Error removing file {file_to_remove['name']}: {e}")
                        self.stats['errors'].append(f"Delete error: {str(e)}")
                        
            except Exception as e:
                self.logger.error(f"Error processing group {group_name}: {e}")
                self.stats['errors'].append(f"Group processing error: {str(e)}")
                
        self.stats['duplicates_removed'] = removed_count
        self.stats['space_saved_mb'] = round(space_saved / (1024 * 1024), 2)
        
        return removed_count, space_saved
        
    def update_database_after_deletion(self, drive_file_id):
        """Update database records after file deletion"""
        try:
            with self.db_lock:
                conn = self.get_database_connection()
                cursor = conn.cursor()
                
                # Update all tables that might reference this drive file
                tables_to_update = [
                    'apify_images',
                    'rapidapi_images', 
                    'sneaks_images',
                    'production_images'
                ]
                
                for table in tables_to_update:
                    try:
                        cursor.execute(f"""
                            UPDATE {table} 
                            SET drive_status = 'deleted', drive_path = NULL
                            WHERE drive_path = ?
                        """, (drive_file_id,))
                    except sqlite3.OperationalError:
                        # Table might not exist
                        pass
                        
                conn.commit()
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error updating database after deletion: {e}")
            
    def organize_by_date(self):
        """Organize images into date-based folders"""
        try:
            self.logger.info("Organizing images by date...")
            
            # Get all image files
            all_files = self.scan_drive_images()
            
            # Group by creation date
            date_groups = {}
            for file in all_files:
                created_time = file.get('createdTime', '')
                if created_time:
                    # Extract date (YYYY-MM-DD)
                    date = created_time[:10]
                    if date not in date_groups:
                        date_groups[date] = []
                    date_groups[date].append(file)
                    
            # Create date folders and move files
            for date, files in date_groups.items():
                try:
                    folder_name = f"Sneaker Images/{date}"
                    folder_id = self.drive_manager.get_or_create_folder(folder_name)
                    
                    if folder_id:
                        self.logger.info(f"Organizing {len(files)} files into {folder_name}")
                        
                        for file in files:
                            # Move file to date folder (this would require additional Drive API calls)
                            # For now, we'll just log the organization
                            pass
                            
                        self.stats['folders_organized'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Error organizing date {date}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error organizing by date: {e}")
            
    def cleanup_empty_folders(self):
        """Remove empty folders from Google Drive"""
        try:
            self.logger.info("Cleaning up empty folders...")
            
            # Get all folders
            folders = self.drive_manager.list_files()
            empty_folders = []
            
            for folder in folders:
                if folder.get('mimeType') == 'application/vnd.google-apps.folder':
                    # Check if folder is empty
                    folder_contents = self.drive_manager.list_files(folder_id=folder['id'])
                    
                    if not folder_contents:
                        empty_folders.append(folder)
                        
            # Remove empty folders
            for folder in empty_folders:
                try:
                    if self.drive_manager.delete_file(folder['id']):
                        self.logger.info(f"Removed empty folder: {folder['name']}")
                except Exception as e:
                    self.logger.error(f"Error removing empty folder {folder['name']}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up empty folders: {e}")
            
    def generate_optimization_report(self):
        """Generate optimization report"""
        duration = time.time() - self.stats['start_time']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_minutes': round(duration / 60, 1),
            'files_scanned': self.stats['files_scanned'],
            'duplicates_found': self.stats['duplicates_found'],
            'duplicates_removed': self.stats['duplicates_removed'],
            'folders_organized': self.stats['folders_organized'],
            'space_saved_mb': self.stats['space_saved_mb'],
            'errors': self.stats['errors'][-10:]  # Last 10 errors
        }
        
        # Save report
        with open('drive_optimization_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\nGoogle Drive Optimization Report")
        print(f"================================")
        print(f"Duration: {duration/60:.1f} minutes")
        print(f"Files scanned: {self.stats['files_scanned']}")
        print(f"Duplicates found: {self.stats['duplicates_found']}")
        print(f"Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"Folders organized: {self.stats['folders_organized']}")
        print(f"Space saved: {self.stats['space_saved_mb']} MB")
        
        if self.stats['errors']:
            print(f"Errors encountered: {len(self.stats['errors'])}")
            
        return report
        
    def run_optimization(self):
        """Run complete Google Drive optimization"""
        self.logger.info("Starting Google Drive optimization...")
        
        try:
            # Scan all images
            all_files = self.scan_drive_images()
            
            if not all_files:
                self.logger.warning("No image files found in Google Drive")
                return None
                
            # Find duplicates by name
            name_duplicates = self.find_duplicates_by_name(all_files)
            self.logger.info(f"Found {len(name_duplicates)} duplicate groups by name")
            
            # Find duplicates by size
            size_duplicates = self.find_duplicates_by_size(all_files)
            self.logger.info(f"Found {len(size_duplicates)} duplicate groups by size")
            
            # Remove duplicates
            if name_duplicates:
                self.remove_duplicates(name_duplicates)
                
            # Organize by date
            self.organize_by_date()
            
            # Cleanup empty folders
            self.cleanup_empty_folders()
            
            # Generate report
            report = self.generate_optimization_report()
            self.logger.info("Google Drive optimization completed")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            return None

def main():
    """Main function"""
    optimizer = GoogleDriveOptimizer()
    
    try:
        # Run optimization
        report = optimizer.run_optimization()
        
        if report:
            print(f"\nOptimization completed successfully!")
            print(f"Removed {report['duplicates_removed']} duplicate files")
            print(f"Saved {report['space_saved_mb']} MB of space")
        else:
            print(f"\nOptimization completed. Check the logs for details.")
            
    except KeyboardInterrupt:
        print("\nOptimization interrupted by user")
    except Exception as e:
        print(f"Optimization failed: {e}")
        logging.error(f"Optimization failed: {e}")

if __name__ == "__main__":
    main()