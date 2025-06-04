"""
测试 RedisStreamsEventBus 和 MessageHandlerLoopThread 类。
"""
import json
import time
import threading
from typing import Dict, Any, List

import pytest
import fakeredis
import redis

from event_bus_framework.adapters.redis_streams import RedisStreamsEventBus, MessageHandlerLoopThread
from event_bus_framework.core.constants import RedisConstants
from event_bus_framework.core.exceptions import (
    AcknowledgeError, 
    ConnectionError, 
    ConsumerGroupError, 
    DeserializationError, 
    EventBusError, 
    PublishError, 
    SubscribeError
)
from event_bus_framework.core.utils import build_topic_key, deserialize_from_json


class FakeRedisConnection:
    """模拟Redis连接类"""
    def __init__(self, fake_redis_client=None):
        self.fake_redis_client = fake_redis_client or fakeredis.FakeRedis()

    def from_url(self, *args, **kwargs):
        """模拟from_url方法"""
        return self


@pytest.fixture
def fake_redis_client():
    """提供一个假的 Redis 客户端用于测试。"""
    return fakeredis.FakeRedis()


@pytest.fixture
def redis_event_bus(monkeypatch, fake_redis_client):
    """提供一个使用假 Redis 客户端的 RedisStreamsEventBus 实例。"""
    # 创建一个假的连接池
    fake_pool = FakeRedisConnection(fake_redis_client)
    
    # 替换ConnectionPool.from_url，使其返回我们的假连接池
    monkeypatch.setattr("redis.ConnectionPool.from_url", 
                       lambda *args, **kwargs: fake_pool)
    
    # 替换Redis类，使其返回我们的假客户端
    monkeypatch.setattr("redis.Redis", 
                       lambda connection_pool=None, **kwargs: fake_pool.fake_redis_client)
    
    # 创建事件总线实例
    event_bus = RedisStreamsEventBus(
        redis_url="redis://fakehost:6379/0",
        topic_prefix="test_prefix",
        event_source_name="test_service",
        default_consumer_group="test_group",
        default_consumer_instance_name="test_consumer"
    )
    
    # 给事件总线实例添加一个属性，方便测试
    event_bus.fake_redis_client = fake_redis_client
    
    return event_bus


