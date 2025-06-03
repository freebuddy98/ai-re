"""
测试事件总线框架的工具函数。
"""
import json
import re
from datetime import datetime

import pytest

from event_bus_framework.core.exceptions import DeserializationError
from event_bus_framework.core.utils import (
    build_topic_key,
    decode_redis_stream_message,
    deserialize_from_json,
    generate_unique_id,
    get_utc_timestamp,
    serialize_to_json,
)


class TestSerializationFunctions:
    """测试序列化和反序列化函数"""
    
    def test_serialize_to_json(self):
        """测试序列化为JSON"""
        # 准备
        data = {"name": "test", "value": 123}
        
        # 执行
        result = serialize_to_json(data)
        
        # 验证
        assert result == '{"name": "test", "value": 123}'
        assert json.loads(result) == data
    
    def test_serialize_to_json_error(self):
        """测试序列化错误"""
        # 准备
        data = {1: lambda x: x}  # 包含不可序列化的对象
        
        # 验证
        with pytest.raises(DeserializationError):
            serialize_to_json(data)
    
    def test_deserialize_from_json(self):
        """测试从JSON反序列化"""
        # 准备
        json_str = '{"name": "test", "value": 123}'
        
        # 执行
        result = deserialize_from_json(json_str)
        
        # 验证
        assert result == {"name": "test", "value": 123}
    
    def test_deserialize_from_json_error(self):
        """测试反序列化错误"""
        # 准备
        json_str = '{"name": "test", "value":'  # 不完整的JSON
        
        # 验证
        with pytest.raises(DeserializationError):
            deserialize_from_json(json_str)


class TestUtilityFunctions:
    """测试其他工具函数"""
    
    def test_generate_unique_id(self):
        """测试生成唯一ID"""
        # 执行
        id1 = generate_unique_id()
        id2 = generate_unique_id()
        
        # 验证
        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', id1)
    
    def test_get_utc_timestamp(self):
        """测试获取UTC时间戳"""
        # 执行
        timestamp = get_utc_timestamp()
        
        # 验证
        assert isinstance(timestamp, str)
        assert re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', timestamp)
        # 检查是否是有效的ISO格式时间
        datetime.fromisoformat(timestamp)
    
    def test_build_topic_key(self):
        """测试构建主题键"""
        # 测试用例
        test_cases = [
            # (prefix, topic, expected)
            ("", "stream:123:input", "stream:123:input"),
            ("dev", "stream:123:input", "dev:stream:123:input"),
            ("dev:", "stream:123:input", "dev:stream:123:input"),
            ("dev", ":stream:123:input", "dev:stream:123:input"),
            ("dev:", ":stream:123:input", "dev:stream:123:input"),
        ]
        
        # 验证所有测试用例
        for prefix, topic, expected in test_cases:
            result = build_topic_key(prefix, topic)
            assert result == expected


class TestRedisMessageDecoding:
    """测试Redis消息解码"""
    
    def test_decode_redis_stream_message(self):
        """测试解码Redis Stream消息"""
        # 准备
        redis_message = [
            ["stream_name", [
                ["message_id_1", {"field1": "value1", "field2": "value2"}]
            ]]
        ]
        
        # 执行
        result = decode_redis_stream_message(redis_message)
        
        # 验证
        assert result == {
            "message_id": "message_id_1",
            "fields": {"field1": "value1", "field2": "value2"}
        }
    
    def test_decode_redis_stream_message_empty(self):
        """测试解码空的Redis Stream消息"""
        # 准备
        redis_message = [["stream_name", []]]
        
        # 执行
        result = decode_redis_stream_message(redis_message)
        
        # 验证
        assert result is None
    
    def test_decode_redis_stream_message_invalid(self):
        """测试解码无效的Redis Stream消息"""
        # 准备
        redis_message = "not_a_valid_message"
        
        # 执行
        result = decode_redis_stream_message(redis_message)
        
        # 验证
        assert result is None 