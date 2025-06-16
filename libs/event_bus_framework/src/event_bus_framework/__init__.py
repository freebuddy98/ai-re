"""
Event Bus Framework

基于Redis Streams的事件总线框架，为AI-RE系统提供可靠的事件源和消息传递。
"""
from typing import Dict, Any

# 导出核心接口
from .core.interfaces import IEventBus, IEventHandler, IEventStorage
from .core.constants import RedisConstants

# 导出实现
from .adapters.redis_streams import RedisStreamEventBus, RedisStreamConsumerGroup

# 导出工厂模式
from .factory import (
    EventBusFactory,
    RedisEventBusFactory,
    EventBusFactoryRegistry,
    create_event_bus
)

# 导出服务管理组件
from .core.subscription_manager import EventSubscriptionManager
from .core.service_manager import BaseServiceManager, MessageHandlerRegistry

# 导出common模块组件
from .common.logger import get_logger
from .common.config import load_config
from .common.events import (
    BaseEvent,
    InputEvent,
    OutputEvent,
    ErrorEvent,
    ServiceStatusEvent,
    EventStatus,
    EventPriority,
    EventType,
    EventMeta,
    MessageContent,
    UserMessageRawEvent
)

# 导出配置管理模块 
from .common.config import get_config, get_service_config

# 向后兼容：导出输入服务配置，建议使用 get_service_config('input_service')
input_service_config = get_service_config('input_service')

# 版本信息
__version__ = "0.1.0"
__author__ = "AI-RE Team"

__all__ = [
    # 核心接口
    "IEventBus", 
    "IEventHandler", 
    "IEventStorage",
    
    # 实现
    "RedisStreamEventBus", 
    "RedisStreamConsumerGroup",
    
    # 工厂模式
    "EventBusFactory",
    "RedisEventBusFactory", 
    "EventBusFactoryRegistry",
    "create_event_bus",
    
    # 服务管理组件
    "EventSubscriptionManager",
    "BaseServiceManager",
    "MessageHandlerRegistry",
    
    # 常量
    "RedisConstants",
    
    # 公共组件
    "get_logger",
    "load_config",
    "get_config",
    "get_service_config",
    
    # 事件模型
    "BaseEvent",
    "InputEvent", 
    "OutputEvent",
    "ErrorEvent",
    "ServiceStatusEvent",
    "EventStatus",
    "EventPriority", 
    "EventType",
    "EventMeta",
    "MessageContent",
    "UserMessageRawEvent",
    
    # 向后兼容
    "input_service_config"
]
