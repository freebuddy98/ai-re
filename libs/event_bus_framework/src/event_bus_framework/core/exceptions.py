"""
事件总线框架的自定义异常定义。
"""


class EventBusError(Exception):
    """事件总线框架的基础异常类"""
    pass


class ConnectionError(EventBusError):
    """与消息中间件连接相关的异常"""
    pass


class PublishError(EventBusError):
    """发布事件时发生的异常"""
    pass


class SubscribeError(EventBusError):
    """订阅事件时发生的异常"""
    pass


class AcknowledgeError(EventBusError):
    """确认消息时发生的异常"""
    pass


class DeserializationError(EventBusError):
    """消息反序列化异常"""
    pass


class ConsumerGroupError(EventBusError):
    """消费者组操作异常"""
    pass 