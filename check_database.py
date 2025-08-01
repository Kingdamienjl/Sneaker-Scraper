#!/usr/bin/env python3
"""
Check Database Status - Verify sneaker data is available
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
    
    # Check static_sneakers table
    cursor.execute('SELECT COUNT(*) FROM static_sneakers')
    count = cursor.fetchone()[0]
    print(f'📊 Static sneakers count: {count}')
    
    if count > 0:
        cursor.execute('SELECT name, brand, price FROM static_sneakers LIMIT 5')
        sneakers = cursor.fetchall()
        print('📝 Sample static sneakers:')
        for i, (name, brand, price) in enumerate(sneakers, 1):
            print(f'  {i}. {brand} - {name} - ${price}')
    
    # Check main sneakers table structure
    try:
        cursor.execute('PRAGMA table_info(sneakers)')
        columns = cursor.fetchall()
        print()
        print('🏗️ Main sneakers table structure:')
        for col in columns:
            print(f'  - {col[1]} ({col[2]})')
            
        # Check count in main table
        cursor.execute('SELECT COUNT(*) FROM sneakers')
        main_count = cursor.fetchone()[0]
        print(f'📊 Main sneakers count: {main_count}')
        
    except Exception as e:
        print(f'❌ Main sneakers table issue: {e}')
    
    # Check apify tables
    try:
        cursor.execute('SELECT COUNT(*) FROM apify_sneakers')
        apify_count = cursor.fetchone()[0]
        print(f'📊 Apify sneakers count: {apify_count}')
    except:
        print('📊 Apify sneakers count: 0 (table not found)')
    
    conn.close()
    
    print()
    print('✅ Database check complete!')
    if count > 0:
        print('🎉 SUCCESS: We now have sneaker data available!')
    else:
        print('❌ ISSUE: No sneaker data found')

if __name__ == "__main__":
    main()