"""
NLUProcessor component

This module implements the main NLUProcessor class that orchestrates the entire
NLU processing pipeline as defined in the design document.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

# DialogueContext is now defined in config/dialogue_context.yml
# We work with Dict[str, Any] for dialogue context data
from ..models.uar import UAR, UARStatus, UARIntent, IntentName
from .context_retriever import ContextRetriever
from .prompt_builder import PromptBuilder
from .llm_client import LLMClient
from .response_validator import ResponseValidator

# Import the canonical event-bus interface from the shared library
from event_bus_framework import IEventBus

logger = logging.getLogger(__name__)


class NLUProcessor:
    """
    NLU Processor component
    
    Main coordinator and orchestrator for the NLU service.
    As defined in design document section 2.1.
    """
    
    def __init__(
        self,
        event_bus: IEventBus,
        context_retriever: ContextRetriever,
        prompt_builder: PromptBuilder,
        llm_client: LLMClient,
        response_validator: ResponseValidator,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize NLUProcessor
        
        Args:
            event_bus: Event bus interface for publishing results
            context_retriever: Component for fetching dialogue context
            prompt_builder: Component for building LLM prompts
            llm_client: Component for calling LLM APIs
            response_validator: Component for validating LLM responses
            config: Configuration dictionary with topics and consumer_group
        """
        self.event_bus = event_bus
        self.context_retriever = context_retriever
        self.prompt_builder = prompt_builder
        self.llm_client = llm_client
        self.response_validator = response_validator
        self.config = config or {}
        
        # Event-bus related configuration - updated structure
        topics = self.config.get("topics", {})
        self.input_topic = topics.get("input", "user_message_raw")
        self.output_topic = topics.get("output", "nlu_uar_result")
        self.consumer_group = self.config.get("consumer_group", "nlu-service")
        
        logger.debug("NLUProcessor initialized successfully")
    
    async def handle_raw_message(
        self, 
        redis_msg_id: str, 
        event_envelope: Dict[str, Any], 
        raw_message_payload: Dict[str, Any]
    ) -> None:
        """
        Main handler for processing raw messages
        
        Args:
            redis_msg_id: Message ID from Redis Stream
            event_envelope: Complete event envelope
            raw_message_payload: user_message_raw payload data following events.yml schema
        """
        try:
            logger.debug(f"Processing raw message {redis_msg_id}")
            
            # Extract key information from user_message_raw schema
            channel_id = raw_message_payload.get("channel_id")
            meta = raw_message_payload.get("meta", {})
            original_message_ref = meta.get("event_id")
            content = raw_message_payload.get("content", {})
            raw_text = content.get("text", "")
            
            if not channel_id or not original_message_ref or not raw_text:
                logger.error(f"Missing required fields in raw message: {raw_message_payload}")
                await self._acknowledge_message(redis_msg_id)
                return
            
            # Step 1: Get context from DPSS
            context = await self._get_context_for_message(channel_id)
            
            # Step 2: Build prompt
            prompt = await self._build_prompt(raw_message_payload, context)
            if prompt is None:
                logger.error(f"Failed to build prompt for message {original_message_ref}")
                await self._acknowledge_message(redis_msg_id)
                return
            
            # Step 3: Call LLM and validate response
            uar_payload = await self._call_llm_and_validate(prompt, original_message_ref)
            if uar_payload is None:
                logger.error(f"LLM processing failed for message {original_message_ref}")
                await self._acknowledge_message(redis_msg_id)
                return
            
            # Step 4: Add metadata to UAR
            final_uar = self._add_metadata_to_uar(uar_payload, raw_message_payload)
            
            # Step 5: Publish UAR result
            success = await self._publish_uar_result(final_uar, channel_id)
            if success:
                logger.debug(f"Successfully processed message {original_message_ref}")
            else:
                logger.error(f"Failed to publish UAR for message {original_message_ref}")
            
            # Step 6: Acknowledge original message
            await self._acknowledge_message(redis_msg_id)
            
        except Exception as e:
            logger.error(f"Unexpected error processing message {redis_msg_id}: {e}")
            await self._acknowledge_message(redis_msg_id)
    
    async def _get_context_for_message(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dialogue context from DPSS for the message
        
        Args:
            channel_id: Channel ID to get context for
            
        Returns:
            Dict[str, Any] containing dialogue context if successful, None if failed
        """
        try:
            context = await self.context_retriever.get_dialogue_context(channel_id)
            if context:
                logger.debug(f"Retrieved context for channel {channel_id}")
            else:
                logger.warning(f"No context available for channel {channel_id}")
            return context
        except Exception as e:
            logger.error(f"Error getting context for channel {channel_id}: {e}")
            return None
    
    async def _build_prompt(
        self, 
        raw_message_payload: Dict[str, Any], 
        context: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Build LLM prompt from message and context
        
        Args:
            raw_message_payload: Raw message data
            context: Dialogue context dictionary (can be None)
            
        Returns:
            Prompt string if successful, None if failed
        """
        try:
            # Get UAR schema definition
            uar_schema_def = self.response_validator.get_schema_json_string()
            
            # Build prompt
            prompt = self.prompt_builder.build_llm_prompt(
                raw_message_payload, context, uar_schema_def
            )
            
            logger.debug(f"Built prompt with length: {len(prompt)} characters")
            return prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            return None
    
    async def _call_llm_and_validate(
        self, 
        prompt: str, 
        original_message_id_for_log: str
    ) -> Optional[Dict[str, Any]]:
        """
        Call LLM and validate the response
        
        Args:
            prompt: Complete prompt to send to LLM
            original_message_id_for_log: Original message ID for logging
            
        Returns:
            Validated UAR payload if successful, None if failed
        """
        try:
            logger.debug(f"Calling LLM for message {original_message_id_for_log}")
            
            # Call LLM
            llm_response = await self.llm_client.call_llm_api(prompt)
            if llm_response is None:
                logger.error(f"LLM call failed for message {original_message_id_for_log}")
                return None
            
            # Validate response
            uar_payload = self.response_validator.validate_and_parse_response(llm_response)
            if uar_payload is None:
                logger.error(f"LLM response validation failed for message {original_message_id_for_log}")
                logger.debug(f"Raw LLM response: {llm_response[:500]}...")
                return None
            
            logger.debug(f"LLM processing successful for message {original_message_id_for_log}")
            return uar_payload
            
        except Exception as e:
            logger.error(f"Error in LLM call/validation for message {original_message_id_for_log}: {e}")
            return None
    
    def _add_metadata_to_uar(
        self, 
        uar_payload: Dict[str, Any], 
        raw_message_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add metadata to UAR payload
        
        Args:
            uar_payload: UAR data from LLM validation
            raw_message_payload: Original user_message_raw payload following events.yml schema
            
        Returns:
            Complete UAR with metadata
        """
        # Extract information from user_message_raw schema
        meta = raw_message_payload.get("meta", {})
        content = raw_message_payload.get("content", {})
        
        # Add required metadata
        uar_payload["uar_id"] = str(uuid.uuid4())
        uar_payload["original_message_ref"] = meta.get("event_id", "unknown")
        uar_payload["user_id"] = raw_message_payload.get("user_id", "unknown")
        uar_payload["channel_id"] = raw_message_payload.get("channel_id", "unknown")
        uar_payload["processing_timestamp_utc"] = datetime.utcnow().isoformat() + "Z"
        uar_payload["raw_text_processed"] = content.get("text", "")
        
        # Ensure status is set if not already present
        if "status" not in uar_payload:
            uar_payload["status"] = "success"
        
        return uar_payload
    
    async def _publish_uar_result(
        self, 
        uar_payload: Dict[str, Any], 
        channel_id: str
    ) -> bool:
        """
        Publish UAR result to event bus
        
        Args:
            uar_payload: Complete UAR payload
            channel_id: Channel ID for dialogue session hint
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            message_id = self.event_bus.publish(
                topic=self.output_topic,
                message_data=uar_payload
            )
            
            if message_id:
                logger.debug(f"Published UAR result with message ID: {message_id}")
                return True
            else:
                logger.error("Failed to publish UAR result")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing UAR result: {e}")
            return False
    
    async def _acknowledge_message(self, redis_msg_id: str) -> None:
        """
        Acknowledge message as processed
        
        Args:
            redis_msg_id: Redis message ID to acknowledge
        """
        try:
            self.event_bus.acknowledge(
                topic=self.input_topic,
                group_name=self.consumer_group,
                message_ids=[redis_msg_id]
            )
            logger.debug(f"Acknowledged message {redis_msg_id}")
        except Exception as e:
            logger.error(f"Error acknowledging message {redis_msg_id}: {e}")
    
    # ---------------------------------------------------------------------
    # Convenience helpers (non-stream usage)
    # ---------------------------------------------------------------------

    async def process_message(self, raw_message: Dict[str, Any]) -> UAR:
        """A convenience wrapper that mirrors the internal pipeline for unit tests.

        Unlike *handle_raw_message* this method is **not** tied to Redis Streams. It
        executes the NLU pipeline synchronously for a single *raw_message* payload
        dictionary and returns the resulting UAR (or an *error* UAR if something
        failed). This keeps our unit tests simple while production traffic still
        goes through *handle_raw_message* via the event-bus consumer.
        """

        # Extract data according to user_message_raw schema
        channel_id = raw_message.get("channel_id")
        meta = raw_message.get("meta", {})
        content = raw_message.get("content", {})
        original_message_ref = meta.get("event_id", "unknown")
        raw_text = content.get("text", "")

        # Default error UAR template (filled only when an unrecoverable error
        # happens before a valid UAR is produced)
        error_intent = UARIntent(
            name=IntentName.UNKNOWN,
            confidence=0.0
        )
        
        error_uar = UAR(
            original_message_ref=original_message_ref,
            user_id=raw_message.get("user_id", "unknown"),
            channel_id=channel_id or "unknown",
            raw_text_processed=raw_text,
            status=UARStatus.PROCESSING_ERROR,
            intent=error_intent,
            entities=[],
            relations=[],
            llm_trace=None,
        )

        try:
            # 1) Context
            context = await self._get_context_for_message(channel_id) if channel_id else None

            # 2) Prompt
            prompt = await self._build_prompt(raw_message, context)
            if prompt is None:
                return error_uar

            # 3) LLM + validation
            uar_payload = await self._call_llm_and_validate(prompt, original_message_ref)
            if uar_payload is None:
                return error_uar

            # 4) Metadata and object
            final_payload = self._add_metadata_to_uar(uar_payload, raw_message)
            return UAR.model_validate(final_payload)
        except Exception as exc:
            logger.error(f"process_message failed: {exc}")
            return error_uar 