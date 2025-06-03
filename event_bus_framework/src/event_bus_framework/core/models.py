"""
事件总线框架的核心数据模型。

此模块定义了事件信封 (Event Envelope) 和其他相关数据结构。
"""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventEnvelope(BaseModel):
    """
    事件信封模型，用于包装所有通过事件总线传递的消息。
    
    事件信封标准化了事件的元数据，便于事件溯源和追踪。
    """
    # 事件的唯一标识符，默认自动生成UUID字符串
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    
    # 事件类型，用于指示此事件的业务含义和处理方式
    event_type: str
    
    # 发布此事件的服务名称，用于追踪事件来源
    source_service: str
    
    # 事件发布的UTC时间，ISO 8601格式
    published_at_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # 分布式追踪ID，用于跨服务追踪相关事件
    trace_id: Optional[str] = None
    
    # 对话会话ID，用于关联同一会话中的相关事件
    dialogue_session_id: Optional[str] = None
    
    # 事件信封的版本号
    version: str = "1.0"
    
    # 事件的实际业务载荷数据
    actual_payload: Dict[str, Any]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "123e4567-e89b-12d3-a456-426614174000",
                "event_type": "UserMessageRaw_v1",
                "source_service": "InputService_v1.0",
                "published_at_utc": "2025-06-03T08:33:00.000Z",
                "trace_id": "trace-123",
                "dialogue_session_id": "channel_xyz",
                "version": "1.0",
                "actual_payload": {
                    "user_id": "user-123",
                    "message": "Hello, world!"
                }
            }
        }
    )

    @classmethod
    def create(
        cls,
        message_data: Dict[str, Any],
        source_service: str,
        event_type: str = "UnknownEventType",
        dialogue_session_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> "EventEnvelope":
        """
        创建标准的事件信封的工厂方法。
        
        Args:
            message_data: 事件的业务载荷数据。
            source_service: 发布事件的服务名称。
            event_type: 应用层定义的具体事件类型。
            dialogue_session_id: 应用层传入的会话标识。
            trace_id: 用于分布式追踪的追踪ID。
            
        Returns:
            包含完整元数据的事件信封对象。
        """
        return cls(
            event_type=event_type,
            source_service=source_service,
            trace_id=trace_id,
            dialogue_session_id=dialogue_session_id,
            actual_payload=message_data
        )


# 为了保持向后兼容性，提供全局函数
def build_event_envelope(
    message_data: Dict[str, Any],
    source_service: str,
    event_type_hint: Optional[str] = None,
    dialogue_session_id_hint: Optional[str] = None,
    trace_id: Optional[str] = None
) -> EventEnvelope:
    """
    构建标准的事件信封。
    
    此函数是为了提供与构造方法不同的接口，使代码更易读，
    并允许在事件创建前进行额外的处理逻辑。
    
    Args:
        message_data: 事件的业务载荷数据。
        source_service: 发布事件的服务名称。
        event_type_hint: 应用层定义的具体事件类型。
        dialogue_session_id_hint: 应用层传入的会话标识。
        trace_id: 用于分布式追踪的追踪ID。
        
    Returns:
        包含完整元数据的事件信封对象。
    """
    return EventEnvelope.create(
        message_data=message_data,
        source_service=source_service,
        event_type=event_type_hint or "UnknownEventType",
        dialogue_session_id=dialogue_session_id_hint,
        trace_id=trace_id
    ) 