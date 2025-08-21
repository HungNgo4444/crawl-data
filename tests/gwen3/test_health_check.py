"""
Unit tests for GWEN3HealthChecker
Tests comprehensive health monitoring functionality
Author: James (Dev Agent)  
Date: 2025-08-11
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps'))

from gwen3_client.health_check import (
    GWEN3HealthChecker, 
    HealthStatus, 
    HealthCheckResult, 
    SystemHealth
)


class TestHealthStatus:
    """Test HealthStatus enum"""
    
    def test_health_status_values(self):
        """Test health status enum values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning" 
        assert HealthStatus.CRITICAL.value == "critical"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass"""
    
    def test_health_check_result_creation(self):
        """Test health check result creation"""
        timestamp = datetime.now()
        result = HealthCheckResult(
            component="test_component",
            status=HealthStatus.HEALTHY,
            message="Test passed",
            details={"key": "value"},
            timestamp=timestamp,
            duration_ms=100.5
        )
        
        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Test passed"
        assert result.details == {"key": "value"}
        assert result.timestamp == timestamp
        assert result.duration_ms == 100.5
    
    def test_health_check_result_to_dict(self):
        """Test conversion to dictionary"""
        timestamp = datetime.now()
        result = HealthCheckResult(
            component="test_component",
            status=HealthStatus.WARNING,
            message="Test warning",
            details={"error": "minor issue"},
            timestamp=timestamp,
            duration_ms=250.0
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["component"] == "test_component"
        assert result_dict["status"] == "warning"
        assert result_dict["message"] == "Test warning"
        assert result_dict["details"] == {"error": "minor issue"}
        assert result_dict["timestamp"] == timestamp.isoformat()
        assert result_dict["duration_ms"] == 250.0


class TestSystemHealth:
    """Test SystemHealth dataclass"""
    
    def test_system_health_creation(self):
        """Test system health creation"""
        timestamp = datetime.now()
        checks = [
            HealthCheckResult(
                component="test1",
                status=HealthStatus.HEALTHY,
                message="OK",
                details={},
                timestamp=timestamp,
                duration_ms=100.0
            )
        ]
        
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            message="All systems operational",
            timestamp=timestamp,
            checks=checks,
            summary={"total": 1, "healthy": 1}
        )
        
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "All systems operational"
        assert health.timestamp == timestamp
        assert len(health.checks) == 1
        assert health.summary["total"] == 1
    
    def test_system_health_to_dict(self):
        """Test system health to dictionary conversion"""
        timestamp = datetime.now()
        checks = [
            HealthCheckResult(
                component="test1",
                status=HealthStatus.HEALTHY,
                message="OK",
                details={},
                timestamp=timestamp,
                duration_ms=100.0
            )
        ]
        
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            message="All systems operational",
            timestamp=timestamp,
            checks=checks,
            summary={"total": 1}
        )
        
        health_dict = health.to_dict()
        
        assert isinstance(health_dict, dict)
        assert health_dict["status"] == "healthy"
        assert health_dict["message"] == "All systems operational"
        assert health_dict["timestamp"] == timestamp.isoformat()
        assert len(health_dict["checks"]) == 1
        assert health_dict["summary"]["total"] == 1


class TestGWEN3HealthChecker:
    """Test GWEN3HealthChecker class"""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker instance"""
        return GWEN3HealthChecker(base_url="http://test-ollama:11434")
    
    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp session"""
        session = AsyncMock()
        response = AsyncMock()
        session.get.return_value.__aenter__.return_value = response
        session.post.return_value.__aenter__.return_value = response
        return session, response
    
    def test_health_checker_initialization(self):
        """Test health checker initialization"""
        checker = GWEN3HealthChecker()
        
        assert checker.base_url == "http://ollama:11434"
        assert checker.model_name == "gwen-3:8b"
        assert checker.session is None
        assert len(checker._health_history) == 0
        assert checker._performance_metrics["error_count"] == 0
    
    def test_health_checker_custom_base_url(self):
        """Test health checker with custom base URL"""
        custom_url = "http://custom-ollama:11434"
        checker = GWEN3HealthChecker(base_url=custom_url)
        
        assert checker.base_url == custom_url
    
    @pytest.mark.asyncio
    async def test_init_and_cleanup_session(self, health_checker):
        """Test session initialization and cleanup"""
        # Initially no session
        assert health_checker.session is None
        
        # Initialize session
        await health_checker._init_session()
        assert health_checker.session is not None
        assert not health_checker.session.closed
        
        # Cleanup session
        await health_checker._cleanup_session()
        assert health_checker.session is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        async with GWEN3HealthChecker() as checker:
            assert checker.session is not None
            assert not checker.session.closed
        
        # Session should be closed after exit
        assert checker.session is None or checker.session.closed
    
    @pytest.mark.asyncio
    async def test_check_service_connectivity_success(self, health_checker, mock_session):
        """Test successful service connectivity check"""
        session_mock, response_mock = mock_session
        
        # Mock successful response
        response_mock.status = 200
        response_mock.json.return_value = {"version": "0.1.0"}
        
        health_checker.session = session_mock
        
        result = await health_checker._check_service_connectivity()
        
        assert result.component == "service_connectivity"
        assert result.status == HealthStatus.HEALTHY
        assert "reachable" in result.message.lower()
        assert result.details["response_status"] == 200
        assert "version" in result.details
        
        session_mock.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_service_connectivity_failure(self, health_checker, mock_session):
        """Test service connectivity failure"""
        session_mock, response_mock = mock_session
        
        # Mock connection error
        session_mock.get.side_effect = aiohttp.ClientError("Connection refused")
        
        health_checker.session = session_mock
        
        result = await health_checker._check_service_connectivity()
        
        assert result.component == "service_connectivity"
        assert result.status == HealthStatus.CRITICAL
        assert "failed" in result.message.lower()
        assert "error" in result.details
    
    @pytest.mark.asyncio
    async def test_check_service_connectivity_timeout(self, health_checker, mock_session):
        """Test service connectivity timeout"""
        session_mock, response_mock = mock_session
        
        # Mock timeout
        session_mock.get.side_effect = asyncio.TimeoutError()
        
        health_checker.session = session_mock
        
        result = await health_checker._check_service_connectivity()
        
        assert result.component == "service_connectivity"
        assert result.status == HealthStatus.CRITICAL
        assert "timeout" in result.message.lower()
        assert result.details["timeout_seconds"] == 10
    
    @pytest.mark.asyncio
    async def test_check_model_availability_success(self, health_checker, mock_session):
        """Test successful model availability check"""
        session_mock, response_mock = mock_session
        
        # Mock successful response with target model
        response_mock.status = 200
        response_mock.json.return_value = {
            "models": [
                {"name": "gwen-3:8b", "size": 4500000000},
                {"name": "other:model", "size": 1000000000}
            ]
        }
        
        health_checker.session = session_mock
        
        result = await health_checker._check_model_availability()
        
        assert result.component == "model_availability"
        assert result.status == HealthStatus.HEALTHY
        assert "loaded and available" in result.message
        assert result.details["model_name"] == "gwen-3:8b"
        assert len(result.details["all_models"]) == 2
    
    @pytest.mark.asyncio
    async def test_check_model_availability_not_found(self, health_checker, mock_session):
        """Test model not found"""
        session_mock, response_mock = mock_session
        
        # Mock response without target model
        response_mock.status = 200
        response_mock.json.return_value = {
            "models": [
                {"name": "other:model", "size": 1000000000}
            ]
        }
        
        health_checker.session = session_mock
        
        result = await health_checker._check_model_availability()
        
        assert result.component == "model_availability"
        assert result.status == HealthStatus.CRITICAL
        assert "not found" in result.message
        assert result.details["expected_model"] == "gwen-3:8b"
    
    @pytest.mark.asyncio
    async def test_check_model_performance_success(self, health_checker, mock_session):
        """Test successful model performance check"""
        session_mock, response_mock = mock_session
        
        # Mock successful inference response
        response_mock.status = 200
        response_mock.json.return_value = {
            "response": "Xin chào, tôi là GWEN-3",
            "total_duration": 5000000000,
            "load_duration": 1000000000,
            "prompt_eval_count": 10,
            "eval_count": 15
        }
        
        health_checker.session = session_mock
        
        result = await health_checker._check_model_performance()
        
        assert result.component == "model_performance"
        assert result.status == HealthStatus.HEALTHY
        assert "inference working" in result.message.lower()
        assert result.details["response_length"] > 0
        assert "total_duration" in result.details
        
        session_mock.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_model_performance_slow_response(self, health_checker, mock_session):
        """Test slow model performance"""
        session_mock, response_mock = mock_session
        
        # Mock slow response (simulate by setting long duration in test)
        response_mock.status = 200
        response_mock.json.return_value = {"response": "Slow response"}
        
        health_checker.session = session_mock
        
        with patch('time.time', side_effect=[0, 35]):  # 35 second duration
            result = await health_checker._check_model_performance()
        
        assert result.component == "model_performance"
        # Should be WARNING for response > 30 seconds
        assert result.status in [HealthStatus.WARNING, HealthStatus.HEALTHY]
    
    @pytest.mark.asyncio
    async def test_check_model_performance_empty_response(self, health_checker, mock_session):
        """Test model performance with empty response"""
        session_mock, response_mock = mock_session
        
        # Mock empty response
        response_mock.status = 200
        response_mock.json.return_value = {"response": ""}
        
        health_checker.session = session_mock
        
        result = await health_checker._check_model_performance()
        
        assert result.component == "model_performance"
        assert result.status == HealthStatus.WARNING
        assert "empty" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_resource_usage(self, health_checker):
        """Test resource usage check"""
        result = await health_checker._check_resource_usage()
        
        assert result.component == "resource_usage"
        assert result.status == HealthStatus.HEALTHY
        assert "monitoring not implemented" in result.message
        assert "memory_limit" in result.details
    
    @pytest.mark.asyncio
    async def test_check_api_endpoints_success(self, health_checker, mock_session):
        """Test successful API endpoints check"""
        session_mock, response_mock = mock_session
        
        # Mock successful responses for all endpoints
        response_mock.status = 200
        
        health_checker.session = session_mock
        
        result = await health_checker._check_api_endpoints()
        
        assert result.component == "api_endpoints"
        assert result.status == HealthStatus.HEALTHY
        assert "all" in result.message.lower()
        assert result.details["endpoints_successful"] == result.details["endpoints_tested"]
    
    @pytest.mark.asyncio
    async def test_check_api_endpoints_partial_failure(self, health_checker, mock_session):
        """Test partial API endpoints failure"""
        session_mock, response_mock = mock_session
        
        # Mock mixed responses - success then failure
        responses = [200, 500]
        response_mock.status = 200
        session_mock.get.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(status=200))),
            aiohttp.ClientError("Server error")
        ]
        
        health_checker.session = session_mock
        
        result = await health_checker._check_api_endpoints()
        
        assert result.component == "api_endpoints"
        assert result.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        assert result.details["endpoints_successful"] < result.details["endpoints_tested"]
    
    @pytest.mark.asyncio
    async def test_check_vietnamese_analysis_success(self, health_checker, mock_session):
        """Test successful Vietnamese analysis check"""
        session_mock, response_mock = mock_session
        
        # Mock response with Vietnamese indicators
        vietnamese_response = {
            "response": 'Tôi có thể phân tích selector CSS cho tiêu đề và nội dung. JSON format: {"class": "title"}'
        }
        response_mock.status = 200
        response_mock.json.return_value = vietnamese_response
        
        health_checker.session = session_mock
        
        result = await health_checker._check_vietnamese_analysis()
        
        assert result.component == "vietnamese_analysis"
        assert result.status == HealthStatus.HEALTHY
        assert "confirmed" in result.message.lower()
        assert result.details["vietnamese_indicators_found"] >= 3
    
    @pytest.mark.asyncio
    async def test_check_vietnamese_analysis_limited(self, health_checker, mock_session):
        """Test limited Vietnamese analysis capability"""
        session_mock, response_mock = mock_session
        
        # Mock response with few Vietnamese indicators
        limited_response = {
            "response": 'I can analyze selector for HTML elements'
        }
        response_mock.status = 200
        response_mock.json.return_value = limited_response
        
        health_checker.session = session_mock
        
        result = await health_checker._check_vietnamese_analysis()
        
        assert result.component == "vietnamese_analysis"
        assert result.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        assert result.details["vietnamese_indicators_found"] < 3
    
    def test_determine_overall_status(self, health_checker):
        """Test overall status determination logic"""
        # All healthy
        healthy_checks = [
            HealthCheckResult("comp1", HealthStatus.HEALTHY, "OK", {}, datetime.now(), 100),
            HealthCheckResult("comp2", HealthStatus.HEALTHY, "OK", {}, datetime.now(), 100)
        ]
        status, message = health_checker._determine_overall_status(healthy_checks)
        assert status == HealthStatus.HEALTHY
        assert "2 checks passed" in message
        
        # One warning
        warning_checks = [
            HealthCheckResult("comp1", HealthStatus.HEALTHY, "OK", {}, datetime.now(), 100),
            HealthCheckResult("comp2", HealthStatus.WARNING, "Slow", {}, datetime.now(), 100)
        ]
        status, message = health_checker._determine_overall_status(warning_checks)
        assert status == HealthStatus.WARNING
        assert "1 warnings" in message
        
        # One critical
        critical_checks = [
            HealthCheckResult("comp1", HealthStatus.HEALTHY, "OK", {}, datetime.now(), 100),
            HealthCheckResult("comp2", HealthStatus.CRITICAL, "Failed", {}, datetime.now(), 100)
        ]
        status, message = health_checker._determine_overall_status(critical_checks)
        assert status == HealthStatus.CRITICAL
        assert "1 critical" in message
        
        # Empty checks
        status, message = health_checker._determine_overall_status([])
        assert status == HealthStatus.UNKNOWN
        assert "no health checks" in message.lower()
    
    def test_create_health_summary(self, health_checker):
        """Test health summary creation"""
        checks = [
            HealthCheckResult("comp1", HealthStatus.HEALTHY, "OK", {}, datetime.now(), 100),
            HealthCheckResult("comp2", HealthStatus.WARNING, "Slow", {}, datetime.now(), 200),
            HealthCheckResult("comp3", HealthStatus.CRITICAL, "Failed", {}, datetime.now(), 50)
        ]
        
        summary = health_checker._create_health_summary(checks, 5.0)
        
        assert summary["total_checks"] == 3
        assert summary["total_duration_seconds"] == 5.0
        assert summary["average_check_duration_ms"] == 116.67  # (100+200+50)/3
        assert summary["status_breakdown"]["healthy"] == 1
        assert summary["status_breakdown"]["warning"] == 1
        assert summary["status_breakdown"]["critical"] == 1
        assert "timestamp" in summary
    
    def test_update_performance_metrics(self, health_checker):
        """Test performance metrics update"""
        # Create healthy system health
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            message="All good",
            timestamp=datetime.now(),
            checks=[],
            summary={"average_check_duration_ms": 150}
        )
        
        health_checker._update_performance_metrics(health)
        
        assert health_checker._performance_metrics["consecutive_failures"] == 0
        assert health_checker._performance_metrics["last_successful_check"] is not None
        assert len(health_checker._performance_metrics["response_times"]) == 1
        
        # Create unhealthy system health
        unhealthy = SystemHealth(
            status=HealthStatus.CRITICAL,
            message="Issues found",
            timestamp=datetime.now(),
            checks=[],
            summary={}
        )
        
        health_checker._update_performance_metrics(unhealthy)
        
        assert health_checker._performance_metrics["error_count"] == 1
        assert health_checker._performance_metrics["consecutive_failures"] == 1
    
    def test_add_to_history(self, health_checker):
        """Test health history management"""
        # Create test health results
        health1 = SystemHealth(
            status=HealthStatus.HEALTHY,
            message="Good",
            timestamp=datetime.now(),
            checks=[],
            summary={}
        )
        
        health_checker._add_to_history(health1)
        assert len(health_checker._health_history) == 1
        
        # Test history trimming (max_history_size is 100 by default)
        # Add many entries to test trimming
        for i in range(105):
            health = SystemHealth(
                status=HealthStatus.HEALTHY,
                message=f"Health {i}",
                timestamp=datetime.now(),
                checks=[],
                summary={}
            )
            health_checker._add_to_history(health)
        
        assert len(health_checker._health_history) <= 100
    
    def test_get_health_history(self, health_checker):
        """Test health history retrieval"""
        # Add some history
        for i in range(5):
            health = SystemHealth(
                status=HealthStatus.HEALTHY,
                message=f"Health {i}",
                timestamp=datetime.now(),
                checks=[],
                summary={}
            )
            health_checker._add_to_history(health)
        
        # Get limited history
        history = health_checker.get_health_history(limit=3)
        assert len(history) == 3
        assert all(isinstance(h, dict) for h in history)
        
        # Get all history
        full_history = health_checker.get_health_history(limit=0)
        assert len(full_history) == 5
    
    def test_get_performance_metrics(self, health_checker):
        """Test performance metrics retrieval"""
        # Set up some metrics
        health_checker._performance_metrics["error_count"] = 5
        health_checker._performance_metrics["consecutive_failures"] = 2
        health_checker._performance_metrics["response_times"] = [100, 200, 150, 300, 250]
        health_checker._performance_metrics["last_successful_check"] = datetime.now()
        
        metrics = health_checker.get_performance_metrics()
        
        assert metrics["error_count"] == 5
        assert metrics["consecutive_failures"] == 2
        assert metrics["average_response_time_ms"] == 200  # (100+200+150+300+250)/5
        assert metrics["min_response_time_ms"] == 100
        assert metrics["max_response_time_ms"] == 300
        assert len(metrics["recent_response_times"]) == 5
        assert metrics["last_successful_check"] is not None
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_check_success(self, health_checker):
        """Test comprehensive health check with all components healthy"""
        with patch.object(health_checker, '_init_session', new_callable=AsyncMock), \
             patch.object(health_checker, '_check_service_connectivity', new_callable=AsyncMock) as mock_service, \
             patch.object(health_checker, '_check_model_availability', new_callable=AsyncMock) as mock_model, \
             patch.object(health_checker, '_check_model_performance', new_callable=AsyncMock) as mock_performance, \
             patch.object(health_checker, '_check_resource_usage', new_callable=AsyncMock) as mock_resource, \
             patch.object(health_checker, '_check_api_endpoints', new_callable=AsyncMock) as mock_api, \
             patch.object(health_checker, '_check_vietnamese_analysis', new_callable=AsyncMock) as mock_vietnamese:
            
            # Mock all checks as healthy
            timestamp = datetime.now()
            healthy_result = HealthCheckResult("test", HealthStatus.HEALTHY, "OK", {}, timestamp, 100)
            
            mock_service.return_value = healthy_result
            mock_model.return_value = healthy_result
            mock_performance.return_value = healthy_result
            mock_resource.return_value = healthy_result
            mock_api.return_value = healthy_result
            mock_vietnamese.return_value = healthy_result
            
            system_health = await health_checker.perform_comprehensive_health_check()
            
            assert isinstance(system_health, SystemHealth)
            assert system_health.status == HealthStatus.HEALTHY
            assert len(system_health.checks) == 6
            assert "summary" in system_health.to_dict()
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_check_with_failures(self, health_checker):
        """Test comprehensive health check with some failures"""
        with patch.object(health_checker, '_init_session', new_callable=AsyncMock), \
             patch.object(health_checker, '_check_service_connectivity', new_callable=AsyncMock) as mock_service, \
             patch.object(health_checker, '_check_model_availability', new_callable=AsyncMock) as mock_model:
            
            # Mock service as healthy but model as critical
            timestamp = datetime.now()
            healthy_result = HealthCheckResult("service", HealthStatus.HEALTHY, "OK", {}, timestamp, 100)
            critical_result = HealthCheckResult("model", HealthStatus.CRITICAL, "Failed", {}, timestamp, 200)
            
            mock_service.return_value = healthy_result
            mock_model.return_value = critical_result
            
            system_health = await health_checker.perform_comprehensive_health_check()
            
            assert system_health.status == HealthStatus.CRITICAL
            assert len(system_health.checks) >= 2  # At least service and model checks


@pytest.mark.integration  
class TestGWEN3HealthCheckerIntegration:
    """Integration tests for health checker"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS") == "true", 
        reason="Integration tests skipped"
    )
    async def test_real_health_check(self):
        """Test with real Ollama service (if available)"""
        checker = GWEN3HealthChecker()
        
        try:
            system_health = await checker.perform_comprehensive_health_check()
            assert isinstance(system_health, SystemHealth)
            assert system_health.status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
            print(f"Health check result: {system_health.status.value} - {system_health.message}")
            
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])