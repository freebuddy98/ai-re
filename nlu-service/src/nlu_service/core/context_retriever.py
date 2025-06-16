"""
ContextRetriever component

This module implements the ContextRetriever class that fetches dialogue context
from the DPSS service via REST API.
"""
import logging
from typing import Optional, Dict, Any

import httpx

# DialogueContext is now defined in config/dialogue_context.yml
# We work with Dict[str, Any] for dialogue context data


logger = logging.getLogger(__name__)


class ContextRetriever:
    """
    Context Retriever component
    
    Responsible for fetching dialogue context from DPSS service.
    As defined in design document section 2.1.
    """
    
    def __init__(self, dpss_base_url: str, timeout: float = 30.0):
        """
        Initialize ContextRetriever
        
        Args:
            dpss_base_url: Base URL of DPSS service (e.g., "http://dpss-service:8080")
            timeout: HTTP request timeout in seconds
        """
        self.dpss_base_url = dpss_base_url.rstrip('/')
        self.dpss_context_url = f"{self.dpss_base_url}/api/v1/dpss/context"
        self.timeout = timeout
        
        # Create async HTTP client
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def get_dialogue_context(
        self, 
        channel_id: str, 
        limit: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Get dialogue context from DPSS service
        
        Args:
            channel_id: Channel ID to get context for
            limit: Maximum number of recent history items to fetch
            
        Returns:
            Dict[str, Any] containing dialogue context if successful, None if failed
        """
        try:
            logger.debug(f"Fetching dialogue context for channel {channel_id}")
            
            params = {
                "channel_id": channel_id,
                "limit": limit
            }
            
            response = await self.client.get(
                self.dpss_context_url,
                params=params,
                headers={"X-Request-ID": f"nlu-context-{channel_id}"}
            )
            
            if response.status_code == 200:
                context_data = response.json()
                # Return as dictionary since DialogueContext schema is now in YAML
                logger.debug(f"Successfully retrieved context for channel {channel_id}")
                return context_data
            elif response.status_code == 404:
                logger.warning(f"Context not found for channel {channel_id}")
                return None
            else:
                logger.error(
                    f"DPSS API returned status {response.status_code} for channel {channel_id}: {response.text}"
                )
                return None
                
        except httpx.RequestError as e:
            logger.error(f"Network error fetching context for channel {channel_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching context for channel {channel_id}: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose() 