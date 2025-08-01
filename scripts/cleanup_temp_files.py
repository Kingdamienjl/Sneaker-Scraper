#!/usr/bin/env python3
"""
Cleanup script for SoleID project - removes temporary files and organizes structure
"""

import os
import shutil
import glob
from pathlib import Path

def cleanup_temp_files():
    """Remove temporary files and organize project structure"""
    
    project_root = Path(__file__).parent.parent
    
    # Files to remove
    temp_patterns = [
        "*.pyc",
        "__pycache__",
        "*.log",
        "*.tmp",
        ".pytest_cache",
        "*.egg-info"
    ]
    
    # Directories to clean
    temp_dirs = [
        "temp",
        "cache", 
        "logs",
        "__pycache__"
    ]
    
    print("🧹 Cleaning up temporary files...")
    
    # Remove temp files
    for pattern in temp_patterns:
        for file_path in project_root.rglob(pattern):
            try:
                if file_path.is_file():
                    file_path.unlink()
                    print(f"   ✅ Removed: {file_path.name}")
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    print(f"   ✅ Removed directory: {file_path.name}")
            except Exception as e:
                print(f"   ❌ Error removing {file_path}: {e}")
    
    # Create organized structure
    scripts_dir = project_root / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    # Move utility scripts to scripts folder
    utility_scripts = [
        "setup.py",
        "setup_system.py", 
        "simple_cleanup.py",
        "restore_and_cleanup.py",
        "cleanup_drive.py",
        "check_drive.py",
        "system_status.py",
        "complete_system_test.py"
    ]
    
    for script in utility_scripts:
        script_path = project_root / script
        if script_path.exists():
            target_path = scripts_dir / script
            if not target_path.exists():
                shutil.move(str(script_path), str(target_path))
                print(f"   📁 Moved {script} to scripts/")
    
    print("✅ Cleanup completed!")

if __name__ == "__main__":
    cleanup_temp_files()