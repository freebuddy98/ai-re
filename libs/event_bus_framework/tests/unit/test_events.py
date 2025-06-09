"""
事件模型单元测试
"""
import uuid
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

import pytest

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from event_bus_framework.common.events import (
    EventType,
    EventStatus,
    EventPriority,
    BaseEvent,
    InputEvent,
    OutputEvent,
    ErrorEvent,
    ServiceStatusEvent,
    EventMeta,
    MessageContent,
    UserMessageRawEvent
)


class TestEventEnums:
    """事件枚举测试"""
    
    def test_event_type_enum(self):
        """测试事件类型枚举"""
        assert EventType.INPUT == "input"
        assert EventType.OUTPUT == "output"
        assert EventType.ERROR == "error"
        assert EventType.STATUS == "status"
        assert EventType.SYSTEM == "system"
        
        # 测试枚举包含所有期望的值
        expected_values = {"input", "output", "error", "status", "system"}
        actual_values = {e.value for e in EventType}
        assert actual_values == expected_values
    
    def test_event_status_enum(self):
        """测试事件状态枚举"""
        assert EventStatus.PENDING == "pending"
        assert EventStatus.PROCESSING == "processing"
        assert EventStatus.COMPLETED == "completed"
        assert EventStatus.FAILED == "failed"
        assert EventStatus.UNKNOWN == "unknown"
        
        # 测试枚举包含所有期望的值
        expected_values = {"pending", "processing", "completed", "failed", "unknown"}
        actual_values = {e.value for e in EventStatus}
        assert actual_values == expected_values
    
    def test_event_priority_enum(self):
        """测试事件优先级枚举"""
        assert EventPriority.LOW == 0
        assert EventPriority.NORMAL == 1
        assert EventPriority.HIGH == 2
        assert EventPriority.URGENT == 3
        
        # 测试优先级可以比较
        assert EventPriority.LOW < EventPriority.NORMAL
        assert EventPriority.HIGH > EventPriority.NORMAL
        assert EventPriority.URGENT > EventPriority.HIGH


class TestBaseEvent:
    """基础事件模型测试"""
    
    def test_base_event_creation_with_required_fields(self):
        """测试使用必填字段创建基础事件"""
        event = BaseEvent(
            event_type=EventType.INPUT,
            source_service="test-service"
        )
        
        assert event.event_type == EventType.INPUT
        assert event.source_service == "test-service"
        assert event.status == EventStatus.PENDING  # 默认状态
        assert event.priority == EventPriority.NORMAL  # 默认优先级
        assert isinstance(event.event_id, str)
        assert len(event.event_id) > 0
        assert isinstance(event.event_time, datetime)
    
    def test_base_event_with_custom_fields(self):
        """测试使用自定义字段创建基础事件"""
        custom_id = str(uuid.uuid4())
        custom_time = datetime.now()
        
        event = BaseEvent(
            event_id=custom_id,
            event_type=EventType.ERROR,
            event_time=custom_time,
            source_service="custom-service",
            status=EventStatus.FAILED,
            priority=EventPriority.HIGH
        )
        
        assert event.event_id == custom_id
        assert event.event_type == EventType.ERROR
        assert event.event_time == custom_time
        assert event.source_service == "custom-service"
        assert event.status == EventStatus.FAILED
        assert event.priority == EventPriority.HIGH
    
    def test_base_event_auto_generated_id(self):
        """测试事件ID自动生成"""
        event1 = BaseEvent(
            event_type=EventType.INPUT,
            source_service="test-service"
        )
        event2 = BaseEvent(
            event_type=EventType.INPUT,
            source_service="test-service"
        )
        
        # 验证ID是唯一的
        assert event1.event_id != event2.event_id
        assert len(event1.event_id) == 36  # UUID4 格式
        assert len(event2.event_id) == 36


