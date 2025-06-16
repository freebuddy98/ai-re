"""
Unit tests for ResponseValidator component

Tests the validation of LLM-generated UARs.
"""
import pytest

from nlu_service.core.response_validator import ResponseValidator
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
def response_validator():
    """Create a ResponseValidator instance for testing"""
    return ResponseValidator()


@pytest.fixture
def valid_uar():
    """Create a valid UAR for testing"""
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
        original_message_ref="msg_123",
        user_id="user_456",
        channel_id="channel_789",
        raw_text_processed="用户应该能够登录系统",
        status=UARStatus.SUCCESS,
        intent=intent,
        entities=[entity],
        relations=[],
        llm_trace=llm_trace
    )


class TestResponseValidator:
    """Test ResponseValidator functionality"""
    
    def test_initialization(self, response_validator):
        """Test ResponseValidator initialization"""
        assert response_validator is not None
    
    def test_validate_valid_uar(self, response_validator, valid_uar):
        """Test validation of a valid UAR"""
        result = response_validator.validate(valid_uar)
        assert result.is_valid
        assert len(result.validation_errors) == 0
    
    def test_validate_missing_intent(self, response_validator):
        """Test validation of UAR with missing intent"""
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="用户应该能够登录系统",
            status=UARStatus.SUCCESS,
            intent=None,
            entities=[],
            relations=[],
            llm_trace=UARLLMTrace(
                model_name_used="gpt-4-turbo",
                prompt_token_count=100,
                completion_token_count=50
            )
        )
        
        result = response_validator.validate(uar)
        assert not result.is_valid
        assert len(result.validation_errors) == 1
        assert "intent" in result.validation_errors[0].lower()
    
    def test_validate_invalid_intent_confidence(self, response_validator):
        """Test validation of UAR with invalid intent confidence"""
        intent = UARIntent(
            name=IntentName.PROPOSENEWREI,
            confidence=1.5,  # Invalid confidence > 1.0
            target_rei_id_if_modifying=None
        )
        
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="用户应该能够登录系统",
            status=UARStatus.SUCCESS,
            intent=intent,
            entities=[],
            relations=[],
            llm_trace=UARLLMTrace(
                model_name_used="gpt-4-turbo",
                prompt_token_count=100,
                completion_token_count=50
            )
        )
        
        result = response_validator.validate(uar)
        assert not result.is_valid
        assert len(result.validation_errors) == 1
        assert "confidence" in result.validation_errors[0].lower()
    
    def test_validate_invalid_entity_span(self, response_validator):
        """Test validation of UAR with invalid entity text span"""
        entity = UAREntity(
            temp_id="ent-1",
            type=EntityType.FUNCTIONALREQUIREMENT,
            text_span="用户登录",
            start_char=5,  # Invalid start position
            end_char=4,    # Invalid end position (before start)
            attributes={"name": "用户登录"},
            is_ambiguous=False
        )
        
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="用户应该能够登录系统",
            status=UARStatus.SUCCESS,
            intent=UARIntent(
                name=IntentName.PROPOSENEWREI,
                confidence=0.85
            ),
            entities=[entity],
            relations=[],
            llm_trace=UARLLMTrace(
                model_name_used="gpt-4-turbo",
                prompt_token_count=100,
                completion_token_count=50
            )
        )
        
        result = response_validator.validate(uar)
        assert not result.is_valid
        assert len(result.validation_errors) == 1
        assert "text span" in result.validation_errors[0].lower()
    
    def test_validate_invalid_relation(self, response_validator):
        """Test validation of UAR with invalid relation"""
        relation = UARRelation(
            source_temp_id="ent-1",
            target_temp_id="ent-2",
            type=RelationType.INVOLVES,
            confidence=1.2  # Invalid confidence > 1.0
        )
        
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="用户应该能够登录系统",
            status=UARStatus.SUCCESS,
            intent=UARIntent(
                name=IntentName.PROPOSENEWREI,
                confidence=0.85
            ),
            entities=[],
            relations=[relation],
            llm_trace=UARLLMTrace(
                model_name_used="gpt-4-turbo",
                prompt_token_count=100,
                completion_token_count=50
            )
        )
        
        result = response_validator.validate(uar)
        assert not result.is_valid
        assert len(result.validation_errors) == 1
        assert "confidence" in result.validation_errors[0].lower()
    
    def test_validate_missing_llm_trace(self, response_validator):
        """Test validation of UAR with missing LLM trace"""
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="用户应该能够登录系统",
            status=UARStatus.SUCCESS,
            intent=UARIntent(
                name=IntentName.PROPOSENEWREI,
                confidence=0.85
            ),
            entities=[],
            relations=[],
            llm_trace=None
        )
        
        result = response_validator.validate(uar)
        assert not result.is_valid
        assert len(result.validation_errors) == 1
        assert "llm trace" in result.validation_errors[0].lower()
    
    def test_validate_multiple_errors(self, response_validator):
        """Test validation of UAR with multiple validation errors"""
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="用户应该能够登录系统",
            status=UARStatus.SUCCESS,
            intent=None,  # Missing intent
            entities=[
                UAREntity(
                    temp_id="ent-1",
                    type=EntityType.FUNCTIONALREQUIREMENT,
                    text_span="用户登录",
                    start_char=5,  # Invalid start position
                    end_char=4,    # Invalid end position
                    attributes={"name": "用户登录"},
                    is_ambiguous=False
                )
            ],
            relations=[],
            llm_trace=None  # Missing LLM trace
        )
        
        result = response_validator.validate(uar)
        assert not result.is_valid
        assert len(result.validation_errors) >= 3  # At least 3 errors
        assert any("intent" in error.lower() for error in result.validation_errors)
        assert any("text span" in error.lower() for error in result.validation_errors)
        assert any("llm trace" in error.lower() for error in result.validation_errors)
    
    def test_validate_ambiguous_entity(self, response_validator):
        """Test validation of UAR with ambiguous entity"""
        entity = UAREntity(
            temp_id="ent-1",
            type=EntityType.FUNCTIONALREQUIREMENT,
            text_span="快速响应",
            start_char=0,
            end_char=4,
            attributes={"name": "响应速度"},
            is_ambiguous=True,
            ambiguity_details=[
                {
                    "attribute_name": "description",
                    "text_fragment": "快速",
                    "reason": "缺乏具体性能指标"
                }
            ]
        )
        
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="系统应该快速响应",
            status=UARStatus.SUCCESS,
            intent=UARIntent(
                name=IntentName.PROPOSENEWREI,
                confidence=0.85
            ),
            entities=[entity],
            relations=[],
            llm_trace=UARLLMTrace(
                model_name_used="gpt-4-turbo",
                prompt_token_count=100,
                completion_token_count=50
            )
        )
        
        result = response_validator.validate(uar)
        assert result.is_valid
        assert len(result.validation_errors) == 0
    
    def test_validate_ambiguous_entity_without_details(self, response_validator):
        """Test validation of UAR with ambiguous entity but missing details"""
        entity = UAREntity(
            temp_id="ent-1",
            type=EntityType.FUNCTIONALREQUIREMENT,
            text_span="快速响应",
            start_char=0,
            end_char=4,
            attributes={"name": "响应速度"},
            is_ambiguous=True,
            ambiguity_details=[]  # Missing details for ambiguous entity
        )
        
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="系统应该快速响应",
            status=UARStatus.SUCCESS,
            intent=UARIntent(
                name=IntentName.PROPOSENEWREI,
                confidence=0.85
            ),
            entities=[entity],
            relations=[],
            llm_trace=UARLLMTrace(
                model_name_used="gpt-4-turbo",
                prompt_token_count=100,
                completion_token_count=50
            )
        )
        
        result = response_validator.validate(uar)
        assert not result.is_valid
        assert len(result.validation_errors) == 1
        assert "ambiguity details" in result.validation_errors[0].lower() 