"""
Content compression utilities
Optimize storage space and transfer speeds
"""

import gzip
import bz2
import lzma
import zlib
from typing import Dict, Any, Tuple, Optional
import logging
from enum import Enum
import json

logger = logging.getLogger(__name__)

class CompressionType(Enum):
    """Available compression algorithms"""
    GZIP = "gzip"
    BZIP2 = "bzip2"
    LZMA = "lzma"
    ZLIB = "zlib"

class CompressionUtils:
    """Utilities for content compression and decompression"""
    
    def __init__(self):
        # Compression settings for different content types
        self.compression_configs = {
            'text': {
                'algorithm': CompressionType.GZIP,
                'level': 6,  # Good balance of speed vs compression
                'expected_ratio': 0.3  # Expect 70% compression
            },
            'html': {
                'algorithm': CompressionType.GZIP, 
                'level': 6,
                'expected_ratio': 0.25  # HTML compresses very well
            },
            'json': {
                'algorithm': CompressionType.GZIP,
                'level': 9,  # JSON has lots of repetition
                'expected_ratio': 0.2
            },
            'binary': {
                'algorithm': CompressionType.LZMA,
                'level': 6,
                'expected_ratio': 0.6  # Binary data doesn't compress as well
            }
        }
    
    def compress_content(
        self, 
        content: str, 
        content_type: str = 'text',
        algorithm: Optional[CompressionType] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress content with specified algorithm
        Returns (compressed_data, metadata)
        """
        if not content:
            return b'', {'error': 'Empty content'}
        
        try:
            # Get compression config
            config = self.compression_configs.get(content_type, self.compression_configs['text'])
            compression_algo = algorithm or config['algorithm']
            level = config['level']
            
            # Convert to bytes
            original_bytes = content.encode('utf-8')
            original_size = len(original_bytes)
            
            # Compress based on algorithm
            if compression_algo == CompressionType.GZIP:
                compressed_data = gzip.compress(original_bytes, compresslevel=level)
            elif compression_algo == CompressionType.BZIP2:
                compressed_data = bz2.compress(original_bytes, compresslevel=level)
            elif compression_algo == CompressionType.LZMA:
                compressed_data = lzma.compress(original_bytes, preset=level)
            elif compression_algo == CompressionType.ZLIB:
                compressed_data = zlib.compress(original_bytes, level=level)
            else:
                raise ValueError(f"Unsupported compression algorithm: {compression_algo}")
            
            compressed_size = len(compressed_data)
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            
            # Create metadata
            metadata = {
                'algorithm': compression_algo.value,
                'level': level,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': round(compression_ratio, 4),
                'compression_percent': round((1 - compression_ratio) * 100, 2),
                'content_type': content_type,
                'encoding': 'utf-8'
            }
            
            logger.debug(f"Compressed {original_size} bytes to {compressed_size} bytes "
                        f"({metadata['compression_percent']}% reduction)")
            
            return compressed_data, metadata
            
        except Exception as e:
            logger.error(f"Error compressing content: {e}")
            return content.encode('utf-8'), {'error': str(e)}
    
    def decompress_content(
        self, 
        compressed_data: bytes, 
        algorithm: CompressionType,
        encoding: str = 'utf-8'
    ) -> Optional[str]:
        """
        Decompress content using specified algorithm
        Returns decompressed string or None on error
        """
        if not compressed_data:
            return ""
        
        try:
            # Decompress based on algorithm
            if algorithm == CompressionType.GZIP:
                decompressed_bytes = gzip.decompress(compressed_data)
            elif algorithm == CompressionType.BZIP2:
                decompressed_bytes = bz2.decompress(compressed_data)
            elif algorithm == CompressionType.LZMA:
                decompressed_bytes = lzma.decompress(compressed_data)
            elif algorithm == CompressionType.ZLIB:
                decompressed_bytes = zlib.decompress(compressed_data)
            else:
                raise ValueError(f"Unsupported compression algorithm: {algorithm}")
            
            # Decode to string
            decompressed_text = decompressed_bytes.decode(encoding)
            
            logger.debug(f"Decompressed {len(compressed_data)} bytes to "
                        f"{len(decompressed_bytes)} bytes")
            
            return decompressed_text
            
        except Exception as e:
            logger.error(f"Error decompressing content: {e}")
            # Try to decode as plain text (fallback)
            try:
                return compressed_data.decode(encoding)
            except:
                return None
    
    def auto_select_compression(self, content: str, content_type: str = 'text') -> CompressionType:
        """
        Automatically select best compression algorithm based on content
        """
        content_size = len(content.encode('utf-8'))
        
        # For small content, use fast compression
        if content_size < 1024:  # 1KB
            return CompressionType.ZLIB
        
        # For HTML/XML, GZIP works very well
        if content_type in ['html', 'xml'] or '<' in content[:100]:
            return CompressionType.GZIP
        
        # For JSON data, GZIP is excellent
        if content_type == 'json' or content.strip().startswith(('{', '[')):
            return CompressionType.GZIP
        
        # For large text content, try different algorithms
        if content_size > 100 * 1024:  # 100KB
            # Test compression ratios with small sample
            sample = content[:10000]  # First 10KB
            
            ratios = {}
            for algo in [CompressionType.GZIP, CompressionType.BZIP2, CompressionType.LZMA]:
                try:
                    compressed, metadata = self.compress_content(sample, content_type, algo)
                    ratios[algo] = metadata.get('compression_ratio', 1.0)
                except:
                    ratios[algo] = 1.0
            
            # Return algorithm with best compression
            best_algo = min(ratios.keys(), key=lambda k: ratios[k])
            logger.debug(f"Auto-selected {best_algo.value} based on sample compression ratios: {ratios}")
            return best_algo
        
        # Default to GZIP for general text
        return CompressionType.GZIP
    
    def compress_json(self, data: Dict[str, Any]) -> Tuple[bytes, Dict[str, Any]]:
        """Compress JSON data with optimal settings"""
        try:
            # Serialize JSON with minimal formatting
            json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            
            # Compress with high level for JSON
            compressed_data, metadata = self.compress_content(
                json_str, 
                content_type='json',
                algorithm=CompressionType.GZIP
            )
            
            metadata['data_type'] = 'json'
            return compressed_data, metadata
            
        except Exception as e:
            logger.error(f"Error compressing JSON: {e}")
            return b'', {'error': str(e)}
    
    def decompress_json(self, compressed_data: bytes) -> Optional[Dict[str, Any]]:
        """Decompress and parse JSON data"""
        try:
            # Decompress
            json_str = self.decompress_content(compressed_data, CompressionType.GZIP)
            
            if json_str is None:
                return None
            
            # Parse JSON
            return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"Error decompressing JSON: {e}")
            return None
    
    def get_compression_stats(
        self, 
        original_content: str, 
        compressed_data: bytes,
        algorithm: CompressionType
    ) -> Dict[str, Any]:
        """Get detailed compression statistics"""
        original_size = len(original_content.encode('utf-8'))
        compressed_size = len(compressed_data)
        
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        return {
            'algorithm': algorithm.value,
            'original_size_bytes': original_size,
            'compressed_size_bytes': compressed_size,
            'compression_ratio': round(compression_ratio, 4),
            'compression_percent': round((1 - compression_ratio) * 100, 2),
            'space_saved_bytes': original_size - compressed_size,
            'space_saved_percent': round((1 - compression_ratio) * 100, 2)
        }
    
    def benchmark_compression(self, content: str, content_type: str = 'text') -> Dict[str, Dict[str, Any]]:
        """
        Benchmark different compression algorithms on given content
        Returns performance comparison
        """
        results = {}
        
        algorithms = [
            CompressionType.GZIP,
            CompressionType.BZIP2, 
            CompressionType.LZMA,
            CompressionType.ZLIB
        ]
        
        for algorithm in algorithms:
            try:
                import time
                
                # Time compression
                start_time = time.time()
                compressed_data, metadata = self.compress_content(content, content_type, algorithm)
                compression_time = time.time() - start_time
                
                # Time decompression
                start_time = time.time()
                decompressed = self.decompress_content(compressed_data, algorithm)
                decompression_time = time.time() - start_time
                
                # Verify integrity
                integrity_ok = decompressed == content
                
                results[algorithm.value] = {
                    'compression_ratio': metadata.get('compression_ratio', 1.0),
                    'compression_percent': metadata.get('compression_percent', 0.0),
                    'compression_time_ms': round(compression_time * 1000, 2),
                    'decompression_time_ms': round(decompression_time * 1000, 2),
                    'integrity_check': integrity_ok,
                    'compressed_size': metadata.get('compressed_size', 0)
                }
                
            except Exception as e:
                results[algorithm.value] = {
                    'error': str(e)
                }
        
        return results