class TestInputEvent:
    """输入事件模型测试"""
    
    def test_input_event_creation(self):
        """测试创建输入事件"""
        event = InputEvent(
            source_service="input-service",
            source_platform="mattermost",
            source_type="webhook",
            user_id="user123",
            content="Hello, world!"
        )
        
        assert event.event_type == EventType.INPUT
        assert event.source_service == "input-service"
        assert event.source_platform == "mattermost"
        assert event.source_type == "webhook"
        assert event.user_id == "user123"
        assert event.content == "Hello, world!"
        assert event.user_name is None  # 可选字段默认为 None
        assert event.raw_content is None
        assert event.attachments is None
    
    def test_input_event_with_optional_fields(self):
        """测试包含可选字段的输入事件"""
        attachments = [{"type": "image", "url": "http://example.com/image.png"}]
        
        event = InputEvent(
            source_service="input-service",
            source_platform="slack",
            source_type="api",
            user_id="user456",
            user_name="testuser",
            content="Processed content",
            raw_content="Raw content from API",
            attachments=attachments
        )
        
        assert event.user_name == "testuser"
        assert event.raw_content == "Raw content from API"
        assert event.attachments == attachments
        assert len(event.attachments) == 1
        assert event.attachments[0]["type"] == "image"


class TestOutputEvent:
    """输出事件模型测试"""
    
    def test_output_event_creation(self):
        """测试创建输出事件"""
        event = OutputEvent(
            source_service="output-service",
            target_platform="mattermost",
            target_id="channel123",
            content="Response message"
        )
        
        assert event.event_type == EventType.OUTPUT
        assert event.source_service == "output-service"
        assert event.target_platform == "mattermost"
        assert event.target_id == "channel123"
        assert event.content == "Response message"
        assert event.content_type == "text"  # 默认内容类型
        assert event.attachments is None
    
    def test_output_event_with_attachments(self):
        """测试包含附件的输出事件"""
        attachments = [
            {"type": "file", "name": "document.pdf", "url": "http://example.com/doc.pdf"},
            {"type": "image", "name": "chart.png", "url": "http://example.com/chart.png"}
        ]
        
        event = OutputEvent(
            source_service="output-service",
            target_platform="slack",
            target_id="user789",
            content="Here are the requested files",
            content_type="rich",
            attachments=attachments
        )
        
        assert event.content_type == "rich"
        assert event.attachments == attachments
        assert len(event.attachments) == 2


class TestErrorEvent:
    """错误事件模型测试"""
    
    def test_error_event_creation(self):
        """测试创建错误事件"""
        event = ErrorEvent(
            source_service="processing-service",
            error_type="ValidationError",
            error_message="Invalid input format"
        )
        
        assert event.event_type == EventType.ERROR
        assert event.source_service == "processing-service"
        assert event.error_type == "ValidationError"
        assert event.error_message == "Invalid input format"
        assert event.error_details is None
        assert event.related_event_id is None
    
    def test_error_event_with_details(self):
        """测试包含详细信息的错误事件"""
        error_details = {
            "field": "user_input",
            "expected": "string",
            "actual": "None",
            "code": "ERR_001"
        }
        related_event_id = str(uuid.uuid4())
        
        event = ErrorEvent(
            source_service="validation-service",
            error_type="TypeError",
            error_message="Expected string, got None",
            error_details=error_details,
            related_event_id=related_event_id
        )
        
        assert event.error_details == error_details
        assert event.related_event_id == related_event_id
        assert event.error_details["code"] == "ERR_001"


