import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import json
import re

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    @abstractmethod
    def scrape_sneaker_data(self, search_term: str) -> List[Dict]:
        pass
    
    def setup_selenium_driver(self):
        """Setup Selenium WebDriver with Chrome options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        return webdriver.Chrome(options=chrome_options)
    
    def download_image(self, image_url: str, file_path: str) -> bool:
        """Download image from URL"""
        try:
            response = self.session.get(image_url, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded image: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {str(e)}")
            return False

class StockXScraper(BaseScraper):
    def __init__(self, delay: float = 1.0):
        super().__init__(delay)
        self.base_url = "https://stockx.com"
    
    def scrape_sneaker_data(self, search_term: str) -> List[Dict]:
        """Scrape sneaker data from StockX"""
        sneakers = []
        
        try:
            driver = self.setup_selenium_driver()
            search_url = f"{self.base_url}/search?s={search_term.replace(' ', '%20')}"
            driver.get(search_url)
            
            # Wait for products to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='ProductTile']"))
            )
            
            products = driver.find_elements(By.CSS_SELECTOR, "[data-testid='ProductTile']")
            
            for product in products[:20]:  # Limit to first 20 results
                try:
                    # Extract basic info
                    name_element = product.find_element(By.CSS_SELECTOR, "[data-testid='ProductTile-name']")
                    name = name_element.text
                    
                    price_element = product.find_element(By.CSS_SELECTOR, "[data-testid='ProductTile-price']")
                    price_text = price_element.text
                    current_price = self._extract_price(price_text)
                    
                    # Get product link
                    link_element = product.find_element(By.TAG_NAME, "a")
                    product_url = link_element.get_attribute("href")
                    
                    # Get image
                    img_element = product.find_element(By.TAG_NAME, "img")
                    image_url = img_element.get_attribute("src")
                    
                    sneaker_data = {
                        'name': name,
                        'brand': self._extract_brand(name),
                        'current_price': current_price,
                        'platform': 'StockX',
                        'product_url': product_url,
                        'image_url': image_url,
                        'scraped_at': time.time()
                    }
                    
                    # Get detailed info from product page
                    detailed_data = self._scrape_product_details(product_url, driver)
                    sneaker_data.update(detailed_data)
                    
                    sneakers.append(sneaker_data)
                    time.sleep(self.delay)
                
                except Exception as e:
                    logger.error(f"Error scraping product: {str(e)}")
                    continue
            
            driver.quit()
            
        except Exception as e:
            logger.error(f"Error scraping StockX: {str(e)}")
        
        return sneakers
    
    def _scrape_product_details(self, product_url: str, driver) -> Dict:
        """Scrape detailed product information"""
        details = {}
        
        try:
            driver.get(product_url)
            time.sleep(2)
            
            # Get retail price
            try:
                retail_element = driver.find_element(By.XPATH, "//dt[text()='Retail Price']/following-sibling::dd")
                details['retail_price'] = self._extract_price(retail_element.text)
            except:
                details['retail_price'] = None
            
            # Get release date
            try:
                release_element = driver.find_element(By.XPATH, "//dt[text()='Release Date']/following-sibling::dd")
                details['release_date'] = release_element.text
            except:
                details['release_date'] = None
            
            # Get SKU
            try:
                sku_element = driver.find_element(By.XPATH, "//dt[text()='Style']/following-sibling::dd")
                details['sku'] = sku_element.text
            except:
                details['sku'] = None
            
            # Get additional images
            try:
                image_elements = driver.find_elements(By.CSS_SELECTOR, "img[data-testid='product-detail-image']")
                details['additional_images'] = [img.get_attribute("src") for img in image_elements]
            except:
                details['additional_images'] = []
        
        except Exception as e:
            logger.error(f"Error scraping product details: {str(e)}")
        
        return details
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        try:
            price_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', price_text)
            if price_match:
                return float(price_match.group(1).replace(',', ''))
        except:
            pass
        return None
    
    def _extract_brand(self, name: str) -> str:
        """Extract brand from sneaker name"""
        brands = ['Nike', 'Adidas', 'Jordan', 'Yeezy', 'New Balance', 'Puma', 'Reebok', 'Vans', 'Converse']
        name_lower = name.lower()
        
        for brand in brands:
            if brand.lower() in name_lower:
                return brand
        
        return 'Unknown'

class GOATScraper(BaseScraper):
    def __init__(self, delay: float = 1.0):
        super().__init__(delay)
        self.base_url = "https://www.goat.com"
    
    def scrape_sneaker_data(self, search_term: str) -> List[Dict]:
        """Scrape sneaker data from GOAT"""
        # Similar implementation to StockX but adapted for GOAT's structure
        # This would need to be implemented based on GOAT's current HTML structure
        logger.info(f"Scraping GOAT for: {search_term}")
        return []

class EbayScraper(BaseScraper):
    def __init__(self, delay: float = 1.0):
        super().__init__(delay)
        self.base_url = "https://www.ebay.com"
    
    def scrape_sneaker_data(self, search_term: str) -> List[Dict]:
        """Scrape sneaker data from eBay"""
        sneakers = []
        
        try:
            search_url = f"{self.base_url}/sch/i.html?_nkw={search_term.replace(' ', '+')}&_sacat=15709"
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            items = soup.find_all('div', class_='s-item__wrapper')
            
            for item in items[:20]:  # Limit to first 20 results
                try:
                    title_element = item.find('h3', class_='s-item__title')
                    if not title_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    
                    price_element = item.find('span', class_='s-item__price')
                    price = self._extract_price(price_element.get_text(strip=True)) if price_element else None
                    
                    link_element = item.find('a', class_='s-item__link')
                    product_url = link_element.get('href') if link_element else None
                    
                    img_element = item.find('img', class_='s-item__image')
                    image_url = img_element.get('src') if img_element else None
                    
                    sneaker_data = {
                        'name': title,
                        'brand': self._extract_brand(title),
                        'current_price': price,
                        'platform': 'eBay',
                        'product_url': product_url,
                        'image_url': image_url,
                        'scraped_at': time.time()
                    }
                    
                    sneakers.append(sneaker_data)
                    time.sleep(self.delay)
                
                except Exception as e:
                    logger.error(f"Error scraping eBay item: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scraping eBay: {str(e)}")
        
        return sneakers
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        try:
            price_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', price_text)
            if price_match:
                return float(price_match.group(1).replace(',', ''))
        except:
            pass
        return None
    
    def _extract_brand(self, name: str) -> str:
        """Extract brand from sneaker name"""
        brands = ['Nike', 'Adidas', 'Jordan', 'Yeezy', 'New Balance', 'Puma', 'Reebok', 'Vans', 'Converse']
        name_lower = name.lower()
        
        for brand in brands:
            if brand.lower() in name_lower:
                return brand
        
        return 'Unknown'