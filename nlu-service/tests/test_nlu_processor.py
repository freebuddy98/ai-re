"""
Unit tests for NLUProcessor component

Tests the main NLU processing functionality that coordinates all components.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from nlu_service.core.nlu_processor import NLUProcessor
from nlu_service.core.context_retriever import ContextRetriever
from nlu_service.core.prompt_builder import PromptBuilder
from nlu_service.core.llm_client import LLMClient
from nlu_service.core.response_validator import ResponseValidator
from nlu_service.models.uar import (
    UAR,
    UARIntent,
    UAREntity,
    UARLLMTrace,
    IntentName,
    EntityType,
    UARStatus
)
# DialogueContext is now a dictionary following YAML schema
from nlu_service.models.dialogue_context_utils import create_dialogue_context
from event_bus_framework import IEventBus


# Stub event bus for testing purposes
class StubEventBus(IEventBus):
    """A minimal in-memory event bus stub for unit tests"""

    def __init__(self):
        self.published: list[tuple[str, dict]] = []
        self.acknowledged: list[tuple[str, list[str]]] = []

    def publish(self, topic: str, message_data: dict):
        self.published.append((topic, message_data))
        # Simulate Redis Stream style ID
        return "1696402181123-0"

    def subscribe(self, *args, **kwargs):
        # Not needed for these unit tests
        raise NotImplementedError

    def acknowledge(self, topic: str, group_name: str, message_ids: list[str]):
        self.acknowledged.append((topic, message_ids))
        return len(message_ids)


@pytest.fixture
def nlu_processor():
    """Create an NLUProcessor instance wired with stub dependencies"""
    # Create core components with dummy external endpoints
    context_retriever = ContextRetriever(dpss_base_url="http://test-dpss:8080", timeout=10.0)
    prompt_builder = PromptBuilder()
    llm_client = LLMClient(default_model="gpt-4-turbo")
    response_validator = ResponseValidator()
    stub_bus = StubEventBus()

    # Use proper config structure
    config = {
        "topics": {
            "input": "user_message_raw",
            "output": "nlu_uar_result"
        },
        "consumer_group": "test-nlu-service"
    }

    return NLUProcessor(
        event_bus=stub_bus,
        context_retriever=context_retriever,
        prompt_builder=prompt_builder,
        llm_client=llm_client,
        response_validator=response_validator,
        config=config
    )


@pytest.fixture
def sample_raw_message():
    """Sample raw message payload dict following events.yml user_message_raw schema"""
    return {
        "meta": {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "source": "mattermost",
            "timestamp": 1609459200000
        },
        "user_id": "user_456",
        "username": "张三",
        "platform": "mattermost", 
        "channel_id": "channel_789",
        "content": {
            "text": "用户应该能够登录系统",
            "attachments": None
        },
        "raw_data": {}
    }


@pytest.fixture
def sample_dialogue_context():
    """Create a sample dialogue context following dialogue_context.yml schema"""
    return {
        "channel_id": "channel_789",
        "retrieval_timestamp_utc": "2024-01-01T10:00:00Z",
        "recent_history": [
            {
                "turn_id": "turn001",
                "speaker_type": "assistant",
                "utterance_text": "请告诉我您的需求",
                "timestamp_utc": "2024-01-01T09:58:00Z"
            },
            {
                "turn_id": "turn002", 
                "speaker_type": "user",
                "user_id_if_user": "user_456",
                "utterance_text": "我需要一个登录功能",
                "timestamp_utc": "2024-01-01T09:59:00Z",
                "simplified_uar_if_available": {
                    "intent_name": "ProposeNewREI",
                    "key_entity_types": ["FunctionalRequirement"]
                }
            }
        ],
        "current_focus_reis_summary": [
            {
                "rei_id": "FR-001",
                "rei_type": "FunctionalRequirement", 
                "name_or_summary": "用户登录功能",
                "status": "Drafting",
                "key_attributes_text": "允许用户通过用户名密码登录系统",
                "source_utterances_summary": ["我需要一个登录功能"]
            }
        ],
        "active_questions": []
    }


@pytest.fixture
def sample_uar():
    """Create a sample UAR for testing"""
    intent = UARIntent(
        name=IntentName.PROPOSENEWREI,
        confidence=0.85,
        target_rei_id_if_modifying=None
    )
    
    entity = UAREntity(
        temp_id="ent-1",
        type=EntityType.FUNCTIONALREQUIREMENT,
        text_span="用户登录",
        start_char=0,
        end_char=4,
        attributes={"name": "用户登录"},
        is_ambiguous=False
    )
    
    llm_trace = UARLLMTrace(
        model_name_used="gpt-4-turbo",
        prompt_token_count=100,
        completion_token_count=50
    )
    
    return UAR(
        original_message_ref="550e8400-e29b-41d4-a716-446655440000",
        user_id="user_456",
        channel_id="channel_789",
        raw_text_processed="用户应该能够登录系统",
        status=UARStatus.SUCCESS,
        intent=intent,
        entities=[entity],
        relations=[],
        llm_trace=llm_trace
    )


class TestNLUProcessor:
    """Test NLUProcessor functionality"""
    
    def test_initialization(self, nlu_processor):
        """Basic sanity check for NLUProcessor fixture"""
        assert nlu_processor.context_retriever is not None
        assert nlu_processor.prompt_builder is not None
        assert nlu_processor.llm_client is not None
        assert nlu_processor.response_validator is not None
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, nlu_processor, sample_raw_message, sample_dialogue_context, sample_uar):
        """Test successful message processing"""
        # Mock the context retriever
        with patch.object(nlu_processor.context_retriever, 'get_dialogue_context', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = sample_dialogue_context
            
            # Mock LLM call & validation
            with patch.object(nlu_processor.llm_client, 'call_llm_api', new_callable=AsyncMock) as mock_llm_call:
                with patch.object(nlu_processor.response_validator, 'validate_and_parse_response') as mock_validate:
                    mock_llm_call.return_value = "LLM_RESPONSE"
                    mock_validate.return_value = sample_uar.model_dump()
                    
                    # Process the message
                    result = await nlu_processor.process_message(sample_raw_message)
                    
                    # Verify the result
                    assert result is not None
                    assert isinstance(result, UAR)
                    assert result.original_message_ref == "550e8400-e29b-41d4-a716-446655440000"
                    assert result.user_id == "user_456"
                    assert result.channel_id == "channel_789"
                    assert result.status == UARStatus.SUCCESS
                    assert result.intent.name == IntentName.PROPOSENEWREI
                    assert len(result.entities) == 1
                    assert result.entities[0].type == EntityType.FUNCTIONALREQUIREMENT
                    
                    # Verify that context was retrieved
                    mock_get_context.assert_called_once_with("channel_789")
                    
                    # Verify that LLM call and validation were successful
                    mock_llm_call.assert_called_once()
                    mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_no_context(self, nlu_processor, sample_raw_message, sample_uar):
        """Test message processing when no context is available"""
        # Mock the context retriever to return None
        with patch.object(nlu_processor.context_retriever, 'get_dialogue_context', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = None
            
            # Mock LLM call & validation
            with patch.object(nlu_processor.llm_client, 'call_llm_api', new_callable=AsyncMock) as mock_llm_call:
                with patch.object(nlu_processor.response_validator, 'validate_and_parse_response') as mock_validate:
                    mock_llm_call.return_value = "LLM_RESPONSE"
                    mock_validate.return_value = sample_uar.model_dump()
                    
                    # Process the message
                    result = await nlu_processor.process_message(sample_raw_message)
                    
                    # Verify the result
                    assert result is not None
                    assert isinstance(result, UAR)
                    assert result.status == UARStatus.SUCCESS
                    
                    # Verify that context was attempted to be retrieved
                    mock_get_context.assert_called_once_with("channel_789")
                    
                    # Verify that LLM call and validation were successful
                    mock_llm_call.assert_called_once()
                    mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_llm_error(self, nlu_processor, sample_raw_message, sample_dialogue_context):
        """Test message processing when LLM service fails"""
        # Mock the context retriever
        with patch.object(nlu_processor.context_retriever, 'get_dialogue_context', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = sample_dialogue_context
            
            # Mock LLM call & validation
            with patch.object(nlu_processor.llm_client, 'call_llm_api', new_callable=AsyncMock) as mock_llm_call:
                with patch.object(nlu_processor.response_validator, 'validate_and_parse_response') as mock_validate:
                    mock_llm_call.return_value = None
                    
                    # Process the message
                    result = await nlu_processor.process_message(sample_raw_message)
                    
                    # Verify the result
                    assert result is not None
                    assert isinstance(result, UAR)
                    assert result.status == UARStatus.PROCESSING_ERROR
                    assert result.intent.name == IntentName.UNKNOWN
                    assert result.intent.confidence == 0.0
                    
                    # Verify that context was retrieved
                    mock_get_context.assert_called_once_with("channel_789")
                    
                    # Verify that LLM call was attempted
                    mock_llm_call.assert_called_once()
                    # Validation should not be called if LLM call failed
                    mock_validate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_message_validation_error(self, nlu_processor, sample_raw_message, sample_dialogue_context):
        """Test message processing when UAR validation fails"""
        # Mock the context retriever
        with patch.object(nlu_processor.context_retriever, 'get_dialogue_context', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.return_value = sample_dialogue_context
            
            # Mock LLM call & validation to return None (validation failure)
            with patch.object(nlu_processor.llm_client, 'call_llm_api', new_callable=AsyncMock) as mock_llm_call:
                with patch.object(nlu_processor.response_validator, 'validate_and_parse_response') as mock_validate:
                    mock_llm_call.return_value = "INVALID_LLM_RESPONSE"
                    mock_validate.return_value = None  # Validation failure
                    
                    # Process the message
                    result = await nlu_processor.process_message(sample_raw_message)
                    
                    # Verify the result
                    assert result is not None
                    assert isinstance(result, UAR)
                    assert result.status == UARStatus.PROCESSING_ERROR
                    assert result.intent.name == IntentName.UNKNOWN
                    assert result.intent.confidence == 0.0
                    
                    # Verify that context was retrieved
                    mock_get_context.assert_called_once_with("channel_789")
                    
                    # Verify that LLM call and validation were attempted
                    mock_llm_call.assert_called_once()
                    mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_context_error(self, nlu_processor, sample_raw_message, sample_uar):
        """Test message processing when context retrieval fails"""
        # Mock the context retriever to raise an exception
        with patch.object(nlu_processor.context_retriever, 'get_dialogue_context', new_callable=AsyncMock) as mock_get_context:
            mock_get_context.side_effect = Exception("DPSS service unavailable")
            
            # Mock LLM call & validation
            with patch.object(nlu_processor.llm_client, 'call_llm_api', new_callable=AsyncMock) as mock_llm_call:
                with patch.object(nlu_processor.response_validator, 'validate_and_parse_response') as mock_validate:
                    mock_llm_call.return_value = "LLM_RESPONSE"
                    mock_validate.return_value = sample_uar.model_dump()
                    
                    # Process the message - should still succeed even without context
                    result = await nlu_processor.process_message(sample_raw_message)
                    
                    # Verify the result
                    assert result is not None
                    assert isinstance(result, UAR)
                    assert result.status == UARStatus.SUCCESS
                    
                    # Verify that context retrieval was attempted
                    mock_get_context.assert_called_once_with("channel_789")
                    
                    # Verify that LLM call and validation were successful
                    mock_llm_call.assert_called_once()
                    mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, nlu_processor):
        """Test closing the NLU processor"""
        # Mock the context retriever close method (LLMClient doesn't have a close method)
        with patch.object(nlu_processor.context_retriever, 'close', new_callable=AsyncMock) as mock_context_close:
            # Call close on the processor (if it has one) or just test context retriever
            await nlu_processor.context_retriever.close()
            mock_context_close.assert_called_once() 