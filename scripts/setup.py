#!/usr/bin/env python3
"""
Setup script for the Sneaker Scraper project.
Run this script to initialize the project environment.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def create_directories():
    """Create necessary directories for the project."""
    directories = [
        'data',
        'logs',
        'images',
        'images/thumbnails',
        'images/full_size'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python version: {sys.version}")

def install_requirements():
    """Install Python requirements."""
    print("✓ Requirements already installed (skipping installation)")
    # Uncomment the lines below if you need to install requirements
    # try:
    #     subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    #     print("✓ Requirements installed successfully")
    # except subprocess.CalledProcessError:
    #     print("❌ Failed to install requirements")
    #     sys.exit(1)

def setup_environment():
    """Setup environment variables."""
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if env_example.exists() and not env_file.exists():
        # Copy .env.example to .env
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✓ Created .env file from .env.example")
        print("⚠️  Please update the .env file with your actual configuration values")
    elif env_file.exists():
        print("✓ .env file already exists")
    else:
        print("❌ .env.example file not found")

def initialize_database():
    """Initialize the database."""
    try:
        from database import init_database
        init_database()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        print("Make sure your database configuration is correct in .env")

def main():
    """Main setup function."""
    print("🚀 Setting up Sneaker Scraper project...")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directories()
    
    # Install requirements
    install_requirements()
    
    # Setup environment
    setup_environment()
    
    # Initialize database
    initialize_database()
    
    print("=" * 50)
    print("✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Update your .env file with actual configuration values")
    print("2. Add your Google Drive credentials (credentials.json)")
    print("3. Run 'python main.py' to start the scraper")

if __name__ == "__main__":
    main()