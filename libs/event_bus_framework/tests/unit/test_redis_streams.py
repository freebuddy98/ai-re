"""
测试 RedisStreamEventBus 和相关类。
"""
import json
import time
import uuid
from typing import Dict, Any, List

import pytest
import fakeredis
import redis

from event_bus_framework.adapters.redis_streams import (
    RedisStreamEventBus, 
    RedisStreamConsumerGroup,
    MessageHandlerLoopThread
)
from event_bus_framework.core.constants import RedisConstants
from event_bus_framework.core.exceptions import (
    ConnectionError as EventBusConnectionError,
    PublishError as EventBusPublishError,
    SubscribeError as EventBusSubscribeError
)


@pytest.fixture
def fake_redis_client():
    """提供一个假的 Redis 客户端用于测试。"""
    return fakeredis.FakeRedis()


@pytest.fixture
def redis_event_bus(monkeypatch, fake_redis_client):
    """提供一个使用假 Redis 客户端的 RedisStreamEventBus 实例。"""
    # 替换redis.from_url，使其返回我们的假客户端
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: fake_redis_client)
    
    # 创建事件总线实例
    event_bus = RedisStreamEventBus(
        redis_url="redis://fakehost:6379/0",
        event_source_name="test_service",
        topic_prefix="test_prefix"
    )
    
    return event_bus


class TestRedisStreamEventBus:
    """测试 RedisStreamEventBus 类的功能。"""

    def test_init_success(self, redis_event_bus):
        """测试成功初始化事件总线。"""
        assert redis_event_bus.redis_url == "redis://fakehost:6379/0"
        assert redis_event_bus.topic_prefix == "test_prefix"
        assert redis_event_bus.event_source_name == "test_service"
        assert redis_event_bus.redis_client is not None

    def test_init_connection_error(self, monkeypatch):
        """测试初始化时连接错误的处理。"""
        # 模拟连接错误
        def mock_from_url(*args, **kwargs):
            raise redis.RedisError("Mock connection error")
        
        monkeypatch.setattr("redis.from_url", mock_from_url)
        
        with pytest.raises(EventBusConnectionError) as excinfo:
            RedisStreamEventBus(redis_url="redis://fakehost:6379/0")
        
        assert "无法连接到Redis" in str(excinfo.value)
        assert "Mock connection error" in str(excinfo.value)

    def test_build_topic_key_with_prefix(self, redis_event_bus):
        """测试构建带前缀的主题键名。"""
        topic_key = redis_event_bus._build_topic_key("test_topic")
        assert topic_key == "test_prefix:test_topic"

    def test_build_topic_key_without_prefix(self, fake_redis_client, monkeypatch):
        """测试构建不带前缀的主题键名。"""
        monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: fake_redis_client)
        
        event_bus = RedisStreamEventBus(
            redis_url="redis://fakehost:6379/0",
            event_source_name="test_service",
            topic_prefix=""
        )
        
        topic_key = event_bus._build_topic_key("test_topic")
        assert topic_key == "test_topic"

    def test_publish_success(self, redis_event_bus):
        """测试成功发布事件。"""
        topic = "test_topic"
        event_data = {"key": "value", "number": 42}
        
        # 发布事件
        message_id = redis_event_bus.publish(topic, event_data)
        
        # 验证消息ID格式
        assert message_id is not None
        assert isinstance(message_id, (str, bytes))
        
        # 验证消息已添加到Redis Stream
        topic_key = redis_event_bus._build_topic_key(topic)
        stream_data = redis_event_bus.redis_client.xread({topic_key: "0"})
        
        # 检查是否有消息
        assert len(stream_data) == 1
        assert len(stream_data[0][1]) == 1
        
        # 解析消息内容
        message = stream_data[0][1][0][1]
        decoded_message = {}
        for k, v in message.items():
            key = k.decode('utf-8') if isinstance(k, bytes) else k
            value = v.decode('utf-8') if isinstance(v, bytes) else v
            decoded_message[key] = value
        
        # 验证消息内容
        assert decoded_message["source"] == "test_service"
        assert "timestamp" in decoded_message
        assert "id" in decoded_message
        assert "data" in decoded_message
        
        # 验证事件数据
        parsed_data = json.loads(decoded_message["data"])
        assert parsed_data == event_data

    def test_publish_redis_error(self, redis_event_bus, monkeypatch):
        """测试发布事件时Redis错误。"""
        # 模拟xadd方法错误
        def mock_xadd(*args, **kwargs):
            raise redis.RedisError("Mock xadd error")
        
        monkeypatch.setattr(redis_event_bus.redis_client, "xadd", mock_xadd)
        
        with pytest.raises(EventBusPublishError) as excinfo:
            redis_event_bus.publish("test_topic", {"key": "value"})
        
        assert "发布事件失败" in str(excinfo.value)
        assert "Mock xadd error" in str(excinfo.value)

    def test_subscribe_creates_consumer_group(self, redis_event_bus, monkeypatch):
        """测试订阅时创建消费者组。"""
        # 模拟handler
        def mock_handler(message):
            pass
        
        # 模拟消费者组创建
        create_group_called = False
        
        class MockConsumerGroup:
            def __init__(self, *args, **kwargs):
                self.redis_client = kwargs.get('redis_client')
                self.topic = kwargs.get('topic')
                self.group_name = kwargs.get('group_name')
                self.consumer_name = kwargs.get('consumer_name')
            
            def create_group(self):
                nonlocal create_group_called
                create_group_called = True
        
        monkeypatch.setattr("event_bus_framework.adapters.redis_streams.RedisStreamConsumerGroup", 
                           MockConsumerGroup)
        
        # 执行订阅
        redis_event_bus.subscribe("test_topic", mock_handler, "test_group", "test_consumer")
        
        # 验证消费者组被创建
        assert create_group_called

    def test_acknowledge_success(self, redis_event_bus):
        """测试成功确认消息。"""
        topic = "test_topic"
        group_name = "test_group"
        message_ids = ["123-0", "124-0"]
        
        # 先发布一些消息到Stream（这样Stream存在）
        redis_event_bus.publish(topic, {"test": "data"})
        
        # 创建消费者组
        topic_key = redis_event_bus._build_topic_key(topic)
        try:
            redis_event_bus.redis_client.xgroup_create(
                name=topic_key,
                groupname=group_name,
                id="0",
                mkstream=True
            )
        except redis.exceptions.ResponseError:
            # 忽略组已存在错误
            pass
        
        # 确认消息（即使消息ID不存在，xack也不会报错）
        redis_event_bus.acknowledge(topic, group_name, message_ids)
        
        # 如果没有抛出异常，则测试通过

    def test_acknowledge_redis_error(self, redis_event_bus, monkeypatch):
        """测试确认消息时Redis错误。"""
        # 模拟xack方法错误
        def mock_xack(*args, **kwargs):
            raise redis.RedisError("Mock xack error")
        
        monkeypatch.setattr(redis_event_bus.redis_client, "xack", mock_xack)
        
        with pytest.raises(EventBusSubscribeError) as excinfo:
            redis_event_bus.acknowledge("test_topic", "test_group", ["123-0"])
        
        assert "确认消息失败" in str(excinfo.value)
        assert "Mock xack error" in str(excinfo.value)


