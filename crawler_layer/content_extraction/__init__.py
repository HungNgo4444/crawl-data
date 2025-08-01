"""
Content Extraction Module
Smart content extraction with multiple strategies
"""

from .strategy_router import StrategyRouter
from .scrapy_engine import ScrapyEngine
from .content_processor import ContentProcessor

__all__ = ['StrategyRouter', 'ScrapyEngine', 'ContentProcessor']