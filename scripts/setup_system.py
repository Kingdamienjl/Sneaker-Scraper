#!/usr/bin/env python3
"""
SoleID Setup Script
Creates Google Drive folders, local directories, and tests the complete system
"""

import sys
import os
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_drive import GoogleDriveManager
from database import create_tables
from config import Config

def setup_logging():
    """Setup logging configuration"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = f"setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_path

def create_local_directories():
    """Create all necessary local directories"""
    directories = [
        "data",
        "data/images", 
        "data/temp",
        "data/exports",
        "logs",
        "backups"
    ]
    
    print("📁 Creating local directories...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ {directory}")
    
    return True

def setup_google_drive():
    """Setup Google Drive folder structure"""
    print("☁️ Setting up Google Drive...")
    
    try:
        # Initialize Google Drive manager
        drive_manager = GoogleDriveManager()
        
        # Create main SoleID folder
        print("   📂 Creating 'SoleID_Images' folder...")
        main_folder_id = drive_manager.get_or_create_folder("SoleID_Images")
        
        if main_folder_id:
            print(f"   ✅ Main folder created: {main_folder_id}")
            
            # Create subfolders for organization
            subfolders = [
                "Nike",
                "Adidas", 
                "Jordan",
                "New_Balance",
                "Converse",
                "Vans",
                "Other_Brands"
            ]
            
            print("   📂 Creating brand subfolders...")
            for subfolder in subfolders:
                subfolder_id = drive_manager.get_or_create_folder(subfolder, main_folder_id)
                if subfolder_id:
                    print(f"      ✅ {subfolder}")
                else:
                    print(f"      ❌ Failed to create {subfolder}")
            
            # Update .env file with folder ID
            update_env_file(main_folder_id)
            
            return main_folder_id
        else:
            print("   ❌ Failed to create main folder")
            return None
            
    except Exception as e:
        print(f"   ❌ Google Drive setup failed: {str(e)}")
        return None

def update_env_file(folder_id):
    """Update .env file with Google Drive folder ID"""
    env_path = ".env"
    
    # Read existing .env or create new one
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add GOOGLE_DRIVE_FOLDER_ID
    folder_id_line = f"GOOGLE_DRIVE_FOLDER_ID={folder_id}\n"
    updated = False
    
    for i, line in enumerate(env_lines):
        if line.startswith("GOOGLE_DRIVE_FOLDER_ID="):
            env_lines[i] = folder_id_line
            updated = True
            break
    
    if not updated:
        env_lines.append(folder_id_line)
    
    # Write back to .env
    with open(env_path, 'w') as f:
        f.writelines(env_lines)
    
    print(f"   ✅ Updated .env with folder ID: {folder_id}")

def test_system():
    """Test the complete system setup"""
    print("🧪 Testing system setup...")
    
    try:
        # Test database
        print("   📊 Testing database...")
        create_tables()
        print("   ✅ Database tables created")
        
        # Test Google Drive
        print("   ☁️ Testing Google Drive connection...")
        drive_manager = GoogleDriveManager()
        files = drive_manager.list_files()
        print(f"   ✅ Google Drive connected ({len(files)} files found)")
        
        # Check directories
        print("   📁 Checking local directories...")
        required_dirs = ["data", "data/images", "logs"]
        for directory in required_dirs:
            if os.path.exists(directory):
                print(f"   ✅ {directory}")
            else:
                print(f"   ❌ {directory} missing")
        
        return True
        
    except Exception as e:
        print(f"   ❌ System test failed: {str(e)}")
        return False

def main():
    """Main setup function"""
    print("🚀 SoleID System Setup")
    print("=" * 40)
    
    # Setup logging
    log_path = setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting SoleID system setup")
    
    try:
        # Step 1: Create local directories
        if create_local_directories():
            print("✅ Local directories created")
        else:
            print("❌ Failed to create local directories")
            return False
        
        # Step 2: Setup Google Drive
        folder_id = setup_google_drive()
        if folder_id:
            print("✅ Google Drive setup complete")
        else:
            print("⚠️ Google Drive setup failed (you can continue without it)")
        
        # Step 3: Test system
        if test_system():
            print("✅ System test passed")
        else:
            print("❌ System test failed")
            return False
        
        print("\n" + "=" * 40)
        print("🎉 SETUP COMPLETE!")
        print("=" * 40)
        
        print("📊 WHAT WAS CREATED:")
        print("   • Local directories: data/, logs/, backups/")
        print("   • Google Drive: SoleID_Images folder with brand subfolders")
        print("   • Database: SQLite tables ready")
        print("   • Environment: .env file updated")
        
        print("\n🔍 WHERE TO FIND YOUR DATA:")
        print("   • Database: sneakers.db")
        print("   • Images: data/images/ (local) + Google Drive")
        print("   • Logs: logs/ folder")
        print("   • Config: .env file")
        
        print("\n🌐 API ENDPOINTS:")
        print("   • All sneakers: http://localhost:8000/api/sneakers")
        print("   • Database stats: http://localhost:8000/api/database-stats")
        print("   • API docs: http://localhost:8000/docs")
        
        print(f"\n📝 Setup log: {log_path}")
        print("\n🚀 Ready to start scraping!")
        
        logger.info("SoleID system setup completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        logger.error(f"Setup failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    main()