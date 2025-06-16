"""
ResponseValidator component

This module implements the ResponseValidator class that validates and parses
LLM responses to ensure they conform to the UAR schema.
"""
import json
import logging
import re
from typing import Optional, Dict, Type

from pydantic import BaseModel, ValidationError

from ..models.uar import UAR


logger = logging.getLogger(__name__)


class ResponseValidator:
    """
    Response Validator component
    
    Responsible for validating and parsing LLM responses using Pydantic models.
    As defined in design document section 2.1.
    """
    
    def __init__(self, uar_schema_model: Type[BaseModel] = UAR):
        """
        Initialize ResponseValidator
        
        Args:
            uar_schema_model: Pydantic model class for UAR validation
        """
        self.uar_schema_model = uar_schema_model
        logger.debug(f"ResponseValidator initialized with schema: {uar_schema_model.__name__}")
    
    def validate_and_parse_response(self, llm_response_str: str) -> Optional[Dict]:
        """
        Validate and parse LLM response string into UAR
        
        Args:
            llm_response_str: Raw response string from LLM
            
        Returns:
            Validated UAR dictionary if successful, None if validation failed
        """
        try:
            logger.debug(f"Validating LLM response, length: {len(llm_response_str)} characters")
            
            # Extract JSON from response if it's wrapped in markdown or other formatting
            json_content = self._extract_json_from_response(llm_response_str)
            if not json_content:
                logger.error("No valid JSON found in LLM response")
                return None
            
            # Parse JSON
            try:
                response_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                logger.debug(f"Problematic JSON content: {json_content[:500]}...")
                return None
            
            # Validate against UAR schema
            try:
                uar_instance = self.uar_schema_model(**response_data)
                validated_data = uar_instance.model_dump()
                logger.debug("LLM response successfully validated against UAR schema")
                return validated_data
            except ValidationError as e:
                logger.error(f"UAR schema validation failed: {e}")
                logger.debug(f"Validation errors: {e.errors()}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error during response validation: {e}")
            return None
    
    def _extract_json_from_response(self, response_str: str) -> Optional[str]:
        """
        Extract JSON content from LLM response that might be wrapped in markdown or other formatting
        
        Args:
            response_str: Raw LLM response string
            
        Returns:
            Extracted JSON string if found, None otherwise
        """
        try:
            # First, try to find JSON within markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_str, re.DOTALL)
            if json_match:
                return json_match.group(1).strip()
            
            # Try to find JSON starting with { and ending with }
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if json_match:
                return json_match.group(0).strip()
            
            # If no specific patterns found, try the entire response (stripped)
            stripped_response = response_str.strip()
            if stripped_response.startswith('{') and stripped_response.endswith('}'):
                return stripped_response
            
            logger.warning("Could not extract JSON from LLM response")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JSON from response: {e}")
            return None
    
    def get_schema_json_string(self) -> str:
        """
        Get UAR schema as JSON string for use in prompts
        
        Returns:
            JSON schema definition as string
        """
        try:
            schema = self.uar_schema_model.model_json_schema()
            return json.dumps(schema, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error generating schema JSON string: {e}")
            return "{}" 