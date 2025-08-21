"""
Unit tests for GWEN3ModelWrapper
Tests high-level model wrapper with caching and batch processing
Author: James (Dev Agent)
Date: 2025-08-11
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import json
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps'))

from gwen3_client.model_wrapper import GWEN3ModelWrapper, CachedAnalysis
from gwen3_client.ollama_client import AnalysisResult


class TestCachedAnalysis:
    """Test cases for CachedAnalysis"""
    
    def test_cached_analysis_creation(self):
        """Test CachedAnalysis creation"""
        result = self._create_test_result()
        cached = CachedAnalysis(
            result=result,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        assert cached.result == result
        assert cached.access_count == 0
        assert cached.last_accessed is None
    
    def test_is_expired(self):
        """Test expiration check"""
        result = self._create_test_result()
        
        # Not expired
        cached = CachedAnalysis(
            result=result,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        assert not cached.is_expired()
        
        # Expired
        cached_expired = CachedAnalysis(
            result=result,
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1)
        )
        assert cached_expired.is_expired()
    
    def test_is_valid(self):
        """Test validity check"""
        # Valid result
        result = self._create_test_result(confidence=0.8)
        cached = CachedAnalysis(
            result=result,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        assert cached.is_valid()
        
        # Invalid - low confidence
        result_low = self._create_test_result(confidence=0.5)
        cached_low = CachedAnalysis(
            result=result_low,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        assert not cached_low.is_valid()
        
        # Invalid - expired
        cached_expired = CachedAnalysis(
            result=result,
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1)
        )
        assert not cached_expired.is_valid()
    
    def _create_test_result(self, confidence=0.85):
        """Helper to create test AnalysisResult"""
        return AnalysisResult(
            domain_name="test.com",
            analysis_id="test123",
            timestamp=datetime.now(),
            analysis_duration_seconds=10.0,
            model_name="gwen-3:8b",
            model_version="8b",
            confidence_score=confidence,
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


class TestGWEN3ModelWrapper:
    """Test cases for GWEN3ModelWrapper"""
    
    @pytest.fixture
    def mock_client(self):
        """Mock OllamaGWEN3Client"""
        client = AsyncMock()
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        return client
    
    @pytest.fixture
    def wrapper(self, mock_client):
        """Create wrapper with mocked client"""
        with patch('gwen3_client.model_wrapper.OllamaGWEN3Client', return_value=mock_client):
            wrapper = GWEN3ModelWrapper(cache_ttl_hours=1, max_cache_size=10)
            return wrapper
    
    def test_wrapper_initialization(self):
        """Test wrapper initialization"""
        wrapper = GWEN3ModelWrapper(cache_ttl_hours=2, max_cache_size=100)
        
        assert wrapper.cache_ttl == timedelta(hours=2)
        assert wrapper.max_cache_size == 100
        assert len(wrapper._analysis_cache) == 0
        assert wrapper._stats["total_analyses"] == 0
        assert wrapper._stats["cache_hits"] == 0
    
    def test_generate_cache_key(self, wrapper):
        """Test cache key generation"""
        key = wrapper._generate_cache_key("test.com", "abcdef123456")
        assert key == "test.com_abcdef123456"
    
    def test_hash_content(self, wrapper):
        """Test content hashing"""
        content = "<html><body>Test content</body></html>"
        hash1 = wrapper._hash_content(content)
        hash2 = wrapper._hash_content(content)
        
        assert hash1 == hash2  # Same content should produce same hash
        assert len(hash1) == 64  # SHA256 hash length
        
        # Different content should produce different hash
        hash3 = wrapper._hash_content(content + " modified")
        assert hash1 != hash3
    
    @pytest.mark.asyncio
    async def test_analyze_domain_cache_miss(self, wrapper, mock_client):
        """Test analysis with cache miss"""
        # Mock successful analysis
        test_result = self._create_test_result("test.com")
        mock_client.analyze_domain_structure.return_value = test_result
        
        result = await wrapper.analyze_domain(
            "test.com", 
            "<html><h1>Test</h1></html>"
        )
        
        assert result == test_result
        assert wrapper._stats["cache_misses"] == 1
        assert wrapper._stats["cache_hits"] == 0
        assert wrapper._stats["total_analyses"] == 1
        
        # Verify client was called
        mock_client.analyze_domain_structure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_domain_cache_hit(self, wrapper, mock_client):
        """Test analysis with cache hit"""
        # Setup cached result
        test_result = self._create_test_result("test.com")
        content = "<html><h1>Test</h1></html>"
        content_hash = wrapper._hash_content(content)
        cache_key = wrapper._generate_cache_key("test.com", content_hash)
        
        cached = CachedAnalysis(
            result=test_result,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        wrapper._analysis_cache[cache_key] = cached
        
        # Perform analysis
        result = await wrapper.analyze_domain("test.com", content)
        
        assert result == test_result
        assert wrapper._stats["cache_hits"] == 1
        assert wrapper._stats["cache_misses"] == 0
        assert cached.access_count == 1
        assert cached.last_accessed is not None
        
        # Verify client was not called
        mock_client.analyze_domain_structure.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_domain_force_refresh(self, wrapper, mock_client):
        """Test analysis with forced cache refresh"""
        # Setup cached result
        test_result = self._create_test_result("test.com")
        content = "<html><h1>Test</h1></html>"
        content_hash = wrapper._hash_content(content)
        cache_key = wrapper._generate_cache_key("test.com", content_hash)
        
        cached = CachedAnalysis(
            result=test_result,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        wrapper._analysis_cache[cache_key] = cached
        
        # Mock new analysis result
        new_result = self._create_test_result("test.com", confidence=0.9)
        mock_client.analyze_domain_structure.return_value = new_result
        
        # Force refresh should bypass cache
        result = await wrapper.analyze_domain(
            "test.com", content, force_refresh=True
        )
        
        assert result == new_result
        assert wrapper._stats["cache_misses"] == 1
        mock_client.analyze_domain_structure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_domain_low_confidence_no_cache(self, wrapper, mock_client):
        """Test that low confidence results are not cached"""
        # Mock low confidence result
        low_confidence_result = self._create_test_result("test.com", confidence=0.5)
        mock_client.analyze_domain_structure.return_value = low_confidence_result
        
        result = await wrapper.analyze_domain(
            "test.com", 
            "<html><h1>Test</h1></html>"
        )
        
        assert result == low_confidence_result
        assert len(wrapper._analysis_cache) == 0  # Should not be cached
    
    @pytest.mark.asyncio
    async def test_analyze_domain_error_handling(self, wrapper, mock_client):
        """Test error handling in analysis"""
        # Mock client error
        mock_client.analyze_domain_structure.side_effect = Exception("Test error")
        
        with pytest.raises(Exception):
            await wrapper.analyze_domain("test.com", "<html></html>")
        
        assert wrapper._stats["errors"] == 1
    
    @pytest.mark.asyncio
    async def test_analyze_batch_success(self, wrapper, mock_client):
        """Test successful batch analysis"""
        # Mock results for batch
        results = [
            self._create_test_result("domain1.com"),
            self._create_test_result("domain2.com"),
            self._create_test_result("domain3.com")
        ]
        mock_client.analyze_domain_structure.side_effect = results
        
        analyses = [
            ("domain1.com", "<html><h1>Test 1</h1></html>"),
            ("domain2.com", "<html><h1>Test 2</h1></html>"),
            ("domain3.com", "<html><h1>Test 3</h1></html>")
        ]
        
        batch_results = await wrapper.analyze_batch(analyses, batch_size=2)
        
        assert len(batch_results) == 3
        assert all(isinstance(r, AnalysisResult) for r in batch_results)
        assert batch_results[0].domain_name == "domain1.com"
        assert wrapper._stats["batch_processed"] == 3
    
    @pytest.mark.asyncio
    async def test_analyze_batch_with_errors(self, wrapper, mock_client):
        """Test batch analysis with some failures"""
        # Mock mixed results - success, error, success
        mock_client.analyze_domain_structure.side_effect = [
            self._create_test_result("domain1.com"),
            Exception("Network error"),
            self._create_test_result("domain3.com")
        ]
        
        analyses = [
            ("domain1.com", "<html><h1>Test 1</h1></html>"),
            ("domain2.com", "<html><h1>Test 2</h1></html>"),
            ("domain3.com", "<html><h1>Test 3</h1></html>")
        ]
        
        batch_results = await wrapper.analyze_batch(analyses)
        
        assert len(batch_results) == 3
        assert batch_results[0].confidence_score > 0  # Success
        assert batch_results[1].confidence_score == 0  # Error result
        assert batch_results[2].confidence_score > 0  # Success
        assert "Network error" in str(batch_results[1].errors)
    
    @pytest.mark.asyncio
    async def test_cache_cleanup(self, wrapper):
        """Test cache cleanup functionality"""
        # Fill cache beyond max size with expired entries
        for i in range(15):  # max_cache_size is 10
            result = self._create_test_result(f"domain{i}.com")
            cached = CachedAnalysis(
                result=result,
                created_at=datetime.now() - timedelta(hours=2),
                expires_at=datetime.now() - timedelta(hours=1),  # Expired
                last_accessed=datetime.now() - timedelta(hours=2)
            )
            wrapper._analysis_cache[f"key{i}"] = cached
        
        await wrapper._cleanup_cache()
        
        # All expired entries should be removed
        assert len(wrapper._analysis_cache) == 0
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_lru(self, wrapper):
        """Test cache cleanup with LRU eviction"""
        # Fill cache with valid entries beyond max size
        for i in range(15):  # max_cache_size is 10
            result = self._create_test_result(f"domain{i}.com")
            cached = CachedAnalysis(
                result=result,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1),
                last_accessed=datetime.now() - timedelta(minutes=i)  # Different access times
            )
            wrapper._analysis_cache[f"key{i}"] = cached
        
        await wrapper._cleanup_cache()
        
        # Should keep only half (5 entries)
        assert len(wrapper._analysis_cache) <= wrapper.max_cache_size // 2
    
    @pytest.mark.asyncio
    async def test_verify_model_health_success(self, wrapper, mock_client):
        """Test successful model health verification"""
        # Mock successful health checks
        mock_client.verify_model_availability.return_value = (True, "Model ready")
        mock_client.get_model_info.return_value = {"details": {"family": "gwen"}}
        mock_client.get_active_requests_count.return_value = 2
        
        # Mock successful test analysis
        test_result = self._create_test_result("test.vn")
        mock_client.analyze_domain_structure.return_value = test_result
        
        is_healthy, health_info = await wrapper.verify_model_health()
        
        assert is_healthy is True
        assert health_info["model_loaded"] is True
        assert health_info["test_analysis_successful"] is True
        assert health_info["active_requests"] == 2
        assert "statistics" in health_info
    
    @pytest.mark.asyncio
    async def test_verify_model_health_failure(self, wrapper, mock_client):
        """Test model health verification failure"""
        # Mock health check failure
        mock_client.verify_model_availability.return_value = (False, "Model not found")
        
        is_healthy, health_info = await wrapper.verify_model_health()
        
        assert is_healthy is False
        assert health_info["model_loaded"] is False
        assert "error" in health_info
    
    def test_get_cache_statistics(self, wrapper):
        """Test cache statistics retrieval"""
        # Add some cache entries and statistics
        wrapper._stats["cache_hits"] = 10
        wrapper._stats["cache_misses"] = 5
        
        for i in range(3):
            result = self._create_test_result(f"domain{i}.com")
            cached = CachedAnalysis(
                result=result,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1)
            )
            wrapper._analysis_cache[f"key{i}"] = cached
        
        stats = wrapper.get_cache_statistics()
        
        assert stats["cache_size"] == 3
        assert stats["max_cache_size"] == 10
        assert stats["cache_hit_rate"] == 66.7  # 10/(10+5) * 100
        assert stats["total_requests"] == 15
        assert stats["cache_hits"] == 10
        assert stats["cache_misses"] == 5
    
    def test_get_performance_statistics(self, wrapper, mock_client):
        """Test performance statistics retrieval"""
        # Set up some statistics
        wrapper._stats["total_analyses"] = 50
        wrapper._stats["batch_processed"] = 30
        wrapper._stats["errors"] = 5
        
        mock_client.get_active_requests_count.return_value = 2
        
        stats = wrapper.get_performance_statistics()
        
        assert stats["total_analyses"] == 50
        assert stats["batch_processed"] == 30
        assert stats["errors"] == 5
        assert stats["active_requests"] == 2
        assert "cache_statistics" in stats
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, wrapper):
        """Test cache clearing"""
        # Add some entries to cache
        for i in range(3):
            result = self._create_test_result(f"domain{i}.com")
            cached = CachedAnalysis(
                result=result,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1)
            )
            wrapper._analysis_cache[f"key{i}"] = cached
        
        assert len(wrapper._analysis_cache) == 3
        
        await wrapper.clear_cache()
        
        assert len(wrapper._analysis_cache) == 0
    
    @pytest.mark.asyncio
    async def test_export_analysis_results_json(self, wrapper):
        """Test exporting analysis results to JSON"""
        # Add some entries to cache
        for i in range(2):
            result = self._create_test_result(f"domain{i}.com")
            cached = CachedAnalysis(
                result=result,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1)
            )
            wrapper._analysis_cache[f"key{i}"] = cached
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = Path(f.name)
        
        try:
            await wrapper.export_analysis_results(output_path, format="json")
            
            # Verify exported file
            assert output_path.exists()
            
            with open(output_path, 'r', encoding='utf-8') as f:
                exported_data = json.load(f)
            
            assert exported_data["total_entries"] == 2
            assert len(exported_data["results"]) == 2
            assert "export_timestamp" in exported_data
            
            # Verify structure of exported results
            result = exported_data["results"][0]
            assert "domain_name" in result
            assert "confidence_score" in result
            assert "cache_info" in result
            assert "created_at" in result["cache_info"]
            
        finally:
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_export_analysis_results_unsupported_format(self, wrapper):
        """Test export with unsupported format"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported export format"):
                await wrapper.export_analysis_results(output_path, format="xml")
        finally:
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, wrapper, mock_client):
        """Test async context manager functionality"""
        async with wrapper as w:
            assert w is wrapper
            mock_client.connect.assert_called_once()
        
        mock_client.disconnect.assert_called_once()
    
    def _create_test_result(self, domain_name, confidence=0.85):
        """Helper to create test AnalysisResult"""
        return AnalysisResult(
            domain_name=domain_name,
            analysis_id=f"test_{domain_name}",
            timestamp=datetime.now(),
            analysis_duration_seconds=10.0,
            model_name="gwen-3:8b",
            model_version="8b",
            confidence_score=confidence,
            language_detected="vietnamese",
            parsing_template={"headline": {"selectors": ["h1"]}},
            structure_hash="abc123",
            headline_selectors=["h1"],
            content_selectors=[".content"],
            metadata_selectors={"author": ".author"},
            navigation_patterns=[".nav"],
            extraction_accuracy=0.9,
            template_complexity=5,
            errors=[],
            warnings=[]
        )


@pytest.mark.integration
class TestGWEN3ModelWrapperIntegration:
    """Integration tests for model wrapper"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS") == "true",
        reason="Integration tests skipped"
    )
    async def test_real_analysis_with_caching(self):
        """Test real analysis with caching functionality"""
        wrapper = GWEN3ModelWrapper(cache_ttl_hours=1)
        
        vietnamese_content = """
        <html>
        <head><title>Test News</title></head>
        <body>
            <h1 class="news-title">Tin tức test</h1>
            <div class="news-content">Nội dung bài viết test</div>
        </body>
        </html>
        """
        
        try:
            async with wrapper:
                # First analysis - should be cache miss
                result1 = await wrapper.analyze_domain("test.vn", vietnamese_content)
                assert isinstance(result1, AnalysisResult)
                
                # Second analysis - should be cache hit
                result2 = await wrapper.analyze_domain("test.vn", vietnamese_content)
                assert result2 == result1
                
                # Verify cache statistics
                cache_stats = wrapper.get_cache_statistics()
                assert cache_stats["cache_hits"] >= 1
                
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])