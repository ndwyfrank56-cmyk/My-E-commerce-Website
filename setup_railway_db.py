#!/usr/bin/env python3
"""
Railway MySQL Database Setup Script
This script connects to your Railway MySQL database and creates all necessary tables.

Usage:
    python setup_railway_db.py
    
Or with environment variables:
    MYSQL_HOST=nozomi.proxy.rlwy.net MYSQL_PORT=26283 MYSQL_USER=root MYSQL_PASSWORD=your_password python setup_railway_db.py
"""

import mysql.connector
import os
import sys
from pathlib import Path

def get_connection_params():
    """Get database connection parameters from environment or user input"""
    
    # Try to get from environment first
    host = os.environ.get('MYSQL_HOST', 'nozomi.proxy.rlwy.net')
    port = int(os.environ.get('MYSQL_PORT', 26283))
    user = os.environ.get('MYSQL_USER', 'root')
    password = os.environ.get('MYSQL_PASSWORD')
    database = os.environ.get('MYSQL_DB', 'railway')
    
    # If password not in environment, ask user
    if not password:
        print("=" * 60)
        print("Railway MySQL Database Setup")
        print("=" * 60)
        print("\nEnter your Railway MySQL connection details:")
        print(f"Host [{host}]: ", end="")
        user_host = input().strip()
        if user_host:
            host = user_host
        
        print(f"Port [{port}]: ", end="")
        user_port = input().strip()
        if user_port:
            port = int(user_port)
        
        print(f"User [{user}]: ", end="")
        user_user = input().strip()
        if user_user:
            user = user_user
        
        print("Password: ", end="")
        password = input().strip()
        
        print(f"Database [{database}]: ", end="")
        user_db = input().strip()
        if user_db:
            database = user_db
    
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database
    }

def read_sql_file(filepath):
    """Read SQL commands from file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split by semicolon and filter empty statements
    statements = [stmt.strip() for stmt in content.split(';') if stmt.strip()]
    return statements

def create_tables(connection, sql_statements):
    """Execute SQL statements to create tables"""
    cursor = connection.cursor()
    
    for i, statement in enumerate(sql_statements, 1):
        try:
            print(f"[{i}/{len(sql_statements)}] Executing: {statement[:60]}...")
            cursor.execute(statement)
            connection.commit()
            print(f"      ✓ Success")
        except mysql.connector.Error as err:
            if "already exists" in str(err):
                print(f"      ⚠ Table already exists (skipping)")
            else:
                print(f"      ✗ Error: {err}")
                connection.rollback()
                return False
    
    cursor.close()
    return True

def verify_tables(connection):
    """Verify that all tables were created"""
    cursor = connection.cursor()
    
    expected_tables = [
        'users',
        'categories',
        'products',
        'image_variations',
        'dropdown_variation',
        'orders',
        'order_items',
        'payments',
        'wishlist',
        'password_resets',
        'banners',
        'low_stock_alerts',
        'reviews',
        'workers',
        'worker_login',
        'worker_page_permissions'
    ]
    
    cursor.execute("SHOW TABLES")
    existing_tables = [table[0] for table in cursor.fetchall()]
    cursor.close()
    
    print("\n" + "=" * 60)
    print("Table Verification")
    print("=" * 60)
    
    all_exist = True
    for table in expected_tables:
        if table in existing_tables:
            print(f"✓ {table}")
        else:
            print(f"✗ {table} (MISSING)")
            all_exist = False
    
    return all_exist

def main():
    """Main setup function"""
    try:
        # Get connection parameters
        params = get_connection_params()
        
        print("\n" + "=" * 60)
        print("Connecting to Railway MySQL...")
        print("=" * 60)
        print(f"Host: {params['host']}")
        print(f"Port: {params['port']}")
        print(f"User: {params['user']}")
        print(f"Database: {params['database']}")
        
        # Connect to database
        connection = mysql.connector.connect(
            host=params['host'],
            port=params['port'],
            user=params['user'],
            password=params['password'],
            database=params['database']
        )
        
        print("✓ Connected successfully!\n")
        
        # Read SQL file - try complete version first, fall back to basic
        sql_file = Path(__file__).parent / 'init_railway_db_complete.sql'
        
        if not sql_file.exists():
            sql_file = Path(__file__).parent / 'init_railway_db.sql'
        
        if not sql_file.exists():
            print(f"✗ Error: No SQL schema file found!")
            print(f"  Expected: init_railway_db_complete.sql or init_railway_db.sql")
            return False
        
        print("=" * 60)
        print("Creating Tables")
        print("=" * 60)
        
        sql_statements = read_sql_file(sql_file)
        
        # Create tables
        if not create_tables(connection, sql_statements):
            print("\n✗ Failed to create tables")
            connection.close()
            return False
        
        # Verify tables
        if verify_tables(connection):
            print("\n" + "=" * 60)
            print("✓ Database setup completed successfully!")
            print("=" * 60)
            print("\nYour Railway MySQL database is now ready to use.")
            print("Update your .env file with these credentials:")
            print(f"  MYSQL_HOST={params['host']}")
            print(f"  MYSQL_PORT={params['port']}")
            print(f"  MYSQL_USER={params['user']}")
            print(f"  MYSQL_PASSWORD={params['password']}")
            print(f"  MYSQL_DB={params['database']}")
        else:
            print("\n⚠ Some tables may be missing!")
        
        connection.close()
        return True
        
    except mysql.connector.Error as err:
        print(f"\n✗ Database connection error: {err}")
        print("\nCommon issues:")
        print("  - Check your host, port, username, and password")
        print("  - Ensure Railway MySQL service is running")
        print("  - Check your internet connection")
        return False
    except Exception as err:
        print(f"\n✗ Error: {err}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
