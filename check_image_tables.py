#!/usr/bin/env python3
"""
Check Image Tables - Analyze database structure for image categorization
"""

import sqlite3

def main():
    conn = sqlite3.connect('sneakers.db')
    cursor = conn.cursor()
    
    # Check all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('📋 Available tables:')
    for table in tables:
        print(f'  - {table[0]}')
    
    print()
    
    # Check images table structure
    try:
        cursor.execute('PRAGMA table_info(images)')
        columns = cursor.fetchall()
        print('🏗️ Images table structure:')
        for col in columns:
            print(f'  - {col[1]} ({col[2]})')
            
        # Get count and sample data
        cursor.execute('SELECT COUNT(*) FROM images')
        count = cursor.fetchone()[0]
        print(f'📊 Images count: {count}')
        
        if count > 0:
            cursor.execute('SELECT * FROM images LIMIT 3')
            samples = cursor.fetchall()
            print('📝 Sample images data:')
            for i, sample in enumerate(samples, 1):
                print(f'  {i}. {sample}')
                
    except Exception as e:
        print(f'❌ Images table error: {e}')
    
    print()
    
    # Check sneaker_images table
    try:
        cursor.execute('PRAGMA table_info(sneaker_images)')
        columns = cursor.fetchall()
        print('🏗️ Sneaker_images table structure:')
        for col in columns:
            print(f'  - {col[1]} ({col[2]})')
            
        cursor.execute('SELECT COUNT(*) FROM sneaker_images')
        count = cursor.fetchone()[0]
        print(f'📊 Sneaker_images count: {count}')
        
        if count > 0:
            cursor.execute('SELECT * FROM sneaker_images LIMIT 3')
            samples = cursor.fetchall()
            print('📝 Sample sneaker_images data:')
            for i, sample in enumerate(samples, 1):
                print(f'  {i}. {sample}')
        
    except Exception as e:
        print(f'❌ Sneaker_images table error: {e}')
    
    print()
    
    # Check for any image-related tables
    image_tables = [table[0] for table in tables if 'image' in table[0].lower()]
    print(f'🖼️ Image-related tables: {image_tables}')
    
    # Check each image table
    for table_name in image_tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'📊 {table_name} count: {count}')
            
            if count > 0:
                cursor.execute(f'SELECT * FROM {table_name} LIMIT 2')
                samples = cursor.fetchall()
                print(f'📝 Sample {table_name} data:')
                for i, sample in enumerate(samples, 1):
                    print(f'  {i}. {sample}')
                print()
                
        except Exception as e:
            print(f'❌ Error checking {table_name}: {e}')
    
    conn.close()

if __name__ == "__main__":
    main()