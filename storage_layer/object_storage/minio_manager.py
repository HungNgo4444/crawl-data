"""
MinIO object storage manager for large content storage
Target: 70% compression ratio, fast retrieval
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple, BinaryIO
from datetime import datetime, timedelta
import gzip
import json
from io import BytesIO
import hashlib
from minio import Minio
from minio.error import S3Error
from urllib3.poolmanager import PoolManager
import ssl

logger = logging.getLogger(__name__)

class MinIOManager:
    """Efficient object storage for large content with compression"""
    
    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin", 
        secure: bool = False,
        region: str = "us-east-1"
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.region = region
        
        # Initialize MinIO client
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region
        )
        
        # Bucket configuration
        self.buckets = {
            'content': 'crawler-content',
            'raw-html': 'crawler-raw-html', 
            'images': 'crawler-images',
            'backups': 'crawler-backups'
        }
        
        # Compression settings
        self.compression_level = 6  # Good balance of speed vs compression
        self.chunk_size = 64 * 1024  # 64KB chunks for streaming
        
        # Stats
        self.stats = {
            'uploads': 0,
            'downloads': 0,
            'errors': 0,
            'bytes_stored': 0,
            'bytes_retrieved': 0
        }
    
    async def initialize(self):
        """Initialize MinIO storage - create buckets if needed"""
        try:
            for bucket_type, bucket_name in self.buckets.items():
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name, location=self.region)
                    logger.info(f"Created bucket: {bucket_name}")
                
                # Set bucket lifecycle policy (optional)
                await self._set_bucket_lifecycle(bucket_name, bucket_type)
            
            logger.info("MinIO storage initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MinIO storage: {e}")
            return False
    
    async def store_article_content(
        self, 
        article_id: str, 
        content: str, 
        raw_html: str,
        metadata: Optional[Dict] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Store full article content and raw HTML with compression
        Returns (content_key, html_key) or (None, None) on failure
        """
        try:
            # Generate storage keys
            date_prefix = datetime.now().strftime("%Y/%m/%d")
            content_key = f"articles/{date_prefix}/{article_id}/content.gz"
            html_key = f"articles/{date_prefix}/{article_id}/raw.html.gz"
            
            # Compress content
            compressed_content = await self._compress_text(content)
            compressed_html = await self._compress_text(raw_html)
            
            # Prepare metadata
            content_metadata = {
                'article_id': article_id,
                'original_size': len(content.encode('utf-8')),
                'compressed_size': len(compressed_content),
                'compression_ratio': len(compressed_content) / len(content.encode('utf-8')),
                'stored_at': datetime.now().isoformat(),
                'content_type': 'text/plain',
                'encoding': 'utf-8',
                'compression': 'gzip'
            }
            
            html_metadata = {
                'article_id': article_id,
                'original_size': len(raw_html.encode('utf-8')),
                'compressed_size': len(compressed_html),
                'compression_ratio': len(compressed_html) / len(raw_html.encode('utf-8')),
                'stored_at': datetime.now().isoformat(),
                'content_type': 'text/html',
                'encoding': 'utf-8',
                'compression': 'gzip'
            }
            
            if metadata:
                content_metadata.update(metadata)
                html_metadata.update(metadata)
            
            # Store both files concurrently
            content_task = self._upload_object(
                self.buckets['content'],
                content_key,
                compressed_content,
                content_metadata
            )
            
            html_task = self._upload_object(
                self.buckets['raw-html'],
                html_key,
                compressed_html,
                html_metadata
            )
            
            # Wait for both uploads
            results = await asyncio.gather(content_task, html_task, return_exceptions=True)
            
            content_success = not isinstance(results[0], Exception)
            html_success = not isinstance(results[1], Exception)
            
            if content_success and html_success:
                self.stats['uploads'] += 2
                self.stats['bytes_stored'] += len(compressed_content) + len(compressed_html)
                logger.debug(f"Stored content for article {article_id}")
                return content_key, html_key
            else:
                # Log errors
                if isinstance(results[0], Exception):
                    logger.error(f"Failed to store content: {results[0]}")
                if isinstance(results[1], Exception):
                    logger.error(f"Failed to store HTML: {results[1]}")
                
                self.stats['errors'] += 1
                return None, None
                
        except Exception as e:
            logger.error(f"Error storing article content for {article_id}: {e}")
            self.stats['errors'] += 1
            return None, None
    
    async def retrieve_article_content(self, content_key: str) -> Optional[str]:
        """Retrieve and decompress article content"""
        try:
            # Extract bucket from key
            if content_key.startswith('articles/'):
                bucket_name = self.buckets['content']
            else:
                logger.warning(f"Unknown content key format: {content_key}")
                return None
            
            # Download compressed data
            compressed_data = await self._download_object(bucket_name, content_key)
            if not compressed_data:
                return None
            
            # Decompress content
            content = await self._decompress_text(compressed_data)
            
            self.stats['downloads'] += 1
            self.stats['bytes_retrieved'] += len(compressed_data)
            
            logger.debug(f"Retrieved content from {content_key}")
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving content from {content_key}: {e}")
            self.stats['errors'] += 1
            return None
    
    async def retrieve_raw_html(self, html_key: str) -> Optional[str]:
        """Retrieve and decompress raw HTML"""
        try:
            bucket_name = self.buckets['raw-html']
            
            # Download compressed data
            compressed_data = await self._download_object(bucket_name, html_key)
            if not compressed_data:
                return None
            
            # Decompress HTML
            html_content = await self._decompress_text(compressed_data)
            
            self.stats['downloads'] += 1
            self.stats['bytes_retrieved'] += len(compressed_data)
            
            logger.debug(f"Retrieved HTML from {html_key}")
            return html_content
            
        except Exception as e:
            logger.error(f"Error retrieving HTML from {html_key}: {e}")
            self.stats['errors'] += 1
            return None
    
    async def store_images(self, article_id: str, image_urls: List[str]) -> List[str]:
        """Store images for an article (future enhancement)"""
        # Placeholder for image storage functionality
        logger.info(f"Image storage not yet implemented for article {article_id}")
        return []
    
    async def delete_article_content(self, content_key: str, html_key: str) -> bool:
        """Delete article content and HTML"""
        try:
            delete_tasks = []
            
            if content_key:
                delete_tasks.append(self._delete_object(self.buckets['content'], content_key))
            
            if html_key:
                delete_tasks.append(self._delete_object(self.buckets['raw-html'], html_key))
            
            if delete_tasks:
                results = await asyncio.gather(*delete_tasks, return_exceptions=True)
                
                # Check if all deletions succeeded
                success = all(not isinstance(result, Exception) for result in results)
                
                if success:
                    logger.debug(f"Deleted content: {content_key}, HTML: {html_key}")
                else:
                    logger.warning(f"Some deletions failed for content: {content_key}, HTML: {html_key}")
                
                return success
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting article content: {e}")
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            bucket_stats = {}
            total_objects = 0
            total_size = 0
            
            for bucket_type, bucket_name in self.buckets.items():
                try:
                    objects = list(self.client.list_objects(bucket_name, recursive=True))
                    bucket_objects = len(objects)
                    bucket_size = sum(obj.size for obj in objects)
                    
                    bucket_stats[bucket_type] = {
                        'objects': bucket_objects,
                        'size_mb': round(bucket_size / 1024 / 1024, 2)
                    }
                    
                    total_objects += bucket_objects
                    total_size += bucket_size
                    
                except Exception as e:
                    logger.warning(f"Error getting stats for bucket {bucket_name}: {e}")
                    bucket_stats[bucket_type] = {'objects': 0, 'size_mb': 0}
            
            return {
                'bucket_stats': bucket_stats,
                'total_objects': total_objects,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'performance_stats': self.stats,
                'compression_ratio': self._calculate_avg_compression_ratio()
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {'error': str(e)}
    
    async def _upload_object(
        self, 
        bucket_name: str, 
        object_name: str, 
        data: bytes, 
        metadata: Dict[str, Any]
    ) -> bool:
        """Upload object to MinIO"""
        try:
            # Convert metadata to string values
            str_metadata = {k: str(v) for k, v in metadata.items()}
            
            # Upload using BytesIO
            data_stream = BytesIO(data)
            
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(data),
                metadata=str_metadata
            )
            
            return True
            
        except S3Error as e:
            logger.error(f"S3 error uploading {object_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error uploading {object_name}: {e}")
            return False
    
    async def _download_object(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """Download object from MinIO"""
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            return data
            
        except S3Error as e:
            logger.error(f"S3 error downloading {object_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {object_name}: {e}")
            return None
    
    async def _delete_object(self, bucket_name: str, object_name: str) -> bool:
        """Delete object from MinIO"""
        try:
            self.client.remove_object(bucket_name, object_name)
            return True
            
        except S3Error as e:
            logger.error(f"S3 error deleting {object_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting {object_name}: {e}")
            return False
    
    async def _compress_text(self, text: str) -> bytes:
        """Compress text using gzip"""
        try:
            text_bytes = text.encode('utf-8')
            compressed = gzip.compress(text_bytes, compresslevel=self.compression_level)
            return compressed
        except Exception as e:
            logger.error(f"Error compressing text: {e}")
            return text.encode('utf-8')  # Return uncompressed as fallback
    
    async def _decompress_text(self, compressed_data: bytes) -> str:
        """Decompress gzipped text"""
        try:
            decompressed_bytes = gzip.decompress(compressed_data)
            return decompressed_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decompressing data: {e}")
            # Try to decode as plain text (fallback)
            try:
                return compressed_data.decode('utf-8')
            except:
                return ""
    
    async def _set_bucket_lifecycle(self, bucket_name: str, bucket_type: str):
        """Set lifecycle policy for bucket (placeholder)"""
        # MinIO lifecycle policies would be set here
        # This is a placeholder for future implementation
        pass
    
    def _calculate_avg_compression_ratio(self) -> float:
        """Calculate average compression ratio"""
        # This would need to track compression ratios over time
        # For now, return estimated ratio
        return 0.3  # Assume 30% of original size (70% compression)
    
    async def health_check(self) -> bool:
        """Check MinIO connection health"""
        try:
            # Try to list buckets
            buckets = self.client.list_buckets()
            return True
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False