"""
NLU Service Package

This package provides Natural Language Understanding capabilities for the AI-RE system.
It processes raw user messages and extracts structured information including:
- User intent  
- Entities
- Dialogue context (schema defined in config/dialogue_context.yml)
- Action requirements

The service integrates with:
- Event Bus Framework for message handling
- DPSS (Dialogue Policy State Service) for context management
- LLM services for natural language processing

Main Components:
- NLUProcessor: Core processing logic
- Configuration management
- Event handling and publishing
- Prompt building and LLM interaction

Usage:
    from nlu_service import NLUProcessor, main
    
    # Run as service
    main()
    
    # Or use processor directly
    processor = NLUProcessor(...)
    result = processor.process_raw_message(message_data)
"""

from .core import (
    NLUProcessor,
    ContextRetriever,
    PromptBuilder,
    LLMClient,
    ResponseValidator,
)
from .models import (
    UAR,
    UARIntent,
    UAREntity,
    UARRelation,
    IntentName,
    EntityType,
    RelationType,
    UARStatus,
)
from .config import (
    NLUServiceConfig,
    LLMConfig,
    DPSSConfig,
    EventBusConfig,
    load_config_from_env,
    load_config_from_dict,
    get_config,
)
from .factory import NLUProcessorFactory
from .service_manager import NLUServiceManager
from .message_handlers import MessageHandlers
from .main import main

__version__ = "0.1.0"
__author__ = "AI-RE Team"

__all__ = [
    # Core components
    "NLUProcessor",
    "ContextRetriever", 
    "PromptBuilder",
    "LLMClient",
    "ResponseValidator",
    # Data models
    "UAR",
    "UARIntent",
    "UAREntity", 
    "UARRelation",
    "IntentName",
    "EntityType",
    "RelationType",
    "UARStatus",
    # Configuration
    "NLUServiceConfig",
    "LLMConfig",
    "DPSSConfig",
    "EventBusConfig",
    "load_config_from_env",
    "load_config_from_dict",
    "get_config",
    # Factory
    "NLUProcessorFactory",
    # Service Management
    "NLUServiceManager",
    "MessageHandlers",
    # Service entry points
    "main",
    # Metadata
    "__version__",
    "__author__"
]

