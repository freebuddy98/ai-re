"""
Unit tests for EventSubscriptionManager

Tests the generic event subscription management functionality.
"""
import asyncio
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any

from event_bus_framework.core.subscription_manager import EventSubscriptionManager
from event_bus_framework.core.interfaces import IEventBus


class TestEventSubscriptionManager:
    """Test cases for EventSubscriptionManager"""
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus"""
        mock_bus = Mock(spec=IEventBus)
        mock_bus.subscribe = Mock()
        mock_bus.acknowledge = Mock(return_value=True)
        mock_bus.redis_client = Mock()
        mock_bus._build_topic_key = Mock(side_effect=lambda x: f"stream:{x}")
        return mock_bus
    
    @pytest.fixture
    def subscription_manager(self, mock_event_bus):
        """Create a subscription manager instance"""
        return EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test-group",
            consumer_name="test-consumer",
            debug_mode=False,
            service_name="test-service"
        )
    
    @pytest.fixture
    def debug_subscription_manager(self, mock_event_bus):
        """Create a subscription manager with debug mode enabled"""
        return EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test-group",
            consumer_name="test-consumer",
            debug_mode=True,
            service_name="test-service"
        )
    
    def test_initialization(self, mock_event_bus):
        """Test proper initialization of EventSubscriptionManager"""
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test-group",
            consumer_name="test-consumer",
            debug_mode=True,
            service_name="test-service"
        )
        
        assert manager.event_bus == mock_event_bus
        assert manager.consumer_group_name == "test-group"
        assert manager.consumer_name == "test-consumer"
        assert manager.debug_mode is True
        assert manager.service_name == "test-service"
        assert manager.topic_handlers == {}
    
    def test_register_handler(self, subscription_manager):
        """Test registering a single handler"""
        def test_handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        subscription_manager.register_handler("test_topic", test_handler)
        
        assert "test_topic" in subscription_manager.topic_handlers
        assert subscription_manager.topic_handlers["test_topic"] == test_handler
    
    def test_register_handlers_batch(self, subscription_manager):
        """Test batch registration of handlers"""
        def handler1(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        def handler2(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        handlers = {
            "topic1": handler1,
            "topic2": handler2
        }
        
        subscription_manager.register_handlers(handlers)
        
        assert len(subscription_manager.topic_handlers) == 2
        assert subscription_manager.topic_handlers["topic1"] == handler1
        assert subscription_manager.topic_handlers["topic2"] == handler2
    
    def test_get_registered_topics(self, subscription_manager):
        """Test getting list of registered topics"""
        def handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        subscription_manager.register_handler("topic1", handler)
        subscription_manager.register_handler("topic2", handler)
        
        topics = subscription_manager.get_registered_topics()
        assert set(topics) == {"topic1", "topic2"}
    
    def test_unregister_handler(self, subscription_manager):
        """Test unregistering a handler"""
        def handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        subscription_manager.register_handler("test_topic", handler)
        assert "test_topic" in subscription_manager.topic_handlers
        
        result = subscription_manager.unregister_handler("test_topic")
        assert result is True
        assert "test_topic" not in subscription_manager.topic_handlers
        
        # Test unregistering non-existent handler
        result = subscription_manager.unregister_handler("non_existent")
        assert result is False
    
    def test_clear_handlers(self, subscription_manager):
        """Test clearing all handlers"""
        def handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        subscription_manager.register_handler("topic1", handler)
        subscription_manager.register_handler("topic2", handler)
        
        assert len(subscription_manager.topic_handlers) == 2
        
        subscription_manager.clear_handlers()
        assert len(subscription_manager.topic_handlers) == 0
    
    def test_reset_consumer_groups_debug_mode(self, debug_subscription_manager, mock_event_bus):
        """Test consumer group reset in debug mode"""
        def handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        debug_subscription_manager.register_handler("topic1", handler)
        debug_subscription_manager.register_handler("topic2", handler)
        
        # Mock Redis client methods
        mock_event_bus.redis_client.xgroup_destroy = Mock()
        
        debug_subscription_manager._reset_consumer_groups_for_debug()
        
        # Verify xgroup_destroy was called for each topic
        expected_calls = [
            call("stream:topic1", "test-group"),
            call("stream:topic2", "test-group")
        ]
        mock_event_bus.redis_client.xgroup_destroy.assert_has_calls(expected_calls, any_order=True)
    
    def test_reset_consumer_groups_no_debug(self, subscription_manager, mock_event_bus):
        """Test that consumer groups are not reset when debug mode is off"""
        def handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        subscription_manager.register_handler("topic1", handler)
        
        mock_event_bus.redis_client.xgroup_destroy = Mock()
        
        subscription_manager._reset_consumer_groups_for_debug()
        
        # Verify xgroup_destroy was not called
        mock_event_bus.redis_client.xgroup_destroy.assert_not_called()
    
    def test_handle_sync_message_success(self, subscription_manager, mock_event_bus):
        """Test successful synchronous message handling"""
        def success_handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        subscription_manager._handle_sync_message(
            "msg-123", "test_topic", success_handler, {"data": "test"}
        )
        
        # Verify acknowledge was called
        mock_event_bus.acknowledge.assert_called_once_with(
            topic="test_topic",
            group_name="test-group",
            message_ids=["msg-123"]
        )
    
    def test_handle_sync_message_failure(self, subscription_manager, mock_event_bus):
        """Test failed synchronous message handling"""
        def failure_handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return False
        
        subscription_manager._handle_sync_message(
            "msg-123", "test_topic", failure_handler, {"data": "test"}
        )
        
        # Verify acknowledge was not called for failed message
        mock_event_bus.acknowledge.assert_not_called()
    
    def test_handle_sync_message_exception(self, subscription_manager, mock_event_bus):
        """Test synchronous message handling with exception"""
        def exception_handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            raise ValueError("Test exception")
        
        # Should not raise exception, should handle it gracefully
        subscription_manager._handle_sync_message(
            "msg-123", "test_topic", exception_handler, {"data": "test"}
        )
        
        # Verify acknowledge was not called for exception
        mock_event_bus.acknowledge.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_async_message_success(self, subscription_manager, mock_event_bus):
        """Test successful asynchronous message handling"""
        async def async_success_handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        # Mock the event loop
        with patch('asyncio.get_running_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            
            subscription_manager._handle_async_message(
                "msg-123", "test_topic", async_success_handler, {"data": "test"}
            )
            
            # Verify a task was created
            mock_loop.create_task.assert_called_once()
    
    def test_create_message_handler_sync(self, subscription_manager):
        """Test creating message handler wrapper for sync handler"""
        def sync_handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        wrapper = subscription_manager._create_message_handler("test_topic", sync_handler)
        
        # Test that wrapper is callable
        assert callable(wrapper)
        
        # Test wrapper execution (should not raise exception)
        wrapper("msg-123", {"envelope": "data"}, {"payload": "data"})
    
    def test_create_message_handler_async(self, subscription_manager):
        """Test creating message handler wrapper for async handler"""
        async def async_handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        wrapper = subscription_manager._create_message_handler("test_topic", async_handler)
        
        # Test that wrapper is callable
        assert callable(wrapper)
        
        # Test wrapper execution (should not raise exception)
        with patch('asyncio.get_running_loop'):
            wrapper("msg-123", {"envelope": "data"}, {"payload": "data"})
    
    def test_setup_subscriptions_success(self, subscription_manager, mock_event_bus):
        """Test successful subscription setup"""
        def handler1(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        def handler2(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        subscription_manager.register_handler("topic1", handler1)
        subscription_manager.register_handler("topic2", handler2)
        
        subscription_manager.setup_subscriptions()
        
        # Verify subscribe was called for each topic
        assert mock_event_bus.subscribe.call_count == 2
        
        # Check the calls
        calls = mock_event_bus.subscribe.call_args_list
        topics_called = [call[1]['topic'] for call in calls]
        assert set(topics_called) == {"topic1", "topic2"}
    
    def test_setup_subscriptions_no_handlers(self, subscription_manager, mock_event_bus):
        """Test subscription setup with no registered handlers"""
        subscription_manager.setup_subscriptions()
        
        # Verify subscribe was not called
        mock_event_bus.subscribe.assert_not_called()
    
    def test_setup_subscriptions_with_debug_reset(self, debug_subscription_manager, mock_event_bus):
        """Test subscription setup with debug mode consumer group reset"""
        def handler(message_id: str, message_data: Dict[str, Any]) -> bool:
            return True
        
        debug_subscription_manager.register_handler("test_topic", handler)
        
        # Mock Redis client
        mock_event_bus.redis_client.xgroup_destroy = Mock()
        
        debug_subscription_manager.setup_subscriptions()
        
        # Verify consumer group was reset
        mock_event_bus.redis_client.xgroup_destroy.assert_called_once_with(
            "stream:test_topic", "test-group"
        )
        
        # Verify subscription was set up
        mock_event_bus.subscribe.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 