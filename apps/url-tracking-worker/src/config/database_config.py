"""
Database configuration for URL tracking worker
"""
import os
from typing import Dict, Any

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'user': os.getenv('DB_USER', 'crawler_user'),
    'password': os.getenv('DB_PASSWORD', 'crawler123'),
    'database': os.getenv('DB_NAME', 'crawler_db'),
}

def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    return DATABASE_CONFIG.copy()