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
