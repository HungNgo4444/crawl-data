"""
Unit tests for database manager and connection pooling
Tests database configuration, connection pooling, and health monitoring
Date: 2025-08-11
Author: James (Dev Agent)
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from storage_layer.database.database_manager import (
    DatabaseManager, get_database_manager, check_database_health
)


class TestDatabaseManager:
    """Test cases for DatabaseManager class"""
    
    def test_load_config_from_env_defaults(self):
        """Test loading default configuration from environment"""
        with patch.dict(os.environ, {}, clear=True):
            db_manager = DatabaseManager()
            config = db_manager.config
            
            assert config['host'] == 'localhost'
            assert config['port'] == 5432
            assert config['database'] == 'crawler_db'
            assert config['username'] == 'crawler_user'
            assert config['password'] == ''
            assert config['pool_size'] == 20
            assert config['max_overflow'] == 30
            assert config['pool_timeout'] == 30
            assert config['pool_recycle'] == 3600
            assert config['echo'] is False
    
    def test_load_config_from_env_custom(self):
        """Test loading custom configuration from environment"""
        env_vars = {
            'DB_HOST': 'custom-host',
            'DB_PORT': '5433', 
            'DB_NAME': 'custom_db',
            'DB_USER': 'custom_user',
            'DB_PASSWORD': 'custom_pass',
            'DB_POOL_SIZE': '15',
            'DB_MAX_OVERFLOW': '25',
            'DB_POOL_TIMEOUT': '45',
            'DB_POOL_RECYCLE': '7200',
            'DB_ECHO': 'true',
            'DB_APPLICATION_NAME': 'test_app'
        }
        
        with patch.dict(os.environ, env_vars):
            db_manager = DatabaseManager()
            config = db_manager.config
            
            assert config['host'] == 'custom-host'
            assert config['port'] == 5433
            assert config['database'] == 'custom_db'
            assert config['username'] == 'custom_user'
            assert config['password'] == 'custom_pass'
            assert config['pool_size'] == 15
            assert config['max_overflow'] == 25
            assert config['pool_timeout'] == 45
            assert config['pool_recycle'] == 7200
            assert config['echo'] is True
            assert config['application_name'] == 'test_app'
    
    def test_build_connection_url_no_password(self):
        """Test building connection URL without password"""
        config = {
            'username': 'testuser',
            'password': '',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb'
        }
        
        db_manager = DatabaseManager(config)
        url = db_manager._build_connection_url()
        
        expected = "postgresql://testuser@localhost:5432/testdb"
        assert url == expected
    
    def test_build_connection_url_with_password(self):
        """Test building connection URL with password"""
        config = {
            'username': 'testuser',
            'password': 'test@pass#123',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb'
        }
        
        db_manager = DatabaseManager(config)
        url = db_manager._build_connection_url()
        
        # Password should be URL encoded
        expected = "postgresql://testuser:test%40pass%23123@localhost:5432/testdb"
        assert url == expected
    
    @patch('storage_layer.database.database_manager.create_engine')
    def test_create_engine_with_proper_config(self, mock_create_engine):
        """Test engine creation with proper configuration"""
        config = {
            'username': 'testuser',
            'password': 'testpass',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'pool_size': 20,
            'max_overflow': 30,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'echo': False,
            'application_name': 'test_app'
        }
        
        db_manager = DatabaseManager(config)
        db_manager._create_engine()
        
        # Verify create_engine was called with correct parameters
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        
        assert 'postgresql://testuser:testpass@localhost:5432/testdb' in args
        assert kwargs['pool_size'] == 20
        assert kwargs['max_overflow'] == 30
        assert kwargs['pool_timeout'] == 30
        assert kwargs['pool_recycle'] == 3600
        assert kwargs['pool_pre_ping'] is True
        assert kwargs['echo'] is False
    
    def test_singleton_pattern(self):
        """Test that get_database_manager returns singleton instance"""
        # Clear global instance for test
        import storage_layer.database.database_manager
        storage_layer.database.database_manager._db_manager = None
        
        # Get two instances
        db1 = get_database_manager()
        db2 = get_database_manager()
        
        # Should be the same instance
        assert db1 is db2
    
    @patch('storage_layer.database.database_manager.DatabaseManager.get_session')
    def test_test_connection_success(self, mock_get_session):
        """Test successful connection test"""
        # Mock session and query result
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        db_manager = DatabaseManager()
        result = db_manager.test_connection()
        
        assert result is True
    
    @patch('storage_layer.database.database_manager.DatabaseManager.get_session')
    def test_test_connection_failure(self, mock_get_session):
        """Test connection test failure"""
        # Mock session to raise exception
        mock_get_session.side_effect = SQLAlchemyError("Connection failed")
        
        db_manager = DatabaseManager()
        result = db_manager.test_connection()
        
        assert result is False
    
    def test_get_pool_status_no_engine(self):
        """Test pool status when engine not initialized"""
        db_manager = DatabaseManager()
        status = db_manager.get_pool_status()
        
        assert status == {"status": "engine_not_initialized"}
    
    @patch('storage_layer.database.database_manager.DatabaseManager._create_engine')
    def test_get_pool_status_with_engine(self, mock_create_engine):
        """Test pool status with initialized engine"""
        # Mock engine and pool
        mock_pool = MagicMock()
        mock_pool.size.return_value = 20
        mock_pool.checkedin.return_value = 15
        mock_pool.checkedout.return_value = 5
        mock_pool.overflow.return_value = 2
        mock_pool.invalid.return_value = 0
        
        mock_engine = MagicMock()
        mock_engine.pool = mock_pool
        mock_create_engine.return_value = mock_engine
        
        db_manager = DatabaseManager()
        # Trigger engine creation
        _ = db_manager.engine
        
        status = db_manager.get_pool_status()
        
        expected_status = {
            "pool_size": 20,
            "checked_in": 15,
            "checked_out": 5,
            "overflow": 2,
            "invalid": 0,
            "total_connections": 20,
            "available_connections": 15
        }
        
        assert status == expected_status
    
    @patch('storage_layer.database.database_manager.DatabaseManager.get_session')
    def test_execute_migration_check_no_table(self, mock_get_session):
        """Test migration check when migrations table doesn't exist"""
        # Mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = False  # Table doesn't exist
        mock_session.execute.return_value = mock_result
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        db_manager = DatabaseManager()
        result = db_manager.execute_migration_check()
        
        assert result is False
    
    @patch('storage_layer.database.database_manager.DatabaseManager.get_session')
    def test_execute_migration_check_success(self, mock_get_session):
        """Test successful migration check"""
        # Mock session
        mock_session = MagicMock()
        
        # Mock two execute calls: table exists check and migration count
        mock_session.execute.side_effect = [
            MagicMock(scalar=lambda: True),   # Table exists
            MagicMock(scalar=lambda: 3)      # All 3 migrations applied
        ]
        
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        db_manager = DatabaseManager()
        result = db_manager.execute_migration_check()
        
        assert result is True


