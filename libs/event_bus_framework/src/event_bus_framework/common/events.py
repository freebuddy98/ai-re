"""
事件模型

定义系统中使用的基础事件模型。具体的事件定义请参考 config/events.yml 配置文件。
"""
import uuid
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field

from .logger import get_logger

# 创建事件模块日志器
logger = get_logger("events")


class EventType(str, Enum):
    """事件类型"""
    INPUT = "input"
    OUTPUT = "output"
    ERROR = "error"
    STATUS = "status"
    SYSTEM = "system"


class EventStatus(str, Enum):
    """事件状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class EventPriority(int, Enum):
    """事件优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class BaseEvent(BaseModel):
    """
    基础事件模型
    
    所有事件的基类，包含事件的基本属性。
    """
    # 事件元数据
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    event_time: datetime = Field(default_factory=datetime.now)
    source_service: str
    
    # 事件状态
    status: EventStatus = EventStatus.PENDING
    priority: EventPriority = EventPriority.NORMAL


class InputEvent(BaseEvent):
    """
    输入事件
    
    表示从外部系统接收到的事件。
    """
    event_type: EventType = EventType.INPUT
    
    # 输入来源
    source_platform: str
    source_type: str
    
    # 用户信息
    user_id: str
    user_name: Optional[str] = None
    
    # 输入内容
    content: str
    raw_content: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class OutputEvent(BaseEvent):
    """
    输出事件
    
    表示发送到外部系统的事件。
    """
    event_type: EventType = EventType.OUTPUT
    
    # 目标信息
    target_platform: str
    target_id: str
    
    # 输出内容
    content: str
    content_type: str = "text"
    attachments: Optional[List[Dict[str, Any]]] = None


class ErrorEvent(BaseEvent):
    """
    错误事件
    
    表示系统中发生的错误。
    """
    event_type: EventType = EventType.ERROR
    
    # 错误信息
    error_type: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    
    # 相关事件
    related_event_id: Optional[str] = None


class ServiceStatusEvent(BaseEvent):
    """
    服务状态事件
    
    表示服务状态变化。
    """
    event_type: EventType = EventType.STATUS
    
    # 服务信息
    service_name: str
    status: str
    
    # 状态详情
    details: Optional[Dict[str, Any]] = None


# 为了向后兼容，保留但标记为废弃的事件模型
class EventMeta(BaseModel):
    """@deprecated 事件元数据，请使用配置文件中的事件定义"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


class MessageContent(BaseModel):
    """@deprecated 消息内容，请使用配置文件中的事件定义"""
    text: str
    attachments: Optional[List[Dict[str, Any]]] = None


class UserMessageRawEvent(BaseModel):
    """@deprecated 用户原始消息事件，请使用配置文件中的事件定义"""
    meta: EventMeta
    user_id: str
    username: Optional[str] = None
    platform: str
    channel_id: str
    content: MessageContent
    raw_data: Optional[Dict[str, Any]] = None 