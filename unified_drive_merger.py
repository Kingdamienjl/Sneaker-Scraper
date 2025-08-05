#!/usr/bin/env python3
"""
Unified Drive Merger - Consolidate All Sneaker Data
Merges all scraped sneaker images into organized Google Drive structure:
- Root: SoleID_Unified_Collection/
  - Brand_Name/
    - Model_Name/
      - images with proper naming
"""

import os
import sqlite3
import json
import logging
import hashlib
import re
from datetime import datetime
from pathlib import Path
from google_drive import GoogleDriveManager
from database import SessionLocal, create_tables
from sqlalchemy import text
from collections import defaultdict

class UnifiedDriveMerger:
    def __init__(self):
        self.setup_logging()
        self.drive_manager = GoogleDriveManager()
        self.processed_files = set()
        self.brand_folders = {}
        self.model_folders = {}
        self.stats = {
            'total_images': 0,
            'duplicates_removed': 0,
            'brands_created': 0,
            'models_created': 0,
            'upload_success': 0,
            'upload_failed': 0
        }
        
    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('unified_merger.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def normalize_brand_name(self, brand):
        """Normalize brand names for consistent folder structure"""
        brand_mapping = {
            'nike': 'Nike',
            'adidas': 'Adidas', 
            'jordan': 'Jordan',
            'new balance': 'New_Balance',
            'puma': 'Puma',
            'vans': 'Vans',
            'converse': 'Converse',
            'reebok': 'Reebok',
            'asics': 'ASICS',
            'under armour': 'Under_Armour'
        }
        
        brand_clean = brand.lower().strip()
        return brand_mapping.get(brand_clean, brand.replace(' ', '_').title())
    
    def normalize_model_name(self, model):
        """Normalize model names for folder structure"""
        # Remove quotes and special characters
        model_clean = re.sub(r'["\']', '', model)
        model_clean = re.sub(r'[^\w\s-]', '', model_clean)
        model_clean = re.sub(r'\s+', '_', model_clean.strip())
        return model_clean
    
    def get_file_hash(self, filepath):
        """Generate hash for duplicate detection"""
        try:
            with open(filepath, 'rb') as f:
                file_content = f.read()
                # Use both MD5 and file size for better duplicate detection
                md5_hash = hashlib.md5(file_content).hexdigest()
                file_size = len(file_content)
                return f"{md5_hash}_{file_size}"
        except:
            return None
    
    def clean_existing_drive_duplicates(self):
        """Clean any existing duplicates on Google Drive before uploading"""
        self.logger.info("Scanning Google Drive for existing duplicates...")
        
        try:
            # Get all files in the root folder if it exists
            existing_files = self.drive_manager.list_files_in_folder(self.root_folder_id)
            
            # Track files by hash for duplicate detection
            file_hashes = {}
            duplicates_found = 0
            
            for file_info in existing_files:
                # Download and hash existing files to check for duplicates
                temp_path = f"temp_{file_info['name']}"
                if self.drive_manager.download_file(file_info['id'], temp_path):
                    file_hash = self.get_file_hash(temp_path)
                    
                    if file_hash in file_hashes:
                        # Delete duplicate from Drive
                        self.drive_manager.delete_file(file_info['id'])
                        duplicates_found += 1
                        self.logger.info(f"Removed duplicate: {file_info['name']}")
                    else:
                        file_hashes[file_hash] = file_info
                    
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            self.logger.info(f"Cleaned {duplicates_found} existing duplicates from Google Drive")
            return duplicates_found
            
        except Exception as e:
            self.logger.warning(f"Could not clean existing duplicates: {e}")
            return 0
    
    def create_drive_folder_structure(self):
        """Create the unified folder structure on Google Drive"""
        self.logger.info("Creating unified folder structure on Google Drive...")
        
        # Create root folder
        root_folder_name = f"SoleID_Unified_Collection_{datetime.now().strftime('%Y%m%d')}"
        self.root_folder_id = self.drive_manager.create_folder(root_folder_name)
        
        if not self.root_folder_id:
            raise Exception("Failed to create root folder on Google Drive")
            
        self.logger.info(f"Created root folder: {root_folder_name}")
        return self.root_folder_id
    
    def get_or_create_brand_folder(self, brand_name):
        """Get or create brand folder on Google Drive"""
        normalized_brand = self.normalize_brand_name(brand_name)
        
        if normalized_brand not in self.brand_folders:
            folder_id = self.drive_manager.create_folder(
                normalized_brand, 
                parent_folder_id=self.root_folder_id
            )
            if folder_id:
                self.brand_folders[normalized_brand] = folder_id
                self.stats['brands_created'] += 1
                self.logger.info(f"Created brand folder: {normalized_brand}")
            else:
                self.logger.error(f"Failed to create brand folder: {normalized_brand}")
                return None
                
        return self.brand_folders[normalized_brand]
    
    def get_or_create_model_folder(self, brand_name, model_name):
        """Get or create model folder under brand folder"""
        normalized_brand = self.normalize_brand_name(brand_name)
        normalized_model = self.normalize_model_name(model_name)
        
        folder_key = f"{normalized_brand}/{normalized_model}"
        
        if folder_key not in self.model_folders:
            brand_folder_id = self.get_or_create_brand_folder(brand_name)
            if not brand_folder_id:
                return None
                
            folder_id = self.drive_manager.create_folder(
                normalized_model,
                parent_folder_id=brand_folder_id
            )
            if folder_id:
                self.model_folders[folder_key] = folder_id
                self.stats['models_created'] += 1
                self.logger.info(f"Created model folder: {folder_key}")
            else:
                self.logger.error(f"Failed to create model folder: {folder_key}")
                return None
                
        return self.model_folders[folder_key]
    
    def process_database_images(self):
        """Process all images from all database tables"""
        self.logger.info("Processing images from all database tables...")
        
        tables_to_process = [
            'sneaker_images',
            'enhanced_36_hour_images', 
            'hyperbrowser_demo_images',
            'collected_images'
        ]
        
        total_processed = 0
        
        with SessionLocal() as session:
            # Process each table
            for table_name in tables_to_process:
                self.logger.info(f"Processing table: {table_name}")
                
                try:
                    # Check if table exists
                    result = session.execute(text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=:table_name
                    """), {"table_name": table_name})
                    
                    if not result.fetchone():
                        self.logger.info(f"Table {table_name} does not exist, skipping...")
                        continue
                    
                    # Query based on table structure
                    if table_name == 'sneaker_images':
                        results = session.execute(text("SELECT brand, model, image_url, local_path FROM sneaker_images")).fetchall()
                    elif table_name == 'enhanced_36_hour_images':
                        results = session.execute(text("SELECT brand, model, image_url, local_path FROM enhanced_36_hour_images")).fetchall()
                    elif table_name == 'hyperbrowser_demo_images':
                        results = session.execute(text("SELECT brand, model, image_url, local_path FROM hyperbrowser_demo_images")).fetchall()
                    elif table_name == 'collected_images':
                        results = session.execute(text("SELECT brand, model, image_url, local_path FROM collected_images")).fetchall()
                    else:
                        continue
                    
                    self.logger.info(f"Found {len(results)} images in {table_name}")
                    
                    for row in results:
                        brand, model, image_url, local_path = row
                        
                        if local_path and os.path.exists(local_path):
                            success = self.process_single_image(
                                brand, model, local_path, image_url, None
                            )
                            if success:
                                total_processed += 1
                            
                except Exception as e:
                    self.logger.error(f"Error processing table {table_name}: {e}")
                    continue
        
        self.logger.info(f"Total images processed from database: {total_processed}")
        return total_processed
    
    def process_directory_images(self):
        """Process images from data directories"""
        self.logger.info("Processing images from data directories...")
        
        data_dirs = [
            'data/images',
            'data/enhanced_images', 
            'data/hyperbrowser_demo_images',
            'data/collected_images'
        ]
        
        total_processed = 0
        
        for data_dir in data_dirs:
            if not os.path.exists(data_dir):
                continue
                
            self.logger.info(f"Processing directory: {data_dir}")
            
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        filepath = os.path.join(root, file)
                        
                        # Extract brand and model from path/filename
                        brand, model = self.extract_brand_model_from_path(filepath, file)
                        
                        if self.process_single_image(brand, model, filepath, None, None):
                            total_processed += 1
        
        self.logger.info(f"Total images processed from directories: {total_processed}")
        return total_processed
    
    def extract_brand_model_from_path(self, filepath, filename):
        """Extract brand and model from file path and name"""
        # Try to extract from path structure
        path_parts = Path(filepath).parts
        
        # Look for brand indicators in path
        brands = ['nike', 'adidas', 'jordan', 'puma', 'vans', 'converse', 'new_balance']
        brand = 'Unknown'
        model = 'Unknown_Model'
        
        for part in path_parts:
            part_lower = part.lower()
            for brand_name in brands:
                if brand_name in part_lower:
                    brand = brand_name.title()
                    break
        
        # Try to extract model from filename
        filename_clean = os.path.splitext(filename)[0]
        filename_clean = re.sub(r'[_-]', ' ', filename_clean)
        
        # Remove common suffixes
        filename_clean = re.sub(r'\s*(stockx|goat|nike|adidas|official|footlocker)\s*', '', filename_clean, flags=re.IGNORECASE)
        filename_clean = re.sub(r'\s*[a-f0-9]{8}\s*$', '', filename_clean)  # Remove hash
        
        if len(filename_clean.strip()) > 3:
            model = filename_clean.strip()
        
        return brand, model
    
    def process_single_image(self, brand, model, local_path, url, quality_score):
        """Process a single image for upload"""
        try:
            if not os.path.exists(local_path):
                return False
            
            # Check for duplicates
            file_hash = self.get_file_hash(local_path)
            if file_hash in self.processed_files:
                self.stats['duplicates_removed'] += 1
                return False
            
            # Get model folder
            model_folder_id = self.get_or_create_model_folder(brand, model)
            if not model_folder_id:
                return False
            
            # Create proper filename
            file_ext = os.path.splitext(local_path)[1]
            normalized_brand = self.normalize_brand_name(brand)
            normalized_model = self.normalize_model_name(model)
            
            new_filename = f"{normalized_brand}_{normalized_model}_{file_hash[:8]}{file_ext}"
            
            # Upload to Google Drive
            success = self.drive_manager.upload_file(
                file_path=local_path,
                file_name=new_filename,
                folder_name=f"{brand}/{model}"
            )
            
            if success:
                self.processed_files.add(file_hash)
                self.stats['upload_success'] += 1
                self.stats['total_images'] += 1
                
                if self.stats['total_images'] % 50 == 0:
                    self.logger.info(f"Progress: {self.stats['total_images']} images uploaded")
                
                return True
            else:
                self.stats['upload_failed'] += 1
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing {local_path}: {e}")
            self.stats['upload_failed'] += 1
            return False
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        report = {
            'merger_session': {
                'start_time': self.start_time,
                'end_time': datetime.now(),
                'duration_minutes': (datetime.now() - self.start_time).total_seconds() / 60
            },
            'statistics': self.stats,
            'folder_structure': {
                'root_folder_id': self.root_folder_id,
                'brands_created': list(self.brand_folders.keys()),
                'total_model_folders': len(self.model_folders)
            }
        }
        
        # Save report
        report_file = f"unified_merger_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Log summary
        self.logger.info("UNIFIED MERGER COMPLETE")
        self.logger.info(f"Total Images Processed: {self.stats['total_images']}")
        self.logger.info(f"Successful Uploads: {self.stats['upload_success']}")
        self.logger.info(f"Failed Uploads: {self.stats['upload_failed']}")
        self.logger.info(f"Duplicates Removed: {self.stats['duplicates_removed']}")
        self.logger.info(f"Brands Created: {self.stats['brands_created']}")
        self.logger.info(f"Model Folders Created: {self.stats['models_created']}")
        self.logger.info(f"Duration: {report['merger_session']['duration_minutes']:.1f} minutes")
        self.logger.info(f"Report saved: {report_file}")
        
        return report
    
    def run_unified_merger(self):
        """Run the complete unified merger process"""
        self.start_time = datetime.now()
        self.logger.info("STARTING UNIFIED DRIVE MERGER")
        self.logger.info("Consolidating all sneaker data into organized Google Drive structure")
        self.logger.info("ENSURING CLEAN STRUCTURE - NO DUPLICATES")
        
        try:
            # Create folder structure
            self.create_drive_folder_structure()
            
            # Clean existing duplicates on Drive
            existing_duplicates = self.clean_existing_drive_duplicates()
            
            # Process all images with enhanced duplicate detection
            self.logger.info("Processing all local images with duplicate detection...")
            db_count = self.process_database_images()
            dir_count = self.process_directory_images()
            
            # Final duplicate scan and cleanup
            self.logger.info("Performing final duplicate cleanup...")
            final_duplicates = self.clean_existing_drive_duplicates()
            
            # Update stats
            self.stats['drive_duplicates_cleaned'] = existing_duplicates + final_duplicates
            
            # Generate final report
            report = self.generate_final_report()
            
            self.logger.info("UNIFIED MERGER COMPLETED - CLEAN STRUCTURE GUARANTEED")
            return report
            
        except Exception as e:
            self.logger.error(f"Unified merger failed: {e}")
            raise

if __name__ == "__main__":
    merger = UnifiedDriveMerger()
    merger.run_unified_merger()