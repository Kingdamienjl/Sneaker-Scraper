#!/usr/bin/env python3
"""
Image Categorizer for Google Drive
Organizes sneaker images by brand in the SoleID Google Drive folder
"""

import os
import sqlite3
import logging
from datetime import datetime
from google_drive import GoogleDriveManager
import requests
from urllib.parse import urlparse
import hashlib

class ImageCategorizer:
    def __init__(self):
        self.setup_logging()
        self.setup_database()
        self.setup_google_drive()
        self.setup_stats()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/image_categorizer_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_database(self):
        """Setup database connection"""
        self.db_path = "sneakers.db"
        
    def setup_google_drive(self):
        """Setup Google Drive manager"""
        try:
            self.drive_manager = GoogleDriveManager()
            self.logger.info("Google Drive manager initialized")
            
            # Get or create SoleID_Images folder
            self.main_folder_id = self.drive_manager.get_or_create_folder("SoleID_Images")
            self.logger.info(f"Main folder ID: {self.main_folder_id}")
            
        except Exception as e:
            self.logger.error(f"Error setting up Google Drive: {e}")
            raise
            
    def setup_stats(self):
        """Initialize statistics"""
        self.stats = {
            'total': 0,
            'categorized': 0,
            'uploaded': 0,
            'errors': 0,
            'skipped': 0
        }
        
    def get_database_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path, timeout=30.0)
        
    def get_images_to_categorize(self):
        """Get all images from database that need categorization"""
        conn = self.get_database_connection()
        cursor = conn.cursor()
        
        try:
            # Get images with brand information from sneaker_images table
            cursor.execute('''
                SELECT DISTINCT 
                    si.id, si.image_url, si.google_drive_id,
                    s.brand, s.name, s.model, s.colorway
                FROM sneaker_images si 
                LEFT JOIN sneakers s ON si.sneaker_id = s.id 
                WHERE si.image_url IS NOT NULL AND si.image_url != ''
                ORDER BY s.brand, s.name
            ''')
            
            images = cursor.fetchall()
            self.logger.info(f"Found {len(images)} images to categorize")
            return images
            
        except Exception as e:
            self.logger.error(f"Error getting images: {e}")
            return []
        finally:
            conn.close()
            
    def download_image(self, url, filename):
        """Download image from URL"""
        try:
            # Create temp directory
            temp_dir = "temp_images"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Download image
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Save to temp file
            temp_path = os.path.join(temp_dir, filename)
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            self.logger.info(f"Downloaded: {filename}")
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Error downloading {url}: {e}")
            return None
            
    def sanitize_filename(self, filename):
        """Sanitize filename for Google Drive"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:95] + ext
            
        return filename
        
    def create_brand_folders(self):
        """Create brand folders in Google Drive"""
        conn = self.get_database_connection()
        cursor = conn.cursor()
        
        try:
            # Get all unique brands
            cursor.execute('''
                SELECT DISTINCT s.brand 
                FROM sneakers s 
                WHERE s.brand IS NOT NULL AND s.brand != ''
                ORDER BY s.brand
            ''')
            
            brands = [row[0] for row in cursor.fetchall()]
            self.logger.info(f"Creating folders for {len(brands)} brands")
            
            brand_folders = {}
            for brand in brands:
                if brand:
                    folder_id = self.drive_manager.get_or_create_folder(brand, self.main_folder_id)
                    if folder_id:
                        brand_folders[brand] = folder_id
                        self.stats['brands_created'] += 1
                        self.logger.info(f"Created/found folder for brand: {brand}")
                        
            return brand_folders
            
        except Exception as e:
            self.logger.error(f"Error creating brand folders: {e}")
            return {}
        finally:
            conn.close()
            
    def categorize_images(self):
        """Main function to categorize all images"""
        self.logger.info("🎯 Starting image categorization...")
        
        # Create brand folders
        brand_folders = self.create_brand_folders()
        self.logger.info(f"Created {len(brand_folders)} brand folders")
        
        # Get images to categorize
        images = self.get_images_to_categorize()
        self.stats['total_images'] = len(images)
        
        if not images:
            self.logger.warning("No images found to categorize")
            return
            
        # Process each image
        for image_data in images:
            try:
                image_id, image_url, google_drive_id, brand, name, model, colorway = image_data
                
                # Skip if no brand
                if not brand:
                    self.logger.warning(f"Skipping image {image_id} - no brand information")
                    continue
                    
                # Skip if already uploaded to Google Drive
                if google_drive_id:
                    self.logger.info(f"Image {image_id} already has Google Drive ID: {google_drive_id}")
                    self.stats['categorized'] += 1
                    continue
                    
                # Get brand folder
                brand_folder_id = brand_folders.get(brand)
                if not brand_folder_id:
                    self.logger.warning(f"No folder found for brand: {brand}")
                    continue
                    
                # Create filename from URL or generate one
                if image_url:
                    filename = os.path.basename(urlparse(image_url).path)
                    if not filename or '.' not in filename:
                        filename = f"{brand}_{name}_{image_id}.jpg"
                else:
                    filename = f"{brand}_{name}_{image_id}.jpg"
                    
                safe_filename = self.sanitize_filename(filename)
                
                # Check if already uploaded
                existing_file = self.drive_manager.find_file_by_name(safe_filename, brand_folder_id)
                if existing_file:
                    self.logger.info(f"Image already exists: {safe_filename}")
                    # Update database with existing file ID
                    self.update_image_drive_id(image_id, existing_file['id'])
                    self.stats['categorized'] += 1
                    continue
                
                # Download image from URL
                try:
                    response = requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    
                    # Create temporary file
                    temp_dir = "temp_images"
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, safe_filename)
                    with open(temp_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Upload to Google Drive
                    file_id = self.drive_manager.upload_image(
                        temp_path, 
                        safe_filename, 
                        brand_folder_id
                    )
                    
                    if file_id:
                        self.logger.info(f"✅ Uploaded {safe_filename} to {brand} folder")
                        self.update_image_drive_id(image_id, file_id)
                        self.stats['categorized'] += 1
                        self.stats['uploaded'] += 1
                    else:
                        self.logger.error(f"Failed to upload {safe_filename}")
                        self.stats['errors'] += 1
                    
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                except requests.RequestException as e:
                    self.logger.error(f"Failed to download image {image_url}: {e}")
                    self.stats['errors'] += 1
                except Exception as e:
                    self.logger.error(f"Error processing image {image_id}: {e}")
                    self.stats['errors'] += 1
                        
            except Exception as e:
                self.logger.error(f"Error processing image {image_data[0]}: {e}")
                self.stats['errors'] += 1
                
        # Print final stats
        self.print_final_stats()
        
    def update_image_drive_id(self, image_id, drive_file_id):
        """Update image record with Google Drive file ID"""
        conn = self.get_database_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE sneaker_images 
                SET google_drive_id = ? 
                WHERE id = ?
            ''', (drive_file_id, image_id))
            
            conn.commit()
            self.logger.debug(f"Updated image {image_id} with Drive ID: {drive_file_id}")
            
        except Exception as e:
            self.logger.error(f"Error updating image Drive ID: {e}")
        finally:
            conn.close()
            
    def print_final_stats(self):
        """Print final statistics"""
        self.logger.info("=" * 50)
        self.logger.info("📊 FINAL STATISTICS")
        self.logger.info("=" * 50)
        self.logger.info(f"📁 Total images processed: {self.stats['total']}")
        self.logger.info(f"✅ Successfully categorized: {self.stats['categorized']}")
        self.logger.info(f"📤 Uploaded to Drive: {self.stats['uploaded']}")
        self.logger.info(f"❌ Errors: {self.stats['errors']}")
        self.logger.info(f"⏭️ Skipped: {self.stats['skipped']}")
        self.logger.info("=" * 50)
        
    def run(self):
        """Run the complete categorization process"""
        try:
            self.categorize_images()
        except Exception as e:
            self.logger.error(f"Fatal error in categorization: {e}")
            raise

def main():
    """Main function"""
    categorizer = ImageCategorizer()
    categorizer.run()

if __name__ == "__main__":
    main()