"""
SoleID API Integrations
Comprehensive integration of Sneaks-API and Sneaker-API for database building
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import subprocess
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from models import Sneaker, SneakerImage, PriceHistory, ScrapingLog
from database import SessionLocal, create_tables
from google_drive import GoogleDriveManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_integrations.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SneakerAPIClient:
    """Client for HoseaCodes Sneaker-API (www.sneakerapi.io)"""
    
    def __init__(self):
        self.base_url = "https://www.sneakerapi.io"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SoleID-Database-Builder/1.0',
            'Accept': 'application/json'
        })
    
    def get_all_sneakers(self, limit: int = 100) -> List[Dict]:
        """Get all sneakers from the API"""
        try:
            response = self.session.get(f"{self.base_url}/api/sneakers", 
                                      params={'limit': limit}, 
                                      timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'sneakers' in data:
                return data['sneakers']
            else:
                logger.warning(f"Unexpected response format: {type(data)}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching sneakers from SneakerAPI: {e}")
            return []
    
    def get_sneaker_by_id(self, sneaker_id: str) -> Optional[Dict]:
        """Get specific sneaker by ID"""
        try:
            response = self.session.get(f"{self.base_url}/api/sneakers/{sneaker_id}", 
                                      timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching sneaker {sneaker_id}: {e}")
            return None

class SneaksAPIManager:
    """Manager for Sneaks-API Node.js package integration"""
    
    def __init__(self):
        self.node_script_path = project_root / "sneaks_api_wrapper.js"
        self.ensure_node_script()
    
    def ensure_node_script(self):
        """Create Node.js wrapper script for Sneaks-API"""
        node_script = '''
const SneaksAPI = require('sneaks-api');
const sneaks = new SneaksAPI();

const args = process.argv.slice(2);
const command = args[0];

function handleCallback(err, data) {
    if (err) {
        console.error(JSON.stringify({error: err.message || err}));
        process.exit(1);
    } else {
        console.log(JSON.stringify({success: true, data: data}));
        process.exit(0);
    }
}

switch(command) {
    case 'getProducts':
        const keyword = args[1] || 'Jordan';
        const limit = parseInt(args[2]) || 10;
        sneaks.getProducts(keyword, limit, handleCallback);
        break;
    
    case 'getMostPopular':
        const popularLimit = parseInt(args[1]) || 20;
        sneaks.getMostPopular(popularLimit, handleCallback);
        break;
    
    case 'getProductPrices':
        const styleId = args[1];
        if (!styleId) {
            console.error(JSON.stringify({error: 'Style ID required'}));
            process.exit(1);
        }
        sneaks.getProductPrices(styleId, handleCallback);
        break;
    
    default:
        console.error(JSON.stringify({error: 'Unknown command'}));
        process.exit(1);
}
'''
        
        try:
            with open(self.node_script_path, 'w') as f:
                f.write(node_script)
            logger.info("Node.js wrapper script created")
        except Exception as e:
            logger.error(f"Error creating Node.js script: {e}")
    
    def install_sneaks_api(self):
        """Install Sneaks-API npm package"""
        try:
            result = subprocess.run(['npm', 'install', 'sneaks-api'], 
                                  cwd=project_root, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=120)
            if result.returncode == 0:
                logger.info("Sneaks-API installed successfully")
                return True
            else:
                logger.error(f"Failed to install Sneaks-API: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error installing Sneaks-API: {e}")
            return False
    
    def run_node_command(self, command: str, *args) -> Optional[Dict]:
        """Run Node.js command and return parsed result"""
        try:
            cmd = ['node', str(self.node_script_path), command] + list(args)
            result = subprocess.run(cmd, 
                                  cwd=project_root, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Node command failed: {result.stderr}")
                return None
                
            # Parse the JSON output
            output = result.stdout.strip()
            if not output:
                logger.error("Empty output from Node command")
                return None
                
            try:
                parsed = json.loads(output)
                if parsed.get('success'):
                    return parsed.get('data', [])
                else:
                    logger.error(f"Node command error: {parsed.get('error', 'Unknown error')}")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON output: {e}")
                logger.error(f"Raw output: {output}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Node command timed out")
            return None
        except Exception as e:
            logger.error(f"Error running node command: {e}")
            return None
    
    def get_products(self, keyword: str, limit: int = 10) -> List[Dict]:
        """Get products by keyword"""
        result = self.run_node_command('getProducts', keyword, str(limit))
        if result and result.get('success'):
            return result.get('data', [])
        return []
    
    def get_most_popular(self, limit: int = 20) -> List[Dict]:
        """Get most popular sneakers"""
        result = self.run_node_command('getMostPopular', str(limit))
        if result and result.get('success'):
            return result.get('data', [])
        return []
    
    def get_popular_sneakers(self, limit=20):
        """Get popular sneakers from SneaksAPI"""
        result = self.run_node_command('getMostPopular', str(limit))
        return result if result else []
    
    def search_sneakers(self, keyword, limit=10):
        """Search for sneakers by keyword"""
        result = self.run_node_command('getProducts', keyword, str(limit))
        return result if result else []
    
    def get_product_prices(self, style_id: str) -> Optional[Dict]:
        """Get detailed product information by style ID"""
        result = self.run_node_command('getProductPrices', style_id)
        if result and result.get('success'):
            return result.get('data')
        return None

class ComprehensiveAPIBuilder:
    """Main class for building database using both APIs"""
    
    def __init__(self):
        self.sneaker_api = SneakerAPIClient()
        self.sneaks_api = SneaksAPIManager()
        self.drive_manager = GoogleDriveManager()
        self.session = SessionLocal()
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'sneaker_api_count': 0,
            'sneaks_api_count': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'images_processed': 0
        }
    
    def setup(self):
        """Setup database and dependencies"""
        try:
            create_tables()
            logger.info("Database tables created/verified")
            
            # Try to install Sneaks-API
            if not self.sneaks_api.install_sneaks_api():
                logger.warning("Sneaks-API installation failed, will skip Sneaks-API integration")
            
            return True
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    def normalize_sneaker_data(self, data: Dict, source: str) -> Dict:
        """Normalize sneaker data from different sources"""
        normalized = {
            'name': '',
            'brand': '',
            'model': '',
            'colorway': '',
            'style_id': '',
            'release_date': None,
            'retail_price': 0.0,
            'description': '',
            'images': [],
            'prices': {},
            'source': source
        }
        
        if source == 'sneaker-api':
            # Normalize SneakerAPI data
            normalized.update({
                'name': data.get('name', ''),
                'brand': data.get('brand', ''),
                'model': data.get('model', ''),
                'colorway': data.get('colorway', ''),
                'style_id': data.get('sku', '') or data.get('styleId', ''),
                'retail_price': float(data.get('retailPrice', 0) or 0),
                'description': data.get('description', ''),
                'images': data.get('images', []) if isinstance(data.get('images'), list) else []
            })
            
            # Parse release date
            if data.get('releaseDate'):
                try:
                    normalized['release_date'] = datetime.strptime(
                        data['releaseDate'], '%Y-%m-%d'
                    ).date()
                except:
                    pass
        
        elif source == 'sneaks-api':
            # Normalize SneaksAPI data
            normalized.update({
                'name': data.get('shoeName', ''),
                'brand': data.get('brand', ''),
                'colorway': data.get('colorway', ''),
                'style_id': data.get('styleID', ''),
                'retail_price': float(data.get('retailPrice', 0) or 0),
                'description': data.get('description', ''),
                'images': []
            })
            
            # Extract images
            if data.get('thumbnail'):
                normalized['images'].append(data['thumbnail'])
            if data.get('image'):
                normalized['images'].append(data['image'])
            
            # Extract prices
            if data.get('lowestResellPrice'):
                normalized['prices']['resell'] = data['lowestResellPrice']
            
            # Parse release date
            if data.get('releaseDate'):
                try:
                    normalized['release_date'] = datetime.strptime(
                        data['releaseDate'], '%m/%d/%Y'
                    ).date()
                except:
                    pass
        
        return normalized
    
    def save_sneaker_to_db(self, sneaker_data: Dict) -> bool:
        """Save normalized sneaker data to database"""
        try:
            # Skip if no name or brand
            if not sneaker_data.get('name') or not sneaker_data.get('brand'):
                logger.debug(f"Skipping sneaker with missing name or brand: {sneaker_data}")
                return False
            
            # Check for existing sneaker
            existing = None
            if sneaker_data['style_id']:
                existing = self.session.query(Sneaker).filter_by(
                    sku=sneaker_data['style_id']
                ).first()
            
            if not existing and sneaker_data['name']:
                existing = self.session.query(Sneaker).filter_by(
                    name=sneaker_data['name'],
                    brand=sneaker_data['brand']
                ).first()
            
            if existing:
                self.stats['duplicates_skipped'] += 1
                logger.debug(f"Skipping duplicate sneaker: {sneaker_data['name']}")
                return False
            
            # Create new sneaker
            sneaker = Sneaker(
                name=sneaker_data['name'],
                brand=sneaker_data['brand'],
                model=sneaker_data['model'],
                colorway=sneaker_data['colorway'],
                sku=sneaker_data['style_id'],  # Use style_id as SKU
                release_date=sneaker_data['release_date'],
                retail_price=sneaker_data['retail_price'],
                description=sneaker_data['description']
            )
            
            self.session.add(sneaker)
            self.session.flush()  # Get the ID
            
            logger.info(f"Saving sneaker: {sneaker_data['name']} by {sneaker_data['brand']}")
            
            # Save images
            for img_url in sneaker_data['images'][:5]:  # Limit to 5 images
                if img_url:
                    image = SneakerImage(
                        sneaker_id=sneaker.id,
                        image_url=img_url,
                        is_primary=(len(sneaker.images) == 0)
                    )
                    self.session.add(image)
                    self.stats['images_processed'] += 1
            
            # Save prices
            for price_type, price_value in sneaker_data['prices'].items():
                if price_value:
                    price_history = PriceHistory(
                        sneaker_id=sneaker.id,
                        platform=price_type,
                        price=float(price_value),
                        size='N/A',  # Default size since not provided by APIs
                        sale_date=datetime.now()
                    )
                    self.session.add(price_history)
            
            self.session.commit()
            self.stats['total_processed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error saving sneaker: {e}")
            self.session.rollback()
            self.stats['errors'] += 1
            return False
    
    def collect_from_sneaker_api(self, limit: int = 100):
        """Collect data from SneakerAPI"""
        logger.info(f"Collecting data from SneakerAPI (limit: {limit})")
        
        sneakers = self.sneaker_api.get_all_sneakers(limit)
        logger.info(f"Retrieved {len(sneakers)} sneakers from SneakerAPI")
        
        for sneaker_data in sneakers:
            normalized = self.normalize_sneaker_data(sneaker_data, 'sneaker-api')
            if self.save_sneaker_to_db(normalized):
                self.stats['sneaker_api_count'] += 1
            
            time.sleep(0.1)  # Rate limiting
    
    def collect_from_sneaks_api(self, limit: int = 50):
        """Collect data from SneaksAPI"""
        logger.info(f"Collecting data from SneaksAPI (limit: {limit})")
        
        # Get most popular sneakers
        popular_sneakers = self.sneaks_api.get_popular_sneakers(limit)
        logger.info(f"Retrieved {len(popular_sneakers)} popular sneakers from SneaksAPI")
        
        for sneaker_data in popular_sneakers:
            normalized = self.normalize_sneaker_data(sneaker_data, 'sneaks-api')
            if self.save_sneaker_to_db(normalized):
                self.stats['sneaks_api_count'] += 1
            
            time.sleep(0.2)  # Rate limiting
        
        # Search for specific brands
        brands = ['Nike', 'Adidas', 'Jordan', 'Yeezy', 'New Balance']
        for brand in brands:
            brand_sneakers = self.sneaks_api.search_sneakers(brand, 10)
            logger.info(f"Retrieved {len(brand_sneakers)} {brand} sneakers")
            
            for sneaker_data in brand_sneakers:
                normalized = self.normalize_sneaker_data(sneaker_data, 'sneaks-api')
                if self.save_sneaker_to_db(normalized):
                    self.stats['sneaks_api_count'] += 1
                
                time.sleep(0.2)
    
    def log_scraping_session(self):
        """Log the scraping session"""
        try:
            log_entry = ScrapingLog(
                platform='API_Integration',
                status='success',
                items_scraped=self.stats['total_processed'],
                errors_count=self.stats['errors'],
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            self.session.add(log_entry)
            self.session.commit()
        except Exception as e:
            logger.error(f"Error logging session: {e}")
    
    def print_summary(self):
        """Print collection summary"""
        print("\n" + "="*60)
        print("API INTEGRATION SUMMARY")
        print("="*60)
        print(f"Total Sneakers Processed: {self.stats['total_processed']}")
        print(f"From SneakerAPI: {self.stats['sneaker_api_count']}")
        print(f"From SneaksAPI: {self.stats['sneaks_api_count']}")
        print(f"Images Processed: {self.stats['images_processed']}")
        print(f"Duplicates Skipped: {self.stats['duplicates_skipped']}")
        print(f"Errors: {self.stats['errors']}")
        print("="*60)
    
    def run_comprehensive_collection(self, sneaker_api_limit: int = 100, 
                                   sneaks_api_limit: int = 50):
        """Run comprehensive data collection from both APIs"""
        start_time = time.time()
        
        logger.info("Starting comprehensive API data collection")
        
        if not self.setup():
            logger.error("Setup failed, aborting collection")
            return
        
        # Collect from SneakerAPI
        try:
            self.collect_from_sneaker_api(sneaker_api_limit)
        except Exception as e:
            logger.error(f"SneakerAPI collection failed: {e}")
        
        # Collect from SneaksAPI
        try:
            self.collect_from_sneaks_api(sneaks_api_limit)
        except Exception as e:
            logger.error(f"SneaksAPI collection failed: {e}")
        
        # Log session
        self.log_scraping_session()
        
        # Print summary
        self.print_summary()
        
        duration = time.time() - start_time
        logger.info(f"Collection completed in {duration:.2f} seconds")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SoleID API Integration')
    parser.add_argument('--sneaker-api-limit', type=int, default=100,
                       help='Limit for SneakerAPI collection')
    parser.add_argument('--sneaks-api-limit', type=int, default=50,
                       help='Limit for SneaksAPI collection')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode with smaller limits')
    
    args = parser.parse_args()
    
    if args.test:
        args.sneaker_api_limit = 10
        args.sneaks_api_limit = 10
        print("Running in TEST mode with reduced limits")
    
    builder = ComprehensiveAPIBuilder()
    builder.run_comprehensive_collection(
        sneaker_api_limit=args.sneaker_api_limit,
        sneaks_api_limit=args.sneaks_api_limit
    )

if __name__ == "__main__":
    main()