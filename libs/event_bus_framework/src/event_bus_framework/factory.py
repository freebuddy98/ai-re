"""
Event Bus Factory

Abstract factory pattern for creating event bus instances.
This decouples the application code from specific event bus implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .core.interfaces import IEventBus
from .adapters.redis_streams import RedisStreamEventBus
from .common.logger import get_logger

logger = get_logger("event_bus_factory")


class EventBusFactory(ABC):
    """Abstract factory for creating event bus instances"""
    
    @abstractmethod
    def create_event_bus(
        self, 
        config: Dict[str, Any], 
        service_name: str
    ) -> IEventBus:
        """
        Create an event bus instance
        
        Args:
            config: Event bus configuration
            service_name: Name of the service using the event bus
            
        Returns:
            IEventBus instance
        """
        pass


class RedisEventBusFactory(EventBusFactory):
    """Factory for creating Redis-based event bus instances"""
    
    def create_event_bus(
        self, 
        config: Dict[str, Any], 
        service_name: str
    ) -> IEventBus:
        """
        Create a Redis-based event bus instance
        
        Args:
            config: Event bus configuration containing Redis settings
            service_name: Name of the service using the event bus
            
        Returns:
            RedisStreamEventBus instance
        """
        try:
            # Extract Redis configuration
            redis_config = config.get('redis', {})
            redis_host = redis_config.get('host', 'localhost')
            redis_port = redis_config.get('port', 6379)
            redis_db = redis_config.get('db', 0)
            redis_password = redis_config.get('password', '')
            
            # Build Redis URL
            if redis_password:
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
            
            # Create event bus instance
            event_bus = RedisStreamEventBus(
                redis_url=redis_url,
                event_source_name=service_name,
                topic_prefix=config.get('stream_prefix', 'ai-re')
            )
            
            logger.debug(f"Created Redis event bus for service '{service_name}' at {redis_host}:{redis_port}")
            return event_bus
            
        except Exception as e:
            logger.error(f"Failed to create Redis event bus: {e}")
            raise


class EventBusFactoryRegistry:
    """Registry for event bus factories"""
    
    _factories: Dict[str, EventBusFactory] = {}
    
    @classmethod
    def register_factory(cls, bus_type: str, factory: EventBusFactory) -> None:
        """
        Register an event bus factory
        
        Args:
            bus_type: Type identifier for the event bus (e.g., 'redis', 'kafka')
            factory: Factory instance
        """
        cls._factories[bus_type] = factory
        logger.debug(f"Registered event bus factory for type: {bus_type}")
    
    @classmethod
    def get_factory(cls, bus_type: str) -> EventBusFactory:
        """
        Get a factory for the specified bus type
        
        Args:
            bus_type: Type identifier for the event bus
            
        Returns:
            EventBusFactory instance
            
        Raises:
            ValueError: If no factory is registered for the bus type
        """
        if bus_type not in cls._factories:
            raise ValueError(f"No factory registered for event bus type: {bus_type}")
        
        return cls._factories[bus_type]
    
    @classmethod
    def create_event_bus(
        cls, 
        config: Dict[str, Any], 
        service_name: str,
        bus_type: Optional[str] = None
    ) -> IEventBus:
        """
        Create an event bus instance using the appropriate factory
        
        Args:
            config: Event bus configuration
            service_name: Name of the service using the event bus
            bus_type: Type of event bus to create (auto-detected if None)
            
        Returns:
            IEventBus instance
        """
        # Auto-detect bus type if not specified
        if bus_type is None:
            bus_type = cls._detect_bus_type(config)
        
        factory = cls.get_factory(bus_type)
        return factory.create_event_bus(config, service_name)
    
    @classmethod
    def _detect_bus_type(cls, config: Dict[str, Any]) -> str:
        """
        Auto-detect the event bus type from configuration
        
        Args:
            config: Event bus configuration
            
        Returns:
            Detected bus type
        """
        # Check for Redis configuration
        if 'redis' in config:
            return 'redis'
        
        # Check for connection URL
        connection_url = config.get('connection_url', '')
        if connection_url:
            parsed = urlparse(connection_url)
            if parsed.scheme in ['redis', 'rediss']:
                return 'redis'
        
        # Default to Redis
        logger.warning("Could not auto-detect event bus type, defaulting to Redis")
        return 'redis'


# Register default factories
EventBusFactoryRegistry.register_factory('redis', RedisEventBusFactory())


def create_event_bus(
    config: Dict[str, Any], 
    service_name: str,
    bus_type: Optional[str] = None
) -> IEventBus:
    """
    Convenience function to create an event bus instance
    
    Args:
        config: Event bus configuration
        service_name: Name of the service using the event bus
        bus_type: Type of event bus to create (auto-detected if None)
        
    Returns:
        IEventBus instance
    """
    return EventBusFactoryRegistry.create_event_bus(config, service_name, bus_type) 