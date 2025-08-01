#!/usr/bin/env python3
"""
Monitor Apify Integration Progress
"""

import sqlite3
import time
import os
from datetime import datetime

def monitor_progress():
    """Monitor the progress of Apify integration"""
    db_path = "sneakers.db"
    
    if not os.path.exists(db_path):
        print("Database not found. Apify integration may not have started yet.")
        return
    
    print("🔍 Monitoring Apify Integration Progress...")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check runs
        cursor.execute("SELECT COUNT(*) FROM apify_runs")
        total_runs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM apify_runs WHERE status = 'completed'")
        completed_runs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM apify_runs WHERE status = 'running'")
        running_runs = cursor.fetchone()[0]
        
        # Check sneakers
        cursor.execute("SELECT COUNT(*) FROM apify_sneakers")
        total_sneakers = cursor.fetchone()[0]
        
        # Check images
        cursor.execute("SELECT COUNT(*) FROM apify_images")
        total_images = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM apify_images WHERE drive_status = 'uploaded'")
        uploaded_images = cursor.fetchone()[0]
        
        # Get latest runs
        cursor.execute("""
            SELECT scraper_type, status, run_id 
            FROM apify_runs 
            ORDER BY rowid DESC 
            LIMIT 5
        """)
        recent_runs = cursor.fetchall()
        
        # Display results
        print(f"📊 RUNS: {total_runs} total | {running_runs} running | {completed_runs} completed")
        print(f"👟 SNEAKERS: {total_sneakers} collected")
        print(f"🖼️  IMAGES: {total_images} downloaded | {uploaded_images} uploaded to Drive")
        print()
        
        if recent_runs:
            print("🕐 Recent Runs:")
            for run in recent_runs:
                scraper_type, status, run_id = run
                print(f"  • {scraper_type}: {status} - {run_id}")
        
        # Check for any errors in logs
        log_files = [f for f in os.listdir("logs") if f.startswith("apify_integration_")]
        if log_files:
            latest_log = max(log_files)
            log_path = os.path.join("logs", latest_log)
            
            with open(log_path, 'r') as f:
                lines = f.readlines()
                error_lines = [line.strip() for line in lines if "ERROR" in line]
                
                if error_lines:
                    print("\n⚠️  Recent Errors:")
                    for error in error_lines[-3:]:  # Show last 3 errors
                        print(f"  • {error}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error monitoring progress: {e}")

def main():
    """Main monitoring loop"""
    print(f"🚀 Starting Apify Integration Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        try:
            monitor_progress()
            print("\n" + "=" * 60)
            print("⏰ Next update in 30 seconds... (Ctrl+C to stop)")
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in monitoring loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()