"""
Unit tests for BaseServiceManager and MessageHandlerRegistry

Tests the generic service management functionality.
"""
import asyncio
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any

from event_bus_framework.core.service_manager import BaseServiceManager, MessageHandlerRegistry
from event_bus_framework.core.interfaces import IEventBus


class TestMessageHandlerRegistry:
    """Test cases for MessageHandlerRegistry"""
    
    @pytest.fixture
    def registry(self):
        """Create a message handler registry"""
        return MessageHandlerRegistry("test-service")
    
    def test_initialization(self):
        """Test proper initialization"""
        registry = MessageHandlerRegistry("test-service")
        assert registry.service_name == "test-service"
        assert registry._handlers == {}
        assert registry._default_handler is None
    
    def test_register_handler(self, registry):
        """Test registering a single handler"""
        def test_handler(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        registry.register_handler("test_topic", test_handler)
        
        assert "test_topic" in registry._handlers
        assert registry._handlers["test_topic"] == test_handler
    
    def test_register_handlers_batch(self, registry):
        """Test batch registration of handlers"""
        def handler1(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        def handler2(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        handlers = {
            "topic1": handler1,
            "topic2": handler2
        }
        
        registry.register_handlers(handlers)
        
        assert len(registry._handlers) == 2
        assert registry._handlers["topic1"] == handler1
        assert registry._handlers["topic2"] == handler2
    
    def test_set_default_handler(self, registry):
        """Test setting default handler"""
        def default_handler(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        registry.set_default_handler(default_handler)
        assert registry._default_handler == default_handler
    
    def test_get_handler_existing(self, registry):
        """Test getting existing handler"""
        def test_handler(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        registry.register_handler("test_topic", test_handler)
        
        handler = registry.get_handler("test_topic")
        assert handler == test_handler
    
    def test_get_handler_default(self, registry):
        """Test getting default handler for unknown topic"""
        def default_handler(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        registry.set_default_handler(default_handler)
        
        handler = registry.get_handler("unknown_topic")
        assert handler == default_handler
    
    def test_get_handler_no_default(self, registry):
        """Test getting handler when no default is set"""
        with pytest.raises(ValueError, match="No handler found for topic"):
            registry.get_handler("unknown_topic")
    
    def test_get_all_handlers(self, registry):
        """Test getting all handlers"""
        def handler1(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        def handler2(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        registry.register_handler("topic1", handler1)
        registry.register_handler("topic2", handler2)
        
        all_handlers = registry.get_all_handlers()
        
        assert len(all_handlers) == 2
        assert all_handlers["topic1"] == handler1
        assert all_handlers["topic2"] == handler2
        
        # Verify it's a copy
        all_handlers["topic3"] = lambda: None
        assert "topic3" not in registry._handlers
    
    def test_get_topics(self, registry):
        """Test getting list of topics"""
        def handler(message_id: str, data: Dict[str, Any]) -> bool:
            return True
        
        registry.register_handler("topic1", handler)
        registry.register_handler("topic2", handler)
        
        topics = registry.get_topics()
        assert set(topics) == {"topic1", "topic2"}


class ConcreteServiceManager(BaseServiceManager):
    """Concrete implementation for testing BaseServiceManager"""
    
    def __init__(self):
        super().__init__()
        self.business_components_initialized = False
        self.message_handlers_dict = {}
    
    def get_service_name(self) -> str:
        return "test_service"
    
    def initialize_business_components(self) -> None:
        self.business_components_initialized = True
    
    def get_message_handlers(self) -> Dict[str, Any]:
        return self.message_handlers_dict
    
    def set_message_handlers(self, handlers: Dict[str, Any]):
        """Helper method for testing"""
        self.message_handlers_dict = handlers


class TestBaseServiceManager:
    """Test cases for BaseServiceManager"""
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus"""
        mock_bus = Mock(spec=IEventBus)
        return mock_bus
    
    @pytest.fixture
    def service_manager(self):
        """Create a concrete service manager for testing"""
        return ConcreteServiceManager()
    
    def test_initialization(self):
        """Test proper initialization"""
        manager = ConcreteServiceManager()
        
        assert manager.config is None
        assert manager.event_bus is None
        assert manager.event_manager is None
        assert manager.running is False
        assert manager._consumer_group is None
        assert manager._consumer_name is None
        assert manager._debug_mode is None
    
    def test_get_service_name(self, service_manager):
        """Test service name retrieval"""
        assert service_manager.get_service_name() == "test_service"
    
    @patch('event_bus_framework.core.service_manager.get_service_config')
    def test_load_configuration_success(self, mock_get_config, service_manager):
        """Test successful configuration loading"""
        mock_config = {
            'topics': {'subscribe': ['topic1']},
            'consumer_group': 'test-group'
        }
        mock_get_config.return_value = mock_config
        
        service_manager.load_configuration()
        
        assert service_manager.config == mock_config
        mock_get_config.assert_called_once_with("test_service")
    
    @patch('event_bus_framework.core.service_manager.get_service_config')
    def test_load_configuration_no_config(self, mock_get_config, service_manager):
        """Test configuration loading when no config found"""
        mock_get_config.return_value = None
        
        service_manager.load_configuration()
        
        assert service_manager.config == {}
    
    @patch('event_bus_framework.core.service_manager.get_service_config')
    @patch('event_bus_framework.core.service_manager.create_event_bus')
    def test_initialize_event_bus_success(self, mock_create_bus, mock_get_config, service_manager, mock_event_bus):
        """Test successful event bus initialization"""
        event_bus_config = {'type': 'redis', 'host': 'localhost'}
        mock_get_config.return_value = event_bus_config
        mock_create_bus.return_value = mock_event_bus
        
        service_manager.initialize_event_bus()
        
        assert service_manager.event_bus == mock_event_bus
        mock_create_bus.assert_called_once_with(
            config=event_bus_config,
            service_name="test_service"
        )
    
    @patch('event_bus_framework.core.service_manager.get_service_config')
    def test_initialize_event_bus_no_config(self, mock_get_config, service_manager):
        """Test event bus initialization with no config"""
        mock_get_config.return_value = None
        
        with pytest.raises(ValueError, match="Event bus configuration is required"):
            service_manager.initialize_event_bus()
    
    def test_get_subscription_config_defaults(self, service_manager):
        """Test getting subscription config with defaults"""
        service_manager.config = {}
        
        config = service_manager.get_subscription_config()
        
        assert config['input_topics'] == []
        assert config['consumer_group'] == 'test_service-group'
        assert config['consumer_name'] == 'test_service-worker'
        assert config['debug_mode'] is False
    
    def test_get_subscription_config_from_config(self, service_manager):
        """Test getting subscription config from service config"""
        service_manager.config = {
            'topics': {'subscribe': ['topic1', 'topic2']},
            'consumer_group': 'custom-group',
            'consumer_name': 'custom-worker',
            'debug_mode': 'true'
        }
        
        config = service_manager.get_subscription_config()
        
        assert config['input_topics'] == ['topic1', 'topic2']
        assert config['consumer_group'] == 'custom-group'
        assert config['consumer_name'] == 'custom-worker'
        assert config['debug_mode'] is True
    
    def test_get_subscription_config_overrides(self, service_manager):
        """Test subscription config with manual overrides"""
        service_manager.config = {
            'consumer_group': 'config-group',
            'debug_mode': False
        }
        
        service_manager.set_consumer_config(
            consumer_group='override-group',
            debug_mode=True
        )
        
        config = service_manager.get_subscription_config()
        
        assert config['consumer_group'] == 'override-group'
        assert config['debug_mode'] is True
    
    def test_set_consumer_config(self, service_manager):
        """Test setting consumer configuration"""
        service_manager.set_consumer_config(
            consumer_group='test-group',
            consumer_name='test-worker',
            debug_mode=True
        )
        
        assert service_manager._consumer_group == 'test-group'
        assert service_manager._consumer_name == 'test-worker'
        assert service_manager._debug_mode is True
    
    @patch('event_bus_framework.core.service_manager.EventSubscriptionManager')
    def test_setup_event_subscriptions_success(self, mock_manager_class, service_manager, mock_event_bus):
        """Test successful event subscription setup"""
        # Setup
        service_manager.event_bus = mock_event_bus
        service_manager.config = {
            'topics': {'subscribe': ['topic1', 'topic2']},
            'consumer_group': 'test-group',
            'consumer_name': 'test-worker',
            'debug_mode': False
        }
        
        def handler1(msg_id, data): return True
        def handler2(msg_id, data): return True
        
        service_manager.set_message_handlers({
            'topic1': handler1,
            'topic2': handler2
        })
        
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Execute
        service_manager.setup_event_subscriptions()
        
        # Verify
        mock_manager_class.assert_called_once_with(
            event_bus=mock_event_bus,
            consumer_group='test-group',
            consumer_name='test-worker',
            debug_mode=False,
            service_name='test_service'
        )
        
        mock_manager.register_handler.assert_any_call('topic1', handler1)
        mock_manager.register_handler.assert_any_call('topic2', handler2)
        mock_manager.setup_subscriptions.assert_called_once()
        
        assert service_manager.event_manager == mock_manager
    
    @pytest.mark.asyncio
    async def test_start_async_success(self, service_manager):
        """Test successful async service start"""
        with patch.multiple(
            service_manager,
            load_configuration=Mock(),
            initialize_event_bus=Mock(),
            initialize_business_components=Mock(),
            setup_event_subscriptions=Mock()
        ):
            await service_manager.start_async()
            
            assert service_manager.running is True
            service_manager.load_configuration.assert_called_once()
            service_manager.initialize_event_bus.assert_called_once()
            service_manager.initialize_business_components.assert_called_once()
            service_manager.setup_event_subscriptions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_async_failure(self, service_manager):
        """Test async service start with failure"""
        with patch.object(service_manager, 'load_configuration', side_effect=Exception("Config error")):
            with pytest.raises(Exception, match="Config error"):
                await service_manager.start_async()
            
            assert service_manager.running is False
    
    @pytest.mark.asyncio
    async def test_stop_async(self, service_manager):
        """Test async service stop"""
        service_manager.running = True
        mock_event_bus = Mock()
        mock_event_bus.stop_all_subscriptions = Mock()
        service_manager.event_bus = mock_event_bus
        
        await service_manager.stop_async()
        
        assert service_manager.running is False
        mock_event_bus.stop_all_subscriptions.assert_called_once()
    
    def test_start_sync(self, service_manager):
        """Test synchronous service start"""
        with patch('asyncio.run') as mock_run:
            service_manager.start()
            mock_run.assert_called_once()
    
    def test_stop_sync_no_loop(self, service_manager):
        """Test synchronous service stop without running loop"""
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_get_loop.return_value.is_running.return_value = False
            
            with patch('asyncio.run') as mock_run:
                service_manager.stop()
                mock_run.assert_called_once()
    
    def test_stop_sync_with_loop(self, service_manager):
        """Test synchronous service stop with running loop"""
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop
            
            with patch('asyncio.create_task') as mock_create_task:
                service_manager.stop()
                mock_create_task.assert_called_once()
    
    def test_is_running(self, service_manager):
        """Test running status check"""
        assert service_manager.is_running() is False
        
        service_manager.running = True
        assert service_manager.is_running() is True
    
    def test_get_subscribed_topics_no_manager(self, service_manager):
        """Test getting subscribed topics when no event manager"""
        topics = service_manager.get_subscribed_topics()
        assert topics == []
    
    def test_get_subscribed_topics_with_manager(self, service_manager):
        """Test getting subscribed topics with event manager"""
        mock_manager = Mock()
        mock_manager.get_registered_topics.return_value = ['topic1', 'topic2']
        service_manager.event_manager = mock_manager
        
        topics = service_manager.get_subscribed_topics()
        assert topics == ['topic1', 'topic2']


if __name__ == "__main__":
    pytest.main([__file__]) 