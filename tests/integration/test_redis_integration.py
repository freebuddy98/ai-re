"""
Redis 事件总线框架集成测试

基于集成测试计划文档 (docs/test/integration_test_plan.md) 实现的测试用例，
验证 Event Bus Framework 与 Redis Streams 的集成功能。

测试范围:
- INT-001: Redis 连接测试
- INT-002: 流创建和删除测试  
- INT-003: 消费者组管理测试
- INT-004: 消息发布和订阅测试
- INT-005: 连接池测试
"""
import json
import os
import time
import uuid
from typing import Dict, Any, List, Optional

import pytest
import redis

from event_bus_framework.adapters.redis_streams import RedisStreamEventBus

# Redis 测试配置
REDIS_HOST = os.environ.get("REDIS_TEST_HOST", "oslab.online")
REDIS_PORT = int(os.environ.get("REDIS_TEST_PORT", "7901"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# 跳过标记
skip_integration = pytest.mark.skipif(
    os.environ.get("SKIP_INTEGRATION_TESTS", "").lower() == "true",
    reason="集成测试被环境变量 SKIP_INTEGRATION_TESTS 跳过"
)


@pytest.fixture
def redis_client():
    """创建 Redis 客户端连接 - 支持 INT-001"""
    client = redis.Redis.from_url(REDIS_URL)
    try:
        # 测试连接
        client.ping()
        yield client
    finally:
        client.close()


@pytest.fixture
def test_prefix():
    """生成唯一的测试前缀，避免测试间冲突"""
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def event_bus(test_prefix):
    """创建事件总线实例"""
    bus = RedisStreamEventBus(
        redis_url=REDIS_URL,
        event_source_name="integration_test",
        topic_prefix=test_prefix
    )
    yield bus
    
    # 清理测试数据
    try:
        client = redis.Redis.from_url(REDIS_URL)
        keys = client.keys(f"{test_prefix}*")
        if keys:
            client.delete(*keys)
        client.close()
    except Exception as e:
        print(f"清理测试数据失败: {e}")


@skip_integration
class TestRedisConnectionIntegration:
    """INT-001: Redis 连接测试"""
    
    def test_redis_basic_connection(self, redis_client):
        """验证与 Redis 服务器的基本连接"""
        # 执行 PING 命令验证连接
        result = redis_client.ping()
        assert result is True, "Redis PING 命令应该返回 True"
    
    def test_redis_connection_info(self, redis_client):
        """验证 Redis 连接信息"""
        info = redis_client.info()
        assert "redis_version" in info, "应该能够获取 Redis 版本信息"
        assert info["connected_clients"] >= 1, "应该至少有一个客户端连接"
    
    def test_event_bus_connection(self, event_bus):
        """验证事件总线到 Redis 的连接"""
        # 尝试获取 Redis 客户端信息
        try:
            # 发布一个测试消息验证连接
            topic = "connection_test"
            message_id = event_bus.publish(topic, {"test": "connection"})
            assert message_id is not None, "发布消息应该返回有效的消息 ID"
        except Exception as e:
            pytest.fail(f"事件总线连接失败: {e}")


@skip_integration
class TestRedisStreamManagement:
    """INT-002: 流创建和删除测试"""
    
    def test_stream_creation_and_deletion(self, redis_client, test_prefix):
        """验证 Redis Streams 的创建和删除功能"""
        stream_name = f"{test_prefix}:test_stream"
        
        # 1. 创建流（通过添加消息）
        message_id = redis_client.xadd(stream_name, {"field": "value"})
        assert message_id is not None, "应该能成功创建流并添加消息"
        
        # 2. 验证流存在
        stream_info = redis_client.xinfo_stream(stream_name)
        assert stream_info["length"] == 1, "流应该包含一条消息"
        
        # 3. 添加更多消息
        redis_client.xadd(stream_name, {"field2": "value2"})
        stream_info = redis_client.xinfo_stream(stream_name)
        assert stream_info["length"] == 2, "流应该包含两条消息"
        
        # 4. 删除流
        redis_client.delete(stream_name)
        
        # 5. 验证流已删除
        with pytest.raises(redis.exceptions.ResponseError):
            redis_client.xinfo_stream(stream_name)
    
    def test_stream_with_event_bus(self, event_bus, redis_client, test_prefix):
        """验证通过事件总线创建的流"""
        topic = "stream_test"
        full_stream_name = f"{test_prefix}:{topic}"
        
        # 通过事件总线发布消息（自动创建流）
        message_id = event_bus.publish(topic, {"event": "test"})
        assert message_id is not None
        
        # 验证流已创建
        stream_info = redis_client.xinfo_stream(full_stream_name)
        assert stream_info["length"] >= 1, "流应该包含至少一条消息"


@skip_integration  
class TestConsumerGroupManagement:
    """INT-003: 消费者组管理测试"""
    
    def test_consumer_group_creation(self, redis_client, test_prefix):
        """验证消费者组的创建和管理"""
        stream_name = f"{test_prefix}:group_test"
        group_name = "test_group"
        
        # 1. 创建流
        redis_client.xadd(stream_name, {"init": "message"})
        
        # 2. 创建消费者组
        redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
        
        # 3. 验证组已创建
        groups_info = redis_client.xinfo_groups(stream_name)
        assert len(groups_info) == 1, "应该创建了一个消费者组"
        assert groups_info[0]["name"] == group_name.encode(), "组名应该匹配"
        
        # 4. 验证再次创建相同组会失败
        with pytest.raises(redis.exceptions.ResponseError, match="BUSYGROUP"):
            redis_client.xgroup_create(stream_name, group_name, id="0")
    
    def test_consumer_group_with_multiple_consumers(self, redis_client, test_prefix):
        """验证多消费者的消费者组"""
        stream_name = f"{test_prefix}:multi_consumer_test"
        group_name = "multi_group"
        
        # 创建流和消费者组
        redis_client.xadd(stream_name, {"test": "message"})
        redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
        
        # 模拟多个消费者读取
        consumer1_messages = redis_client.xreadgroup(
            group_name, "consumer1", {stream_name: ">"}, count=1, block=100
        )
        
        consumer2_messages = redis_client.xreadgroup(
            group_name, "consumer2", {stream_name: ">"}, count=1, block=100
        )
        
        # 验证消费者信息
        consumers_info = redis_client.xinfo_consumers(stream_name, group_name)
        consumer_names = [c["name"].decode() for c in consumers_info]
        assert "consumer1" in consumer_names, "consumer1 应该在消费者列表中"
        assert "consumer2" in consumer_names, "consumer2 应该在消费者列表中"


@skip_integration
class TestEventBusIntegration:
    """INT-101 到 INT-105: 事件总线框架集成测试"""
    
    def test_event_publishing_integration(self, event_bus):
        """INT-101: 验证事件发布功能的完整性"""
        topic = "publish_test"
        test_data = {
            "user_id": "test_user",
            "action": "login",
            "timestamp": int(time.time())
        }
        
        # 发布事件
        message_id = event_bus.publish(topic, test_data)
        
        # 验证发布结果
        assert message_id is not None, "发布应该返回有效的消息 ID"
        # Redis 返回的消息 ID 可能是 bytes 类型
        if isinstance(message_id, bytes):
            message_id = message_id.decode('utf-8')
        assert isinstance(message_id, str), "消息 ID 应该是字符串类型"
        assert "-" in message_id, "消息 ID 应该包含时间戳分隔符"
    
    def test_event_subscription_integration(self, event_bus, redis_client, test_prefix):
        """INT-102: 验证事件订阅功能（简化版 - 验证消费者组创建）"""
        topic = "subscribe_test"
        group_name = "test_group"
        consumer_name = "test_consumer"
        
        # 创建订阅（只是创建消费者组）
        event_bus.subscribe(
            topic=topic,
            handler=lambda x: None,  # 简单的处理器
            group_name=group_name,
            consumer_name=consumer_name
        )
        
        # 验证消费者组已创建
        stream_name = f"{test_prefix}:{topic}"
        groups_info = redis_client.xinfo_groups(stream_name)
        assert len(groups_info) >= 1, "应该至少有一个消费者组"
        
        group_names = [group['name'].decode() for group in groups_info]
        assert group_name in group_names, f"消费者组 {group_name} 应该存在"
        
        # 发布消息并验证消息存在于流中
        test_data = {"message": "test_subscription"}
        message_id = event_bus.publish(topic, test_data)
        assert message_id is not None
        
        # 验证消息在流中
        stream_info = redis_client.xinfo_stream(stream_name)
        assert stream_info["length"] >= 1, "流中应该有消息"
    
    def test_multi_topic_publishing_subscription(self, event_bus, redis_client, test_prefix):
        """INT-103: 验证多主题场景下的功能（简化版）"""
        topics = ["topic1", "topic2", "topic3"]
        
        # 为每个主题创建消费者组
        for topic in topics:
            event_bus.subscribe(
                topic=topic,
                handler=lambda x: None,
                group_name=f"group_{topic}",
                consumer_name=f"consumer_{topic}"
            )
        
        # 向每个主题发布消息
        for i, topic in enumerate(topics):
            test_data = {"topic": topic, "index": i}
            message_id = event_bus.publish(topic, test_data)
            assert message_id is not None
        
        # 验证每个主题的流都有消息
        for topic in topics:
            stream_name = f"{test_prefix}:{topic}"
            stream_info = redis_client.xinfo_stream(stream_name)
            assert stream_info["length"] >= 1, f"主题 {topic} 的流中应该有消息"
            
            # 验证消费者组存在
            groups_info = redis_client.xinfo_groups(stream_name)
            group_names = [group['name'].decode() for group in groups_info]
            assert f"group_{topic}" in group_names, f"消费者组 group_{topic} 应该存在"
    
    def test_event_serialization_integration(self, event_bus, redis_client, test_prefix):
        """INT-104: 验证事件序列化和反序列化"""
        topic = "serialization_test"
        
        # 创建消费者组
        event_bus.subscribe(
            topic=topic,
            handler=lambda x: None,
            group_name="serialize_group",
            consumer_name="serialize_consumer"
        )
        
        # 创建复杂事件对象
        complex_data = {
            "string": "test_string",
            "number": 12345,
            "float": 123.45,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3, "item"],
            "nested_dict": {
                "inner_key": "inner_value",
                "inner_number": 999
            },
            "unicode": "测试中文字符",
            "special_chars": "!@#$%^&*()"
        }
        
        # 发布复杂数据
        message_id = event_bus.publish(topic, complex_data)
        assert message_id is not None
        
        # 直接从 Redis 读取消息验证序列化
        stream_name = f"{test_prefix}:{topic}"
        messages = redis_client.xread({stream_name: "0"}, count=1)
        assert len(messages) > 0, "应该能读取到消息"
        
        stream, message_list = messages[0]
        assert len(message_list) > 0, "消息列表不应为空"
        
        # 获取消息数据
        message_id, fields = message_list[-1]
        # Redis 返回的字段名是 bytes，需要解码
        field_keys = [k.decode() if isinstance(k, bytes) else k for k in fields.keys()]
        assert "data" in field_keys, f"消息应该包含 data 字段，实际字段: {field_keys}"
        
        # 验证序列化数据
        import json
        # 获取数据字段（可能是 bytes 类型的 key）
        data_value = fields.get(b'data') or fields.get('data')
        if isinstance(data_value, bytes):
            data_value = data_value.decode('utf-8')
        event_data = json.loads(data_value)
        
        # 详细验证每个字段
        assert event_data["string"] == complex_data["string"]
        assert event_data["number"] == complex_data["number"]  
        assert event_data["float"] == complex_data["float"]
        assert event_data["boolean"] == complex_data["boolean"]
        assert event_data["null"] == complex_data["null"]
        assert event_data["list"] == complex_data["list"]
        assert event_data["nested_dict"] == complex_data["nested_dict"]
        assert event_data["unicode"] == complex_data["unicode"]
        assert event_data["special_chars"] == complex_data["special_chars"]


@skip_integration
class TestConnectionPoolIntegration:
    """INT-005: 连接池测试"""
    
    def test_connection_pool_behavior(self, test_prefix):
        """验证 Redis 连接池的正确性"""
        # 创建多个事件总线实例（共享连接池）
        buses = []
        for i in range(5):
            bus = RedisStreamEventBus(
                redis_url=REDIS_URL,
                event_source_name=f"pool_test_{i}",
                topic_prefix=test_prefix
            )
            buses.append(bus)
        
        # 并发发布消息
        import threading
        results = []
        
        def publish_messages(bus, index):
            try:
                for j in range(10):
                    message_id = bus.publish(f"pool_topic_{index}", {"index": index, "msg": j})
                    results.append(message_id)
            except Exception as e:
                results.append(f"Error: {e}")
        
        threads = []
        for i, bus in enumerate(buses):
            thread = threading.Thread(target=publish_messages, args=(bus, i))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        error_count = sum(1 for r in results if isinstance(r, str) and r.startswith("Error"))
        success_count = len(results) - error_count
        
        assert error_count == 0, f"不应该有连接错误，但发现 {error_count} 个错误"
        assert success_count == 50, f"应该成功发布 50 条消息，实际成功 {success_count} 条" 