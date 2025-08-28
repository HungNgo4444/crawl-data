"""
URL Tracking Worker configuration
"""
import os
from typing import Dict, Any

WORKER_CONFIG = {
    'monitoring_interval_minutes': int(os.getenv('MONITORING_INTERVAL_MINUTES', '15')),
    'batch_size': int(os.getenv('BATCH_SIZE', '10')),
    'max_workers': int(os.getenv('MAX_WORKERS', '4')),
    'request_timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
    'retry_attempts': int(os.getenv('RETRY_ATTEMPTS', '3')),
    'enable_logging': os.getenv('ENABLE_LOGGING', 'true').lower() == 'true',
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    'enable_sitemap_monitoring': os.getenv('ENABLE_SITEMAP_MONITORING', 'false').lower() == 'true',
}

def get_worker_config() -> Dict[str, Any]:
    """Get worker configuration"""
    return WORKER_CONFIG.copy()