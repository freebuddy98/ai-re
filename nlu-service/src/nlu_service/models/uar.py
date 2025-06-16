"""
UAR (User Utterance Analysis Result) data models

This module defines the complete schema for UAR as specified in the design document.
Uses enums generated from configuration files to avoid duplication.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Import enums generated from configuration files
from .schema_models import (
    UARStatus,
    IntentName, 
    EntityType,
    RelationType
)


class UARIntent(BaseModel):
    """Intent information in UAR"""
    name: IntentName
    confidence: float = Field(ge=0.0, le=1.0)
    target_rei_id_if_modifying: Optional[str] = None


class UARAmbiguityDetail(BaseModel):
    """Ambiguity details for entities"""
    attribute_name: Optional[str] = None
    text_fragment: str
    reason: Optional[str] = None


class UAREntity(BaseModel):
    """Entity extracted from user utterance"""
    temp_id: str
    type: EntityType
    text_span: str
    start_char: int = Field(ge=0)
    end_char: int
    attributes: Dict[str, Union[str, int, float, bool, None]]
    is_ambiguous: bool = False
    ambiguity_details: List[UARAmbiguityDetail] = Field(default_factory=list)


class UARRelation(BaseModel):
    """Relation between entities"""
    source_temp_id: str
    target_temp_id: str
    type: RelationType
    text_span_if_explicit: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class UARLLMTrace(BaseModel):
    """LLM trace information for debugging"""
    model_name_used: str
    prompt_token_count: Optional[int] = None
    completion_token_count: Optional[int] = None
    raw_llm_output_if_debug_mode: Optional[str] = None


class UAR(BaseModel):
    """
    User Utterance Analysis Result (UAR)
    
    Complete schema as defined in the design document section 3.2
    """
    uar_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_message_ref: str
    user_id: str
    channel_id: str
    processing_timestamp_utc: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    raw_text_processed: str
    status: UARStatus
    intent: UARIntent
    entities: List[UAREntity] = Field(default_factory=list)
    relations: List[UARRelation] = Field(default_factory=list)
    llm_trace: Optional[UARLLMTrace] = None 