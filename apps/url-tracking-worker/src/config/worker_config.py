"""
URL Tracking Worker configuration
"""
import os
from typing import Dict, Any

WORKER_CONFIG = {
    # Core scheduling
    'monitoring_interval_minutes': int(os.getenv('MONITORING_INTERVAL_MINUTES', '15')),
    'monitoring_timeout_seconds': int(os.getenv('MONITORING_TIMEOUT_SECONDS', '840')),  # 14 minutes
    
    # Processing options
    'use_pure_async': os.getenv('USE_PURE_ASYNC', 'false').lower() == 'true',
    'max_concurrent_domains': int(os.getenv('MAX_CONCURRENT_DOMAINS', '15')),
    'batch_size': int(os.getenv('BATCH_SIZE', '500')),  # URLs per batch
    
    # Legacy settings
    'max_workers': int(os.getenv('MAX_WORKERS', '4')),
    'request_timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
    'retry_attempts': int(os.getenv('RETRY_ATTEMPTS', '3')),
    
    # Features
    'enable_logging': os.getenv('ENABLE_LOGGING', 'true').lower() == 'true',
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    'enable_sitemap_monitoring': os.getenv('ENABLE_SITEMAP_MONITORING', 'false').lower() == 'true',
    'enable_gap_detection': os.getenv('ENABLE_GAP_DETECTION', 'true').lower() == 'true',
}

def get_worker_config() -> Dict[str, Any]:
    """Get worker configuration"""
    return WORKER_CONFIG.copy()