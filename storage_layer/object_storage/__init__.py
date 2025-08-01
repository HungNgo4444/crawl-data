"""
Object Storage Layer
MinIO integration for large content storage
"""

from .minio_manager import MinIOManager
from .compression_utils import CompressionUtils

__all__ = ['MinIOManager', 'CompressionUtils']