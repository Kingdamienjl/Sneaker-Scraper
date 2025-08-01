#!/usr/bin/env python3
"""
Working Image Downloader - Downloads real sneaker images
"""

import os
import requests
import time
from google_drive import GoogleDriveManager

def download_real_images():
    """Download real sneaker images from working URLs"""
    
    # Working image URLs (these should work)
    test_images = [
        {
            'name': 'Air_Jordan_1_Bred',
            'brand': 'Nike',
            'image_url': 'https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/b7d9211c-26e7-431a-ac24-b0540fb3c00f/air-jordan-1-retro-high-og-shoes-Pq0hCP.png'
        },
        {
            'name': 'Nike_Dunk_Low_Panda',
            'brand': 'Nike',
            'image_url': 'https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/b1bcbca4-e853-4df7-b329-5be3c61ee057/dunk-low-shoes-5FQWGR.png'
        },
        {
            'name': 'Adidas_Yeezy_350',
            'brand': 'Adidas', 
            'image_url': 'https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/fbaf991a29d14d8ca87fad8d00f7e10c_9366/Yeezy_Boost_350_V2_Shoes_White_FX4348_01_standard.jpg'
        }
    ]
    
    print("🖼️ Downloading real sneaker images...")
    
    # Initialize Google Drive
    try:
        drive_manager = GoogleDriveManager()
        print("✅ Google Drive connected")
    except Exception as e:
        print(f"⚠️ Google Drive failed: {str(e)}")
        drive_manager = None
    
    downloaded_count = 0
    
    for img_data in test_images:
        try:
            print(f"\n📥 Downloading: {img_data['name']}")
            
            # Download image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(img_data['image_url'], timeout=15, headers=headers)
            
            if response.status_code == 200:
                # Save locally
                file_name = f"{img_data['name']}_{int(time.time())}.jpg"
                local_path = os.path.join("data/images", file_name)
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                print(f"   ✅ Saved locally: {file_name} ({file_size:,} bytes)")
                
                # Upload to Google Drive
                if drive_manager:
                    try:
                        drive_id = drive_manager.upload_image(
                            local_path,
                            file_name,
                            folder_name=img_data['brand']
                        )
                        if drive_id:
                            print(f"   ☁️ Uploaded to Google Drive: {drive_id}")
                        else:
                            print(f"   ⚠️ Google Drive upload returned no ID")
                    except Exception as e:
                        print(f"   ⚠️ Google Drive upload failed: {str(e)}")
                
                downloaded_count += 1
                
            else:
                print(f"   ❌ Download failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error downloading {img_data['name']}: {str(e)}")
        
        # Small delay between downloads
        time.sleep(1)
    
    print(f"\n📊 Summary: Downloaded {downloaded_count}/{len(test_images)} images")
    
    # Show local files
    try:
        local_images = os.listdir("data/images")
        if local_images:
            print(f"\n📁 Local images ({len(local_images)}):")
            for img in local_images:
                size = os.path.getsize(os.path.join("data/images", img))
                print(f"   • {img} ({size:,} bytes)")
        else:
            print(f"\n📁 No local images found")
    except Exception as e:
        print(f"\n❌ Could not list local images: {str(e)}")

if __name__ == "__main__":
    download_real_images()