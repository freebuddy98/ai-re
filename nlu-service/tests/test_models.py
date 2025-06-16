"""
Unit tests for NLU Service data models

Tests the Pydantic models for proper validation, serialization, and deserialization.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from nlu_service.models.uar import (
    UAR,
    UARIntent,
    UAREntity,
    UARRelation,
    UARAmbiguityDetail,
    UARLLMTrace,
    IntentName,
    EntityType,
    RelationType,
    UARStatus,
)
# DialogueContext models are now utility functions
from nlu_service.models.dialogue_context_utils import (
    create_dialogue_context,
    create_conversation_turn,
    create_current_focus_rei,
    create_active_question,
    create_simplified_uar,
    validate_dialogue_context,
    get_rei_type_enum,
)


class TestUARModels:
    """Test UAR-related models"""
    
    def test_uar_intent_creation(self):
        """Test UARIntent model creation and validation"""
        intent = UARIntent(
            name=IntentName.PROPOSENEWREI,
            confidence=0.85,
            target_rei_id_if_modifying=None
        )
        
        assert intent.name == IntentName.PROPOSENEWREI
        assert intent.confidence == 0.85
        assert intent.target_rei_id_if_modifying is None
    
    def test_uar_intent_confidence_validation(self):
        """Test that intent confidence is validated to be between 0 and 1"""
        # Valid confidence
        intent = UARIntent(name=IntentName.PROPOSENEWREI, confidence=0.5)
        assert intent.confidence == 0.5
        
        # Invalid confidence - too low
        with pytest.raises(ValidationError):
            UARIntent(name=IntentName.PROPOSENEWREI, confidence=-0.1)
        
        # Invalid confidence - too high
        with pytest.raises(ValidationError):
            UARIntent(name=IntentName.PROPOSENEWREI, confidence=1.1)
    
    def test_uar_entity_creation(self):
        """Test UAREntity model creation"""
        entity = UAREntity(
            temp_id="ent-1",
            type=EntityType.FUNCTIONALREQUIREMENT,
            text_span="用户应该能够登录",
            start_char=0,
            end_char=8,
            attributes={"name": "用户登录", "priority": "High"},
            is_ambiguous=False
        )
        
        assert entity.temp_id == "ent-1"
        assert entity.type == EntityType.FUNCTIONALREQUIREMENT
        assert entity.text_span == "用户应该能够登录"
        assert entity.start_char == 0
        assert entity.end_char == 8
        assert entity.attributes["name"] == "用户登录"
        assert not entity.is_ambiguous
        assert len(entity.ambiguity_details) == 0
    
    def test_uar_entity_with_ambiguity(self):
        """Test UAREntity with ambiguity details"""
        ambiguity_detail = UARAmbiguityDetail(
            attribute_name="description",
            text_fragment="快速",
            reason="缺乏具体性能指标"
        )
        
        entity = UAREntity(
            temp_id="ent-2",
            type=EntityType.NONFUNCTIONALREQUIREMENT,
            text_span="系统应该快速响应",
            start_char=0,
            end_char=9,
            attributes={"name": "响应速度", "description": "系统应该快速响应"},
            is_ambiguous=True,
            ambiguity_details=[ambiguity_detail]
        )
        
        assert entity.is_ambiguous
        assert len(entity.ambiguity_details) == 1
        assert entity.ambiguity_details[0].text_fragment == "快速"
    
    def test_uar_relation_creation(self):
        """Test UARRelation model creation"""
        relation = UARRelation(
            source_temp_id="ent-1",
            target_temp_id="ent-2",
            type=RelationType.INVOLVES,
            confidence=0.9
        )
        
        assert relation.source_temp_id == "ent-1"
        assert relation.target_temp_id == "ent-2"
        assert relation.type == RelationType.INVOLVES
        assert relation.confidence == 0.9
        assert relation.text_span_if_explicit is None
    
    def test_uar_full_creation(self):
        """Test complete UAR model creation"""
        intent = UARIntent(name=IntentName.PROPOSENEWREI, confidence=0.85)
        
        entity = UAREntity(
            temp_id="ent-1",
            type=EntityType.FUNCTIONALREQUIREMENT,
            text_span="用户登录",
            start_char=0,
            end_char=4,
            attributes={"name": "用户登录"},
            is_ambiguous=False
        )
        
        relation = UARRelation(
            source_temp_id="ent-1",
            target_temp_id="ent-2",
            type=RelationType.INVOLVES,
            confidence=0.8
        )
        
        llm_trace = UARLLMTrace(
            model_name_used="gpt-4-turbo",
            prompt_token_count=100,
            completion_token_count=50
        )
        
        uar = UAR(
            original_message_ref="msg_123",
            user_id="user_456",
            channel_id="channel_789",
            raw_text_processed="用户应该能够登录系统",
            status=UARStatus.SUCCESS,
            intent=intent,
            entities=[entity],
            relations=[relation],
            llm_trace=llm_trace
        )
        
        assert uar.original_message_ref == "msg_123"
        assert uar.user_id == "user_456"
        assert uar.channel_id == "channel_789"
        assert uar.status == UARStatus.SUCCESS
        assert len(uar.entities) == 1
        assert len(uar.relations) == 1
        assert uar.llm_trace.model_name_used == "gpt-4-turbo"
        # uar_id should be auto-generated
        assert uar.uar_id is not None
        assert len(uar.uar_id) == 36  # UUID length


class TestDialogueContextUtils:
    """Test DialogueContext utility functions"""
    
    def test_simplified_uar_creation(self):
        """Test create_simplified_uar utility function"""
        simplified_uar = create_simplified_uar(
            intent_name="ProposeNewREI",
            key_entity_types=["FunctionalRequirement", "Actor"]
        )
        
        assert simplified_uar["intent_name"] == "ProposeNewREI"
        assert len(simplified_uar["key_entity_types"]) == 2
        assert "FunctionalRequirement" in simplified_uar["key_entity_types"]
    
    def test_simplified_uar_validation(self):
        """Test simplified UAR validation with enums"""
        # Valid intent name
        uar = create_simplified_uar(intent_name="ProposeNewREI")
        assert uar["intent_name"] == "ProposeNewREI"
        
        # Invalid intent name should raise error
        with pytest.raises(ValueError, match="Invalid intent_name"):
            create_simplified_uar(intent_name="InvalidIntent")
        
        # Invalid entity type should raise error
        with pytest.raises(ValueError, match="Invalid entity type"):
            create_simplified_uar(key_entity_types=["InvalidEntityType"])
    
    def test_conversation_turn_creation(self):
        """Test create_conversation_turn utility function"""
        simplified_uar = create_simplified_uar(
            intent_name="ProposeNewREI",
            key_entity_types=["FunctionalRequirement"]
        )
        
        turn = create_conversation_turn(
            turn_id="turn_123",
            speaker_type="user",
            utterance_text="系统应该支持用户登录",
            user_id_if_user="user_456",
            simplified_uar_if_available=simplified_uar
        )
        
        assert turn["turn_id"] == "turn_123"
        assert turn["speaker_type"] == "user"
        assert turn["user_id_if_user"] == "user_456"
        assert turn["utterance_text"] == "系统应该支持用户登录"
        assert turn["simplified_uar_if_available"]["intent_name"] == "ProposeNewREI"
    
    def test_conversation_turn_validation(self):
        """Test conversation turn validation"""
        # Valid speaker type
        turn = create_conversation_turn(
            turn_id="turn_123",
            speaker_type="user",
            utterance_text="Hello"
        )
        assert turn["speaker_type"] == "user"
        
        # Invalid speaker type should raise error
        with pytest.raises(ValueError, match="Invalid speaker_type"):
            create_conversation_turn(
                turn_id="turn_123",
                speaker_type="invalid_speaker",
                utterance_text="Hello"
            )
    
    def test_current_focus_rei_creation(self):
        """Test create_current_focus_rei utility function"""
        focus_rei = create_current_focus_rei(
            rei_id="FR-001",
            rei_type="FunctionalRequirement",
            name_or_summary="用户登录功能",
            status="Drafting",
            key_attributes_text="支持用户名密码登录",
            source_utterances_summary=["用户应该能够登录", "支持用户名密码"]
        )
        
        assert focus_rei["rei_id"] == "FR-001"
        assert focus_rei["rei_type"] == "FunctionalRequirement"
        assert focus_rei["name_or_summary"] == "用户登录功能"
        assert focus_rei["status"] == "Drafting"
        assert len(focus_rei["source_utterances_summary"]) == 2
    
    def test_current_focus_rei_validation(self):
        """Test REI creation validation with enums"""
        # Valid REI type and status
        rei = create_current_focus_rei(
            rei_id="FR-001",
            rei_type="FunctionalRequirement",
            name_or_summary="Test REI",
            status="Drafting"
        )
        assert rei["rei_type"] == "FunctionalRequirement"
        assert rei["status"] == "Drafting"
        
        # Invalid REI type should raise error
        with pytest.raises(ValueError, match="Invalid rei_type"):
            create_current_focus_rei(
                rei_id="FR-001",
                rei_type="InvalidREIType",
                name_or_summary="Test REI",
                status="Drafting"
            )
        
        # Invalid status should raise error
        with pytest.raises(ValueError, match="Invalid status"):
            create_current_focus_rei(
                rei_id="FR-001",
                rei_type="FunctionalRequirement",
                name_or_summary="Test REI",
                status="InvalidStatus"
            )
    
    def test_active_question_creation(self):
        """Test create_active_question utility function"""
        question = create_active_question(
            question_id="q_001",
            question_text="您希望支持哪些登录方式？",
            relates_to_rei_id="FR-001",
            relates_to_attribute="authentication_methods"
        )
        
        assert question["question_id"] == "q_001"
        assert question["question_text"] == "您希望支持哪些登录方式？"
        assert question["relates_to_rei_id"] == "FR-001"
        assert question["relates_to_attribute"] == "authentication_methods"
    
    def test_dialogue_context_creation(self):
        """Test complete DialogueContext creation using utility functions"""
        turn = create_conversation_turn(
            turn_id="turn_123",
            speaker_type="user",
            utterance_text="我们需要用户登录功能"
        )
        
        focus_rei = create_current_focus_rei(
            rei_id="FR-001",
            rei_type="FunctionalRequirement",
            name_or_summary="用户登录功能",
            status="Drafting"
        )
        
        question = create_active_question(
            question_id="q_001",
            question_text="您希望支持哪些登录方式？",
            relates_to_rei_id="FR-001"
        )
        
        context = create_dialogue_context(
            channel_id="channel_789",
            recent_history=[turn],
            current_focus_reis_summary=[focus_rei],
            active_questions=[question]
        )
        
        assert context["channel_id"] == "channel_789"
        assert len(context["recent_history"]) == 1
        assert len(context["current_focus_reis_summary"]) == 1
        assert len(context["active_questions"]) == 1
        assert context["recent_history"][0]["utterance_text"] == "我们需要用户登录功能"
    
    def test_dialogue_context_validation(self):
        """Test dialogue context validation function"""
        # Valid context
        context = create_dialogue_context(channel_id="test_channel")
        assert validate_dialogue_context(context) == True
        
        # Invalid context - missing channel_id
        invalid_context = {"invalid": "data"}
        assert validate_dialogue_context(invalid_context) == False
    
    def test_enum_functions(self):
        """Test enum getter functions"""
        rei_types = get_rei_type_enum()
        assert "FunctionalRequirement" in rei_types
        assert "Goal" in rei_types
        assert len(rei_types) == 11  # Should have all 11 REI types


class TestEnums:
    """Test enum values"""
    
    def test_intent_name_enum(self):
        """Test IntentName enum values"""
        assert IntentName.PROPOSENEWREI.value == "ProposeNewREI"
        assert IntentName.MODIFYEXISTINGREI.value == "ModifyExistingREI"
        assert IntentName.PROVIDECLARIFICATION.value == "ProvideClarification"
        assert IntentName.UNKNOWN.value == "Unknown"
    
    def test_entity_type_enum(self):
        """Test EntityType enum values"""
        assert EntityType.GOAL.value == "Goal"
        assert EntityType.FUNCTIONALREQUIREMENT.value == "FunctionalRequirement"
        assert EntityType.NONFUNCTIONALREQUIREMENT.value == "NonFunctionalRequirement"
        assert EntityType.ACTOR.value == "Actor"
    
    def test_relation_type_enum(self):
        """Test RelationType enum values"""
        assert RelationType.REFINES.value == "REFINES"
        assert RelationType.CONTAINS.value == "CONTAINS"
        assert RelationType.DEPENDS_ON.value == "DEPENDS_ON"
        assert RelationType.INVOLVES.value == "INVOLVES"
    
    def test_uar_status_enum(self):
        """Test UARStatus enum values"""
        assert UARStatus.SUCCESS.value == "success"
        assert UARStatus.LLM_CALL_FAILED.value == "llm_call_failed"
        assert UARStatus.VALIDATION_FAILED_AGAINST_SCHEMA.value == "validation_failed_against_schema" 