class TestRedisStreamConsumerGroup:
    """测试 RedisStreamConsumerGroup 类的功能。"""

    def test_init(self, fake_redis_client):
        """测试初始化消费者组。"""
        consumer_group = RedisStreamConsumerGroup(
            redis_client=fake_redis_client,
            topic="test_topic",
            group_name="test_group",
            consumer_name="test_consumer"
        )
        
        assert consumer_group.redis_client == fake_redis_client
        assert consumer_group.topic == "test_topic"
        assert consumer_group.group_name == "test_group"
        assert consumer_group.consumer_name == "test_consumer"
        assert consumer_group.block_ms == RedisConstants.DEFAULT_BLOCK_MS
        assert consumer_group.batch_size == RedisConstants.DEFAULT_BATCH_SIZE

    def test_create_group_success(self, fake_redis_client):
        """测试成功创建消费者组。"""
        consumer_group = RedisStreamConsumerGroup(
            redis_client=fake_redis_client,
            topic="test_topic",
            group_name="test_group",
            consumer_name="test_consumer"
        )
        
        # 创建组
        consumer_group.create_group()
        
        # 验证组已创建（通过检查组信息来验证）
        try:
            # 尝试获取组信息，如果组存在，应该不会抛出异常
            info = fake_redis_client.xinfo_groups("test_topic")
            assert len(info) >= 1
            assert any(group['name'] == b'test_group' for group in info)
        except redis.exceptions.ResponseError:
            # 如果Stream不存在，说明创建组时出现了问题
            pytest.fail("Consumer group was not created successfully")


class TestMessageHandlerLoopThread:
    """测试 MessageHandlerLoopThread 类的功能。"""

    def test_init(self, redis_event_bus):
        """测试初始化消息处理线程。"""
        from event_bus_framework.adapters.redis_streams import IMessageHandler

        class MockHandler(IMessageHandler):
            def handle_message(self, topic: str, message_data: Dict[str, Any]) -> None:
                pass

        handlers = [MockHandler()]

        thread = MessageHandlerLoopThread(
            event_bus=redis_event_bus,
            topic="test_topic",
            handlers=handlers,
            consumer_group="test_group",
            consumer_name="test_consumer"
        )

        assert thread._event_bus == redis_event_bus
        assert thread._topic == "test_topic"
        assert thread._handlers == handlers
        assert thread._consumer_group == "test_group"
        assert thread._consumer_name == "test_consumer"
        assert thread._running is False

    def test_thread_lifecycle(self, redis_event_bus):
        """测试线程生命周期。"""
        from event_bus_framework.adapters.redis_streams import IMessageHandler
        
        class MockHandler(IMessageHandler):
            def handle_message(self, topic: str, message_data: Dict[str, Any]) -> None:
                pass
        
        handlers = [MockHandler()]
        
        thread = MessageHandlerLoopThread(
            event_bus=redis_event_bus,
            topic="test_topic",
            handlers=handlers,
            consumer_group="test_group",
            consumer_name="test_consumer"
        )
        
        # 启动线程
        thread.start()
        assert thread._running is True
        
        # 停止线程
        thread.stop()
        thread.join(timeout=1)  # 等待线程结束
        assert thread._running is False 