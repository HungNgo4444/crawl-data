"""
Data Access Layer
High-performance data access with smart caching
"""

from .article_repository import ArticleRepository
from .query_optimizer import QueryOptimizer

__all__ = ['ArticleRepository', 'QueryOptimizer']