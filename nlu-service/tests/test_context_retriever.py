"""
Unit tests for ContextRetriever component

Tests the DPSS API integration for fetching dialogue context.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from nlu_service.core.context_retriever import ContextRetriever
# DialogueContext is now a dictionary following YAML schema
from nlu_service.models.dialogue_context_utils import create_dialogue_context, create_conversation_turn


@pytest.fixture
def context_retriever():
    """Create a ContextRetriever instance for testing"""
    return ContextRetriever(dpss_base_url="http://test-dpss:8080", timeout=10.0)


@pytest.fixture
def sample_context_response():
    """Sample DPSS context response"""
    return {
        "channel_id": "channel_123",
        "retrieval_timestamp_utc": "2024-01-01T10:00:00Z",
        "recent_history": [
            {
                "turn_id": "turn_001",
                "speaker_type": "user",
                "user_id_if_user": "user_456",
                "utterance_text": "我们需要用户登录功能",
                "timestamp_utc": "2024-01-01T09:59:00Z"
            }
        ],
        "current_focus_reis_summary": [
            {
                "rei_id": "FR-001",
                "rei_type": "FunctionalRequirement",
                "name_or_summary": "用户登录功能",
                "status": "Drafting"
            }
        ],
        "active_questions": []
    }


class TestContextRetriever:
    """Test ContextRetriever functionality"""
    
    def test_initialization(self):
        """Test ContextRetriever initialization"""
        retriever = ContextRetriever(
            dpss_base_url="http://test-dpss:8080",
            timeout=30.0
        )
        
        assert retriever.dpss_base_url == "http://test-dpss:8080"
        assert retriever.dpss_context_url == "http://test-dpss:8080/api/v1/dpss/context"
        assert retriever.timeout == 30.0
        assert retriever.client is not None
    
    def test_url_normalization(self):
        """Test that base URL is normalized correctly"""
        # Test with trailing slash
        retriever = ContextRetriever(dpss_base_url="http://test-dpss:8080/")
        assert retriever.dpss_base_url == "http://test-dpss:8080"
        assert retriever.dpss_context_url == "http://test-dpss:8080/api/v1/dpss/context"
        
        # Test without trailing slash
        retriever = ContextRetriever(dpss_base_url="http://test-dpss:8080")
        assert retriever.dpss_base_url == "http://test-dpss:8080"
        assert retriever.dpss_context_url == "http://test-dpss:8080/api/v1/dpss/context"
    
    @pytest.mark.asyncio
    async def test_get_dialogue_context_success(self, context_retriever, sample_context_response):
        """Test successful context retrieval"""
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_context_response
        
        with patch.object(context_retriever.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the method
            result = await context_retriever.get_dialogue_context("channel_123", limit=5)
            
            # Verify the result
            assert result is not None
            assert isinstance(result, dict)
            assert result["channel_id"] == "channel_123"
            assert len(result["recent_history"]) == 1
            assert result["recent_history"][0]["utterance_text"] == "我们需要用户登录功能"
            
            # Verify the HTTP call was made correctly
            mock_get.assert_called_once_with(
                "http://test-dpss:8080/api/v1/dpss/context",
                params={"channel_id": "channel_123", "limit": 5},
                headers={"X-Request-ID": "nlu-context-channel_123"}
            )
    
    @pytest.mark.asyncio
    async def test_get_dialogue_context_not_found(self, context_retriever):
        """Test context retrieval when channel not found"""
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch.object(context_retriever.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the method
            result = await context_retriever.get_dialogue_context("nonexistent_channel")
            
            # Verify the result
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_dialogue_context_server_error(self, context_retriever):
        """Test context retrieval when server returns error"""
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch.object(context_retriever.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the method
            result = await context_retriever.get_dialogue_context("channel_123")
            
            # Verify the result
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_dialogue_context_network_error(self, context_retriever):
        """Test context retrieval when network error occurs"""
        with patch.object(context_retriever.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.RequestError("Network error")
            
            # Call the method
            result = await context_retriever.get_dialogue_context("channel_123")
            
            # Verify the result
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_dialogue_context_invalid_json(self, context_retriever):
        """Test context retrieval when DPSS returns invalid JSON"""
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        with patch.object(context_retriever.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the method
            result = await context_retriever.get_dialogue_context("channel_123")
            
            # Verify the result
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_dialogue_context_invalid_schema(self, context_retriever):
        """Test context retrieval when DPSS returns data that doesn't match schema"""
        # Invalid context response (missing required fields)
        invalid_response = {
            "channel_id": "channel_123",
            # missing other required fields
        }
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = invalid_response
        
        with patch.object(context_retriever.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call the method
            result = await context_retriever.get_dialogue_context("channel_123")
            
            # Verify the result - should return the raw data since validation is now handled elsewhere
            assert result is not None
            assert result == invalid_response
    
    @pytest.mark.asyncio
    async def test_close(self, context_retriever):
        """Test closing the HTTP client"""
        with patch.object(context_retriever.client, 'aclose', new_callable=AsyncMock) as mock_close:
            await context_retriever.close()
            mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_custom_limit_parameter(self, context_retriever, sample_context_response):
        """Test that custom limit parameter is passed correctly"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_context_response
        
        with patch.object(context_retriever.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Call with custom limit
            await context_retriever.get_dialogue_context("channel_123", limit=10)
            
            # Verify the correct limit was passed
            mock_get.assert_called_once_with(
                "http://test-dpss:8080/api/v1/dpss/context",
                params={"channel_id": "channel_123", "limit": 10},
                headers={"X-Request-ID": "nlu-context-channel_123"}
            )
    
    @pytest.mark.asyncio
    async def test_context_with_empty_history(self, context_retriever):
        """Test context retrieval with empty history"""
        empty_context_response = {
            "channel_id": "new_channel",
            "retrieval_timestamp_utc": "2024-01-01T10:00:00Z",
            "recent_history": [],
            "current_focus_reis_summary": [],
            "active_questions": []
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = empty_context_response
        
        with patch.object(context_retriever.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await context_retriever.get_dialogue_context("new_channel")
            
            assert result is not None
            assert isinstance(result, dict)
            assert result["channel_id"] == "new_channel"
            assert len(result["recent_history"]) == 0
            assert len(result["current_focus_reis_summary"]) == 0
            assert len(result["active_questions"]) == 0 