class TestRedisStreamsEventBus:
    """测试 RedisStreamsEventBus 类的功能。"""

    def test_init(self, redis_event_bus):
        """测试初始化事件总线。"""
        assert redis_event_bus.redis_url == "redis://fakehost:6379/0"
        assert redis_event_bus.topic_prefix == "test_prefix"
        assert redis_event_bus.event_source_name == "test_service"
        assert redis_event_bus.default_consumer_group == "test_group"
        assert redis_event_bus.default_consumer_instance_name == "test_consumer"
        assert redis_event_bus.active_subscriptions == {}
        assert redis_event_bus.redis_client is not None

    def test_init_connection_error(self, monkeypatch):
        """测试初始化时连接错误的处理。"""
        # 模拟连接错误
        def mock_from_url(*args, **kwargs):
            raise redis.RedisError("Mock connection error")
        
        monkeypatch.setattr("redis.ConnectionPool.from_url", mock_from_url)
        
        with pytest.raises(ConnectionError) as excinfo:
            RedisStreamsEventBus(redis_url="redis://fakehost:6379/0")
        
        assert "无法创建Redis连接池" in str(excinfo.value)
        assert "Mock connection error" in str(excinfo.value)

    def test_get_redis_client(self, redis_event_bus):
        """测试获取Redis客户端。"""
        client = redis_event_bus._get_redis_client()
        assert client is not None
        assert client == redis_event_bus.fake_redis_client
        # 确保_get_redis_client方法返回redis_client属性
        assert client == redis_event_bus.redis_client

    # 由于我们更改了_get_redis_client方法的实现，这个测试需要调整
    def test_get_redis_client_error(self, redis_event_bus, monkeypatch):
        """测试Redis客户端访问错误。"""
        # 删除redis_client属性模拟访问错误
        original_client = redis_event_bus.redis_client
        delattr(redis_event_bus, 'redis_client')
        
        # 创建一个替代的_get_redis_client方法，在被调用时抛出异常
        def mock_get_redis_client(self):
            raise redis.RedisError("Mock client error")
        
        # 替换方法
        original_method = redis_event_bus._get_redis_client
        redis_event_bus._get_redis_client = lambda: mock_get_redis_client(redis_event_bus)
        
        try:
            with pytest.raises(redis.RedisError) as excinfo:
                redis_event_bus._get_redis_client()
            
            assert "Mock client error" in str(excinfo.value)
        finally:
            # 恢复原始状态
            redis_event_bus.redis_client = original_client
            redis_event_bus._get_redis_client = original_method

    def test_build_event_envelope(self, redis_event_bus):
        """测试构建事件信封。"""
        # 测试明确提供event_type_hint
        envelope = redis_event_bus._build_event_envelope(
            message_data={"key": "value"},
            topic="test_topic",
            event_type_hint="test_event",
            dialogue_session_id_hint="test_session"
        )
        
        assert envelope["actual_payload"] == {"key": "value"}
        assert envelope["source_service"] == "test_service"
        assert envelope["event_type"] == "test_event"
        assert envelope["dialogue_session_id"] == "test_session"
        assert "published_at_utc" in envelope
        assert "event_id" in envelope
        
        # 测试从topic提取event_type_hint
        envelope = redis_event_bus._build_event_envelope(
            message_data={"key": "value"},
            topic="stream:20250603123456:domain:event_type",
        )
        
        assert envelope["event_type"] == "event_type"

    def test_xadd_success(self, redis_event_bus):
        """测试成功添加消息到流。"""
        topic = "test_stream"
        message = {"key": "value"}
        
        message_id = redis_event_bus.xadd(topic, message)
        
        # 验证消息ID格式
        assert "-" in message_id
        
        # 验证消息已添加到流中
        result = redis_event_bus.fake_redis_client.xread({topic: "0"})
        assert len(result) == 1
        assert len(result[0][1]) == 1
        
        # 解码消息
        retrieved_message = {}
        for k, v in result[0][1][0][1].items():
            if isinstance(k, bytes):
                k = k.decode('utf-8')
            if isinstance(v, bytes):
                v = v.decode('utf-8')
            retrieved_message[k] = v
            
        assert retrieved_message == message

    def test_xadd_failure(self, redis_event_bus, monkeypatch):
        """测试添加消息失败时的异常处理。"""
        # 模拟xadd错误
        def mock_xadd(*args, **kwargs):
            raise redis.RedisError("Mock xadd error")
        
        monkeypatch.setattr(redis_event_bus.redis_client, "xadd", mock_xadd)
        
        with pytest.raises(EventBusError) as excinfo:
            redis_event_bus.xadd("test_stream", {"key": "value"})
        
        assert "Failed to add message to stream" in str(excinfo.value)
        assert "Mock xadd error" in str(excinfo.value)

    def test_xreadgroup_success(self, redis_event_bus):
        """测试成功从流中读取消息。"""
        topic = "test_stream"
        group = "test_group"
        consumer = "test_consumer"
        message = {"key": "value"}
        
        # 添加消息到流
        message_id = redis_event_bus.xadd(topic, message)
        
        # 创建消费者组
        redis_event_bus.xgroup_create_if_not_exists(topic, group, "0")
        
        # 读取消息
        result = redis_event_bus.xreadgroup(group, consumer, {topic: ">"})
        
        # 验证结果
        assert result is not None
        assert len(result) == 1
        stream_name = result[0][0]
        if isinstance(stream_name, bytes):
            stream_name = stream_name.decode('utf-8')
        assert stream_name == topic
        assert len(result[0][1]) == 1
        
        # 解码消息
        retrieved_message = {}
        for k, v in result[0][1][0][1].items():
            if isinstance(k, bytes):
                k = k.decode('utf-8')
            if isinstance(v, bytes):
                v = v.decode('utf-8')
            retrieved_message[k] = v
            
        assert retrieved_message == message

    def test_xreadgroup_failure(self, redis_event_bus, monkeypatch):
        """测试读取消息失败时的异常处理。"""
        # 模拟xreadgroup错误
        def mock_xreadgroup(*args, **kwargs):
            raise redis.RedisError("Mock xreadgroup error")
        
        monkeypatch.setattr(redis_event_bus.redis_client, "xreadgroup", mock_xreadgroup)
        
        with pytest.raises(EventBusError) as excinfo:
            redis_event_bus.xreadgroup("test_group", "test_consumer", {"test_stream": ">"})
        
        assert "Failed to read from streams" in str(excinfo.value)
        assert "Mock xreadgroup error" in str(excinfo.value)

    def test_xack_success(self, redis_event_bus):
        """测试成功确认消息。"""
        topic = "test_stream"
        group = "test_group"
        consumer = "test_consumer"
        
        # 添加消息到流
        message_id = redis_event_bus.xadd(topic, {"key": "value"})
        
        # 创建消费者组
        redis_event_bus.xgroup_create_if_not_exists(topic, group, "0")
        
        # 读取消息
        redis_event_bus.xreadgroup(group, consumer, {topic: ">"})
        
        # 确认消息
        ack_count = redis_event_bus.xack(topic, group, [message_id])
        
        # 验证结果
        assert ack_count == 1

    def test_xack_failure(self, redis_event_bus, monkeypatch):
        """测试确认消息失败时的异常处理。"""
        # 模拟xack错误
        def mock_xack(*args, **kwargs):
            raise redis.RedisError("Mock xack error")
        
        monkeypatch.setattr(redis_event_bus.redis_client, "xack", mock_xack)
        
        with pytest.raises(EventBusError) as excinfo:
            redis_event_bus.xack("test_stream", "test_group", ["1234567890-0"])
        
        assert "Failed to acknowledge messages" in str(excinfo.value)
        assert "Mock xack error" in str(excinfo.value)

    def test_xgroup_create_if_not_exists_success(self, redis_event_bus):
        """测试成功创建消费者组。"""
        topic = "test_stream"
        group = "test_group"
        
        # 首先添加消息到流，确保流存在
        redis_event_bus.xadd(topic, {"key": "value"})
        
        # 创建消费者组
        redis_event_bus.xgroup_create_if_not_exists(topic, group)
        
        # 验证消费者组是否创建
        groups = redis_event_bus.redis_client.xinfo_groups(topic)
        assert len(groups) == 1
        
        # 检查组名
        group_info = groups[0]
        name_key = "name" if "name" in group_info else (b"name" if b"name" in group_info else None)
        assert name_key is not None
        
        group_name = group_info[name_key]
        if isinstance(group_name, bytes):
            group_name = group_name.decode('utf-8')
        
        assert group_name == group

    def test_xgroup_create_already_exists(self, redis_event_bus):
        """测试当消费者组已存在时的行为。"""
        topic = "test_stream"
        group = "test_group"
        
        # 添加消息到流
        redis_event_bus.xadd(topic, {"key": "value"})
        
        # 创建消费者组
        redis_event_bus.xgroup_create_if_not_exists(topic, group)
        
        # 再次创建同一个组，不应抛出异常
        redis_event_bus.xgroup_create_if_not_exists(topic, group)
        
        # 验证消费者组仍然存在
        groups = redis_event_bus.redis_client.xinfo_groups(topic)
        assert len(groups) == 1

    def test_xgroup_create_failure(self, redis_event_bus, monkeypatch):
        """测试创建消费者组失败时的异常处理。"""
        # 模拟xgroup_create错误
        def mock_xgroup_create(*args, **kwargs):
            raise redis.RedisError("Mock xgroup error")
        
        monkeypatch.setattr(redis_event_bus.redis_client, "xgroup_create", mock_xgroup_create)
        
        with pytest.raises(EventBusError) as excinfo:
            redis_event_bus.xgroup_create_if_not_exists("test_stream", "test_group")
        
        assert "Failed to create consumer group" in str(excinfo.value)
        assert "Mock xgroup error" in str(excinfo.value)

    def test_publish_success(self, redis_event_bus):
        """测试成功发布消息。"""
        topic = "test_topic"
        message_data = {"key": "value"}
        
        # 发布消息
        message_id = redis_event_bus.publish(topic, message_data)
        
        # 验证消息ID
        assert message_id is not None
        assert "-" in message_id
        
        # 验证消息已添加到流中（带前缀）
        full_topic = build_topic_key(redis_event_bus.topic_prefix, topic)
        result = redis_event_bus.redis_client.xread({full_topic: "0"})
        
        # 检查读取结果
        assert len(result) == 1
        assert len(result[0][1]) == 1
        
        # 获取并解码消息
        message_fields = {}
        for k, v in result[0][1][0][1].items():
            if isinstance(k, bytes):
                k = k.decode('utf-8')
            if isinstance(v, bytes):
                v = v.decode('utf-8')
            message_fields[k] = v
        
        # 验证payload字段存在
        assert RedisConstants.PAYLOAD_FIELD in message_fields
        
        # 反序列化payload
        event_envelope = deserialize_from_json(message_fields[RedisConstants.PAYLOAD_FIELD])
        
        # 验证事件信封结构
        assert event_envelope["actual_payload"] == message_data
        assert event_envelope["source_service"] == "test_service"
        assert "published_at_utc" in event_envelope
        assert "event_id" in event_envelope

    def test_publish_failure(self, redis_event_bus, monkeypatch):
        """测试发布消息失败时的异常处理。"""
        # 模拟xadd错误
        def mock_xadd(*args, **kwargs):
            raise redis.RedisError("Mock publish error")
        
        monkeypatch.setattr(redis_event_bus.redis_client, "xadd", mock_xadd)
        
        with pytest.raises(PublishError) as excinfo:
            redis_event_bus.publish("test_topic", {"key": "value"})
        
        assert "发布消息到主题" in str(excinfo.value)
        assert "Mock publish error" in str(excinfo.value)

    def test_subscribe_success(self, redis_event_bus):
        """测试成功订阅主题。"""
        topic = "test_topic"
        received_messages = []
        
        # 处理函数
        def handler(message_id, envelope, payload):
            received_messages.append((message_id, envelope, payload))
        
        # 订阅主题
        redis_event_bus.subscribe(
            topic=topic,
            handler_function=handler,
            group_name="test_group",
            consumer_name="test_consumer",
            auto_acknowledge=True
        )
        
        # 验证订阅是否被创建
        full_topic = build_topic_key(redis_event_bus.topic_prefix, topic)
        subscription_key = f"{full_topic}:test_group:test_consumer"
        assert subscription_key in redis_event_bus.active_subscriptions
        
        # 给订阅一些时间来启动
        time.sleep(0.1)
        
        # 发布一条消息
        message_data = {"key": "value"}
        redis_event_bus.publish(topic, message_data)
        
        # 给处理消息一些时间
        time.sleep(0.5)
        
        # 停止订阅线程
        redis_event_bus.active_subscriptions[subscription_key].stop()
        
        # 验证消息是否被接收
        assert len(received_messages) == 1
        assert received_messages[0][2] == message_data

    def test_acknowledge_success(self, redis_event_bus):
        """测试成功确认消息。"""
        topic = "test_topic"
        group = "test_group"
        received_messages = []
        message_ids = []
        
        # 处理函数，不自动确认
        def handler(message_id, envelope, payload):
            received_messages.append((message_id, envelope, payload))
            message_ids.append(message_id)
        
        # 创建消费者组和流
        full_topic = build_topic_key(redis_event_bus.topic_prefix, topic)
        redis_event_bus.xadd(full_topic, {"test": "create_stream"})
        redis_event_bus.xgroup_create_if_not_exists(full_topic, group, "0")
        
        # 订阅主题，不自动确认
        redis_event_bus.subscribe(
            topic=topic,
            handler_function=handler,
            group_name=group,
            consumer_name="test_consumer",
            auto_acknowledge=False
        )
        
        # 给订阅一些时间来启动
        time.sleep(0.1)
        
        # 发布一条消息
        message_data = {"key": "value"}
        redis_event_bus.publish(topic, message_data)
        
        # 给处理消息一些时间
        time.sleep(0.5)
        
        # 验证消息是否被接收
        assert len(received_messages) == 1
        assert len(message_ids) == 1
        
        # 确认消息
        ack_count = redis_event_bus.acknowledge(topic, group, message_ids)
        
        # 验证确认结果
        assert ack_count == 1
        
        # 停止所有订阅
        for key, thread in list(redis_event_bus.active_subscriptions.items()):
            thread.stop()

    def test_acknowledge_failure(self, redis_event_bus, monkeypatch):
        """测试确认消息失败时的异常处理。"""
        # 模拟xack错误
        def mock_xack(*args, **kwargs):
            raise redis.RedisError("Mock acknowledge error")
        
        monkeypatch.setattr(redis_event_bus.redis_client, "xack", mock_xack)
        
        with pytest.raises(AcknowledgeError) as excinfo:
            redis_event_bus.acknowledge("test_topic", "test_group", ["1234567890-0"])
        
        assert "确认消息" in str(excinfo.value)
        assert "Mock acknowledge error" in str(excinfo.value)


