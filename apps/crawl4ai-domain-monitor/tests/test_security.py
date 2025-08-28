import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.utils.database import DatabaseManager


class TestDatabaseSecurity:
    """Test database security against SQL injection attacks"""
    
    @pytest.fixture
    def db_manager(self):
        return DatabaseManager(
            container_name="test_postgres",
            database="test_db", 
            user="test_user"
        )
    
    def test_sql_injection_prevention_string_param(self, db_manager):
        """Test that malicious string parameters are properly escaped"""
        # Common SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE url_tracking; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; DELETE FROM domains; --",
            "' OR 1=1 UNION SELECT password FROM users --",
            "Robert'; DROP TABLE students; --"  # Classic Little Bobby Tables
        ]
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "count\n------\n 0\n"
            mock_run.return_value = mock_result
            
            for malicious_input in malicious_inputs:
                # Test parameter escaping
                sql = "SELECT COUNT(*) FROM url_tracking WHERE original_url = %s;"
                params = (malicious_input,)
                
                # Should not throw exception and should properly escape
                result = db_manager.execute_sql(sql, params)
                
                # Verify subprocess was called
                mock_run.assert_called()
                
                # Get the actual SQL that was executed
                call_args = mock_run.call_args[0][0]  # First positional argument (cmd)
                executed_sql = call_args[-1]  # Last argument is the SQL command
                
                # Verify malicious input was properly escaped
                # The dangerous SQL should be inside quotes and escaped
                escaped_input = malicious_input.replace("'", "''")
                assert f"'{escaped_input}'" in executed_sql
                
                # Reset mock for next test
                mock_run.reset_mock()
    
    def test_sql_injection_prevention_integer_param(self, db_manager):
        """Test integer parameters are handled safely"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "id\n---\n 1\n"
            mock_run.return_value = mock_result
            
            # Test with legitimate integer
            sql = "SELECT id FROM domains WHERE id = %s;"
            params = (1,)
            
            result = db_manager.execute_sql(sql, params)
            
            # Verify integer was not quoted
            call_args = mock_run.call_args[0][0]
            executed_sql = call_args[-1]
            assert "WHERE id = 1;" in executed_sql
            assert "WHERE id = '1';" not in executed_sql
    
    def test_sql_injection_prevention_null_param(self, db_manager):
        """Test NULL parameters are handled safely"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "count\n------\n 5\n"
            mock_run.return_value = mock_result
            
            sql = "SELECT COUNT(*) FROM url_tracking WHERE last_error IS %s;"
            params = (None,)
            
            result = db_manager.execute_sql(sql, params)
            
            call_args = mock_run.call_args[0][0]
            executed_sql = call_args[-1]
            assert "WHERE last_error IS NULL;" in executed_sql
    
    def test_sql_injection_prevention_datetime_param(self, db_manager):
        """Test datetime parameters are handled safely"""
        from datetime import datetime
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "count\n------\n 3\n"
            mock_run.return_value = mock_result
            
            test_datetime = datetime(2024, 1, 15, 12, 30, 45)
            sql = "SELECT COUNT(*) FROM url_tracking WHERE created_at > %s;"
            params = (test_datetime,)
            
            result = db_manager.execute_sql(sql, params)
            
            call_args = mock_run.call_args[0][0]
            executed_sql = call_args[-1]
            assert "created_at > '2024-01-15T12:30:45';" in executed_sql
    
    def test_sql_injection_prevention_boolean_param(self, db_manager):
        """Test boolean parameters are handled safely"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "count\n------\n 2\n"
            mock_run.return_value = mock_result
            
            sql = "SELECT COUNT(*) FROM domains WHERE status = 'ACTIVE' AND verified = %s;"
            params = (True,)
            
            result = db_manager.execute_sql(sql, params)
            
            call_args = mock_run.call_args[0][0]
            executed_sql = call_args[-1]
            assert "verified = TRUE;" in executed_sql
    
    def test_sql_injection_prevention_multiple_params(self, db_manager):
        """Test multiple parameters including malicious ones"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "count\n------\n 0\n"
            mock_run.return_value = mock_result
            
            # Mix of safe and malicious parameters
            malicious_url = "'; DROP TABLE domains; SELECT * FROM url_tracking WHERE '1'='1"
            domain_id = 1
            
            sql = "SELECT COUNT(*) FROM url_tracking WHERE original_url = %s AND domain_id = %s;"
            params = (malicious_url, domain_id)
            
            result = db_manager.execute_sql(sql, params)
            
            call_args = mock_run.call_args[0][0]
            executed_sql = call_args[-1]
            
            # Verify malicious SQL was escaped
            assert "'''; DROP TABLE domains;" in executed_sql  # Single quotes escaped
            assert "domain_id = 1;" in executed_sql  # Integer not quoted
    
    def test_parameter_escaping_error_handling(self, db_manager):
        """Test error handling when parameter escaping fails"""
        
        # Test with object that cannot be safely converted
        class UnserializableObject:
            def __str__(self):
                raise Exception("Cannot serialize")
        
        sql = "SELECT * FROM domains WHERE data = %s;"
        params = (UnserializableObject(),)
        
        # Should return None when escaping fails (error is logged)
        result = db_manager.execute_sql(sql, params)
        assert result is None
    
    def test_no_params_sql_execution(self, db_manager):
        """Test that SQL without parameters still works"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "count\n------\n 42\n"
            mock_run.return_value = mock_result
            
            # SQL without parameters
            sql = "SELECT COUNT(*) FROM domains WHERE status = 'ACTIVE';"
            
            result = db_manager.execute_sql(sql)
            
            call_args = mock_run.call_args[0][0]
            executed_sql = call_args[-1]
            assert executed_sql == sql  # Should be unchanged
    
    def test_empty_params_tuple(self, db_manager):
        """Test with empty parameters tuple"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "test\n-----\n 1\n"
            mock_run.return_value = mock_result
            
            sql = "SELECT 1 as test;"
            params = ()
            
            result = db_manager.execute_sql(sql, params)
            
            call_args = mock_run.call_args[0][0]
            executed_sql = call_args[-1]
            assert executed_sql == sql
    
    def test_sql_injection_prevention_comprehensive(self, db_manager):
        """Comprehensive test with various SQL injection techniques"""
        injection_vectors = [
            # Classic injection
            "admin'--",
            "admin'/*",
            # Union-based injection
            "' UNION SELECT NULL--",
            "' UNION ALL SELECT NULL,NULL,NULL--",
            # Boolean-based injection
            "' AND '1'='1",
            "' AND '1'='2",
            # Time-based injection
            "'; WAITFOR DELAY '00:00:05'--",
            # Error-based injection
            "' AND (SELECT COUNT(*) FROM sysobjects)>0--",
            # Blind injection
            "' AND SUBSTRING((SELECT TOP 1 name FROM sysobjects),1,1)='a",
            # Second-order injection
            "admin'; INSERT INTO users VALUES ('hacker','password')--"
        ]
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "result\n-------\n safe\n"
            mock_run.return_value = mock_result
            
            for injection in injection_vectors:
                sql = "SELECT 'safe' as result WHERE username = %s;"
                params = (injection,)
                
                # Should execute safely without injection
                result = db_manager.execute_sql(sql, params)
                
                call_args = mock_run.call_args[0][0]
                executed_sql = call_args[-1]
                
                # Verify dangerous SQL keywords are escaped
                dangerous_keywords = ['DROP', 'INSERT', 'DELETE', 'UPDATE', 'UNION', 'SELECT']
                for keyword in dangerous_keywords:
                    if keyword in injection:
                        # Should not appear unescaped in final SQL
                        assert f"'{keyword}" not in executed_sql or f"''{keyword}" in executed_sql
                
                mock_run.reset_mock()


if __name__ == '__main__':
    pytest.main([__file__])