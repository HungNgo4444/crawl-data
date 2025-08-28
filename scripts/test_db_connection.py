#!/usr/bin/env python3
"""Test database connection"""
import psycopg2
import sys

def test_connection():
    try:
        print("Testing database connection...")
        
        # Test connection
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            user='crawler_user',
            password='crawler123',
            database='crawler_db'
        )
        
        print("Connection successful!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM domains WHERE status = 'ACTIVE' LIMIT 5;")
        domains = cursor.fetchall()
        
        print(f"Found {len(domains)} active domains:")
        for domain in domains:
            print(f"  - {domain[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)