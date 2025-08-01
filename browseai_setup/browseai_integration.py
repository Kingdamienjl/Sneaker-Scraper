
import os
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
