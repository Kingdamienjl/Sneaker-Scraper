from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        self.max_size = Config.MAX_IMAGE_SIZE
        self.quality = Config.IMAGE_QUALITY
    
    def process_image(self, image_path: str) -> str:
        """Process image: resize, enhance, and optimize"""
        try:
            # Open image with PIL
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize image while maintaining aspect ratio
                img = self._resize_image(img)
                
                # Enhance image quality
                img = self._enhance_image(img)
                
                # Save processed image
                processed_path = image_path.replace('.jpg', '_processed.jpg')
                img.save(processed_path, 'JPEG', quality=self.quality, optimize=True)
                
                logger.info(f"Processed image: {processed_path}")
                return processed_path
        
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            return image_path  # Return original path if processing fails
    
    def _resize_image(self, img: Image.Image) -> Image.Image:
        """Resize image while maintaining aspect ratio"""
        width, height = img.size
        
        if width <= self.max_size and height <= self.max_size:
            return img
        
        # Calculate new dimensions
        if width > height:
            new_width = self.max_size
            new_height = int((height * self.max_size) / width)
        else:
            new_height = self.max_size
            new_width = int((width * self.max_size) / height)
        
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _enhance_image(self, img: Image.Image) -> Image.Image:
        """Enhance image quality"""
        try:
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            # Enhance contrast slightly
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.05)
            
            # Enhance color saturation slightly
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.05)
            
            return img
        
        except Exception as e:
            logger.error(f"Error enhancing image: {str(e)}")
            return img
    
    def extract_features(self, image_path: str) -> dict:
        """Extract features from image for similarity comparison"""
        try:
            # Read image with OpenCV
            img = cv2.imread(image_path)
            if img is None:
                return {}
            
            # Convert to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Extract color histogram
            hist_r = cv2.calcHist([img_rgb], [0], None, [256], [0, 256])
            hist_g = cv2.calcHist([img_rgb], [1], None, [256], [0, 256])
            hist_b = cv2.calcHist([img_rgb], [2], None, [256], [0, 256])
            
            # Extract dominant colors
            dominant_colors = self._get_dominant_colors(img_rgb)
            
            # Calculate image statistics
            mean_color = np.mean(img_rgb, axis=(0, 1))
            std_color = np.std(img_rgb, axis=(0, 1))
            
            return {
                'histogram_r': hist_r.flatten().tolist(),
                'histogram_g': hist_g.flatten().tolist(),
                'histogram_b': hist_b.flatten().tolist(),
                'dominant_colors': dominant_colors,
                'mean_color': mean_color.tolist(),
                'std_color': std_color.tolist(),
                'image_size': img_rgb.shape[:2]
            }
        
        except Exception as e:
            logger.error(f"Error extracting features from {image_path}: {str(e)}")
            return {}
    
    def _get_dominant_colors(self, img_rgb: np.ndarray, k: int = 5) -> list:
        """Extract dominant colors using K-means clustering"""
        try:
            # Reshape image to be a list of pixels
            pixels = img_rgb.reshape(-1, 3)
            
            # Apply K-means clustering
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get the dominant colors
            colors = kmeans.cluster_centers_.astype(int)
            
            # Get the percentage of each color
            labels = kmeans.labels_
            percentages = np.bincount(labels) / len(labels)
            
            # Sort by percentage
            sorted_indices = np.argsort(percentages)[::-1]
            
            dominant_colors = []
            for i in sorted_indices:
                dominant_colors.append({
                    'color': colors[i].tolist(),
                    'percentage': float(percentages[i])
                })
            
            return dominant_colors
        
        except Exception as e:
            logger.error(f"Error extracting dominant colors: {str(e)}")
            return []
    
    def compare_images(self, features1: dict, features2: dict) -> float:
        """Compare two images based on their features"""
        try:
            if not features1 or not features2:
                return 0.0
            
            # Compare histograms
            hist_similarity = self._compare_histograms(features1, features2)
            
            # Compare dominant colors
            color_similarity = self._compare_dominant_colors(
                features1.get('dominant_colors', []),
                features2.get('dominant_colors', [])
            )
            
            # Compare mean colors
            mean_similarity = self._compare_mean_colors(
                features1.get('mean_color', []),
                features2.get('mean_color', [])
            )
            
            # Weighted average
            similarity = (hist_similarity * 0.4 + color_similarity * 0.4 + mean_similarity * 0.2)
            
            return similarity
        
        except Exception as e:
            logger.error(f"Error comparing images: {str(e)}")
            return 0.0
    
    def _compare_histograms(self, features1: dict, features2: dict) -> float:
        """Compare color histograms"""
        try:
            hist1_r = np.array(features1.get('histogram_r', []))
            hist1_g = np.array(features1.get('histogram_g', []))
            hist1_b = np.array(features1.get('histogram_b', []))
            
            hist2_r = np.array(features2.get('histogram_r', []))
            hist2_g = np.array(features2.get('histogram_g', []))
            hist2_b = np.array(features2.get('histogram_b', []))
            
            if len(hist1_r) == 0 or len(hist2_r) == 0:
                return 0.0
            
            # Calculate correlation coefficient for each channel
            corr_r = np.corrcoef(hist1_r, hist2_r)[0, 1]
            corr_g = np.corrcoef(hist1_g, hist2_g)[0, 1]
            corr_b = np.corrcoef(hist1_b, hist2_b)[0, 1]
            
            # Handle NaN values
            corr_r = 0.0 if np.isnan(corr_r) else corr_r
            corr_g = 0.0 if np.isnan(corr_g) else corr_g
            corr_b = 0.0 if np.isnan(corr_b) else corr_b
            
            return (corr_r + corr_g + corr_b) / 3
        
        except Exception as e:
            logger.error(f"Error comparing histograms: {str(e)}")
            return 0.0
    
    def _compare_dominant_colors(self, colors1: list, colors2: list) -> float:
        """Compare dominant colors"""
        try:
            if not colors1 or not colors2:
                return 0.0
            
            similarity_scores = []
            
            for color1 in colors1[:3]:  # Compare top 3 colors
                best_match = 0.0
                for color2 in colors2[:3]:
                    # Calculate color distance
                    c1 = np.array(color1['color'])
                    c2 = np.array(color2['color'])
                    distance = np.linalg.norm(c1 - c2)
                    
                    # Convert distance to similarity (0-1)
                    similarity = max(0, 1 - distance / 441.67)  # 441.67 is max distance in RGB space
                    
                    # Weight by color percentage
                    weighted_similarity = similarity * min(color1['percentage'], color2['percentage'])
                    
                    best_match = max(best_match, weighted_similarity)
                
                similarity_scores.append(best_match)
            
            return np.mean(similarity_scores) if similarity_scores else 0.0
        
        except Exception as e:
            logger.error(f"Error comparing dominant colors: {str(e)}")
            return 0.0
    
    def _compare_mean_colors(self, mean1: list, mean2: list) -> float:
        """Compare mean colors"""
        try:
            if not mean1 or not mean2:
                return 0.0
            
            m1 = np.array(mean1)
            m2 = np.array(mean2)
            
            distance = np.linalg.norm(m1 - m2)
            similarity = max(0, 1 - distance / 441.67)
            
            return similarity
        
        except Exception as e:
            logger.error(f"Error comparing mean colors: {str(e)}")
            return 0.0