"""
Unit tests for PromptBuilder component

Tests the prompt construction and formatting functionality.
"""
import pytest
from nlu_service.core.prompt_builder import PromptBuilder
# DialogueContext models are now utility functions
from nlu_service.models.dialogue_context_utils import (
    create_dialogue_context,
    create_conversation_turn,
    create_current_focus_rei,
    create_active_question,
    create_simplified_uar,
)


@pytest.fixture
def prompt_builder():
    """Create a PromptBuilder instance for testing"""
    return PromptBuilder()


@pytest.fixture
def sample_dialogue_context():
    """Create a sample dialogue context for testing"""
    turn1 = create_conversation_turn(
        turn_id="turn_001",
        speaker_type="user",
        user_id_if_user="user_123",
        utterance_text="我们需要用户登录功能",
        timestamp_utc="2024-01-01T09:59:00Z"
    )
    
    turn2 = create_conversation_turn(
        turn_id="turn_002",
        speaker_type="assistant",
        utterance_text="好的，我来帮您记录这个需求。您希望支持哪些登录方式？",
        timestamp_utc="2024-01-01T10:00:00Z"
    )
    
    focus_rei = create_current_focus_rei(
        rei_id="FR-001",
        rei_type="FunctionalRequirement",
        name_or_summary="用户登录功能",
        status="Drafting",
        key_attributes_text="支持用户名密码登录",
        source_utterances_summary=["用户应该能够登录"]
    )
    
    question = create_active_question(
        question_id="q_001",
        question_text="您希望支持哪些登录方式？",
        relates_to_rei_id="FR-001"
    )
    
    return create_dialogue_context(
        channel_id="channel_123",
        retrieval_timestamp_utc="2024-01-01T10:01:00Z",
        recent_history=[turn1, turn2],
        current_focus_reis_summary=[focus_rei],
        active_questions=[question]
    )


