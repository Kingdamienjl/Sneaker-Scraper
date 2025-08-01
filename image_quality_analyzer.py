#!/usr/bin/env python3
"""
Image Quality Analyzer - Check for redundant and non-shoe images
Analyzes all images in the database for quality, relevance, and duplicates
"""

import os
import sys
import time
import logging
import sqlite3
import hashlib
import requests
from datetime import datetime
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path
import tempfile
from PIL import Image
import imagehash
import cv2
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_drive import GoogleDriveManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/image_quality_analyzer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ImageQualityAnalyzer:
    """Comprehensive image quality and relevance analyzer"""
    
    def __init__(self):
        # Initialize Google Drive
        try:
            self.drive_manager = GoogleDriveManager()
            logger.info("✅ Google Drive authentication successful")
        except Exception as e:
            logger.error(f"❌ Google Drive authentication failed: {e}")
            self.drive_manager = None
        
        # Create temp directory for analysis
        self.temp_dir = Path("temp_analysis")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Analysis results
        self.results = {
            'total_images': 0,
            'analyzed': 0,
            'duplicates': [],
            'low_quality': [],
            'non_shoe_images': [],
            'broken_links': [],
            'high_quality': [],
            'errors': 0
        }
        
        # Shoe detection keywords
        self.shoe_keywords = [
            'sneaker', 'shoe', 'boot', 'trainer', 'runner', 'basketball',
            'nike', 'adidas', 'jordan', 'yeezy', 'air', 'max', 'force',
            'dunk', 'blazer', 'cortez', 'pegasus', 'react', 'zoom',
            'ultra', 'boost', 'nmd', 'stan', 'smith', 'gazelle',
            'superstar', 'continental', 'forum', 'samba'
        ]
        
        # Non-shoe indicators
        self.non_shoe_indicators = [
            'logo', 'brand', 'text', 'banner', 'advertisement', 'ad',
            'person', 'model', 'face', 'body', 'lifestyle', 'outfit',
            'background', 'pattern', 'texture', 'abstract', 'graphic'
        ]
    
    def download_image_for_analysis(self, image_url: str) -> Optional[Path]:
        """Download image temporarily for analysis"""
        try:
            response = requests.get(image_url, timeout=10, stream=True)
            if response.status_code != 200:
                return None
            
            # Create temp file
            temp_file = self.temp_dir / f"temp_{int(time.time())}_{hash(image_url) % 10000}.jpg"
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return temp_file
            
        except Exception as e:
            logger.error(f"Error downloading {image_url}: {e}")
            return None
    
    def calculate_image_hashes(self, image_path: Path) -> Dict[str, str]:
        """Calculate multiple types of image hashes"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                return {
                    'phash': str(imagehash.phash(img)),
                    'dhash': str(imagehash.dhash(img)),
                    'ahash': str(imagehash.average_hash(img)),
                    'whash': str(imagehash.whash(img))
                }
        except Exception as e:
            logger.error(f"Error calculating hashes for {image_path}: {e}")
            return {}
    
    def analyze_image_quality(self, image_path: Path) -> Dict:
        """Analyze image quality metrics"""
        try:
            # PIL analysis
            with Image.open(image_path) as img:
                width, height = img.size
                file_size = image_path.stat().st_size
                
                # Basic quality metrics
                resolution = width * height
                aspect_ratio = width / height if height > 0 else 0
                
            # OpenCV analysis for more advanced metrics
            cv_img = cv2.imread(str(image_path))
            if cv_img is not None:
                # Calculate sharpness (Laplacian variance)
                gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                
                # Calculate brightness
                brightness = np.mean(cv_img)
                
                # Calculate contrast
                contrast = np.std(cv_img)
            else:
                sharpness = brightness = contrast = 0
            
            return {
                'width': width,
                'height': height,
                'resolution': resolution,
                'file_size': file_size,
                'aspect_ratio': aspect_ratio,
                'sharpness': sharpness,
                'brightness': brightness,
                'contrast': contrast
            }
            
        except Exception as e:
            logger.error(f"Error analyzing quality for {image_path}: {e}")
            return {}
    
    def detect_shoe_content(self, image_path: Path, image_url: str) -> Dict:
        """Detect if image contains shoe content"""
        try:
            # URL-based detection
            url_lower = image_url.lower()
            
            # Check for shoe keywords in URL
            shoe_score = sum(1 for keyword in self.shoe_keywords if keyword in url_lower)
            
            # Check for non-shoe indicators
            non_shoe_score = sum(1 for indicator in self.non_shoe_indicators if indicator in url_lower)
            
            # Simple heuristic scoring
            is_likely_shoe = shoe_score > non_shoe_score and shoe_score > 0
            
            # Additional checks based on image properties
            quality_metrics = self.analyze_image_quality(image_path)
            
            # Very small images are likely logos/icons
            if quality_metrics.get('resolution', 0) < 10000:  # Less than 100x100
                is_likely_shoe = False
                non_shoe_score += 2
            
            # Very wide or tall images are likely banners
            aspect_ratio = quality_metrics.get('aspect_ratio', 1)
            if aspect_ratio > 3 or aspect_ratio < 0.3:
                is_likely_shoe = False
                non_shoe_score += 1
            
            return {
                'is_likely_shoe': is_likely_shoe,
                'shoe_score': shoe_score,
                'non_shoe_score': non_shoe_score,
                'confidence': min(abs(shoe_score - non_shoe_score) / max(shoe_score + non_shoe_score, 1), 1.0)
            }
            
        except Exception as e:
            logger.error(f"Error detecting shoe content for {image_path}: {e}")
            return {'is_likely_shoe': True, 'shoe_score': 0, 'non_shoe_score': 0, 'confidence': 0}
    
    def is_high_quality_image(self, quality_metrics: Dict, shoe_detection: Dict) -> bool:
        """Determine if image meets high quality standards"""
        if not quality_metrics:
            return False
        
        # Quality thresholds
        min_resolution = 50000  # 200x250 minimum
        min_sharpness = 100
        min_file_size = 5000  # 5KB minimum
        
        # Check basic quality requirements
        meets_resolution = quality_metrics.get('resolution', 0) >= min_resolution
        meets_sharpness = quality_metrics.get('sharpness', 0) >= min_sharpness
        meets_file_size = quality_metrics.get('file_size', 0) >= min_file_size
        is_shoe_content = shoe_detection.get('is_likely_shoe', False)
        
        return meets_resolution and meets_sharpness and meets_file_size and is_shoe_content
    
    def find_duplicate_images(self, image_hashes: List[Dict]) -> List[List[Dict]]:
        """Find duplicate images using perceptual hashing"""
        logger.info("🔍 Finding duplicate images...")
        
        duplicate_groups = []
        processed = set()
        
        for i, img1 in enumerate(image_hashes):
            if img1['id'] in processed:
                continue
            
            duplicate_group = [img1]
            processed.add(img1['id'])
            
            # Compare with remaining images
            for j, img2 in enumerate(image_hashes[i+1:], i+1):
                if img2['id'] in processed:
                    continue
                
                # Check if images are similar
                if self.are_images_similar(img1['hashes'], img2['hashes']):
                    duplicate_group.append(img2)
                    processed.add(img2['id'])
            
            if len(duplicate_group) > 1:
                duplicate_groups.append(duplicate_group)
        
        return duplicate_groups
    
    def are_images_similar(self, hashes1: Dict, hashes2: Dict, threshold: int = 5) -> bool:
        """Check if two images are similar based on their hashes"""
        try:
            # Compare perceptual hashes
            phash1 = imagehash.hex_to_hash(hashes1.get('phash', ''))
            phash2 = imagehash.hex_to_hash(hashes2.get('phash', ''))
            
            phash_distance = phash1 - phash2
            
            # Also check difference hash
            dhash1 = imagehash.hex_to_hash(hashes1.get('dhash', ''))
            dhash2 = imagehash.hex_to_hash(hashes2.get('dhash', ''))
            
            dhash_distance = dhash1 - dhash2
            
            # Images are similar if both distances are below threshold
            return phash_distance <= threshold and dhash_distance <= threshold
            
        except Exception as e:
            logger.error(f"Error comparing hashes: {e}")
            return False
    
    def analyze_all_images(self):
        """Analyze all images in the database"""
        logger.info("🚀 Starting comprehensive image analysis...")
        
        try:
            conn = sqlite3.connect('sneakers.db')
            cursor = conn.cursor()
            
            # Get all images from database
            cursor.execute("""
                SELECT si.id, si.image_url, si.google_drive_id, s.name, s.brand, s.model
                FROM sneaker_images si
                JOIN sneakers s ON si.sneaker_id = s.id
                ORDER BY si.id
            """)
            
            images = cursor.fetchall()
            self.results['total_images'] = len(images)
            
            logger.info(f"📊 Found {len(images)} images to analyze")
            
            image_data = []
            
            for i, (img_id, image_url, drive_id, name, brand, model) in enumerate(images):
                try:
                    logger.info(f"🔍 Analyzing image {i+1}/{len(images)}: {name}")
                    
                    # Download image for analysis
                    temp_path = self.download_image_for_analysis(image_url)
                    if not temp_path:
                        self.results['broken_links'].append({
                            'id': img_id,
                            'url': image_url,
                            'sneaker': f"{brand} {model}",
                            'reason': 'Download failed'
                        })
                        continue
                    
                    # Calculate hashes
                    hashes = self.calculate_image_hashes(temp_path)
                    if not hashes:
                        self.results['errors'] += 1
                        temp_path.unlink(missing_ok=True)
                        continue
                    
                    # Analyze quality
                    quality_metrics = self.analyze_image_quality(temp_path)
                    
                    # Detect shoe content
                    shoe_detection = self.detect_shoe_content(temp_path, image_url)
                    
                    # Store analysis data
                    analysis_data = {
                        'id': img_id,
                        'url': image_url,
                        'drive_id': drive_id,
                        'sneaker': f"{brand} {model}",
                        'hashes': hashes,
                        'quality': quality_metrics,
                        'shoe_detection': shoe_detection
                    }
                    
                    image_data.append(analysis_data)
                    
                    # Categorize image
                    if not shoe_detection['is_likely_shoe']:
                        self.results['non_shoe_images'].append(analysis_data)
                    elif self.is_high_quality_image(quality_metrics, shoe_detection):
                        self.results['high_quality'].append(analysis_data)
                    else:
                        self.results['low_quality'].append(analysis_data)
                    
                    self.results['analyzed'] += 1
                    
                    # Cleanup temp file
                    temp_path.unlink(missing_ok=True)
                    
                    # Progress update
                    if (i + 1) % 50 == 0:
                        logger.info(f"📈 Progress: {i+1}/{len(images)} analyzed")
                    
                except Exception as e:
                    logger.error(f"Error analyzing image {img_id}: {e}")
                    self.results['errors'] += 1
            
            # Find duplicates
            duplicate_groups = self.find_duplicate_images(image_data)
            self.results['duplicates'] = duplicate_groups
            
            # Generate report
            self.generate_analysis_report()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
    
    def generate_analysis_report(self):
        """Generate comprehensive analysis report"""
        logger.info("📋 Generating analysis report...")
        
        report = f"""
