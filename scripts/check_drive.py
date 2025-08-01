#!/usr/bin/env python3
"""Check Google Drive status"""

from google_drive import GoogleDriveManager

try:
    gdm = GoogleDriveManager()
    files = gdm.list_files()
    print(f"Google Drive Files ({len(files)} total):")
    for f in files[:10]:
        print(f"  - {f['name']} ({f['id']})")
    
    # Check for SoleID folder
    folder = gdm.find_folder_by_name("SoleID_Images")
    if folder:
        print(f"\n✅ SoleID_Images folder found: {folder['id']}")
    else:
        print(f"\n❌ SoleID_Images folder not found")
        
except Exception as e:
    print(f"Error: {str(e)}")