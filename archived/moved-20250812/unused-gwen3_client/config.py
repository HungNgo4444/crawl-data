"""
GWEN-3 Configuration Management
Centralized configuration for Ollama integration and Vietnamese analysis
Author: James (Dev Agent)
Date: 2025-08-11
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class LogLevel(Enum):
    """Logging levels for GWEN-3 client"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

@dataclass
class OllamaConfig:
    """Ollama server configuration settings"""
    
    # Connection settings
    base_url: str = "http://ollama:11434"
    timeout: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay: int = 10
    
    # Model settings
    model_name: str = "gwen-3:8b"
    max_concurrent_requests: int = 2
    
    # Performance settings
    connection_pool_size: int = 10
    keep_alive_timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'OllamaConfig':
        """Create configuration from environment variables"""
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            timeout=int(os.getenv("OLLAMA_TIMEOUT", "300")),
            max_retries=int(os.getenv("OLLAMA_MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("OLLAMA_RETRY_DELAY", "10")),
            model_name=os.getenv("OLLAMA_MODEL_NAME", "gwen-3:8b"),
            max_concurrent_requests=int(os.getenv("OLLAMA_MAX_CONCURRENT", "2")),
            connection_pool_size=int(os.getenv("OLLAMA_POOL_SIZE", "10")),
            keep_alive_timeout=int(os.getenv("OLLAMA_KEEP_ALIVE", "30"))
        )

@dataclass
class AnalysisConfig:
    """Vietnamese content analysis configuration"""
    
    # Model parameters
    temperature: float = 0.1
    top_p: float = 0.9
    top_k: int = 40
    num_predict: int = 4096
    num_ctx: int = 8192
    repeat_penalty: float = 1.1
    
    # Analysis settings
    min_confidence_score: float = 0.7
    max_content_length: int = 50000  # characters
    content_sample_size: int = 5000  # characters for analysis
    
    # Vietnamese specific
    language_detection_threshold: float = 0.8
    vietnamese_keywords: list = None
    
    def __post_init__(self):
        """Initialize Vietnamese keywords if not provided"""
        if self.vietnamese_keywords is None:
            self.vietnamese_keywords = [
                "tin tức", "báo chí", "thông tin", "bài viết",
                "tiêu đề", "nội dung", "tác giả", "ngày đăng",
                "chuyên mục", "danh mục", "trang chủ", "liên kết"
            ]
    
    @classmethod
    def from_env(cls) -> 'AnalysisConfig':
        """Create configuration from environment variables"""
        return cls(
            temperature=float(os.getenv("GWEN3_TEMPERATURE", "0.1")),
            top_p=float(os.getenv("GWEN3_TOP_P", "0.9")),
            top_k=int(os.getenv("GWEN3_TOP_K", "40")),
            num_predict=int(os.getenv("GWEN3_NUM_PREDICT", "4096")),
            num_ctx=int(os.getenv("GWEN3_NUM_CTX", "8192")),
            repeat_penalty=float(os.getenv("GWEN3_REPEAT_PENALTY", "1.1")),
            min_confidence_score=float(os.getenv("GWEN3_MIN_CONFIDENCE", "0.7")),
            max_content_length=int(os.getenv("GWEN3_MAX_CONTENT", "50000")),
            content_sample_size=int(os.getenv("GWEN3_SAMPLE_SIZE", "5000"))
        )

@dataclass
class LoggingConfig:
    """Logging configuration for GWEN-3 client"""
    
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Create configuration from environment variables"""
        level_str = os.getenv("GWEN3_LOG_LEVEL", "INFO").upper()
        level = LogLevel(level_str) if level_str in LogLevel.__members__ else LogLevel.INFO
        
        return cls(
            level=level,
            format=os.getenv("GWEN3_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file_path=os.getenv("GWEN3_LOG_FILE"),
            max_file_size=int(os.getenv("GWEN3_LOG_MAX_SIZE", str(10 * 1024 * 1024))),
            backup_count=int(os.getenv("GWEN3_LOG_BACKUP_COUNT", "5"))
        )

class GWEN3Config:
    """Main configuration class for GWEN-3 client"""
    
    def __init__(self):
        self.ollama = OllamaConfig.from_env()
        self.analysis = AnalysisConfig.from_env()
        self.logging = LoggingConfig.from_env()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "ollama": {
                "base_url": self.ollama.base_url,
                "timeout": self.ollama.timeout,
                "max_retries": self.ollama.max_retries,
                "retry_delay": self.ollama.retry_delay,
                "model_name": self.ollama.model_name,
                "max_concurrent_requests": self.ollama.max_concurrent_requests,
                "connection_pool_size": self.ollama.connection_pool_size,
                "keep_alive_timeout": self.ollama.keep_alive_timeout
            },
            "analysis": {
                "temperature": self.analysis.temperature,
                "top_p": self.analysis.top_p,
                "top_k": self.analysis.top_k,
                "num_predict": self.analysis.num_predict,
                "num_ctx": self.analysis.num_ctx,
                "repeat_penalty": self.analysis.repeat_penalty,
                "min_confidence_score": self.analysis.min_confidence_score,
                "max_content_length": self.analysis.max_content_length,
                "content_sample_size": self.analysis.content_sample_size,
                "vietnamese_keywords": self.analysis.vietnamese_keywords
            },
            "logging": {
                "level": self.logging.level.value,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count
            }
        }
    
    def validate(self) -> bool:
        """Validate configuration settings"""
        try:
            # Validate Ollama settings
            assert self.ollama.timeout > 0, "Timeout must be positive"
            assert self.ollama.max_retries >= 0, "Max retries cannot be negative"
            assert self.ollama.retry_delay > 0, "Retry delay must be positive"
            
            # Validate analysis settings
            assert 0.0 <= self.analysis.temperature <= 2.0, "Temperature must be between 0.0 and 2.0"
            assert 0.0 <= self.analysis.top_p <= 1.0, "Top-p must be between 0.0 and 1.0"
            assert self.analysis.top_k > 0, "Top-k must be positive"
            assert self.analysis.num_predict > 0, "Num predict must be positive"
            assert self.analysis.num_ctx > 0, "Num context must be positive"
            assert 0.0 <= self.analysis.min_confidence_score <= 1.0, "Min confidence must be between 0.0 and 1.0"
            
            return True
            
        except AssertionError as e:
            raise ValueError(f"Configuration validation failed: {e}")

# Global configuration instance
config = GWEN3Config()