"""
Schema-based model generation

This module generates Pydantic models based on configuration files to avoid
duplication between code and configuration.
"""
import yaml
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Type, Union
from pydantic import BaseModel, Field


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load YAML configuration file"""
    path = Path(config_path)
    if not path.exists():
        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        path = project_root / config_path
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_enum_from_config(enum_name: str, enum_config: Dict[str, Any]) -> Type[Enum]:
    """Create an Enum class from configuration"""
    values = {}
    for value_config in enum_config.get('values', []):
        value = value_config['value']
        values[value.upper().replace(' ', '_')] = value
    
    return Enum(enum_name, values)


# Load dialogue context configuration
dialogue_context_config = load_config_file('config/dialogue_context.yml')
enums_config = dialogue_context_config['dialogue_context']['enums']

# Create enums from configuration
SpeakerType = create_enum_from_config('SpeakerType', enums_config['speaker_type'])
REIType = create_enum_from_config('REIType', enums_config['rei_type'])
REIStatus = create_enum_from_config('REIStatus', enums_config['rei_status'])
IntentName = create_enum_from_config('IntentName', enums_config['intent_name'])

# Load events configuration
events_config = load_config_file('config/events.yml')

# Create UAR status enum based on events.yml if needed
# For now, we'll keep the UAR status as defined in the original uar.py
# since it's more about processing status than business logic

class UARStatus(str, Enum):
    """UAR processing status"""
    SUCCESS = "success"
    LLM_CALL_FAILED = "llm_call_failed"
    LLM_RESPONSE_INVALID_FORMAT = "llm_response_invalid_format"
    VALIDATION_FAILED_AGAINST_SCHEMA = "validation_failed_against_schema"
    PROCESSING_ERROR = "processing_error"


# Entity and Relation types from dialogue_context.yml
EntityType = REIType  # They are the same
RelationType = create_enum_from_config('RelationType', {
    'values': [
        {'value': 'REFINES'},
        {'value': 'CONTAINS'},
        {'value': 'PART_OF'},
        {'value': 'DEPENDS_ON'},
        {'value': 'AFFECTS'},
        {'value': 'CONFLICTS_WITH'},
        {'value': 'INVOLVES'},
        {'value': 'QUALIFIES'},
        {'value': 'ADDRESSES'},
        {'value': 'RELATES_TO'}
    ]
})


# Export the generated enums
__all__ = [
    'SpeakerType',
    'REIType', 
    'REIStatus',
    'IntentName',
    'EntityType',
    'RelationType',
    'UARStatus'
] 