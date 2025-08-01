#!/usr/bin/env python3
"""
Restore Brand Folders and Clean Root Drive
This script will:
1. Restore the 83 brand folders inside SoleID_Images for scraping
2. Clean up empty folders at the root level of Google Drive (not inside SoleID_Images)
3. Increase scraping depth for better accuracy
"""

import os
import sys
from google_drive import GoogleDriveManager
from config import Config

def restore_brand_folders():
    """Restore the brand folders needed for scraping"""
    
    # List of popular sneaker brands for comprehensive scraping
    brands = [
        "Nike", "Adidas", "Jordan", "Puma", "Reebok", "New Balance", "Converse", 
        "Vans", "ASICS", "Under Armour", "Saucony", "Brooks", "Mizuno", "Diadora",
        "Fila", "Kappa", "Umbro", "Lotto", "Joma", "Hummel", "Salomon", "Merrell",
        "Timberland", "Dr. Martens", "Clarks", "Crocs", "Birkenstock", "UGG",
        "Balenciaga", "Gucci", "Louis Vuitton", "Prada", "Versace", "Dolce & Gabbana",
        "Saint Laurent", "Bottega Veneta", "Givenchy", "Valentino", "Burberry",
        "Off-White", "Fear of God", "Stone Island", "Common Projects", "Golden Goose",
        "Maison Margiela", "Rick Owens", "Yeezy", "Travis Scott", "Fragment Design",
        "Comme des Garcons", "A Bathing Ape", "Neighborhood", "Visvim", "Mastermind",
        "Kaws", "Supreme", "Palace", "Stussy", "Brain Dead", "Gallery Dept",
        "Rhude", "Amiri", "Chrome Hearts", "Dior", "Chanel", "Hermes", "Celine",
        "Loewe", "Acne Studios", "Ganni", "Jacquemus", "Lemaire", "The Row",
        "Bottega Veneta", "Jil Sander", "Marni", "Proenza Schouler", "3.1 Phillip Lim",
        "Alexander Wang", "Helmut Lang", "Ann Demeulemeester", "Dries Van Noten",
        "Issey Miyake", "Yohji Yamamoto", "Rei Kawakubo", "Undercover", "Sacai"
    ]
    
    print("🔄 Restoring brand folders for comprehensive scraping...")
    
    try:
        drive_manager = GoogleDriveManager()
        
        # Find SoleID_Images folder
        soleid_folder = drive_manager.find_folder_by_name("SoleID_Images")
        if not soleid_folder:
            print("❌ SoleID_Images folder not found!")
            return False
            
        print(f"📁 Found SoleID_Images folder: {soleid_folder['id']}")
        
        # Get existing folders
        existing_folders = drive_manager.service.files().list(
            q=f"'{soleid_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)"
        ).execute().get('files', [])
        
        existing_names = {folder['name'] for folder in existing_folders}
        print(f"📊 Found {len(existing_names)} existing brand folders")
        
        # Create missing brand folders
        created_count = 0
        for brand in brands:
            if brand not in existing_names:
                try:
                    folder_id = drive_manager.create_folder(brand, soleid_folder['id'])
                    if folder_id:
                        created_count += 1
                        print(f"✅ Created folder: {brand}")
                    else:
                        print(f"❌ Failed to create folder: {brand}")
                except Exception as e:
                    print(f"❌ Error creating {brand}: {str(e)}")
            else:
                print(f"📁 Folder already exists: {brand}")
        
        print(f"\n🎯 Summary:")
        print(f"   • Existing folders: {len(existing_names)}")
        print(f"   • Created folders: {created_count}")
        print(f"   • Total brand folders: {len(existing_names) + created_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error restoring brand folders: {str(e)}")
        return False

def clean_root_drive_folders():
    """Clean up empty folders at the root level of Google Drive (not inside SoleID_Images)"""
    
    print("\n🧹 Cleaning empty folders at Google Drive root level...")
    
    try:
        drive_manager = GoogleDriveManager()
        
        # Get all folders at root level (not inside any parent folder)
        root_folders = drive_manager.service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and 'root' in parents",
            fields="files(id, name)"
        ).execute().get('files', [])
        
        print(f"📁 Found {len(root_folders)} folders at root level")
        
        deleted_count = 0
        for folder in root_folders:
            # Skip the SoleID_Images folder
            if folder['name'] == 'SoleID_Images':
                print(f"🔒 Skipping SoleID_Images folder: {folder['name']}")
                continue
                
            # Check if folder is empty
            contents = drive_manager.service.files().list(
                q=f"'{folder['id']}' in parents",
                fields="files(id)"
            ).execute().get('files', [])
            
            if not contents:  # Folder is empty
                try:
                    drive_manager.service.files().delete(fileId=folder['id']).execute()
                    deleted_count += 1
                    print(f"🗑️ Deleted empty folder: {folder['name']}")
                except Exception as e:
                    print(f"❌ Failed to delete {folder['name']}: {str(e)}")
            else:
                print(f"📁 Keeping non-empty folder: {folder['name']} ({len(contents)} items)")
        
        print(f"\n🎯 Root cleanup summary:")
        print(f"   • Total root folders checked: {len(root_folders)}")
        print(f"   • Empty folders deleted: {deleted_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning root folders: {str(e)}")
        return False

def main():
    print("🚀 Starting Google Drive Restoration and Cleanup...")
    print("=" * 60)
    
    # Step 1: Restore brand folders for scraping
    if restore_brand_folders():
        print("✅ Brand folders restored successfully!")
    else:
        print("❌ Failed to restore brand folders!")
        return
    
    # Step 2: Clean up root-level empty folders
    if clean_root_drive_folders():
        print("✅ Root drive cleanup completed!")
    else:
        print("❌ Failed to clean root drive!")
        return
    
    print("\n" + "=" * 60)
    print("🎉 Google Drive restoration and cleanup completed!")
    print("\n📋 Next steps:")
    print("   1. ✅ Brand folders restored for scraping")
    print("   2. ✅ Root drive cleaned of empty folders") 
    print("   3. 🔄 Ready to increase scraping depth")
    print("   4. 🚀 Start enhanced scraping process")

if __name__ == "__main__":
    main()