============================================================
🔍 IMAGE QUALITY ANALYSIS REPORT
============================================================
📊 Analysis Summary:
   • Total Images: {self.results['total_images']:,}
   • Successfully Analyzed: {self.results['analyzed']:,}
   • Analysis Errors: {self.results['errors']:,}

🎯 Quality Categories:
   • High Quality Images: {len(self.results['high_quality']):,}
   • Low Quality Images: {len(self.results['low_quality']):,}
   • Non-Shoe Images: {len(self.results['non_shoe_images']):,}
   • Broken Links: {len(self.results['broken_links']):,}

🔄 Duplicate Analysis:
   • Duplicate Groups Found: {len(self.results['duplicates']):,}
   • Total Duplicate Images: {sum(len(group)-1 for group in self.results['duplicates']):,}

============================================================
📝 DETAILED FINDINGS:
============================================================
"""
        
        # Non-shoe images details
        if self.results['non_shoe_images']:
            report += "\n❌ NON-SHOE IMAGES:\n"
            for img in self.results['non_shoe_images'][:10]:  # Show first 10
                report += f"   • {img['sneaker']}: {img['url'][:80]}...\n"
            if len(self.results['non_shoe_images']) > 10:
                report += f"   ... and {len(self.results['non_shoe_images'])-10} more\n"
        
        # Duplicate groups details
        if self.results['duplicates']:
            report += "\n🔄 DUPLICATE GROUPS:\n"
            for i, group in enumerate(self.results['duplicates'][:5], 1):  # Show first 5 groups
                report += f"   Group {i} ({len(group)} images):\n"
                for img in group:
                    report += f"     - {img['sneaker']}: {img['url'][:60]}...\n"
            if len(self.results['duplicates']) > 5:
                report += f"   ... and {len(self.results['duplicates'])-5} more groups\n"
        
        # Broken links
        if self.results['broken_links']:
            report += "\n🔗 BROKEN LINKS:\n"
            for img in self.results['broken_links'][:10]:  # Show first 10
                report += f"   • {img['sneaker']}: {img['url'][:80]}...\n"
            if len(self.results['broken_links']) > 10:
                report += f"   ... and {len(self.results['broken_links'])-10} more\n"
        
        report += f"""
============================================================
💡 RECOMMENDATIONS:
============================================================
1. Remove {len(self.results['non_shoe_images'])} non-shoe images
2. Remove {sum(len(group)-1 for group in self.results['duplicates'])} duplicate images
3. Fix or remove {len(self.results['broken_links'])} broken image links
4. Keep {len(self.results['high_quality'])} high-quality images
5. Consider improving {len(self.results['low_quality'])} low-quality images

🎉 Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
============================================================
"""
        
        print(report)
        
        # Save report to file
        report_file = Path(f"image_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 Report saved to: {report_file}")
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            if self.temp_dir.exists():
                for temp_file in self.temp_dir.glob("*"):
                    temp_file.unlink(missing_ok=True)
                self.temp_dir.rmdir()
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

def main():
    """Main execution function"""
    analyzer = ImageQualityAnalyzer()
    
    try:
        analyzer.analyze_all_images()
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
    finally:
        analyzer.cleanup_temp_files()

if __name__ == "__main__":
    main()