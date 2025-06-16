"""
DialogueContext utility functions

This module provides utility functions for working with DialogueContext data
as defined in config/dialogue_context.yml. Since we moved from Pydantic models
to YAML-based configuration, these utilities help validate and work with
dialogue context data as dictionaries.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


# Enum values from dialogue_context.yml - updated structure
SPEAKER_TYPES = ["user", "assistant"]

REI_TYPES = [
    "Goal", "FunctionalRequirement", "NonFunctionalRequirement", "Actor",
    "Constraint", "Issue", "DataObject", "SystemComponent", "UserStory",
    "UseCase", "Stakeholder"
]

REI_STATUSES = ["Drafting", "Review", "Approved", "Implemented", "Deprecated"]

INTENT_NAMES = [
    "ProposeNewREI", "ModifyExistingREI", "ProvideClarification",
    "ConfirmUnderstanding", "DenyUnderstanding", "AskQuestion",
    "GeneralStatement", "ChitChat", "Unknown"
]


def create_dialogue_context(
    channel_id: str,
    retrieval_timestamp_utc: Optional[str] = None,
    recent_history: Optional[List[Dict[str, Any]]] = None,
    current_focus_reis_summary: Optional[List[Dict[str, Any]]] = None,
    active_questions: Optional[List[Dict[str, Any]]] = None  # Updated name
) -> Dict[str, Any]:
    """
    Create a dialogue context dictionary following the YAML schema.
    
    Args:
        channel_id: Channel identifier
        retrieval_timestamp_utc: Optional timestamp, auto-generated if None
        recent_history: List of conversation turns
        current_focus_reis_summary: List of current focus REIs
        active_questions: List of active questions (renamed from active_system_questions)
    
    Returns:
        Dictionary representing dialogue context
    """
    return {
        "channel_id": channel_id,
        "retrieval_timestamp_utc": retrieval_timestamp_utc or datetime.utcnow().isoformat() + "Z",
        "recent_history": recent_history or [],
        "current_focus_reis_summary": current_focus_reis_summary or [],
        "active_questions": active_questions or []  # Updated name
    }


def create_conversation_turn(
    turn_id: str,
    speaker_type: str,
    utterance_text: str,
    timestamp_utc: Optional[str] = None,
    user_id_if_user: Optional[str] = None,
    simplified_uar_if_available: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a conversation turn dictionary.
    
    Args:
        turn_id: Unique identifier for this turn
        speaker_type: Must be "user" or "assistant"
        utterance_text: The actual text content
        timestamp_utc: Optional timestamp, auto-generated if None
        user_id_if_user: User ID if speaker_type is "user"
        simplified_uar_if_available: Optional simplified UAR data
    
    Returns:
        Dictionary representing a conversation turn
        
    Raises:
        ValueError: If speaker_type is not valid
    """
    if speaker_type not in SPEAKER_TYPES:
        raise ValueError(f"Invalid speaker_type: {speaker_type}. Must be one of {SPEAKER_TYPES}")
    
    turn = {
        "turn_id": turn_id,
        "speaker_type": speaker_type,
        "utterance_text": utterance_text,
        "timestamp_utc": timestamp_utc or datetime.utcnow().isoformat() + "Z"
    }
    
    if user_id_if_user is not None:
        turn["user_id_if_user"] = user_id_if_user
    
    if simplified_uar_if_available is not None:
        turn["simplified_uar_if_available"] = simplified_uar_if_available
    
    return turn


