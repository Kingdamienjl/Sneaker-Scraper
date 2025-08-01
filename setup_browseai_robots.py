#!/usr/bin/env python3
"""
BrowseAI Robot Setup Helper
Provides guidance and templates for setting up BrowseAI robots
"""

import json
import os
from datetime import datetime

class BrowseAIRobotSetup:
    def __init__(self):
        self.robots_config = {
            "nike_product_scraper": {
                "name": "Nike Product Scraper",
                "description": "Scrapes Nike product pages for sneaker images and details",
                "target_sites": ["nike.com"],
                "data_fields": [
                    {"name": "product_name", "selector": "h1[data-automation-id='product-title']"},
                    {"name": "price", "selector": ".product-price"},
                    {"name": "images", "selector": "img[data-sub-type='product']", "attribute": "src", "multiple": True},
                    {"name": "description", "selector": ".product-description"},
                    {"name": "sku", "selector": "[data-automation-id='product-sku']"},
                    {"name": "colorway", "selector": ".product-subtitle"},
                    {"name": "availability", "selector": ".product-availability"}
                ],
                "example_urls": [
                    "https://www.nike.com/t/air-jordan-1-retro-high-og-shoes-Mh1J2e",
                    "https://www.nike.com/t/air-force-1-07-shoes-WrLlWX"
                ]
            },
            "stockx_product_scraper": {
                "name": "StockX Product Scraper", 
                "description": "Scrapes StockX product pages for sneaker market data",
                "target_sites": ["stockx.com"],
                "data_fields": [
                    {"name": "product_name", "selector": "h1[data-testid='product-name']"},
                    {"name": "current_price", "selector": "[data-testid='current-price']"},
                    {"name": "images", "selector": "img[data-testid='product-media']", "attribute": "src", "multiple": True},
                    {"name": "last_sale", "selector": "[data-testid='last-sale-price']"},
                    {"name": "price_change", "selector": "[data-testid='price-change']"},
                    {"name": "market_cap", "selector": "[data-testid='market-cap']"},
                    {"name": "trade_range", "selector": "[data-testid='trade-range']"}
                ],
                "example_urls": [
                    "https://stockx.com/air-jordan-1-retro-high-og-chicago-2015",
                    "https://stockx.com/nike-dunk-low-panda"
                ]
            },
            "goat_product_scraper": {
                "name": "GOAT Product Scraper",
                "description": "Scrapes GOAT product pages for sneaker marketplace data", 
                "target_sites": ["goat.com"],
                "data_fields": [
                    {"name": "product_name", "selector": "h1[class*='ProductDetailsHeader']"},
                    {"name": "lowest_price", "selector": "[data-qa='lowest-price']"},
                    {"name": "images", "selector": "img[class*='ProductImage']", "attribute": "src", "multiple": True},
                    {"name": "brand", "selector": "[data-qa='brand-name']"},
                    {"name": "retail_price", "selector": "[data-qa='retail-price']"},
                    {"name": "release_date", "selector": "[data-qa='release-date']"},
                    {"name": "condition_guide", "selector": "[data-qa='condition-guide']"}
                ],
                "example_urls": [
                    "https://www.goat.com/sneakers/air-jordan-1-retro-high-og-chicago-555088-101",
                    "https://www.goat.com/sneakers/nike-dunk-low-white-black-dd1391-100"
                ]
            }
        }
        
    def generate_robot_instructions(self):
        """Generate detailed setup instructions for each robot"""
        instructions = {
            "setup_steps": [
                "1. Go to https://browse.ai and create an account",
                "2. Click 'Create Robot' and select 'Extract structured data'",
                "3. Enter the target URL from the examples below",
                "4. Use the visual selector to identify data fields",
                "5. Configure the robot settings (frequency, pagination, etc.)",
                "6. Test the robot with sample URLs",
                "7. Schedule the robot or use API integration"
            ],
            "robots": {}
        }
        
        for robot_id, config in self.robots_config.items():
            instructions["robots"][robot_id] = {
                "name": config["name"],
                "description": config["description"],
                "setup_guide": {
                    "target_sites": config["target_sites"],
                    "data_fields_to_extract": config["data_fields"],
                    "example_urls": config["example_urls"],
                    "recommended_settings": {
                        "run_frequency": "Daily",
                        "max_pages": 1,
                        "wait_time": "2 seconds",
                        "retry_attempts": 3,
                        "output_format": "JSON"
                    }
                }
            }
        
        return instructions
    
    def generate_api_integration_code(self):
        """Generate Python code for BrowseAI API integration"""
        code = '''
import requests
import json
import time
from datetime import datetime

class BrowseAIIntegration:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.browse.ai/v2"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def run_robot(self, robot_id, input_parameters=None):
        """Run a BrowseAI robot"""
        url = f"{self.base_url}/robots/{robot_id}/tasks"
        
        payload = {}
        if input_parameters:
            payload["inputParameters"] = input_parameters
            
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error running robot: {response.status_code} - {response.text}")
            return None
    
    def get_task_result(self, robot_id, task_id):
        """Get results from a completed task"""
        url = f"{self.base_url}/robots/{robot_id}/tasks/{task_id}"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting task result: {response.status_code} - {response.text}")
            return None
    
    def wait_for_task_completion(self, robot_id, task_id, max_wait=300):
        """Wait for a task to complete"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            result = self.get_task_result(robot_id, task_id)
            
            if result and result.get("result", {}).get("status") == "successful":
                return result
            elif result and result.get("result", {}).get("status") == "failed":
                print(f"Task failed: {result}")
                return None
            
            time.sleep(10)  # Wait 10 seconds before checking again
        
        print("Task timed out")
        return None
    
    def scrape_sneaker_data(self, robot_id, product_urls):
        """Scrape sneaker data from multiple URLs"""
        results = []
        
        for url in product_urls:
            print(f"Scraping: {url}")
            
            # Run robot with URL
            task = self.run_robot(robot_id, {"url": url})
            
            if task and "result" in task:
                task_id = task["result"]["id"]
                
                # Wait for completion
                result = self.wait_for_task_completion(robot_id, task_id)
                
                if result:
                    extracted_data = result.get("result", {}).get("extractedData", [])
                    if extracted_data:
                        results.append({
                            "url": url,
                            "data": extracted_data[0],  # First row of data
                            "timestamp": datetime.now().isoformat()
                        })
            
            time.sleep(2)  # Rate limiting
        
        return results

# Example usage:
if __name__ == "__main__":
    # Initialize with your BrowseAI API key
    api_key = os.getenv('BROWSEAI_API_KEY', 'your_browseai_api_key_here')
    browse_ai = BrowseAIIntegration(api_key)
    
    # Example robot IDs (replace with your actual robot IDs)
    nike_robot_id = "your_nike_robot_id"
    stockx_robot_id = "your_stockx_robot_id"
    
    # Example URLs to scrape
    nike_urls = [
        "https://www.nike.com/t/air-jordan-1-retro-high-og-shoes-Mh1J2e",
        "https://www.nike.com/t/air-force-1-07-shoes-WrLlWX"
    ]
    
    # Scrape Nike data
    nike_results = browse_ai.scrape_sneaker_data(nike_robot_id, nike_urls)
    
    # Save results
    with open("browseai_nike_results.json", "w") as f:
        json.dump(nike_results, f, indent=2)
    
    print(f"Scraped {len(nike_results)} Nike products")
'''
        return code
    
    def save_setup_files(self):
        """Save all setup files and instructions"""
        # Create BrowseAI directory
        browseai_dir = "browseai_setup"
        os.makedirs(browseai_dir, exist_ok=True)
        
        # Save robot instructions
        instructions = self.generate_robot_instructions()
        with open(os.path.join(browseai_dir, "robot_setup_instructions.json"), "w") as f:
            json.dump(instructions, f, indent=2)
        
        # Save API integration code
        api_code = self.generate_api_integration_code()
        with open(os.path.join(browseai_dir, "browseai_integration.py"), "w") as f:
            f.write(api_code)
        
        # Save robot configurations
        with open(os.path.join(browseai_dir, "robot_configurations.json"), "w") as f:
            json.dump(self.robots_config, f, indent=2)
        
        # Create README
        readme_content = self.generate_readme()
        with open(os.path.join(browseai_dir, "README.md"), "w") as f:
            f.write(readme_content)
        
        print(f"BrowseAI setup files saved to {browseai_dir}/")
        return browseai_dir
    
    def generate_readme(self):
        """Generate README for BrowseAI setup"""
        return '''# BrowseAI Robot Setup for Sneaker Scraping

This directory contains everything you need to set up BrowseAI robots for scraping sneaker data.

## Files Included

- `robot_setup_instructions.json` - Detailed setup instructions for each robot
- `robot_configurations.json` - Robot configuration templates
- `browseai_integration.py` - Python code for API integration
- `README.md` - This file

## Quick Start

1. **Create BrowseAI Account**
   - Go to https://browse.ai
   - Sign up for an account
   - Get your API key from the dashboard

2. **Set Up Robots**
   - Follow the instructions in `robot_setup_instructions.json`
   - Create robots for Nike, StockX, and GOAT
   - Test each robot with the provided example URLs

3. **API Integration**
   - Use the code in `browseai_integration.py`
   - Replace `your_browseai_api_key_here` with your actual API key
   - Replace robot IDs with your actual robot IDs

## Robot Types

### Nike Product Scraper
- Extracts product details from Nike.com
- Gets images, prices, descriptions, SKUs
- Best for official product data

### StockX Product Scraper  
- Extracts market data from StockX.com
- Gets current prices, last sales, market trends
- Best for resale market data

### GOAT Product Scraper
- Extracts marketplace data from GOAT.com
- Gets prices, conditions, authenticity info
- Best for authenticated sneaker data

## Cost Estimation

- BrowseAI: $49/month for 50 robots + API access
- Each robot can run multiple times per day
- Estimated cost per sneaker: $0.02-0.05

## Next Steps

1. Set up the robots following the instructions
2. Test with sample URLs
3. Integrate with your existing scraper
4. Schedule regular data collection
5. Monitor and optimize robot performance

## Support

- BrowseAI Documentation: https://docs.browse.ai
- BrowseAI Support: support@browse.ai
'''
    
    def print_summary(self):
        """Print setup summary"""
        print("\n" + "="*60)
        print("BrowseAI Robot Setup Summary")
        print("="*60)
        
        print(f"\nRobots to create: {len(self.robots_config)}")
        for robot_id, config in self.robots_config.items():
            print(f"  • {config['name']}")
            print(f"    Target: {', '.join(config['target_sites'])}")
            print(f"    Fields: {len(config['data_fields'])} data points")
        
        print(f"\nEstimated setup time: 2-3 hours")
        print(f"Monthly cost: $49 (50 robots + API access)")
        print(f"Expected data quality: High (visual scraping)")
        
        print(f"\nBenefits:")
        print(f"  • No code required for robot setup")
        print(f"  • Handles JavaScript and dynamic content")
        print(f"  • Built-in scheduling and monitoring")
        print(f"  • API integration available")
        print(f"  • Reliable data extraction")

def main():
    """Main function"""
    setup = BrowseAIRobotSetup()
    
    # Save all setup files
    setup_dir = setup.save_setup_files()
    
    # Print summary
    setup.print_summary()
    
    print(f"\n✅ BrowseAI setup files created in: {setup_dir}")
    print(f"📖 Check the README.md file for detailed instructions")
    print(f"🚀 Ready to set up your BrowseAI robots!")

if __name__ == "__main__":
    main()