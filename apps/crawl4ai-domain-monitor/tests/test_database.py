import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.utils.database import DatabaseManager
from src.integration.domain_database import DomainDatabaseManager


class TestDatabaseManager:
    """Test database manager functionality"""
    
    @pytest.fixture
    def db_manager(self):
        return DatabaseManager(
            container_name="test_postgres",
            database="test_db",
            user="test_user"
        )
    
    @patch('subprocess.run')
    def test_execute_sql_success(self, mock_run, db_manager):
        # Mock successful subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "id | name | status\n----+------+--------\n 1 | test | active\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = db_manager.execute_sql("SELECT * FROM test_table;")
        
        assert result is not None
        assert len(result) > 0
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_execute_sql_error(self, mock_run, db_manager):
        # Mock failed subprocess response
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: relation 'test_table' does not exist"
        mock_run.return_value = mock_result
        
        result = db_manager.execute_sql("SELECT * FROM nonexistent_table;")
        
        assert result is None
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_execute_sql_timeout(self, mock_run, db_manager):
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("psql", 30)
        
        result = db_manager.execute_sql("SELECT * FROM test_table;")
        
        assert result is None
        mock_run.assert_called_once()
    
    def test_parse_psql_output(self, db_manager):
        output = """id | name | status
----+------+--------
 1 | test | active
 2 | demo | inactive
(2 rows)"""
        
        result = db_manager._parse_psql_output(output)
        
        assert len(result) == 2
        assert result[0]['id'] == '1'
        assert result[0]['name'] == 'test'
        assert result[0]['status'] == 'active'
        assert result[1]['id'] == '2'
        assert result[1]['name'] == 'demo'
        assert result[1]['status'] == 'inactive'
    
    def test_parse_psql_output_empty(self, db_manager):
        output = "(0 rows)"
        
        result = db_manager._parse_psql_output(output)
        
        assert result == []
    
    @patch('builtins.open')
    @patch.object(DatabaseManager, 'execute_sql')
    def test_run_migration(self, mock_execute, mock_open, db_manager):
        # Mock file content
        mock_file = Mock()
        mock_file.read.return_value = "CREATE TABLE test_table (id SERIAL);"
        mock_open.return_value.__enter__.return_value = mock_file
        
        mock_execute.return_value = [{'success': True}]
        
        result = db_manager.run_migration("/path/to/migration.sql")
        
        assert result is True
        mock_open.assert_called_once_with("/path/to/migration.sql", 'r', encoding='utf-8')
        mock_execute.assert_called_once()
    
    @patch.object(DatabaseManager, 'execute_sql')
    def test_test_connection_success(self, mock_execute, db_manager):
        mock_execute.return_value = [{'test': '1'}]
        
        result = db_manager.test_connection()
        
        assert result is True
        mock_execute.assert_called_once_with("SELECT 1 as test;")
    
    @patch.object(DatabaseManager, 'execute_sql')
    def test_test_connection_failure(self, mock_execute, db_manager):
        mock_execute.return_value = None
        
        result = db_manager.test_connection()
        
        assert result is False


class TestDomainDatabaseManager:
    """Test domain database manager functionality"""
    
    @pytest.fixture
    def mock_db_manager(self):
        return Mock(spec=DatabaseManager)
    
    @pytest.fixture
    def domain_db_manager(self, mock_db_manager):
        return DomainDatabaseManager(mock_db_manager)
    
    def test_load_domain_configs_success(self, domain_db_manager, mock_db_manager):
        # Mock database response
        mock_db_manager.execute_sql.return_value = [
            {
                'id': '1',
                'name': 'vnexpress.net',
                'display_name': 'VnExpress',
                'base_url': 'https://vnexpress.net',
                'rss_feeds': '["https://vnexpress.net/rss.xml"]',
                'sitemaps': '["https://vnexpress.net/sitemap.xml"]',
                'css_selectors': '{}',
                'status': 'ACTIVE',
                'created_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T00:00:00',
                'url_example': 'https://vnexpress.net/article-123.html'
            }
        ]
        
        configs = domain_db_manager.load_domain_configs()
        
        assert len(configs) == 1
        assert configs[0].id == 1
        assert configs[0].name == 'vnexpress.net'
        assert configs[0].display_name == 'VnExpress'
        assert len(configs[0].rss_feeds) == 1
        assert len(configs[0].monitoring_pages) >= 1
        assert len(configs[0].url_patterns) > 0
        assert len(configs[0].exclude_patterns) > 0
    
    def test_load_domain_configs_empty(self, domain_db_manager, mock_db_manager):
        mock_db_manager.execute_sql.return_value = []
        
        configs = domain_db_manager.load_domain_configs()
        
        assert configs == []
    
    def test_load_domain_configs_error(self, domain_db_manager, mock_db_manager):
        mock_db_manager.execute_sql.return_value = None
        
        configs = domain_db_manager.load_domain_configs()
        
        assert configs == []
    
    def test_parse_json_field_list(self, domain_db_manager):
        # Test list string parsing
        json_str = '["url1", "url2", "url3"]'
        result = domain_db_manager._parse_json_field(json_str)
        
        assert result == ["url1", "url2", "url3"]
    
    def test_parse_json_field_empty(self, domain_db_manager):
        # Test empty cases
        assert domain_db_manager._parse_json_field('[]') == []
        assert domain_db_manager._parse_json_field('{}') == []
        assert domain_db_manager._parse_json_field('') == []
    
    def test_parse_json_field_single_value(self, domain_db_manager):
        result = domain_db_manager._parse_json_field('single_value')
        
        assert result == ['single_value']
    
    def test_update_monitoring_metadata(self, domain_db_manager, mock_db_manager):
        mock_db_manager.execute_sql.return_value = [{'success': True}]
        
        metadata = {
            'last_monitored_at': '2024-01-01T12:00:00',
            'urls_discovered': 50
        }
        
        result = domain_db_manager.update_monitoring_metadata(1, metadata)
        
        assert result is True
        mock_db_manager.execute_sql.assert_called_once()
    
    def test_get_domain_by_id_found(self, domain_db_manager, mock_db_manager):
        mock_db_manager.execute_sql.return_value = [{
            'id': '1',
            'name': 'vnexpress.net',
            'display_name': 'VnExpress',
            'base_url': 'https://vnexpress.net',
            'rss_feeds': '[]',
            'sitemaps': '[]',
            'css_selectors': '{}',
            'status': 'ACTIVE',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00',
            'url_example': None
        }]
        
        config = domain_db_manager.get_domain_by_id(1)
        
        assert config is not None
        assert config.id == 1
        assert config.name == 'vnexpress.net'
    
    def test_get_domain_by_id_not_found(self, domain_db_manager, mock_db_manager):
        mock_db_manager.execute_sql.return_value = []
        
        config = domain_db_manager.get_domain_by_id(999)
        
        assert config is None


if __name__ == '__main__':
    pytest.main([__file__])