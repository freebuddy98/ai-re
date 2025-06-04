"""
事件总线框架适配器模块。

此模块包含各种后端存储适配器的实现。
"""

from .redis_streams import RedisStreamsEventBus, MessageHandlerLoopThread

__all__ = [
    "RedisStreamsEventBus",
    "MessageHandlerLoopThread"
]
