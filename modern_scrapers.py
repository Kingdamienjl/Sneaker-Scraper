#!/usr/bin/env python3
"""
Updated SoleID Scrapers with Current Website Selectors and Alternative Data Sources
"""

import requests
import time
import random
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ModernStockXScraper:
    """Updated StockX scraper with current selectors"""
    
    def __init__(self):
        self.base_url = "https://stockx.com"
        self.search_url = "https://stockx.com/search"
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver with modern options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {str(e)}")
            return False
    
    def search_sneakers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for sneakers on StockX"""
        if not self.setup_driver():
            return []
        
        results = []
        try:
            # Navigate to search page
            search_url = f"{self.search_url}?s={query.replace(' ', '%20')}"
            self.driver.get(search_url)
            
            # Wait for results to load
            time.sleep(3)
            
            # Try multiple selectors for product tiles
            selectors = [
                "[data-testid='search-results'] [data-testid='browse-tile']",
                ".browse-tile",
                "[data-automation-id='product-tile']",
                ".tile",
                ".search-tile"
            ]
            
            products = []
            for selector in selectors:
                try:
                    products = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if products:
                        logger.info(f"Found {len(products)} products using selector: {selector}")
                        break
                except:
                    continue
            
            if not products:
                logger.warning(f"No products found for query: {query}")
                return results
            
            # Extract data from each product
            for i, product in enumerate(products[:max_results]):
                try:
                    sneaker_data = self.extract_product_data(product)
                    if sneaker_data:
                        results.append(sneaker_data)
                except Exception as e:
                    logger.error(f"Error extracting product {i}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error searching StockX: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
        
        return results
    
    def extract_product_data(self, product_element) -> Optional[Dict]:
        """Extract data from a product element"""
        try:
            # Try multiple selectors for different elements
            name_selectors = [
                "[data-testid='product-tile-name']",
                ".tile-name",
                ".product-name",
                "h3",
                ".name"
            ]
            
            price_selectors = [
                "[data-testid='product-tile-price']",
                ".tile-price",
                ".price",
                ".lowest-ask"
            ]
            
            image_selectors = [
                "img[data-testid='product-tile-image']",
                ".tile-image img",
                ".product-image img",
                "img"
            ]
            
            link_selectors = [
                "a[data-testid='product-tile-link']",
                "a",
                ".tile-link"
            ]
            
            # Extract name
            name = None
            for selector in name_selectors:
                try:
                    element = product_element.find_element(By.CSS_SELECTOR, selector)
                    name = element.text.strip()
                    if name:
                        break
                except:
                    continue
            
            # Extract price
            price = None
            for selector in price_selectors:
                try:
                    element = product_element.find_element(By.CSS_SELECTOR, selector)
                    price_text = element.text.strip()
                    # Extract numeric price
                    import re
                    price_match = re.search(r'\$(\d+(?:,\d+)?)', price_text)
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
                        break
                except:
                    continue
            
            # Extract image URL
            image_url = None
            for selector in image_selectors:
                try:
                    element = product_element.find_element(By.CSS_SELECTOR, selector)
                    image_url = element.get_attribute('src') or element.get_attribute('data-src')
                    if image_url:
                        break
                except:
                    continue
            
            # Extract product link
            product_url = None
            for selector in link_selectors:
                try:
                    element = product_element.find_element(By.CSS_SELECTOR, selector)
                    href = element.get_attribute('href')
                    if href and '/sneakers/' in href:
                        product_url = href if href.startswith('http') else f"{self.base_url}{href}"
                        break
                except:
                    continue
            
            if name and price:
                return {
                    'name': name,
                    'price': price,
                    'image_url': image_url,
                    'product_url': product_url,
                    'platform': 'StockX',
                    'scraped_at': datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error extracting product data: {str(e)}")
        
        return None

class SneaksAPIScraper:
    """Alternative data source using SneaksAPI (free sneaker API)"""
    
    def __init__(self):
        self.base_url = "https://sneaksapi.vercel.app"
        
    def search_sneakers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search sneakers using SneaksAPI"""
        results = []
        
        try:
            # Search endpoint
            search_url = f"{self.base_url}/search/{query.replace(' ', '%20')}"
            
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                for item in data[:max_results]:
                    sneaker_data = {
                        'name': item.get('shoeName', ''),
                        'brand': item.get('brand', ''),
                        'price': self.parse_price(item.get('lowestResellPrice', {}).get('stockX')),
                        'retail_price': self.parse_price(item.get('retailPrice')),
                        'image_url': item.get('thumbnail', ''),
                        'product_url': item.get('links', {}).get('stockX', ''),
                        'sku': item.get('styleID', ''),
                        'release_date': item.get('releaseDate', ''),
                        'platform': 'SneaksAPI',
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    if sneaker_data['name']:
                        results.append(sneaker_data)
            
        except Exception as e:
            logger.error(f"Error with SneaksAPI: {str(e)}")
        
        return results
    
    def parse_price(self, price_str) -> Optional[float]:
        """Parse price string to float"""
        if not price_str:
            return None
        
        try:
            # Remove currency symbols and parse
            import re
            price_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)', str(price_str))
            if price_match:
                return float(price_match.group(1).replace(',', ''))
        except:
            pass
        
        return None

