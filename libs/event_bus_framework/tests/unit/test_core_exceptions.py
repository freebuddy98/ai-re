"""
核心异常模块单元测试
"""
import sys
import os
import pytest

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from event_bus_framework.core.exceptions import (
    EventBusError,
    ConnectionError,
    PublishError,
    SubscribeError,
    AcknowledgeError,
    DeserializationError,
    ConsumerGroupError
)


class TestEventBusExceptions:
    """事件总线异常单元测试"""
    
    def test_event_bus_error_base(self):
        """测试基础事件总线异常"""
        message = "This is a base event bus exception"
        exception = EventBusError(message)
        
        assert str(exception) == message
        assert isinstance(exception, Exception)
    
    def test_connection_error(self):
        """测试连接异常"""
        message = "Failed to connect to Redis"
        exception = ConnectionError(message)
        
        assert str(exception) == message
        assert isinstance(exception, EventBusError)
        assert isinstance(exception, Exception)
    
    def test_publish_error(self):
        """测试发布异常"""
        message = "Failed to publish message to stream"
        exception = PublishError(message)
        
        assert str(exception) == message
        assert isinstance(exception, EventBusError)
    
    def test_subscribe_error(self):
        """测试订阅异常"""
        message = "Failed to subscribe to stream"
        exception = SubscribeError(message)
        
        assert str(exception) == message
        assert isinstance(exception, EventBusError)
    
    def test_acknowledge_error(self):
        """测试确认消息异常"""
        message = "Failed to acknowledge message"
        exception = AcknowledgeError(message)
        
        assert str(exception) == message
        assert isinstance(exception, EventBusError)
    
    def test_deserialization_error(self):
        """测试反序列化异常"""
        message = "Failed to deserialize event data"
        exception = DeserializationError(message)
        
        assert str(exception) == message
        assert isinstance(exception, EventBusError)
    
    def test_consumer_group_error(self):
        """测试消费者组异常"""
        message = "Consumer group operation failed"
        exception = ConsumerGroupError(message)
        
        assert str(exception) == message
        assert isinstance(exception, EventBusError)
    
    def test_exception_chaining(self):
        """测试异常链"""
        original_exception = ValueError("Original error")
        
        # 测试异常链传递
        try:
            try:
                raise original_exception
            except ValueError as e:
                raise ConnectionError("Connection failed") from e
        except ConnectionError as ce:
            assert ce.__cause__ == original_exception
            assert "Connection failed" in str(ce)
    
    def test_exception_with_none_message(self):
        """测试没有消息的异常"""
        exception = EventBusError()
        
        # 异常应该可以正常创建
        assert isinstance(exception, EventBusError)
        assert isinstance(exception, Exception)
    
    def test_exception_with_empty_message(self):
        """测试空消息的异常"""
        exception = EventBusError("")
        
        assert str(exception) == ""
        assert isinstance(exception, EventBusError)
    
    def test_all_exceptions_are_event_bus_errors(self):
        """测试所有自定义异常都继承自 EventBusError"""
        exceptions = [
            ConnectionError("test"),
            PublishError("test"),
            SubscribeError("test"),
            AcknowledgeError("test"),
            DeserializationError("test"),
            ConsumerGroupError("test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, EventBusError)
            assert isinstance(exc, Exception)
    
    def test_exception_repr(self):
        """测试异常的字符串表示"""
        message = "Test exception message"
        exception = EventBusError(message)
        
        repr_str = repr(exception)
        assert "EventBusError" in repr_str
        assert message in repr_str 