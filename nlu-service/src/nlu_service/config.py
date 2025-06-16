"""
Configuration module for NLU Service

This module handles all configuration parameters for the NLU service.
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM configuration"""
    model: str = "gpt-4-turbo"
    temperature: float = 0.2
    max_tokens: int = 2000
    timeout: float = 60.0


@dataclass
class DPSSConfig:
    """DPSS service configuration"""
    base_url: str = "http://localhost:8080"
    timeout: float = 30.0
    context_limit: int = 5


@dataclass
class EventBusConfig:
    """Event bus configuration"""
    input_topic: str = "input:raw_message"
    output_topic: str = "nlu:uar_result"
    consumer_group: str = "nlu-service"
    consumer_name: str = "nlu-worker"


@dataclass
class NLUServiceConfig:
    """Main NLU service configuration"""
    service_name: str = "nlu-service"
    log_level: str = "INFO"
    llm: LLMConfig = None
    dpss: DPSSConfig = None
    event_bus: EventBusConfig = None
    
    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMConfig()
        if self.dpss is None:
            self.dpss = DPSSConfig()
        if self.event_bus is None:
            self.event_bus = EventBusConfig()


def load_config_from_env() -> NLUServiceConfig:
    """
    Load configuration from environment variables
    
    Returns:
        NLUServiceConfig instance with values from environment
    """
    # LLM configuration
    llm_config = LLMConfig(
        model=os.getenv("NLU_LLM_MODEL", "gpt-4-turbo"),
        temperature=float(os.getenv("NLU_LLM_TEMPERATURE", "0.2")),
        max_tokens=int(os.getenv("NLU_LLM_MAX_TOKENS", "2000")),
        timeout=float(os.getenv("NLU_LLM_TIMEOUT", "60.0"))
    )
    
    # DPSS configuration
    dpss_config = DPSSConfig(
        base_url=os.getenv("NLU_DPSS_BASE_URL", "http://localhost:8080"),
        timeout=float(os.getenv("NLU_DPSS_TIMEOUT", "30.0")),
        context_limit=int(os.getenv("NLU_DPSS_CONTEXT_LIMIT", "5"))
    )
    
    # Event bus configuration
    event_bus_config = EventBusConfig(
        input_topic=os.getenv("NLU_INPUT_TOPIC", "input:raw_message"),
        output_topic=os.getenv("NLU_OUTPUT_TOPIC", "nlu:uar_result"),
        consumer_group=os.getenv("NLU_CONSUMER_GROUP", "nlu-service"),
        consumer_name=os.getenv("NLU_CONSUMER_NAME", "nlu-worker")
    )
    
    # Main configuration
    config = NLUServiceConfig(
        service_name=os.getenv("NLU_SERVICE_NAME", "nlu-service"),
        log_level=os.getenv("NLU_LOG_LEVEL", "INFO"),
        llm=llm_config,
        dpss=dpss_config,
        event_bus=event_bus_config
    )
    
    return config


def load_config_from_dict(config_dict: Dict[str, Any]) -> NLUServiceConfig:
    """
    Load configuration from a dictionary
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        NLUServiceConfig instance
    """
    # Extract LLM config
    llm_dict = config_dict.get("llm", {})
    llm_config = LLMConfig(
        model=llm_dict.get("model", "gpt-4-turbo"),
        temperature=llm_dict.get("temperature", 0.2),
        max_tokens=llm_dict.get("max_tokens", 2000),
        timeout=llm_dict.get("timeout", 60.0)
    )
    
    # Extract DPSS config
    dpss_dict = config_dict.get("dpss", {})
    dpss_config = DPSSConfig(
        base_url=dpss_dict.get("base_url", "http://localhost:8080"),
        timeout=dpss_dict.get("timeout", 30.0),
        context_limit=dpss_dict.get("context_limit", 5)
    )
    
    # Extract event bus config
    event_bus_dict = config_dict.get("event_bus", {})
    event_bus_config = EventBusConfig(
        input_topic=event_bus_dict.get("input_topic", "input:raw_message"),
        output_topic=event_bus_dict.get("output_topic", "nlu:uar_result"),
        consumer_group=event_bus_dict.get("consumer_group", "nlu-service"),
        consumer_name=event_bus_dict.get("consumer_name", "nlu-worker")
    )
    
    # Main configuration
    config = NLUServiceConfig(
        service_name=config_dict.get("service_name", "nlu-service"),
        log_level=config_dict.get("log_level", "INFO"),
        llm=llm_config,
        dpss=dpss_config,
        event_bus=event_bus_config
    )
    
    return config


# Default configuration instance
default_config = NLUServiceConfig()


def get_config() -> NLUServiceConfig:
    """
    Get the current configuration, preferring environment variables
    
    Returns:
        NLUServiceConfig instance
    """
    return load_config_from_env() 