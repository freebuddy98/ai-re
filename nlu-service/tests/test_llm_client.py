"""
Unit tests for LLMClient component

Tests the interaction with the LLM service for UAR generation.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from nlu_service.core.llm_client import LLMClient
from nlu_service.models.uar import (
    UAR,
    UARIntent,
    UAREntity,
    UARRelation,
    UARLLMTrace,
    IntentName,
    EntityType,
    RelationType,
    UARStatus
)


@pytest.fixture
def llm_client():
    """Create an LLMClient instance for testing"""
    return LLMClient(
        default_model="gpt-4-turbo",
        timeout=10.0
    )


@pytest.fixture
def sample_llm_response():
    """Sample LLM service response"""
    return {
        "uar": {
            "original_message_ref": "msg_123",
            "user_id": "user_456",
            "channel_id": "channel_789",
            "raw_text_processed": "用户应该能够登录系统",
            "status": "SUCCESS",
            "intent": {
                "name": "PROPOSE_NEW_REI",
                "confidence": 0.85,
                "target_rei_id_if_modifying": None
            },
            "entities": [
                {
                    "temp_id": "ent-1",
                    "type": "FUNCTIONAL_REQUIREMENT",
                    "text_span": "用户登录",
                    "start_char": 0,
                    "end_char": 4,
                    "attributes": {
                        "name": "用户登录"
                    },
                    "is_ambiguous": False,
                    "ambiguity_details": []
                }
            ],
            "relations": [],
            "llm_trace": {
                "model_name_used": "gpt-4-turbo",
                "prompt_token_count": 100,
                "completion_token_count": 50
            }
        }
    }


class TestLLMClient:
    """Test LLMClient functionality"""
    
    def test_initialization(self):
        """Test LLMClient initialization"""
        client = LLMClient(
            default_model="gpt-3.5-turbo",
            timeout=30.0,
            default_temperature=0.5
        )
        
        assert client.default_model == "gpt-3.5-turbo"
        assert client.timeout == 30.0
        assert client.default_temperature == 0.5
    
    def test_url_normalization(self):
        """Test that model configuration is handled correctly"""
        # Test with different model
        client = LLMClient(default_model="claude-3-opus-20240229")
        assert client.default_model == "claude-3-opus-20240229"
        
        # Test default model
        client2 = LLMClient()
        assert client2.default_model == "gpt-4-turbo"
    
    # Old test methods removed - replaced with new call_llm_api tests below
    
    # Additional old test methods removed

    @pytest.mark.asyncio
    async def test_call_llm_api_success(self, llm_client):
        """Test successful LLM API call"""
        # Mock LiteLLM acompletion
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Test LLM response"))
        ]
        
        with patch('nlu_service.core.llm_client.litellm.acompletion', new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response
            
            # Call the method
            result = await llm_client.call_llm_api("Test prompt")
            
            # Verify the result
            assert result == "Test LLM response"
            
            # Verify the call was made correctly
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args
            assert call_args[1]['model'] == "gpt-4-turbo"
            assert call_args[1]['messages'][0]['content'] == "Test prompt"
            assert call_args[1]['temperature'] == 0.2
            assert call_args[1]['max_tokens'] == 2000

    @pytest.mark.asyncio
    async def test_call_llm_api_error(self, llm_client):
        """Test LLM API call when service returns error"""
        with patch('nlu_service.core.llm_client.litellm.acompletion', new_callable=AsyncMock) as mock_completion:
            mock_completion.side_effect = Exception("API Error")
            
            # Call the method
            result = await llm_client.call_llm_api("Test prompt")
            
            # Verify the result
            assert result is None

    @pytest.mark.asyncio
    async def test_call_llm_api_empty_response(self, llm_client):
        """Test LLM API call when response is empty"""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=""))
        ]
        
        with patch('nlu_service.core.llm_client.litellm.acompletion', new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response
            
            # Call the method
            result = await llm_client.call_llm_api("Test prompt")
            
            # Verify the result
            assert result is None

    @pytest.mark.asyncio
    async def test_call_llm_api_custom_parameters(self, llm_client):
        """Test LLM API call with custom parameters"""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Custom response"))
        ]
        
        with patch('nlu_service.core.llm_client.litellm.acompletion', new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response
            
            # Call with custom parameters
            result = await llm_client.call_llm_api(
                "Test prompt",
                model="gpt-3.5-turbo",
                temperature=0.5,
                max_tokens=1000
            )
            
            # Verify the result
            assert result == "Custom response"
            
            # Verify custom parameters were used
            call_args = mock_completion.call_args
            assert call_args[1]['model'] == "gpt-3.5-turbo"
            assert call_args[1]['temperature'] == 0.5
            assert call_args[1]['max_tokens'] == 1000

    def test_get_model_info(self, llm_client):
        """Test getting model configuration info"""
        info = llm_client.get_model_info()
        
        assert info['default_model'] == "gpt-4-turbo"
        assert info['default_temperature'] == 0.2
        assert info['default_max_tokens'] == 2000
        assert info['timeout'] == 10.0 