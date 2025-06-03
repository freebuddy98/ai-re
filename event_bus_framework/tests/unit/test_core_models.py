"""
测试事件总线框架的核心数据模型。
"""
import json
import re
import uuid
from datetime import datetime

import pytest

from event_bus_framework.core.models import EventEnvelope, build_event_envelope


class TestEventEnvelope:
    """测试事件信封模型"""
    
    def test_event_envelope_creation(self):
        """测试创建事件信封"""
        # 准备
        payload = {"user_id": "123", "message": "Hello"}
        
        # 执行
        envelope = EventEnvelope(
            event_type="TestEvent",
            source_service="TestService",
            actual_payload=payload
        )
        
        # 验证
        assert envelope.event_type == "TestEvent"
        assert envelope.source_service == "TestService"
        assert envelope.actual_payload == payload
        assert envelope.version == "1.0"
        
        # 验证自动生成的字段
        assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', envelope.event_id)
        assert re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', envelope.published_at_utc)
    
    def test_event_envelope_create_method(self):
        """测试事件信封的create工厂方法"""
        # 准备
        payload = {"user_id": "123", "message": "Hello"}
        
        # 执行
        envelope = EventEnvelope.create(
            message_data=payload,
            source_service="TestService",
            event_type="TestEvent",
            dialogue_session_id="session123",
            trace_id="trace123"
        )
        
        # 验证
        assert envelope.event_type == "TestEvent"
        assert envelope.source_service == "TestService"
        assert envelope.dialogue_session_id == "session123"
        assert envelope.trace_id == "trace123"
        assert envelope.actual_payload == payload
        assert envelope.version == "1.0"
        
    def test_event_envelope_serialization(self):
        """测试事件信封的序列化"""
        # 准备
        payload = {"user_id": "123", "message": "Hello"}
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        envelope = EventEnvelope(
            event_id=event_id,
            event_type="TestEvent",
            source_service="TestService",
            published_at_utc=timestamp,
            dialogue_session_id="session123",
            actual_payload=payload
        )
        
        # 执行
        json_str = envelope.model_dump_json()
        deserialized = json.loads(json_str)
        
        # 验证
        assert deserialized["event_id"] == event_id
        assert deserialized["event_type"] == "TestEvent"
        assert deserialized["source_service"] == "TestService"
        assert deserialized["published_at_utc"] == timestamp
        assert deserialized["dialogue_session_id"] == "session123"
        assert deserialized["actual_payload"] == payload
        assert deserialized["version"] == "1.0"
        assert deserialized["trace_id"] is None


class TestBuildEventEnvelope:
    """测试构建事件信封的函数"""
    
    def test_build_event_envelope(self):
        """测试构建事件信封函数"""
        # 准备
        payload = {"user_id": "123", "message": "Hello"}
        
        # 执行
        envelope = build_event_envelope(
            message_data=payload,
            source_service="TestService",
            event_type_hint="TestEvent",
            dialogue_session_id_hint="session123",
            trace_id="trace123"
        )
        
        # 验证
        assert envelope.event_type == "TestEvent"
        assert envelope.source_service == "TestService"
        assert envelope.dialogue_session_id == "session123"
        assert envelope.trace_id == "trace123"
        assert envelope.actual_payload == payload
        
    def test_build_event_envelope_default_values(self):
        """测试构建事件信封函数的默认值"""
        # 准备
        payload = {"user_id": "123", "message": "Hello"}
        
        # 执行
        envelope = build_event_envelope(
            message_data=payload,
            source_service="TestService"
        )
        
        # 验证
        assert envelope.event_type == "UnknownEventType"
        assert envelope.source_service == "TestService"
        assert envelope.dialogue_session_id is None
        assert envelope.trace_id is None
        assert envelope.actual_payload == payload 