"""
事件总线框架核心模块。

此模块包含事件总线框架的核心接口、数据模型、常量和工具函数。
"""

from .constants import ErrorMessages, RedisConstants
from .exceptions import (
    AcknowledgeError,
    ConnectionError,
    ConsumerGroupError,
    DeserializationError,
    EventBusError,
    PublishError,
    SubscribeError,
)
from .interfaces import IEventBus
from .logging import get_logger, log_event, logger
from .models import EventEnvelope, build_event_envelope
from .subscription_manager import EventSubscriptionManager
from .service_manager import BaseServiceManager, MessageHandlerRegistry
from .utils import (
    build_topic_key,
    decode_redis_stream_message,
    deserialize_from_json,
    generate_unique_id,
    get_machine_hostname,
    get_utc_timestamp,
    serialize_to_json,
)

__all__ = [
    # 接口
    "IEventBus",
    
    # 数据模型
    "EventEnvelope",
    "build_event_envelope",
    
    # 服务管理组件
    "EventSubscriptionManager",
    "BaseServiceManager", 
    "MessageHandlerRegistry",
    
    # 常量
    "RedisConstants",
    "ErrorMessages",
    
    # 异常
    "EventBusError",
    "ConnectionError",
    "PublishError",
    "SubscribeError",
    "AcknowledgeError",
    "DeserializationError",
    "ConsumerGroupError",
    
    # 日志
    "logger",
    "get_logger",
    "log_event",
    
    # 工具函数
    "serialize_to_json",
    "deserialize_from_json",
    "get_machine_hostname",
    "generate_unique_id",
    "get_utc_timestamp",
    "build_topic_key",
    "decode_redis_stream_message",
]
