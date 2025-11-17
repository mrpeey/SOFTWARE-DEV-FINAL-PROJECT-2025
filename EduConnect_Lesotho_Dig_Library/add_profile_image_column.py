#!/usr/bin/env python3
"""
Add profile_image column to users table
"""

import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'library.db')

print(f"Connecting to database: {db_path}")

try:
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'profile_image' in columns:
        print("✓ Column 'profile_image' already exists in users table")
    else:
        # Add the profile_image column
        print("Adding 'profile_image' column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(500)")
        conn.commit()
        print("✓ Successfully added 'profile_image' column to users table")
    
    # Verify the column was added
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    
    print("\nCurrent users table schema:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    conn.close()
    print("\n✓ Database migration completed successfully!")
    
except sqlite3.Error as e:
    print(f"✗ Database error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
