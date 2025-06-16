"""
Message Handlers

Contains all message handling logic for different event types.
Separated from main.py for better organization and maintainability.
"""
from typing import Dict, Any
from event_bus_framework import get_logger

logger = get_logger("nlu_service.message_handlers")


class MessageHandlers:
    """
    Centralized message handlers for different event types.
    
    This class contains all the message processing logic,
    keeping the main service class clean and focused.
    """
    
    def __init__(self, nlu_processor):
        """
        Initialize message handlers with NLU processor dependency
        
        Args:
            nlu_processor: NLU processor instance for message processing
        """
        self.nlu_processor = nlu_processor
    
    async def handle_user_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Handle user raw messages (primary NLU processing)
        
        Args:
            message_id: Unique message ID
            message_data: Message payload data
            
        Returns:
            bool: True if processing was successful
        """
        try:
            logger.info(f"Processing user message {message_id}")
            
            # Validate message structure for user messages
            if not self._validate_user_message(message_data):
                logger.error(f"Invalid user message structure for message {message_id}")
                return False
            
            # Process the message using NLU processor
            result = await self.nlu_processor.process_message(message_data)
            
            if result and result.status.value == "success":
                logger.debug(f"Successfully processed user message {message_id}")
                return True
            else:
                logger.error(f"Failed to process user message {message_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling user message {message_id}: {e}")
            return False
    
    async def handle_intent_request(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Handle intent-specific requests
        
        Args:
            message_id: Unique message ID
            message_data: Message payload data
            
        Returns:
            bool: True if processing was successful
        """
        try:
            logger.debug(f"Processing intent request {message_id}")
            
            # Validate message structure for intent requests
            if not self._validate_intent_request(message_data):
                logger.error(f"Invalid intent request structure for message {message_id}")
                return False
            
            # Process intent-specific logic
            result = await self.nlu_processor.process_intent_request(message_data)
            
            if result and result.status.value == "success":
                logger.debug(f"Successfully processed intent request {message_id}")
                return True
            else:
                logger.error(f"Failed to process intent request {message_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling intent request {message_id}: {e}")
            return False
    
    async def handle_entity_extraction(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Handle entity extraction requests
        
        Args:
            message_id: Unique message ID
            message_data: Message payload data
            
        Returns:
            bool: True if processing was successful
        """
        try:
            logger.debug(f"Processing entity extraction {message_id}")
            
            # Validate message structure for entity extraction
            if not self._validate_entity_request(message_data):
                logger.error(f"Invalid entity request structure for message {message_id}")
                return False
            
            # Process entity extraction logic
            result = await self.nlu_processor.process_entity_extraction(message_data)
            
            if result and result.status.value == "success":
                logger.debug(f"Successfully processed entity extraction {message_id}")
                return True
            else:
                logger.error(f"Failed to process entity extraction {message_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling entity extraction {message_id}: {e}")
            return False
    
    async def handle_context_update(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Handle dialogue context updates
        
        Args:
            message_id: Unique message ID
            message_data: Message payload data
            
        Returns:
            bool: True if processing was successful
        """
        try:
            logger.debug(f"Processing context update {message_id}")
            
            # Validate message structure for context updates
            if not self._validate_context_update(message_data):
                logger.error(f"Invalid context update structure for message {message_id}")
                return False
            
            # Process context update logic
            result = await self.nlu_processor.process_context_update(message_data)
            
            if result and result.status.value == "success":
                logger.debug(f"Successfully processed context update {message_id}")
                return True
            else:
                logger.error(f"Failed to process context update {message_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling context update {message_id}: {e}")
            return False
    
    async def handle_unknown_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Handle unknown message types (fallback handler)
        
        Args:
            message_id: Unique message ID
            message_data: Message payload data
            
        Returns:
            bool: True if processing was successful
        """
        try:
            logger.warning(f"Processing unknown message type {message_id}")
            
            # Try to process with default NLU processor
            result = await self.nlu_processor.process_message(message_data)
            
            if result and result.status.value == "success":
                logger.debug(f"Successfully processed unknown message {message_id}")
                return True
            else:
                logger.error(f"Failed to process unknown message {message_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling unknown message {message_id}: {e}")
            return False
    
    def _validate_user_message(self, message_data: Dict[str, Any]) -> bool:
        """Validate user message structure based on events.yml schema"""
        try:
            logger.debug(f"Validating message data: {message_data}")
            logger.debug(f"Message data keys: {list(message_data.keys())}")
            
            # Check top-level required fields
            required_top_level = ['meta', 'user_id', 'username', 'platform', 'channel_id', 'content', 'raw_data']
            missing_fields = [field for field in required_top_level if field not in message_data]
            if missing_fields:
                logger.error(f"Missing required top-level fields: {missing_fields}")
                return False
            
            # Check meta structure
            meta = message_data.get('meta', {})
            required_meta_fields = ['event_id', 'source', 'timestamp']
            if not all(field in meta for field in required_meta_fields):
                return False
            
            # Check content structure
            content = message_data.get('content', {})
            required_content_fields = ['text', 'attachments']
            if not all(field in content for field in required_content_fields):
                return False
            
            # Validate data types
            if not isinstance(meta.get('timestamp'), int):
                return False
            
            if not isinstance(content.get('text'), str):
                return False
            
            if content.get('attachments') is not None and not isinstance(content.get('attachments'), list):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating user message: {e}")
            return False
    
    def _validate_intent_request(self, message_data: Dict[str, Any]) -> bool:
        """Validate intent request structure"""
        required_fields = ['user_id', 'text', 'context']
        return all(field in message_data for field in required_fields)
    
    def _validate_entity_request(self, message_data: Dict[str, Any]) -> bool:
        """Validate entity extraction request structure"""
        required_fields = ['user_id', 'text', 'entity_types']
        return all(field in message_data for field in required_fields)
    
    def _validate_context_update(self, message_data: Dict[str, Any]) -> bool:
        """Validate context update structure"""
        required_fields = ['user_id', 'context_data', 'update_type']
        return all(field in message_data for field in required_fields)


# TopicHandlerRegistry has been moved to event_bus_framework.core.service_manager.MessageHandlerRegistry
# This file now only contains the MessageHandlers class with business logic 