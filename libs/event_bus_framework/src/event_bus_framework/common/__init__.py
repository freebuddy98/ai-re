"""
公共模块

包含共享的日志、配置和事件定义。
"""
from .logger import get_logger
from .config import (
    load_config, 
    get_config, 
    get_service_config, 
    get_event_bus_config, 
    get_logging_config, 
    get_topics_for_service,
    get_input_service_config  # 保持向后兼容
)

__all__ = [
    "get_logger",
    "load_config",
    "get_config",
    "get_service_config",
    "get_event_bus_config",
    "get_logging_config",
    "get_topics_for_service",
    "get_input_service_config"  # 保持向后兼容
] 