class TestPromptBuilder:
    """Test PromptBuilder functionality"""
    
    def test_initialization(self, prompt_builder):
        """Test PromptBuilder initialization"""
        assert prompt_builder is not None
    
    def test_build_prompt_with_context(self, prompt_builder, sample_dialogue_context):
        """Test building a prompt with dialogue context"""
        raw_message = {
            "message_id": "msg_003",
            "channel_id": "channel_123",
            "user_id": "user_123",
            "raw_text": "支持用户名密码和手机号登录",
        }
        
        prompt = prompt_builder.build_llm_prompt(raw_message, sample_dialogue_context, "UAR_SCHEMA_PLACEHOLDER")
        
        # Verify prompt structure
        assert "您是一位经验丰富、技术精湛的 AI 需求工程分析师" in prompt
        assert "channel_123" in prompt
        assert "user_123" in prompt
        assert "我们需要用户登录功能" in prompt  # First turn
        assert "好的，我来帮您记录这个需求。您希望支持哪些登录方式？" in prompt  # Second turn
        assert "支持用户名密码和手机号登录" in prompt  # Current message
        assert "FR-001" in prompt  # Focus REI
        assert "您希望支持哪些登录方式？" in prompt  # Active question
    
    def test_build_prompt_without_context(self, prompt_builder):
        """Test building a prompt without dialogue context"""
        raw_message = {
            "message_id": "msg_001",
            "channel_id": "channel_123",
            "user_id": "user_123",
            "raw_text": "我们需要用户登录功能",
        }
        
        prompt = prompt_builder.build_llm_prompt(raw_message, None, "UAR_SCHEMA_PLACEHOLDER")
        
        # Verify prompt structure
        assert "您是一位经验丰富、技术精湛的 AI 需求工程分析师" in prompt
        assert "channel_123" in prompt
        assert "user_123" in prompt
        assert "我们需要用户登录功能" in prompt  # Current message
        assert "{}" in prompt  # Empty context
    
    def test_build_prompt_with_empty_context(self, prompt_builder):
        """Test building a prompt with empty dialogue context"""
        raw_message = {
            "message_id": "msg_001",
            "channel_id": "channel_123",
            "user_id": "user_123",
            "raw_text": "我们需要用户登录功能",
        }
        
        empty_context = create_dialogue_context(
            channel_id="channel_123",
            retrieval_timestamp_utc="2024-01-01T09:59:00Z",
            recent_history=[],
            current_focus_reis_summary=[],
            active_questions=[]
        )
        
        prompt = prompt_builder.build_llm_prompt(raw_message, empty_context, "UAR_SCHEMA_PLACEHOLDER")
        
        # Verify prompt structure
        assert "您是一位经验丰富、技术精湛的 AI 需求工程分析师" in prompt
        assert "channel_123" in prompt
        assert "user_123" in prompt
        assert "我们需要用户登录功能" in prompt  # Current message
        assert "recent_history\": []" in prompt  # Empty history
        assert "current_focus_reis_summary\": []" in prompt  # Empty focus REIs
        assert "active_questions\": []" in prompt  # Empty questions
    
    def test_build_prompt_with_simplified_uars(self, prompt_builder, sample_dialogue_context):
        """Test building a prompt with simplified UARs in conversation turns"""
        # Add simplified UAR to the first turn
        simplified_uar = create_simplified_uar(
            intent_name="ProposeNewREI",
            key_entity_types=["FunctionalRequirement"]
        )
        sample_dialogue_context["recent_history"][0]["simplified_uar_if_available"] = simplified_uar
        
        raw_message = {
            "message_id": "msg_003",
            "channel_id": "channel_123",
            "user_id": "user_123",
            "raw_text": "支持用户名密码和手机号登录",
        }
        
        prompt = prompt_builder.build_llm_prompt(raw_message, sample_dialogue_context, "UAR_SCHEMA_PLACEHOLDER")
        
        # Verify that simplified UAR information is included
        assert "ProposeNewREI" in prompt
        assert "FunctionalRequirement" in prompt
    
    def test_build_prompt_with_long_history(self, prompt_builder):
        """Test building a prompt with a long conversation history"""
        # Create a context with many turns
        turns = []
        for i in range(10):
            turn = create_conversation_turn(
                turn_id=f"turn_{i:03d}",
                speaker_type="user" if i % 2 == 0 else "assistant",
                user_id_if_user="user_123" if i % 2 == 0 else None,
                utterance_text=f"Message {i}",
                timestamp_utc=f"2024-01-01T09:{i:02d}:00Z"
            )
            turns.append(turn)
        
        context = create_dialogue_context(
            channel_id="channel_123",
            retrieval_timestamp_utc="2024-01-01T10:00:00Z",
            recent_history=turns,
            current_focus_reis_summary=[],
            active_questions=[]
        )
        
        raw_message = {
            "message_id": "msg_011",
            "channel_id": "channel_123",
            "user_id": "user_123",
            "raw_text": "Final message",
        }
        
        prompt = prompt_builder.build_llm_prompt(raw_message, context, "UAR_SCHEMA_PLACEHOLDER")
        
        # Verify that all turns are included in order
        for i in range(10):
            assert f"Message {i}" in prompt
    
    def test_build_prompt_with_special_characters(self, prompt_builder):
        """Test building a prompt with special characters in the message"""
        raw_message = {
            "message_id": "msg_001",
            "channel_id": "channel_123",
            "user_id": "user_123",
            "raw_text": "特殊字符测试：!@#$%^&*()_+{}|:\"<>?[]\\;',./~`",
        }
        
        prompt = prompt_builder.build_llm_prompt(raw_message, None, "UAR_SCHEMA_PLACEHOLDER")
        
        # Verify that special characters are preserved
        assert "特殊字符测试：!@#$%^&*()_+{}|:\"<>?[]\\;',./~`" in prompt 