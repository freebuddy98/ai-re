"""
NLU Service Factory

Factory pattern for creating NLU service components with proper dependency injection.
"""
from typing import Dict, Any, List
from event_bus_framework import IEventBus

from .core.nlu_processor import NLUProcessor
from .core.context_retriever import ContextRetriever
from .core.prompt_builder import PromptBuilder
from .core.llm_client import LLMClient
from .core.response_validator import ResponseValidator
from .config import NLUServiceConfig


class NLUProcessorFactory:
    """Factory for creating NLU processor instances"""
    
    @staticmethod
    def create_nlu_processor(
        event_bus: IEventBus,
        config: NLUServiceConfig,
        input_topics: List[str],
        output_topics: List[str]
    ) -> NLUProcessor:
        """
        Create a fully configured NLU processor instance
        
        Args:
            event_bus: Event bus interface for publishing results
            config: NLU service configuration
            input_topics: List of topics to subscribe to
            output_topics: List of topics to publish to
            
        Returns:
            Configured NLUProcessor instance
        """
        # Create context retriever
        context_retriever = ContextRetriever(
            dpss_base_url=config.dpss.base_url,
            timeout=config.dpss.timeout
        )
        
        # Create prompt builder
        prompt_builder = PromptBuilder()
        
        # Create LLM client
        llm_client = LLMClient(
            default_model=config.llm.model,
            default_temperature=config.llm.temperature,
            default_max_tokens=config.llm.max_tokens,
            timeout=config.llm.timeout
        )
        
        # Create response validator
        response_validator = ResponseValidator()
        
        # Create processor configuration
        processor_config = {
            "input_topics": input_topics,
            "output_topics": output_topics,
            "consumer_group": config.event_bus.consumer_group,
            "consumer_name": config.event_bus.consumer_name
        }
        
        # Create and return NLU processor
        return NLUProcessor(
            event_bus=event_bus,
            context_retriever=context_retriever,
            prompt_builder=prompt_builder,
            llm_client=llm_client,
            response_validator=response_validator,
            config=processor_config
        ) 