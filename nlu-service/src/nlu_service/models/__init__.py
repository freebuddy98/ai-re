"""
Data models for NLU Service

This module contains all the data structures used in the NLU service,
including UAR (User Utterance Analysis Result). DialogueContext schema
is now defined in config/dialogue_context.yml for configuration-driven
approach.
"""

from .uar import (
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

__all__ = [
    # UAR models
    "UAR",
    "UARIntent",
    "UAREntity",
    "UARRelation",
    "UARAmbiguityDetail",
    "UARLLMTrace",
    "IntentName",
    "EntityType",
    "RelationType",
    "UARStatus",
] 