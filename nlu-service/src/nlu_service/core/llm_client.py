"""
LLMClient component

This module implements the LLMClient class that communicates with external LLM services
using the LiteLLM library for unified API access.
"""
import logging
from typing import Optional

try:
    import litellm
except ImportError:
    litellm = None

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM Client component
    
    Responsible for calling external LLM services using LiteLLM.
    As defined in design document section 2.1.
    """
    
    def __init__(
        self,
        default_model: str = "gpt-4-turbo",
        default_temperature: float = 0.2,
        default_max_tokens: int = 2000,
        timeout: float = 60.0
    ):
        """
        Initialize LLMClient
        
        Args:
            default_model: Default LLM model to use
            default_temperature: Default temperature for generation
            default_max_tokens: Default max tokens for generation
            timeout: Request timeout in seconds
        """
        if litellm is None:
            raise ImportError("litellm is required but not installed. Please install with: pip install litellm")
        
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.timeout = timeout
        
        # Configure LiteLLM
        litellm.set_verbose = False  # Set to True for debugging
        
        logger.debug(f"LLMClient initialized with model: {default_model}")
    
    async def call_llm_api(
        self, 
        prompt_content: str, 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """
        Call LLM API with the given prompt
        
        Args:
            prompt_content: The complete prompt to send to LLM
            model: Model to use (defaults to default_model)
            temperature: Temperature for generation (defaults to default_temperature)
            max_tokens: Max tokens for generation (defaults to default_max_tokens)
            
        Returns:
            LLM response string if successful, None if failed
        """
        try:
            # Use provided parameters or defaults
            model_to_use = model or self.default_model
            temp_to_use = temperature if temperature is not None else self.default_temperature
            tokens_to_use = max_tokens if max_tokens is not None else self.default_max_tokens
            
            logger.debug(f"Calling LLM API with model: {model_to_use}")
            logger.debug(f"Prompt length: {len(prompt_content)} characters")
            
            # Prepare messages for LiteLLM
            messages = [
                {"role": "user", "content": prompt_content}
            ]
            
            # Call LiteLLM async completion
            response = await litellm.acompletion(
                model=model_to_use,
                messages=messages,
                temperature=temp_to_use,
                max_tokens=tokens_to_use,
                timeout=self.timeout
            )
            
            # Extract response content
            if response and response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    logger.debug(f"LLM API call successful, response length: {len(content)} characters")
                    return content.strip()
                else:
                    logger.error("LLM API returned empty content")
                    return None
            else:
                logger.error("LLM API returned no choices")
                return None
                
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None
    
    def get_model_info(self) -> dict:
        """Get information about the current model configuration"""
        return {
            "default_model": self.default_model,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
            "timeout": self.timeout
        } 