class StaticDataScraper:
    """Fallback scraper with curated sneaker data"""
    
    def __init__(self):
        self.popular_sneakers = [
            {
                'name': 'Air Jordan 1 Retro High OG "Bred"',
                'brand': 'Nike',
                'model': 'Air Jordan 1',
                'colorway': 'Bred',
                'sku': '555088-061',
                'retail_price': 170.0,
                'price': 450.0,
                'image_url': 'https://images.stockx.com/images/Air-Jordan-1-Retro-High-OG-Bred-2016.jpg',
                'release_date': '2016-09-03',
                'platform': 'Static Data'
            },
            {
                'name': 'Nike Dunk Low "Panda"',
                'brand': 'Nike',
                'model': 'Dunk Low',
                'colorway': 'White Black',
                'sku': 'DD1391-100',
                'retail_price': 100.0,
                'price': 150.0,
                'image_url': 'https://images.stockx.com/images/Nike-Dunk-Low-White-Black-2021.jpg',
                'release_date': '2021-03-10',
                'platform': 'Static Data'
            },
            {
                'name': 'Adidas Yeezy Boost 350 V2 "Zebra"',
                'brand': 'Adidas',
                'model': 'Yeezy Boost 350 V2',
                'colorway': 'Zebra',
                'sku': 'CP9654',
                'retail_price': 220.0,
                'price': 300.0,
                'image_url': 'https://images.stockx.com/images/Adidas-Yeezy-Boost-350-V2-Zebra.jpg',
                'release_date': '2017-02-25',
                'platform': 'Static Data'
            },
            {
                'name': 'Air Jordan 4 Retro "Black Cat"',
                'brand': 'Nike',
                'model': 'Air Jordan 4',
                'colorway': 'Black Cat',
                'sku': 'CU1110-010',
                'retail_price': 200.0,
                'price': 350.0,
                'image_url': 'https://images.stockx.com/images/Air-Jordan-4-Retro-Black-Cat-2020.jpg',
                'release_date': '2020-01-25',
                'platform': 'Static Data'
            },
            {
                'name': 'Nike Air Force 1 Low "White"',
                'brand': 'Nike',
                'model': 'Air Force 1 Low',
                'colorway': 'White',
                'sku': '315122-111',
                'retail_price': 90.0,
                'price': 120.0,
                'image_url': 'https://images.stockx.com/images/Nike-Air-Force-1-Low-White-07.jpg',
                'release_date': '1982-01-01',
                'platform': 'Static Data'
            }
        ]
    
    def search_sneakers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Return curated sneaker data matching query"""
        results = []
        query_lower = query.lower()
        
        for sneaker in self.popular_sneakers:
            # Simple matching logic
            if (query_lower in sneaker['name'].lower() or 
                query_lower in sneaker['brand'].lower() or
                query_lower in sneaker['model'].lower()):
                
                sneaker_copy = sneaker.copy()
                sneaker_copy['scraped_at'] = datetime.now().isoformat()
                results.append(sneaker_copy)
                
                if len(results) >= max_results:
                    break
        
        return results

class MultiSourceScraper:
    """Combines multiple scraping sources for better results"""
    
    def __init__(self):
        self.scrapers = [
            SneaksAPIScraper(),
            StaticDataScraper(),
            # ModernStockXScraper()  # Enable when needed
        ]
    
    def search_sneakers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search across multiple sources"""
        all_results = []
        
        for scraper in self.scrapers:
            try:
                logger.info(f"Searching with {scraper.__class__.__name__}")
                results = scraper.search_sneakers(query, max_results)
                
                if results:
                    logger.info(f"Found {len(results)} results from {scraper.__class__.__name__}")
                    all_results.extend(results)
                else:
                    logger.warning(f"No results from {scraper.__class__.__name__}")
                
                # Add delay between scrapers
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error with {scraper.__class__.__name__}: {str(e)}")
                continue
        
        # Remove duplicates and limit results
        unique_results = self.deduplicate_results(all_results)
        return unique_results[:max_results]
    
    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate sneakers based on name similarity"""
        unique_results = []
        seen_names = set()
        
        for result in results:
            name_key = result.get('name', '').lower().strip()
            if name_key and name_key not in seen_names:
                seen_names.add(name_key)
                unique_results.append(result)
        
        return unique_results

def test_scrapers():
    """Test all scraping sources"""
    print("🧪 Testing Modern Scrapers")
    print("=" * 40)
    
    scraper = MultiSourceScraper()
    test_queries = ["Air Jordan 1", "Nike Dunk", "Yeezy"]
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        results = scraper.search_sneakers(query, max_results=5)
        
        if results:
            print(f"✅ Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.get('name', 'Unknown')} - ${result.get('price', 'N/A')} ({result.get('platform', 'Unknown')})")
        else:
            print("❌ No results found")

if __name__ == "__main__":
    test_scrapers()