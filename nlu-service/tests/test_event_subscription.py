"""
事件订阅功能测试

测试统一的事件订阅管理器和消息处理器。
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List

from event_bus_framework.core.subscription_manager import EventSubscriptionManager


class MockEventBus:
    """测试用的模拟事件总线"""
    
    def __init__(self):
        self.subscriptions = {}
        self.messages = {}
        self.acknowledged_messages = []
        self.redis_client = Mock()  # 用于调试模式测试的模拟Redis客户端
        
    def subscribe(self, topic: str, handler, group_name: str, 
                 consumer_name: str):
        """模拟订阅方法"""
        self.subscriptions[topic] = {
            'handler': handler,
            'group_name': group_name,
            'consumer_name': consumer_name
        }
        
    def acknowledge(self, topic: str, group_name: str, message_ids: List[str]) -> bool:
        """模拟确认方法"""
        for msg_id in message_ids:
            self.acknowledged_messages.append({
                'topic': topic,
                'group_name': group_name,
                'message_id': msg_id
            })
        return True
        
    def simulate_message(self, topic: str, message_id: str, event_envelope: Dict[str, Any], actual_payload: Dict[str, Any]):
        """模拟接收消息"""
        if topic in self.subscriptions:
            handler = self.subscriptions[topic]['handler']
            handler(message_id, event_envelope, actual_payload)
    
    def _build_topic_key(self, topic: str) -> str:
        """模拟构建主题键的方法"""
        return f"test:{topic}"


class TestEventSubscriptionManager:
    """测试统一的事件订阅管理器"""
    
    def test_register_and_setup_handlers(self):
        """测试注册处理器和设置订阅"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=False,
            service_name="test_service"
        )
        
        # 注册处理器
        handler1 = Mock(return_value=True)
        handler2 = Mock(return_value=True)
        
        manager.register_handler("topic1", handler1)
        manager.register_handler("topic2", handler2)
        
        # 设置订阅
        manager.setup_subscriptions()
        
        # 验证
        assert len(manager.topic_handlers) == 2
        assert "topic1" in manager.topic_handlers
        assert "topic2" in manager.topic_handlers
        assert len(mock_event_bus.subscriptions) == 2
        
        # 测试消息处理
        mock_event_bus.simulate_message("topic1", "msg1", {}, {"data": "test1"})
        handler1.assert_called_once_with("msg1", {"data": "test1"})
    
    def test_sync_message_handling(self):
        """测试同步消息处理和确认"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=False,
            service_name="test_service"
        )
        
        # 注册同步处理器
        sync_handler = Mock(return_value=True)
        manager.register_handler("test_topic", sync_handler)
        manager.setup_subscriptions()
        
        # 模拟消息
        message_id = "msg_123"
        event_envelope = {"envelope": "data"}
        actual_payload = {"payload": "data"}
        
        mock_event_bus.simulate_message("test_topic", message_id, event_envelope, actual_payload)
        
        # 验证
        sync_handler.assert_called_once_with(message_id, actual_payload)
        assert len(mock_event_bus.acknowledged_messages) == 1
        assert mock_event_bus.acknowledged_messages[0]['message_id'] == message_id
    
    @pytest.mark.asyncio
    async def test_async_message_handling(self):
        """测试异步消息处理和确认"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=False,
            service_name="test_service"
        )
        
        # 注册异步处理器
        async_handler = AsyncMock(return_value=True)
        manager.register_handler("test_topic", async_handler)
        manager.setup_subscriptions()
        
        # 模拟消息
        message_id = "msg_456"
        event_envelope = {"envelope": "data"}
        actual_payload = {"payload": "data"}
        
        mock_event_bus.simulate_message("test_topic", message_id, event_envelope, actual_payload)
        
        # 等待异步处理
        await asyncio.sleep(0.1)
        
        # 验证
        async_handler.assert_called_once_with(message_id, actual_payload)
        assert len(mock_event_bus.acknowledged_messages) == 1
        assert mock_event_bus.acknowledged_messages[0]['message_id'] == message_id
    
    def test_failed_message_handling(self):
        """测试失败消息处理（不确认）"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=False,
            service_name="test_service"
        )
        
        # 注册失败的处理器
        failure_handler = Mock(return_value=False)
        manager.register_handler("test_topic", failure_handler)
        manager.setup_subscriptions()
        
        # 模拟消息
        message_id = "msg_failed"
        mock_event_bus.simulate_message("test_topic", message_id, {}, {"data": "test"})
        
        # 验证
        failure_handler.assert_called_once_with(message_id, {"data": "test"})
        assert len(mock_event_bus.acknowledged_messages) == 0  # 失败消息不确认
    
    def test_debug_mode_configuration(self):
        """测试调试模式配置"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=True,
            service_name="test_service"
        )
        
        # 注册处理器
        handler = Mock(return_value=True)
        manager.register_handler("test_topic", handler)
        
        # 设置订阅
        manager.setup_subscriptions()
        
        # 验证调试模式设置 - 订阅已成功创建
        assert "test_topic" in mock_event_bus.subscriptions
        subscription = mock_event_bus.subscriptions["test_topic"]
        assert subscription['group_name'] == 'test_group'
    
    def test_debug_mode_consumer_group_reset(self):
        """测试调试模式下消费者组重置"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=True,
            service_name="test_service"
        )
        
        # 注册处理器
        handler = Mock(return_value=True)
        manager.register_handler("test_topic", handler)
        
        # 设置订阅（会触发调试模式重置）
        manager.setup_subscriptions()
        
        # 验证Redis客户端的xgroup_destroy被调用
        mock_event_bus.redis_client.xgroup_destroy.assert_called_once_with(
            "test:test_topic", "test_group"
        )
    
    def test_consumption_lifecycle(self):
        """测试消费生命周期管理"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=False,
            service_name="test_service"
        )
        
        # 注册处理器
        handler = Mock(return_value=True)
        manager.register_handler("test_topic", handler)
        
        # 设置订阅
        manager.setup_subscriptions()
        
        # 验证订阅已创建
        assert "test_topic" in mock_event_bus.subscriptions
        
        # 模拟消息处理
        mock_event_bus.simulate_message("test_topic", "msg1", {}, {"data": "test"})
        handler.assert_called_once_with("msg1", {"data": "test"})
    
    @pytest.mark.asyncio
    async def test_async_consumption_lifecycle(self):
        """测试异步消费生命周期管理"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=False,
            service_name="test_service"
        )
        
        # 注册异步处理器
        async_handler = AsyncMock(return_value=True)
        manager.register_handler("test_topic", async_handler)
        
        # 设置订阅
        manager.setup_subscriptions()
        
        # 模拟消息处理
        mock_event_bus.simulate_message("test_topic", "msg1", {}, {"data": "test"})
        
        # 等待异步处理
        await asyncio.sleep(0.1)
        
        # 验证
        async_handler.assert_called_once_with("msg1", {"data": "test"})
    
    def test_mixed_sync_async_handlers(self):
        """测试混合同步和异步处理器"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=False,
            service_name="test_service"
        )
        
        # 注册混合处理器
        sync_handler = Mock(return_value=True)
        async_handler = AsyncMock(return_value=True)
        
        manager.register_handler("sync_topic", sync_handler)
        manager.register_handler("async_topic", async_handler)
        
        # 设置订阅
        manager.setup_subscriptions()
        
        # 验证两个订阅都已创建
        assert len(mock_event_bus.subscriptions) == 2
        assert "sync_topic" in mock_event_bus.subscriptions
        assert "async_topic" in mock_event_bus.subscriptions
    
    def test_exception_handling(self):
        """测试异常处理"""
        # 设置
        mock_event_bus = MockEventBus()
        manager = EventSubscriptionManager(
            event_bus=mock_event_bus,
            consumer_group="test_group",
            consumer_name="test_consumer",
            debug_mode=False,
            service_name="test_service"
        )
        
        # 注册会抛出异常的处理器
        exception_handler = Mock(side_effect=Exception("Test exception"))
        manager.register_handler("test_topic", exception_handler)
        manager.setup_subscriptions()
        
        # 模拟消息处理（不应该抛出异常）
        mock_event_bus.simulate_message("test_topic", "msg1", {}, {"data": "test"})
        
        # 验证处理器被调用但异常被捕获
        exception_handler.assert_called_once_with("msg1", {"data": "test"})
        # 异常消息不应该被确认
        assert len(mock_event_bus.acknowledged_messages) == 0


if __name__ == "__main__":
    pytest.main([__file__]) 