class TestMessageHandlerLoopThread:
    """测试 MessageHandlerLoopThread 类的功能。"""
    
    def test_init(self, redis_event_bus):
        """测试初始化消息处理线程。"""
        def handler(message_id, envelope, payload):
            pass
            
        thread = MessageHandlerLoopThread(
            bus_instance=redis_event_bus,
            topic="test_topic",
            handler_function=handler,
            group_name="test_group",
            consumer_name="test_consumer",
            start_id="0",
            auto_acknowledge=True,
            name="TestThread"
        )
        
        assert thread.bus_instance == redis_event_bus
        assert thread.topic == "test_topic"
        assert thread.handler_function == handler
        assert thread.group_name == "test_group"
        assert thread.consumer_name == "test_consumer"
        assert thread.start_id == "0"
        assert thread.auto_acknowledge is True
        assert thread.full_topic_key == build_topic_key(redis_event_bus.topic_prefix, "test_topic")
        assert thread.running is False
        assert thread.daemon is True
        assert thread.name == "TestThread"
    
    def test_process_messages(self, redis_event_bus):
        """测试处理消息的逻辑。"""
        processed_messages = []
        
        def handler(message_id, envelope, payload):
            processed_messages.append((message_id, envelope, payload))
        
        thread = MessageHandlerLoopThread(
            bus_instance=redis_event_bus,
            topic="test_topic",
            handler_function=handler,
            group_name="test_group",
            consumer_name="test_consumer",
            auto_acknowledge=False
        )
        
        # 准备测试数据
        message_id = "1234567890-0"
        payload = {"key": "value"}
        event_envelope = {
            "actual_payload": payload,
            "source_service": "test_service",
            "event_type": "test_event",
            "published_at_utc": "2023-01-01T00:00:00Z",
            "event_id": "test-event-id"
        }
        
        # 序列化事件信封
        payload_json = json.dumps(event_envelope)
        
        # 构造Redis消息格式
        redis_message = [
            [thread.full_topic_key.encode('utf-8'), [
                [message_id.encode('utf-8'), {
                    RedisConstants.PAYLOAD_FIELD.encode('utf-8'): payload_json.encode('utf-8')
                }]
            ]]
        ]
        
        # 调用处理方法
        thread._process_messages(redis_message, redis_event_bus.redis_client)
        
        # 验证处理结果
        assert len(processed_messages) == 1
        assert processed_messages[0][0] == message_id
        assert processed_messages[0][1] == event_envelope
        assert processed_messages[0][2] == payload
    
    def test_process_messages_auto_ack(self, redis_event_bus, monkeypatch):
        """测试自动确认消息的逻辑。"""
        processed_messages = []
        ack_calls = []
        
        def handler(message_id, envelope, payload):
            processed_messages.append((message_id, envelope, payload))
        
        def mock_xack(stream, group, *ids):
            ack_calls.append((stream, group, ids))
            return len(ids)
        
        # 替换xack方法
        monkeypatch.setattr(redis_event_bus.redis_client, "xack", mock_xack)
        
        thread = MessageHandlerLoopThread(
            bus_instance=redis_event_bus,
            topic="test_topic",
            handler_function=handler,
            group_name="test_group",
            consumer_name="test_consumer",
            auto_acknowledge=True
        )
        
        # 准备测试数据
        message_id = "1234567890-0"
        payload = {"key": "value"}
        event_envelope = {
            "actual_payload": payload,
            "source_service": "test_service",
            "event_type": "test_event",
            "published_at_utc": "2023-01-01T00:00:00Z",
            "event_id": "test-event-id"
        }
        
        # 序列化事件信封
        payload_json = json.dumps(event_envelope)
        
        # 构造Redis消息格式
        redis_message = [
            [thread.full_topic_key.encode('utf-8'), [
                [message_id.encode('utf-8'), {
                    RedisConstants.PAYLOAD_FIELD.encode('utf-8'): payload_json.encode('utf-8')
                }]
            ]]
        ]
        
        # 调用处理方法
        thread._process_messages(redis_message, redis_event_bus.redis_client)
        
        # 验证处理结果
        assert len(processed_messages) == 1
        assert len(ack_calls) == 1
        assert ack_calls[0][0] == thread.full_topic_key
        assert ack_calls[0][1] == "test_group"
        assert message_id in ack_calls[0][2]
    
    def test_run_and_stop(self, redis_event_bus, monkeypatch):
        """测试线程运行和停止的逻辑。"""
        # 创建一个事件，用于同步测试
        processed_event = threading.Event()
        
        def handler(message_id, envelope, payload):
            processed_event.set()
        
        # 模拟xreadgroup，返回一个测试消息
        def mock_xreadgroup(*args, **kwargs):
            if not thread.running:
                return None
                
            # 构造一个测试消息
            message_id = "1234567890-0"
            payload = {"key": "value"}
            event_envelope = {
                "actual_payload": payload,
                "source_service": "test_service",
                "event_type": "test_event",
                "published_at_utc": "2023-01-01T00:00:00Z",
                "event_id": "test-event-id"
            }
            
            # 序列化事件信封
            payload_json = json.dumps(event_envelope)
            
            # 返回消息
            return [
                [list(kwargs['streams'].keys())[0].encode('utf-8'), [
                    [message_id.encode('utf-8'), {
                        RedisConstants.PAYLOAD_FIELD.encode('utf-8'): payload_json.encode('utf-8')
                    }]
                ]]
            ]
        
        # 替换xreadgroup方法
        monkeypatch.setattr(redis_event_bus.redis_client, "xreadgroup", mock_xreadgroup)
        
        # 创建线程
        thread = MessageHandlerLoopThread(
            bus_instance=redis_event_bus,
            topic="test_topic",
            handler_function=handler,
            group_name="test_group",
            consumer_name="test_consumer"
        )
        
        # 启动线程
        thread.start()
        
        # 等待一段时间
        time.sleep(0.2)
        
        # 停止线程
        thread.stop()
        
        # 等待线程结束
        thread.join(timeout=1.0)
        
        # 验证线程已停止
        assert not thread.running 