class TestHealthCheck:
    """Test cases for database health check functionality"""
    
    @patch('storage_layer.database.database_manager.get_database_manager')
    def test_check_database_health_success(self, mock_get_db_manager):
        """Test successful database health check"""
        # Mock database manager
        mock_db_manager = MagicMock()
        mock_db_manager.test_connection.return_value = True
        mock_db_manager.execute_migration_check.return_value = True
        mock_db_manager.get_pool_status.return_value = {
            "pool_size": 20,
            "checked_in": 15,
            "checked_out": 5
        }
        mock_get_db_manager.return_value = mock_db_manager
        
        health = check_database_health()
        
        assert health["connection_test"] is True
        assert health["migrations_applied"] is True
        assert health["overall_health"] == "healthy"
        assert "pool_status" in health
    
    @patch('storage_layer.database.database_manager.get_database_manager')
    def test_check_database_health_degraded(self, mock_get_db_manager):
        """Test degraded database health (connection ok, migrations missing)"""
        # Mock database manager
        mock_db_manager = MagicMock()
        mock_db_manager.test_connection.return_value = True
        mock_db_manager.execute_migration_check.return_value = False  # Migrations missing
        mock_db_manager.get_pool_status.return_value = {}
        mock_get_db_manager.return_value = mock_db_manager
        
        health = check_database_health()
        
        assert health["connection_test"] is True
        assert health["migrations_applied"] is False
        assert health["overall_health"] == "degraded"
    
    @patch('storage_layer.database.database_manager.get_database_manager')
    def test_check_database_health_unhealthy(self, mock_get_db_manager):
        """Test unhealthy database (connection failed)"""
        # Mock database manager
        mock_db_manager = MagicMock()
        mock_db_manager.test_connection.return_value = False  # Connection failed
        mock_db_manager.execute_migration_check.return_value = False
        mock_db_manager.get_pool_status.return_value = {}
        mock_get_db_manager.return_value = mock_db_manager
        
        health = check_database_health()
        
        assert health["connection_test"] is False
        assert health["migrations_applied"] is False
        assert health["overall_health"] == "unhealthy"
    
    @patch('storage_layer.database.database_manager.get_database_manager')
    def test_check_database_health_exception(self, mock_get_db_manager):
        """Test health check when exception occurs"""
        # Mock database manager to raise exception
        mock_db_manager = MagicMock()
        mock_db_manager.test_connection.side_effect = Exception("Database unavailable")
        mock_get_db_manager.return_value = mock_db_manager
        
        health = check_database_health()
        
        assert "error" in health
        assert health["error"] == "Database unavailable"
        assert health["overall_health"] == "unhealthy"


class TestContextManager:
    """Test cases for session context manager"""
    
    @patch('storage_layer.database.database_manager.DatabaseManager.session_factory')
    def test_session_context_manager_success(self, mock_session_factory):
        """Test successful session context manager usage"""
        # Mock session
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            session.query = MagicMock()
        
        # Verify session lifecycle
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
    
    @patch('storage_layer.database.database_manager.DatabaseManager.session_factory')
    def test_session_context_manager_exception(self, mock_session_factory):
        """Test session context manager with exception"""
        # Mock session
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        
        db_manager = DatabaseManager()
        
        try:
            with db_manager.get_session() as session:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify rollback was called on exception
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])