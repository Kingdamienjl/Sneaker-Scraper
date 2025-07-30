"""
Utility functions for the sneaker scraper.
"""

import re
import hashlib
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text data."""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\-\.\,\(\)\$]', '', text)
    
    return text

def extract_price(text: str) -> float:
    """Extract price from text string."""
    if not text:
        return 0.0
    
    # Remove currency symbols and extract numbers
    price_match = re.search(r'[\$]?(\d+(?:,\d{3})*(?:\.\d{2})?)', text.replace(',', ''))
    
    if price_match:
        try:
            return float(price_match.group(1).replace(',', ''))
        except ValueError:
            pass
    
    return 0.0

def normalize_brand(brand: str) -> str:
    """Normalize brand names to standard format."""
    if not brand:
        return ""
    
    brand = clean_text(brand).lower()
    
    # Brand name mappings
    brand_mappings = {
        'nike': 'Nike',
        'jordan': 'Jordan',
        'adidas': 'Adidas',
        'yeezy': 'Yeezy',
        'new balance': 'New Balance',
        'converse': 'Converse',
        'vans': 'Vans',
        'puma': 'Puma',
        'reebok': 'Reebok',
        'asics': 'ASICS',
        'under armour': 'Under Armour'
    }
    
    for key, value in brand_mappings.items():
        if key in brand:
            return value
    
    return brand.title()

def generate_sneaker_hash(name: str, brand: str, colorway: str = "") -> str:
    """Generate a unique hash for a sneaker based on its attributes."""
    combined = f"{normalize_brand(brand)}_{clean_text(name)}_{clean_text(colorway)}".lower()
    return hashlib.md5(combined.encode()).hexdigest()

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def make_absolute_url(base_url: str, relative_url: str) -> str:
    """Convert relative URL to absolute URL."""
    if is_valid_url(relative_url):
        return relative_url
    return urljoin(base_url, relative_url)

def extract_sku(text: str) -> str:
    """Extract SKU from text."""
    if not text:
        return ""
    
    # Common SKU patterns
    sku_patterns = [
        r'SKU[:\s]*([A-Z0-9\-]+)',
        r'Style[:\s]*([A-Z0-9\-]+)',
        r'Model[:\s]*([A-Z0-9\-]+)',
        r'\b([A-Z]{2}\d{4}-\d{3})\b',  # Nike pattern
        r'\b([A-Z0-9]{6,12})\b'  # General pattern
    ]
    
    for pattern in sku_patterns:
        match = re.search(pattern, text.upper())
        if match:
            return match.group(1)
    
    return ""

def validate_sneaker_data(data: Dict[str, Any]) -> bool:
    """Validate sneaker data before saving."""
    required_fields = ['name', 'brand']
    
    for field in required_fields:
        if not data.get(field) or not data[field].strip():
            logger.warning(f"Missing required field: {field}")
            return False
    
    # Validate prices
    if data.get('retail_price', 0) < 0 or data.get('current_price', 0) < 0:
        logger.warning("Invalid price values")
        return False
    
    return True

def format_sneaker_name(name: str) -> str:
    """Format sneaker name to standard format."""
    if not name:
        return ""
    
    name = clean_text(name)
    
    # Remove common prefixes/suffixes
    prefixes_to_remove = ['nike ', 'jordan ', 'adidas ', 'air ']
    suffixes_to_remove = [' sneakers', ' shoes', ' trainers']
    
    name_lower = name.lower()
    for prefix in prefixes_to_remove:
        if name_lower.startswith(prefix):
            name = name[len(prefix):]
            break
    
    for suffix in suffixes_to_remove:
        if name_lower.endswith(suffix):
            name = name[:-len(suffix)]
            break
    
    return name.strip()

def get_image_filename(url: str, sneaker_hash: str, index: int = 0) -> str:
    """Generate a filename for downloaded images."""
    extension = url.split('.')[-1].lower()
    if extension not in ['jpg', 'jpeg', 'png', 'webp']:
        extension = 'jpg'
    
    return f"{sneaker_hash}_{index}.{extension}"

def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scraper.log'),
            logging.StreamHandler()
        ]
    )