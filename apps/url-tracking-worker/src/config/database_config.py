"""
Database configuration for URL tracking worker
"""
import os
import sys
from typing import Dict, Any

def _get_required_env(key: str, description: str = None) -> str:
    """Get required environment variable or exit with error"""
    value = os.getenv(key)
    if not value:
        error_msg = f"CRITICAL: Required environment variable '{key}' is not set."
        if description:
            error_msg += f" {description}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        sys.exit(1)
    return value

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'user': os.getenv('DB_USER', 'crawler_user'),
    'password': _get_required_env('DB_PASSWORD', 'Please set database password in environment.'),
    'database': os.getenv('DB_NAME', 'crawler_db'),
    # Connection pool settings
    'minconn': int(os.getenv('DB_MIN_CONNECTIONS', '2')),
    'maxconn': int(os.getenv('DB_MAX_CONNECTIONS', '20')),
}

def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    return DATABASE_CONFIG.copy()