class TestServiceStatusEvent:
    """服务状态事件模型测试"""
    
    def test_service_status_event_creation(self):
        """测试创建服务状态事件"""
        event = ServiceStatusEvent(
            source_service="monitoring-service",
            service_name="api-gateway",
            status="healthy"
        )
        
        assert event.event_type == EventType.STATUS
        assert event.source_service == "monitoring-service"
        assert event.service_name == "api-gateway"
        assert event.status == "healthy"
        assert event.details is None
    
    def test_service_status_event_with_details(self):
        """测试包含详细信息的服务状态事件"""
        status_details = {
            "uptime": "24h 15m",
            "memory_usage": "85%",
            "cpu_usage": "23%",
            "active_connections": 156,
            "last_health_check": "2023-12-01T10:30:00Z"
        }
        
        event = ServiceStatusEvent(
            source_service="monitoring-service",
            service_name="database",
            status="degraded",
            details=status_details
        )
        
        assert event.status == "degraded"
        assert event.details == status_details
        assert event.details["memory_usage"] == "85%"
        assert event.details["active_connections"] == 156


class TestLegacyEventModels:
    """遗留事件模型测试（向后兼容性）"""
    
    def test_event_meta_creation(self):
        """测试事件元数据创建"""
        event_meta = EventMeta(
            source="mattermost"
        )
        
        assert isinstance(event_meta.event_id, str)
        assert len(event_meta.event_id) == 36  # UUID4 格式
        assert event_meta.source == "mattermost"
        assert isinstance(event_meta.timestamp, int)
        assert event_meta.timestamp > 0
    
    def test_message_content_creation(self):
        """测试消息内容创建"""
        content = MessageContent(
            text="Hello, AI assistant!"
        )
        
        assert content.text == "Hello, AI assistant!"
        assert content.attachments is None
        
        # 测试包含附件的消息
        attachments = [{"type": "image", "url": "http://example.com/image.jpg"}]
        content_with_attachments = MessageContent(
            text="Check out this image",
            attachments=attachments
        )
        
        assert content_with_attachments.attachments == attachments
    
    def test_user_message_raw_event_creation(self):
        """测试用户原始消息事件创建"""
        meta = EventMeta(source="mattermost")
        content = MessageContent(text="Test message")
        
        event = UserMessageRawEvent(
            meta=meta,
            user_id="user123",
            platform="mattermost",
            channel_id="channel456",
            content=content
        )
        
        assert event.meta == meta
        assert event.user_id == "user123"
        assert event.platform == "mattermost"
        assert event.channel_id == "channel456"
        assert event.content == content
        assert event.username is None
        assert event.raw_data is None
    
    def test_user_message_raw_event_with_optional_fields(self):
        """测试包含可选字段的用户原始消息事件"""
        meta = EventMeta(source="slack")
        content = MessageContent(text="Message with optional fields")
        raw_data = {"original_payload": {"key": "value"}}
        
        event = UserMessageRawEvent(
            meta=meta,
            user_id="user789",
            username="testuser",
            platform="slack",
            channel_id="general",
            content=content,
            raw_data=raw_data
        )
        
        assert event.username == "testuser"
        assert event.raw_data == raw_data
        assert event.raw_data["original_payload"]["key"] == "value"


class TestEventModelSerialization:
    """事件模型序列化测试"""
    
    def test_base_event_dict_serialization(self):
        """测试基础事件字典序列化"""
        event = BaseEvent(
            event_type=EventType.INPUT,
            source_service="test-service"
        )
        
        event_dict = event.dict()
        
        assert isinstance(event_dict, dict)
        assert event_dict["event_type"] == "input"
        assert event_dict["source_service"] == "test-service"
        assert event_dict["status"] == "pending"
        assert event_dict["priority"] == 1
        assert "event_id" in event_dict
        assert "event_time" in event_dict
    
    def test_input_event_json_serialization(self):
        """测试输入事件JSON序列化"""
        event = InputEvent(
            source_service="input-service",
            source_platform="mattermost",
            source_type="webhook",
            user_id="user123",
            content="Test message"
        )
        
        json_str = event.json()
        
        assert isinstance(json_str, str)
        assert "input-service" in json_str
        assert "Test message" in json_str
        assert "mattermost" in json_str
        
        # 验证可以反序列化
        import json
        parsed = json.loads(json_str)
        assert parsed["source_service"] == "input-service"
        assert parsed["content"] == "Test message" 