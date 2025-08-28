import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx

from src.integration.newspaper4k_client import Newspaper4kClient
from src.integration.queue_manager import QueueManager, QueuePriority
from src.integration.status_tracker import StatusTracker
from src.models.url_models import URLBatch, ProcessingResult, URLStatus


class TestNewspaper4kClient:
    """Test Newspaper4k API client"""
    
    @pytest.fixture
    def client(self):
        return Newspaper4kClient(
            base_url="http://localhost:8001",
            timeout=30,
            max_retries=2
        )
    
    @pytest.mark.asyncio
    async def test_extract_single_url_success(self, client):
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'title': 'Test Article',
            'content': 'Article content here...',
            'processing_time': 1.5
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await client.extract_single_url("https://vnexpress.net/article-123.html", 1)
            
            assert result.success is True
            assert result.url == "https://vnexpress.net/article-123.html"
            assert result.extracted_data is not None
            assert result.processing_time == 1.5
    
    @pytest.mark.asyncio
    async def test_extract_single_url_failure(self, client):
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await client.extract_single_url("https://vnexpress.net/article-123.html", 1)
            
            assert result.success is False
            assert "Timeout" in result.error
    
    @pytest.mark.asyncio
    async def test_extract_batch_urls(self, client):
        url_batch = URLBatch(
            domain_id=1,
            urls=["https://vnexpress.net/article-1.html", "https://vnexpress.net/article-2.html"],
            batch_id="test_batch_123"
        )
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [
                {
                    'url': 'https://vnexpress.net/article-1.html',
                    'success': True,
                    'data': {'title': 'Article 1'},
                    'processing_time': 1.2
                },
                {
                    'url': 'https://vnexpress.net/article-2.html',
                    'success': False,
                    'error': 'Parse error',
                    'processing_time': 0.5
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            results = await client.extract_batch_urls(url_batch)
            
            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False
            assert results[1].error == 'Parse error'
    
    @pytest.mark.asyncio
    async def test_check_service_health(self, client):
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'healthy',
            'version': '1.0.0',
            'uptime': 3600
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            is_healthy, health_data = await client.check_service_health()
            
            assert is_healthy is True
            assert health_data['status'] == 'healthy'
    
    def test_create_url_batch(self, client):
        urls = [
            "https://vnexpress.net/article-1.html",
            "https://vnexpress.net/article-2.html",
            "https://vnexpress.net/article-3.html"
        ]
        
        batches = client.create_url_batch(urls, domain_id=1, batch_size=2)
        
        assert len(batches) == 2
        assert len(batches[0].urls) == 2
        assert len(batches[1].urls) == 1
        assert all(batch.domain_id == 1 for batch in batches)


class TestQueueManager:
    """Test queue management functionality"""
    
    @pytest.fixture
    def mock_db_manager(self):
        return Mock()
    
    @pytest.fixture
    def queue_manager(self, mock_db_manager):
        return QueueManager(mock_db_manager, max_queue_size=1000)
    
    @pytest.mark.asyncio
    async def test_add_urls_to_queue(self, queue_manager, mock_db_manager):
        urls = [
            "https://vnexpress.net/article-1.html",
            "https://vnexpress.net/article-2.html"
        ]
        
        # Mock database responses
        mock_db_manager.execute_sql.side_effect = [
            [],  # URL not in queue
            [{'success': True}],  # Insert success
            [],  # URL not in queue
            [{'success': True}]   # Insert success
        ]
        
        count = await queue_manager.add_urls_to_queue(urls, domain_id=1, priority=QueuePriority.NORMAL)
        
        assert count == 2
        assert mock_db_manager.execute_sql.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_get_next_batch(self, queue_manager, mock_db_manager):
        # Mock database response
        mock_db_manager.execute_sql.side_effect = [
            [  # Get batch query
                {'id': 1, 'domain_id': 1, 'url': 'https://vnexpress.net/article-1.html', 'priority': 2},
                {'id': 2, 'domain_id': 1, 'url': 'https://vnexpress.net/article-2.html', 'priority': 2}
            ],
            [{'success': True}]  # Mark processing query
        ]
        
        batch = await queue_manager.get_next_batch(domain_id=1, batch_size=10)
        
        assert batch is not None
        assert batch.domain_id == 1
        assert len(batch.urls) == 2
        assert batch.priority == 2
    
    @pytest.mark.asyncio
    async def test_get_next_batch_empty(self, queue_manager, mock_db_manager):
        # Mock empty database response
        mock_db_manager.execute_sql.return_value = []
        
        batch = await queue_manager.get_next_batch(domain_id=1)
        
        assert batch is None
    
    @pytest.mark.asyncio
    async def test_mark_batch_completed(self, queue_manager, mock_db_manager):
        batch = URLBatch(
            domain_id=1,
            urls=["https://vnexpress.net/article-1.html", "https://vnexpress.net/article-2.html"],
            batch_id="test_batch"
        )
        
        success_urls = ["https://vnexpress.net/article-1.html"]
        failed_urls = ["https://vnexpress.net/article-2.html"]
        
        # Mock database responses
        mock_db_manager.execute_sql.side_effect = [
            [{'success': True}],  # Update successful
            [{'attempts': 1}],    # Get attempts for failed URL
            [{'success': True}]   # Update failed URL
        ]
        
        result = await queue_manager.mark_batch_completed(batch, success_urls, failed_urls)
        
        assert result is True
        assert mock_db_manager.execute_sql.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_get_queue_statistics(self, queue_manager, mock_db_manager):
        # Mock statistics data
        mock_db_manager.execute_sql.return_value = [
            {'status': 'pending', 'count': '50', 'avg_attempts': '1.0'},
            {'status': 'completed', 'count': '200', 'avg_attempts': '1.2'},
            {'status': 'failed', 'count': '10', 'avg_attempts': '3.0'}
        ]
        
        stats = await queue_manager.get_queue_statistics(domain_id=1)
        
        assert stats['pending'] == 50
        assert stats['completed'] == 200
        assert stats['failed'] == 10
        assert stats['total'] == 260
        assert stats['avg_attempts'] > 0


class TestStatusTracker:
    """Test status tracking functionality"""
    
    @pytest.fixture
    def mock_db_manager(self):
        return Mock()
    
    @pytest.fixture
    def status_tracker(self, mock_db_manager):
        return StatusTracker(mock_db_manager)
    
    @pytest.mark.asyncio
    async def test_update_processing_status(self, status_tracker, mock_db_manager):
        results = [
            ProcessingResult(
                url="https://vnexpress.net/article-1.html",
                success=True,
                processing_time=1.5,
                extracted_data={'title': 'Article 1'}
            ),
            ProcessingResult(
                url="https://vnexpress.net/article-2.html",
                success=False,
                error="Parse error"
            )
        ]
        
        # Mock database updates
        mock_db_manager.execute_sql.return_value = [{'success': True}]
        
        success = await status_tracker.update_processing_status(results)
        
        assert success is True
        assert mock_db_manager.execute_sql.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_domain_processing_stats(self, status_tracker, mock_db_manager):
        # Mock statistics data
        mock_db_manager.execute_sql.return_value = [
            {
                'status': 'completed',
                'count': '150',
                'avg_attempts': '1.2',
                'oldest_entry': '2024-01-01T00:00:00',
                'latest_processed': '2024-01-07T23:59:59'
            },
            {
                'status': 'failed',
                'count': '15',
                'avg_attempts': '2.8',
                'oldest_entry': '2024-01-02T00:00:00',
                'latest_processed': '2024-01-07T20:00:00'
            }
        ]
        
        stats = await status_tracker.get_domain_processing_stats(domain_id=1, days_back=7)
        
        assert stats['domain_id'] == 1
        assert stats['total_urls'] == 165
        assert stats['success_rate'] > 90  # 150/165
        assert 'completed' in stats['statuses']
        assert 'failed' in stats['statuses']
        assert stats['statuses']['completed']['count'] == 150
    
    @pytest.mark.asyncio
    async def test_get_recent_failures(self, status_tracker, mock_db_manager):
        # Mock failure data
        mock_db_manager.execute_sql.return_value = [
            {
                'original_url': 'https://vnexpress.net/failed-1.html',
                'domain_id': 1,
                'last_error': 'Timeout error',
                'processing_attempts': 3,
                'processed_at': '2024-01-07T12:00:00',
                'created_at': '2024-01-07T10:00:00'
            },
            {
                'original_url': 'https://vnexpress.net/failed-2.html',
                'domain_id': 1,
                'last_error': 'Parse error',
                'processing_attempts': 2,
                'processed_at': '2024-01-07T11:30:00',
                'created_at': '2024-01-07T09:30:00'
            }
        ]
        
        failures = await status_tracker.get_recent_failures(domain_id=1, limit=10)
        
        assert len(failures) == 2
        assert failures[0]['url'] == 'https://vnexpress.net/failed-1.html'
        assert failures[0]['error'] == 'Timeout error'
        assert failures[0]['attempts'] == 3
    
    @pytest.mark.asyncio
    async def test_get_url_status(self, status_tracker, mock_db_manager):
        # Mock URL status data
        mock_db_manager.execute_sql.return_value = [
            {
                'url_hash': 'abc123def456',
                'original_url': 'https://vnexpress.net/article-123.html',
                'normalized_url': 'https://vnexpress.net/article-123.html',
                'domain_id': 1,
                'status': 'completed',
                'created_at': '2024-01-07T10:00:00',
                'processed_at': '2024-01-07T10:05:00',
                'expires_at': '2024-02-07T10:00:00',
                'processing_attempts': 1,
                'last_error': None,
                'metadata': '{"processing_time": 1.5}'
            }
        ]
        
        status = await status_tracker.get_url_status("https://vnexpress.net/article-123.html")
        
        assert status is not None
        assert status['original_url'] == 'https://vnexpress.net/article-123.html'
        assert status['status'] == 'completed'
        assert status['processing_attempts'] == 1
    
    @pytest.mark.asyncio
    async def test_mark_urls_for_retry(self, status_tracker, mock_db_manager):
        urls = [
            "https://vnexpress.net/failed-1.html",
            "https://vnexpress.net/failed-2.html"
        ]
        
        mock_db_manager.execute_sql.return_value = [{'success': True}]
        
        count = await status_tracker.mark_urls_for_retry(urls, domain_id=1)
        
        assert count == 2
        mock_db_manager.execute_sql.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])