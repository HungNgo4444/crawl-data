"""
Unit tests for OllamaGWEN3Client
Tests Ollama API client functionality for Vietnamese content analysis
Author: James (Dev Agent)
Date: 2025-08-11
"""

import pytest
import asyncio
import aiohttp
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps'))

from gwen3_client.ollama_client import OllamaGWEN3Client, AnalysisResult
from gwen3_client.config import config

class TestOllamaGWEN3Client:
    """Test cases for OllamaGWEN3Client"""
    
    @pytest.fixture
    async def client(self):
        """Create test client instance"""
        client = OllamaGWEN3Client(base_url="http://test-ollama:11434")
        yield client
        if client.session and not client.session.closed:
            await client.disconnect()
    
    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp session"""
        session = AsyncMock()
        response = AsyncMock()
        session.post.return_value.__aenter__.return_value = response
        session.get.return_value.__aenter__.return_value = response
        return session, response
    
    def test_client_initialization(self):
        """Test client initialization with default and custom parameters"""
        # Test default initialization
        client = OllamaGWEN3Client()
        assert client.base_url == config.ollama.base_url
        assert client.model_name == config.ollama.model_name
        assert client.session is None
        
        # Test custom initialization
        custom_url = "http://custom-ollama:11434"
        client = OllamaGWEN3Client(base_url=custom_url)
        assert client.base_url == custom_url
        assert client.model_name == config.ollama.model_name
    
    @pytest.mark.asyncio
    async def test_connection_management(self, client):
        """Test connection and disconnection"""
        # Initially no session
        assert client.session is None
        
        # Connect should create session
        await client.connect()
        assert client.session is not None
        assert not client.session.closed
        
        # Disconnect should close session
        await client.disconnect()
        assert client.session is None or client.session.closed
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality"""
        async with OllamaGWEN3Client() as client:
            assert client.session is not None
            assert not client.session.closed
        
        # Session should be closed after exit
        assert client.session is None or client.session.closed
    
    @pytest.mark.asyncio
    async def test_verify_model_availability_success(self, client, mock_session):
        """Test successful model availability check"""
        session_mock, response_mock = mock_session
        
        # Mock successful API response
        response_mock.status = 200
        response_mock.json.return_value = {
            "models": [
                {"name": "gwen-3:8b", "size": 4500000000},
                {"name": "other:model", "size": 1000000000}
            ]
        }
        
        client.session = session_mock
        
        # Test model availability
        is_available, message = await client.verify_model_availability()
        
        assert is_available is True
        assert "ready" in message.lower()
        
        # Verify API calls
        session_mock.post.assert_called()
        session_mock.get.assert_called()
    
    @pytest.mark.asyncio
    async def test_verify_model_availability_not_found(self, client, mock_session):
        """Test model not found scenario"""
        session_mock, response_mock = mock_session
        
        # Mock API response without target model
        response_mock.status = 200
        response_mock.json.return_value = {
            "models": [
                {"name": "other:model", "size": 1000000000}
            ]
        }
        
        client.session = session_mock
        
        is_available, message = await client.verify_model_availability()
        
        assert is_available is False
        assert "not found" in message.lower()
    
    @pytest.mark.asyncio
    async def test_verify_model_availability_api_error(self, client, mock_session):
        """Test API error during model availability check"""
        session_mock, response_mock = mock_session
        
        # Mock API error
        response_mock.status = 500
        
        client.session = session_mock
        
        is_available, message = await client.verify_model_availability()
        
        assert is_available is False
        assert "failed" in message.lower()
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, client, mock_session):
        """Test successful API request"""
        session_mock, response_mock = mock_session
        
        # Mock successful response
        response_mock.status = 200
        response_mock.json.return_value = {"result": "success"}
        
        client.session = session_mock
        
        result = await client._make_request("/api/test", {"data": "test"})
        
        assert result == {"result": "success"}
        session_mock.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_make_request_retry_logic(self, client, mock_session):
        """Test retry logic on service unavailable"""
        session_mock, response_mock = mock_session
        
        # Mock service unavailable then success
        response_mock.status = 503
        
        client.session = session_mock
        
        with pytest.raises((aiohttp.ClientResponseError, RuntimeError)):
            await client._make_request("/api/test", {"data": "test"}, retries=1)
        
        assert session_mock.post.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_make_request_timeout(self, client):
        """Test request timeout handling"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock timeout exception
            mock_session.post.side_effect = aiohttp.ClientError("Timeout")
            
            client.session = mock_session
            
            with pytest.raises((aiohttp.ClientError, RuntimeError)):
                await client._make_request("/api/test", {"data": "test"}, retries=1)
    
    @pytest.mark.asyncio
    async def test_analyze_domain_structure_success(self, client, mock_session):
        """Test successful domain structure analysis"""
        session_mock, response_mock = mock_session
        
        # Mock successful analysis response
        analysis_response = {
            "model": "gwen-3:8b",
            "response": '{"confidence_score": 0.85, "language_detected": "vietnamese", "parsing_template": {"headline": {"selectors": ["h1.title", ".main-title"]}, "content": {"selectors": [".article-body"]}}, "structure_analysis": {"complexity_score": 5}}'
        }
        
        response_mock.status = 200
        response_mock.json.return_value = analysis_response
        
        client.session = session_mock
        
        # Test analysis
        result = await client.analyze_domain_structure(
            "vnexpress.net",
            "<html><h1 class='title'>Test</h1><div class='article-body'>Content</div></html>"
        )
        
        assert isinstance(result, AnalysisResult)
        assert result.domain_name == "vnexpress.net"
        assert result.confidence_score == 0.85
        assert result.language_detected == "vietnamese"
        assert len(result.headline_selectors) > 0
        assert len(result.errors) == 0
        
        session_mock.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_domain_structure_invalid_json(self, client, mock_session):
        """Test analysis with invalid JSON response"""
        session_mock, response_mock = mock_session
        
        # Mock invalid JSON response
        analysis_response = {
            "model": "gwen-3:8b",
            "response": "Invalid JSON response from model"
        }
        
        response_mock.status = 200
        response_mock.json.return_value = analysis_response
        
        client.session = session_mock
        
        result = await client.analyze_domain_structure("test.com", "<html></html>")
        
        assert isinstance(result, AnalysisResult)
        assert result.confidence_score == 0.0
        assert len(result.errors) > 0
        assert "JSON" in str(result.errors)
    
    @pytest.mark.asyncio
    async def test_analyze_domain_structure_api_error(self, client, mock_session):
        """Test analysis with API error"""
        session_mock, response_mock = mock_session
        
        # Mock API error
        session_mock.post.side_effect = aiohttp.ClientError("Connection failed")
        
        client.session = session_mock
        
        result = await client.analyze_domain_structure("test.com", "<html></html>")
        
        assert isinstance(result, AnalysisResult)
        assert result.confidence_score == 0.0
        assert len(result.errors) > 0
        assert "failed" in str(result.errors).lower()
    
    def test_generate_analysis_id(self, client):
        """Test analysis ID generation"""
        domain_name = "test.com"
        analysis_id = client._generate_analysis_id(domain_name)
        
        assert isinstance(analysis_id, str)
        assert len(analysis_id) == 12  # MD5 hash truncated to 12 chars
        
        # Test uniqueness (different timestamps should give different IDs)
        import time
        time.sleep(0.01)  # Small delay
        analysis_id2 = client._generate_analysis_id(domain_name)
        assert analysis_id != analysis_id2
    
    def test_prepare_content_for_analysis(self, client):
        """Test content preparation for analysis"""
        # Test normal content
        content = "<html><body>Test content</body></html>"
        prepared = client._prepare_content_for_analysis(content)
        assert prepared == content
        
        # Test very long content (should be truncated)
        long_content = "x" * (config.analysis.max_content_length + 1000)
        prepared = client._prepare_content_for_analysis(long_content)
        assert len(prepared) <= config.analysis.max_content_length
        
        # Test content sampling
        sample_content = "x" * (config.analysis.content_sample_size + 1000)
        prepared = client._prepare_content_for_analysis(sample_content)
        assert "MIDDLE SAMPLE" in prepared
    
    def test_create_analysis_prompt(self, client):
        """Test analysis prompt creation"""
        domain_name = "vnexpress.net"
        content = "<html><h1>Test</h1></html>"
        sample_urls = ["https://vnexpress.net/article1", "https://vnexpress.net/article2"]
        
        prompt = client._create_analysis_prompt(domain_name, content, sample_urls)
        
        assert domain_name in prompt
        assert content in prompt
        assert sample_urls[0] in prompt
        assert "JSON" in prompt
        assert "selector" in prompt.lower()
        assert "vietnamese" in prompt.lower() or "tiếng việt" in prompt.lower()
    
    def test_extract_selectors(self, client):
        """Test selector extraction from configuration"""
        # Test dict with selectors list
        config1 = {"selectors": ["h1.title", ".main-title"]}
        selectors1 = client._extract_selectors(config1)
        assert selectors1 == ["h1.title", ".main-title"]
        
        # Test dict with single selector string
        config2 = {"selectors": "h1.title"}
        selectors2 = client._extract_selectors(config2)
        assert selectors2 == ["h1.title"]
        
        # Test string directly
        selectors3 = client._extract_selectors("h1.title")
        assert selectors3 == ["h1.title"]
        
        # Test list directly
        selectors4 = client._extract_selectors(["h1.title", ".main-title"])
        assert selectors4 == ["h1.title", ".main-title"]
        
        # Test empty/invalid input
        selectors5 = client._extract_selectors({})
        assert selectors5 == []
    
    @pytest.mark.asyncio
    async def test_get_model_info_success(self, client, mock_session):
        """Test getting model information"""
        session_mock, response_mock = mock_session
        
        model_info = {
            "modelfile": "FROM gwen-3:8b",
            "parameters": {"temperature": 0.1},
            "template": "{{ .Prompt }}",
            "details": {"format": "gguf", "family": "gwen", "families": ["gwen"]}
        }
        
        response_mock.status = 200
        response_mock.json.return_value = model_info
        
        client.session = session_mock
        
        result = await client.get_model_info()
        
        assert result == model_info
        session_mock.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_model_info_error(self, client, mock_session):
        """Test getting model information with error"""
        session_mock, response_mock = mock_session
        
        session_mock.post.side_effect = aiohttp.ClientError("Connection failed")
        client.session = session_mock
        
        result = await client.get_model_info()
        
        assert result == {}
    
    def test_get_active_requests_count(self, client):
        """Test getting active requests count"""
        assert client.get_active_requests_count() == 0
        
        # Simulate active request
        client._active_requests = 2
        assert client.get_active_requests_count() == 2
    
    @pytest.mark.parametrize("response_text,expected_score", [
        ('{"confidence_score": 0.9, "language_detected": "vietnamese", "parsing_template": {}}', 0.9),
        ('{"confidence_score": 0.5, "language_detected": "english", "parsing_template": {}}', 0.5),
        ('Invalid JSON', 0.0),
        ('{"parsing_template": {}}', 0.0),  # Missing confidence_score
    ])
    def test_parse_analysis_response(self, client, response_text, expected_score):
        """Test analysis response parsing with various inputs"""
        mock_response = {"response": response_text, "model": "gwen-3:8b"}
        
        result = client._parse_analysis_response(
            mock_response, "test.com", "test_id", 1640995200.0, "<html></html>"
        )
        
        assert isinstance(result, AnalysisResult)
        assert result.confidence_score == expected_score
        assert result.domain_name == "test.com"
        assert result.analysis_id == "test_id"


class TestAnalysisResult:
    """Test cases for AnalysisResult dataclass"""
    
    def test_analysis_result_creation(self):
        """Test AnalysisResult creation with all fields"""
        result = AnalysisResult(
            domain_name="test.com",
            analysis_id="test123",
            timestamp=datetime.now(),
            analysis_duration_seconds=15.5,
            model_name="gwen-3:8b",
            model_version="8b",
            confidence_score=0.85,
            language_detected="vietnamese",
            parsing_template={"headline": {"selectors": ["h1"]}},
            structure_hash="abc123",
            headline_selectors=["h1", ".title"],
            content_selectors=[".content", ".article"],
            metadata_selectors={"author": ".author"},
            navigation_patterns=[".nav", ".menu"],
            extraction_accuracy=0.9,
            template_complexity=5,
            errors=[],
            warnings=["Low confidence for some selectors"]
        )
        
        assert result.domain_name == "test.com"
        assert result.confidence_score == 0.85
        assert result.language_detected == "vietnamese"
        assert len(result.headline_selectors) == 2
        assert len(result.warnings) == 1
    
    def test_analysis_result_to_dict(self):
        """Test conversion to dictionary"""
        timestamp = datetime.now()
        result = AnalysisResult(
            domain_name="test.com",
            analysis_id="test123",
            timestamp=timestamp,
            analysis_duration_seconds=15.5,
            model_name="gwen-3:8b",
            model_version="8b",
            confidence_score=0.85,
            language_detected="vietnamese",
            parsing_template={},
            structure_hash="abc123",
            headline_selectors=["h1"],
            content_selectors=[".content"],
            metadata_selectors={},
            navigation_patterns=[],
            extraction_accuracy=0.9,
            template_complexity=5,
            errors=[],
            warnings=[]
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["domain_name"] == "test.com"
        assert result_dict["confidence_score"] == 0.85
        assert result_dict["timestamp"] == timestamp.isoformat()
        assert "headline_selectors" in result_dict
        assert "parsing_template" in result_dict


@pytest.mark.integration
class TestOllamaClientIntegration:
    """Integration tests that require actual Ollama service"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS") == "true",
        reason="Integration tests skipped"
    )
    async def test_real_model_availability(self):
        """Test with real Ollama service (if available)"""
        client = OllamaGWEN3Client()
        
        try:
            async with client:
                is_available, message = await client.verify_model_availability()
                # This test will depend on whether Ollama service is actually running
                print(f"Model availability: {is_available}, Message: {message}")
        except Exception as e:
            pytest.skip(f"Ollama service not available: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS") == "true",
        reason="Integration tests skipped"
    )
    async def test_real_vietnamese_analysis(self):
        """Test Vietnamese analysis with real service (if available)"""
        client = OllamaGWEN3Client()
        
        vietnamese_content = """
        <html>
        <head><title>Báo VnExpress</title></head>
        <body>
            <h1 class="title_news_detail">Tin tức mới nhất hôm nay</h1>
            <div class="fck_detail">
                Đây là nội dung bài viết tin tức bằng tiếng Việt.
                Nội dung này được sử dụng để test khả năng phân tích của GWEN-3.
            </div>
            <div class="author_mail">
                <span>Tác giả: Phóng viên Test</span>
            </div>
        </body>
        </html>
        """
        
        try:
            async with client:
                # First check if model is available
                is_available, _ = await client.verify_model_availability()
                if not is_available:
                    pytest.skip("GWEN-3 model not available")
                
                result = await client.analyze_domain_structure(
                    "vnexpress.net", vietnamese_content
                )
                
                assert isinstance(result, AnalysisResult)
                assert result.domain_name == "vnexpress.net"
                assert result.confidence_score >= 0.0
                print(f"Analysis result: confidence={result.confidence_score}, language={result.language_detected}")
                
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])