def create_simplified_uar(
    intent_name: Optional[str] = None,
    key_entity_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a simplified UAR dictionary.
    
    Args:
        intent_name: Intent name, must be from INTENT_NAMES enum
        key_entity_types: List of entity types, each must be from REI_TYPES enum
    
    Returns:
        Dictionary representing simplified UAR
        
    Raises:
        ValueError: If intent_name or entity types are not valid
    """
    if intent_name is not None and intent_name not in INTENT_NAMES:
        raise ValueError(f"Invalid intent_name: {intent_name}. Must be one of {INTENT_NAMES}")
    
    if key_entity_types:
        for entity_type in key_entity_types:
            if entity_type not in REI_TYPES:
                raise ValueError(f"Invalid entity type: {entity_type}. Must be one of {REI_TYPES}")
    
    return {
        "intent_name": intent_name,
        "key_entity_types": key_entity_types or []
    }


def create_current_focus_rei(
    rei_id: str,
    rei_type: str,
    name_or_summary: str,
    status: str,
    key_attributes_text: Optional[str] = None,
    source_utterances_summary: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a current focus REI dictionary.
    
    Args:
        rei_id: Unique REI identifier
        rei_type: Must be from REI_TYPES enum
        name_or_summary: REI name or summary
        status: Must be from REI_STATUSES enum
        key_attributes_text: Optional key attributes text
        source_utterances_summary: Optional list of source utterances
    
    Returns:
        Dictionary representing current focus REI
        
    Raises:
        ValueError: If rei_type or status are not valid
    """
    if rei_type not in REI_TYPES:
        raise ValueError(f"Invalid rei_type: {rei_type}. Must be one of {REI_TYPES}")
    
    if status not in REI_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {REI_STATUSES}")
    
    rei = {
        "rei_id": rei_id,
        "rei_type": rei_type,
        "name_or_summary": name_or_summary,
        "status": status,
        "source_utterances_summary": source_utterances_summary or []
    }
    
    if key_attributes_text is not None:
        rei["key_attributes_text"] = key_attributes_text
    
    return rei


def create_active_question(  # Updated function name
    question_id: str,
    question_text: str,
    relates_to_rei_id: Optional[str] = None,
    relates_to_attribute: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an active question dictionary.
    
    Args:
        question_id: Unique question identifier
        question_text: The question text (can be from user or system)
        relates_to_rei_id: Optional REI ID this question relates to
        relates_to_attribute: Optional REI attribute this question relates to
    
    Returns:
        Dictionary representing active question
    """
    question = {
        "question_id": question_id,
        "question_text": question_text
    }
    
    if relates_to_rei_id is not None:
        question["relates_to_rei_id"] = relates_to_rei_id
    
    if relates_to_attribute is not None:
        question["relates_to_attribute"] = relates_to_attribute
    
    return question


# Keep backward compatibility
def create_active_system_question(*args, **kwargs) -> Dict[str, Any]:
    """
    Backward compatibility function for create_active_system_question.
    Redirects to create_active_question.
    """
    return create_active_question(*args, **kwargs)


def validate_dialogue_context(context: Dict[str, Any]) -> bool:
    """
    Validate a dialogue context dictionary against the schema.
    
    Args:
        context: Dictionary to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required fields
        if "channel_id" not in context:
            return False
        
        # Validate optional fields if present
        if "recent_history" in context:
            for turn in context["recent_history"]:
                if not isinstance(turn, dict):
                    return False
                if "speaker_type" in turn and turn["speaker_type"] not in SPEAKER_TYPES:
                    return False
        
        if "current_focus_reis_summary" in context:
            for rei in context["current_focus_reis_summary"]:
                if not isinstance(rei, dict):
                    return False
                if "rei_type" in rei and rei["rei_type"] not in REI_TYPES:
                    return False
                if "status" in rei and rei["status"] not in REI_STATUSES:
                    return False
        
        return True
    except Exception:
        return False


def get_rei_type_enum() -> List[str]:
    """Get the list of valid REI types."""
    return REI_TYPES.copy()


def get_rei_status_enum() -> List[str]:
    """Get the list of valid REI statuses."""
    return REI_STATUSES.copy()


def get_intent_name_enum() -> List[str]:
    """Get the list of valid intent names."""
    return INTENT_NAMES.copy()


def get_speaker_type_enum() -> List[str]:
    """Get the list of valid speaker types."""
    return SPEAKER_TYPES.copy() 