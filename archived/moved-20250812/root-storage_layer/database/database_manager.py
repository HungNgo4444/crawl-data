"""
Database Manager with Connection Pooling
Enhanced database configuration for domain management and GWEN-3 analysis workers
Date: 2025-08-11
Author: James (Dev Agent)
"""

import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .models.domain_models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Enhanced Database Manager with optimized connection pooling
    Supports multiple services: API, Analysis Workers, Enhanced Crawlers
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize database manager with enhanced connection pooling
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config or self._load_config_from_env()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        
    def _load_config_from_env(self) -> Dict[str, Any]:
        """Load database configuration from environment variables"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', 'crawler_db'),
            'username': os.getenv('DB_USER', 'crawler_user'),
            'password': os.getenv('DB_PASSWORD', ''),
            'pool_size': int(os.getenv('DB_POOL_SIZE', '20')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '30')),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
            'echo': os.getenv('DB_ECHO', 'false').lower() == 'true',
            'application_name': os.getenv('DB_APPLICATION_NAME', 'domain_crawler_system')
        }
    
    def _build_connection_url(self) -> str:
        """Build PostgreSQL connection URL with proper encoding"""
        password = quote_plus(self.config['password']) if self.config['password'] else ''
        password_part = f":{password}" if password else ""
        
        return (
            f"postgresql://{self.config['username']}{password_part}@"
            f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )
    
    def _create_engine(self) -> Engine:
        """
        Create SQLAlchemy engine with optimized connection pooling
        
        Pool Configuration:
        - pool_size: 20 (base connections for normal load)
        - max_overflow: 30 (additional connections for peak load)  
        - Total max connections: 50 (within 16GB RAM constraint)
        - pool_timeout: 30s (reasonable wait time)
        - pool_recycle: 1 hour (prevent stale connections)
        """
        connection_url = self._build_connection_url()
        
        # Enhanced connection parameters for performance
        connect_args = {
            'application_name': self.config['application_name'],
            'connect_timeout': 10,
            'server_settings': {
                'timezone': 'UTC',
                'statement_timeout': '300000',  # 5 minutes
                'lock_timeout': '30000',        # 30 seconds
            }
        }
        
        engine = create_engine(
            connection_url,
            poolclass=QueuePool,
            pool_size=self.config['pool_size'],
            max_overflow=self.config['max_overflow'],
            pool_timeout=self.config['pool_timeout'],
            pool_recycle=self.config['pool_recycle'],
            pool_pre_ping=True,  # Validate connections before use
            echo=self.config['echo'],
            connect_args=connect_args,
            # Performance optimizations
            isolation_level="READ_COMMITTED",
            executemany_mode="batch",
        )
        
        logger.info(
            f"Database engine created with pool_size={self.config['pool_size']}, "
            f"max_overflow={self.config['max_overflow']}, "
            f"total_max_connections={self.config['pool_size'] + self.config['max_overflow']}"
        )
        
        return engine
    
    @property 
    def engine(self) -> Engine:
        """Get or create database engine"""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get or create session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions with automatic cleanup
        
        Usage:
            with db_manager.get_session() as session:
                # Use session here
                pass
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self, drop_existing: bool = False):
        """
        Create all database tables
        
        Args:
            drop_existing: Whether to drop existing tables first
        """
        try:
            if drop_existing:
                logger.warning("Dropping all existing tables")
                Base.metadata.drop_all(self.engine)
            
            logger.info("Creating database tables")
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
            
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test database connection and return success status
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.get_session() as session:
                # Test basic query
                result = session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
                if test_value == 1:
                    logger.info("Database connection test successful")
                    return True
                else:
                    logger.error("Database connection test failed - unexpected result")
                    return False
                    
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current connection pool status for monitoring
        
        Returns:
            dict: Pool statistics including utilization metrics
        """
        if self._engine is None:
            return {"status": "engine_not_initialized"}
        
        pool = self.engine.pool
        
        # Calculate utilization metrics
        total_connections = pool.checkedin() + pool.checkedout()
        max_connections = pool.size() + pool.overflow()
        utilization_pct = (total_connections / max_connections * 100) if max_connections > 0 else 0
        
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "total_connections": total_connections,
            "available_connections": pool.checkedin(),
            "max_connections": max_connections,
            "utilization_percent": round(utilization_pct, 2),
            "is_healthy": utilization_pct < 90  # Flag high utilization
        }
    
    def close_all_connections(self):
        """Close all database connections and clean up"""
        if self._engine:
            logger.info("Closing all database connections")
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    def execute_migration_check(self) -> bool:
        """
        Check if database schema is up to date
        
        Returns:
            bool: True if migrations are applied, False otherwise
        """
        try:
            with self.get_session() as session:
                # Check if schema_migrations table exists
                result = session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'schema_migrations'
                    );
                """))
                
                migrations_table_exists = result.scalar()
                
                if not migrations_table_exists:
                    logger.warning("schema_migrations table not found - migrations not applied")
                    return False
                
                # Check if core migrations are applied
                result = session.execute(text("""
                    SELECT COUNT(*) FROM schema_migrations 
                    WHERE version IN ('001_initial_domain_schema', '002_add_domain_indexes', '003_foreign_key_constraints');
                """))
                
                applied_migrations = result.scalar()
                
                if applied_migrations >= 3:
                    logger.info("Core database migrations are applied")
                    return True
                else:
                    logger.warning(f"Only {applied_migrations}/3 core migrations applied")
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    """
    Get global database manager instance (singleton pattern)
    
    Args:
        config: Optional database configuration
        
    Returns:
        DatabaseManager: Global database manager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
    
    return _db_manager


def get_session():
    """
    Convenience function to get database session
    
    Usage:
        with get_session() as session:
            # Use session here
            pass
    """
    return get_database_manager().get_session()


# Connection pool health check for monitoring
def check_database_health() -> Dict[str, Any]:
    """
    Comprehensive database health check for monitoring systems
    
    Returns:
        dict: Database health status and metrics
    """
    db_manager = get_database_manager()
    
    health_status = {
        "timestamp": os.environ.get("REQUEST_TIME", "unknown"),
        "connection_test": False,
        "migrations_applied": False,
        "pool_status": {},
        "overall_health": "unhealthy"
    }
    
    try:
        # Test connection
        health_status["connection_test"] = db_manager.test_connection()
        
        # Check migrations
        health_status["migrations_applied"] = db_manager.execute_migration_check()
        
        # Get pool status
        health_status["pool_status"] = db_manager.get_pool_status()
        
        # Determine overall health
        if health_status["connection_test"] and health_status["migrations_applied"]:
            health_status["overall_health"] = "healthy"
        elif health_status["connection_test"]:
            health_status["overall_health"] = "degraded"
        else:
            health_status["overall_health"] = "unhealthy"
            
    except Exception as e:
        health_status["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    
    return health_status