#!/usr/bin/env python3
"""
Sneaks API Integration for SoleID
Integrates the free Sneaks API (Node.js) with our Python system
"""

import os
import sqlite3
import requests
import json
import subprocess
import time
import logging
from datetime import datetime
import hashlib
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sneaks_api_integration.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class SneaksAPIIntegration:
    def __init__(self):
        self.db_path = "sneakers.db"
        self.image_dir = "data/sneaks_images"
        os.makedirs(self.image_dir, exist_ok=True)
        
        # Node.js service configuration
        self.node_service_port = 3001
        self.node_service_url = f"http://localhost:{self.node_service_port}"
        
        # Statistics
        self.stats = {
            'products_fetched': 0,
            'images_downloaded': 0,
            'prices_updated': 0,
            'errors': []
        }
        
        # Initialize database schema
        self.init_database()
        
        # Setup Node.js service
        self.setup_node_service()
    
    def init_database(self):
        """Initialize database schema for Sneaks API data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create price_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sneaker_id INTEGER NOT NULL,
                marketplace TEXT NOT NULL,
                size TEXT,
                price REAL,
                currency TEXT DEFAULT 'USD',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sneaker_id) REFERENCES sneakers (id)
            )
        """)
        
        # Create marketplace_links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sneaker_id INTEGER NOT NULL,
                marketplace TEXT NOT NULL,
                url TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sneaker_id) REFERENCES sneakers (id)
            )
        """)
        
        # Add columns to sneakers table if they don't exist
        try:
            cursor.execute("ALTER TABLE sneakers ADD COLUMN style_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE sneakers ADD COLUMN retail_price REAL")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE sneakers ADD COLUMN release_date TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()
    
    def setup_node_service(self):
        """Setup Node.js service for Sneaks API"""
        # Check if Node.js is installed
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                logging.error("Node.js is not installed. Please install Node.js first.")
                return False
            logging.info(f"Node.js version: {result.stdout.strip()}")
        except FileNotFoundError:
            logging.error("Node.js is not found. Please install Node.js first.")
            return False
        
        # Create Node.js service file
        node_service_code = '''
const express = require('express');
const SneaksAPI = require('sneaks-api');
const app = express();
const sneaks = new SneaksAPI();

app.use(express.json());

// Search products endpoint
app.get('/search/:keyword', (req, res) => {
    const keyword = req.params.keyword;
    const limit = req.query.limit || 10;
    
    sneaks.getProducts(keyword, parseInt(limit), function(err, products) {
        if (err) {
            res.status(500).json({ error: err.message });
        } else {
            res.json({ products: products || [] });
        }
    });
});

// Get product details by style ID
app.get('/product/:styleId', (req, res) => {
    const styleId = req.params.styleId;
    
    sneaks.getProductPrices(styleId, function(err, product) {
        if (err) {
            res.status(500).json({ error: err.message });
        } else {
            res.json({ product: product || {} });
        }
    });
});

// Get most popular products
app.get('/popular/:limit?', (req, res) => {
    const limit = req.params.limit || 10;
    
    sneaks.getMostPopular(parseInt(limit), function(err, products) {
        if (err) {
            res.status(500).json({ error: err.message });
        } else {
            res.json({ products: products || [] });
        }
    });
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
    console.log(`Sneaks API service running on port ${PORT}`);
});
'''
        
        # Write Node.js service file
        with open('sneaks_service.js', 'w') as f:
            f.write(node_service_code)
        
        # Install dependencies if package.json doesn't exist
        if not os.path.exists('package.json'):
            logging.info("Installing Sneaks API dependencies...")
            try:
                subprocess.run(['npm', 'init', '-y'], check=True)
                subprocess.run(['npm', 'install', 'sneaks-api', 'express'], check=True)
                logging.info("Dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to install dependencies: {e}")
                return False
        
        return True
    
    def start_node_service(self):
        """Start the Node.js service"""
        try:
            # Check if service is already running
            response = requests.get(f"{self.node_service_url}/health", timeout=2)
            if response.status_code == 200:
                logging.info("Node.js service is already running")
                return True
        except requests.exceptions.RequestException:
            pass
        
        # Start the service
        logging.info("Starting Node.js Sneaks API service...")
        try:
            self.node_process = subprocess.Popen(
                ['node', 'sneaks_service.js'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for service to start
            time.sleep(3)
            
            # Test if service is running
            response = requests.get(f"{self.node_service_url}/health", timeout=5)
            if response.status_code == 200:
                logging.info("Node.js service started successfully")
                return True
            else:
                logging.error("Node.js service failed to start properly")
                return False
                
        except Exception as e:
            logging.error(f"Failed to start Node.js service: {e}")
            return False
    
    def search_products(self, keyword, limit=10):
        """Search for products using Sneaks API"""
        try:
            response = requests.get(
                f"{self.node_service_url}/search/{keyword}",
                params={'limit': limit},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                self.stats['products_fetched'] += len(products)
                return products
            else:
                logging.error(f"Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logging.error(f"Search error: {e}")
            self.stats['errors'].append(f"Search error for '{keyword}': {e}")
            return []
    
    def get_product_details(self, style_id):
        """Get detailed product information including prices"""
        try:
            response = requests.get(
                f"{self.node_service_url}/product/{style_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('product', {})
            else:
                logging.error(f"Product details failed: {response.status_code}")
                return {}
                
        except Exception as e:
            logging.error(f"Product details error: {e}")
            self.stats['errors'].append(f"Product details error for '{style_id}': {e}")
            return {}
    
    def get_popular_products(self, limit=10):
        """Get most popular products"""
        try:
            response = requests.get(
                f"{self.node_service_url}/popular/{limit}",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                self.stats['products_fetched'] += len(products)
                return products
            else:
                logging.error(f"Popular products failed: {response.status_code}")
                return []
                
        except Exception as e:
            logging.error(f"Popular products error: {e}")
            self.stats['errors'].append(f"Popular products error: {e}")
            return []
    
    def download_image(self, url, filename):
        """Download and save an image"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, timeout=15, stream=True, headers=headers)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                return False
            
            # Save file
            filepath = os.path.join(self.image_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file size
            if os.path.exists(filepath) and os.path.getsize(filepath) > 5000:
                self.stats['images_downloaded'] += 1
                return filepath
            else:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return False
                
        except Exception as e:
            logging.error(f"Error downloading {url}: {e}")
            return False
    
    def save_product_to_database(self, product_data):
        """Save product data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract product information
            name = product_data.get('shoeName', '')
            brand = product_data.get('brand', '')
            colorway = product_data.get('colorway', '')
            style_id = product_data.get('styleID', '')
            retail_price = product_data.get('retailPrice', 0)
            release_date = product_data.get('releaseDate', '')
            
            # Check if product already exists
            cursor.execute("""
                SELECT id FROM sneakers 
                WHERE style_id = ? OR (brand = ? AND model = ? AND colorway = ?)
            """, (style_id, brand, name, colorway))
            
            existing = cursor.fetchone()
            
            if existing:
                sneaker_id = existing[0]
                # Update existing record
                cursor.execute("""
                    UPDATE sneakers 
                    SET style_id = ?, retail_price = ?, release_date = ?
                    WHERE id = ?
                """, (style_id, retail_price, release_date, sneaker_id))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO sneakers (brand, model, colorway, style_id, retail_price, release_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (brand, name, colorway, style_id, retail_price, release_date))
                sneaker_id = cursor.lastrowid
            
            # Save marketplace links
            links = product_data.get('links', {})
            for marketplace, url in links.items():
                if url:
                    cursor.execute("""
                        INSERT OR REPLACE INTO marketplace_links 
                        (sneaker_id, marketplace, url, last_updated)
                        VALUES (?, ?, ?, datetime('now'))
                    """, (sneaker_id, marketplace, url))
            
            # Save price data
            price_map = product_data.get('priceMap', {})
            for marketplace, sizes in price_map.items():
                if isinstance(sizes, dict):
                    for size, price in sizes.items():
                        if price and price > 0:
                            cursor.execute("""
                                INSERT INTO price_history 
                                (sneaker_id, marketplace, size, price, recorded_at)
                                VALUES (?, ?, ?, ?, datetime('now'))
                            """, (sneaker_id, marketplace, size, price))
                            self.stats['prices_updated'] += 1
            
            # Download and save images
            images = product_data.get('imageLinks', [])
            for i, img_url in enumerate(images[:5]):  # Limit to 5 images
                if img_url:
                    url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                    filename = f"{sneaker_id}_{url_hash}_{i+1}.jpg"
                    
                    local_path = self.download_image(img_url, filename)
                    if local_path:
                        # Save to images table
                        cursor.execute("""
                            INSERT OR IGNORE INTO images 
                            (sneaker_id, url, local_path, created_at)
                            VALUES (?, ?, ?, datetime('now'))
                        """, (sneaker_id, img_url, local_path))
            
            conn.commit()
            conn.close()
            return sneaker_id
            
        except Exception as e:
            logging.error(f"Error saving product to database: {e}")
            return None
    
    def collect_popular_sneakers(self, limit=20):
        """Collect popular sneakers data"""
        logging.info(f"Collecting {limit} popular sneakers...")
        
        if not self.start_node_service():
            logging.error("Failed to start Node.js service")
            return
        
        products = self.get_popular_products(limit)
        
        for product in products:
            # Get detailed information
            style_id = product.get('styleID')
            if style_id:
                detailed_product = self.get_product_details(style_id)
                if detailed_product:
                    product.update(detailed_product)
            
            # Save to database
            sneaker_id = self.save_product_to_database(product)
            if sneaker_id:
                logging.info(f"Saved: {product.get('shoeName', 'Unknown')} (ID: {sneaker_id})")
            
            time.sleep(1)  # Rate limiting
    
    def search_and_collect(self, keywords, limit_per_keyword=10):
        """Search for specific keywords and collect data"""
        logging.info(f"Searching for keywords: {keywords}")
        
        if not self.start_node_service():
            logging.error("Failed to start Node.js service")
            return
        
        for keyword in keywords:
            logging.info(f"Searching for: {keyword}")
            products = self.search_products(keyword, limit_per_keyword)
            
            for product in products:
                # Get detailed information
                style_id = product.get('styleID')
                if style_id:
                    detailed_product = self.get_product_details(style_id)
                    if detailed_product:
                        product.update(detailed_product)
                
                # Save to database
                sneaker_id = self.save_product_to_database(product)
                if sneaker_id:
                    logging.info(f"Saved: {product.get('shoeName', 'Unknown')} (ID: {sneaker_id})")
                
                time.sleep(1)  # Rate limiting
    
    def generate_report(self):
        """Generate collection report"""
        report = f"""
        Sneaks API Collection Report
        ============================
        Products fetched: {self.stats['products_fetched']}
        Images downloaded: {self.stats['images_downloaded']}
        Prices updated: {self.stats['prices_updated']}
        Errors: {len(self.stats['errors'])}
        
        Recent Errors:
        {chr(10).join(self.stats['errors'][-5:]) if self.stats['errors'] else 'None'}
        """
        
        logging.info(report)
        return self.stats

if __name__ == "__main__":
    # Initialize the integration
    sneaks = SneaksAPIIntegration()
    
    # Collect popular sneakers
    sneaks.collect_popular_sneakers(limit=15)
    
    # Search for specific brands
    keywords = ["Nike Air Jordan", "Yeezy", "Nike Dunk", "Adidas Ultraboost", "New Balance 550"]
    sneaks.search_and_collect(keywords, limit_per_keyword=5)
    
    # Generate report
    sneaks.generate_report()