"""
事件总线框架 (Event Bus Framework)

事件总线框架为 AI-RE 助手系统中的各个服务提供一个统一的、高可靠的、
支持事件溯源与重放的异步消息传递机制。

基本用法:

```python
from event_bus_framework import RedisStreamsEventBus

# 创建事件总线客户端
event_bus = RedisStreamsEventBus(
    redis_url="redis://localhost:6379/0",
    event_source_name="MyService"
)

# 发布事件
event_id = event_bus.publish(
    topic="stream:20250603123456:input:raw_message",
    message_data={"user_id": "123", "message": "Hello"}
)

# 定义处理函数
def message_handler(message_id, event_envelope, actual_payload):
    print(f"Received message: {actual_payload}")
    event_bus.acknowledge(
        topic="stream:20250603123456:input:raw_message",
        group_name="ProcessingGroup",
        message_ids=[message_id]
    )

# 订阅事件
event_bus.subscribe(
    topic="stream:20250603123456:input:raw_message",
    handler_function=message_handler,
    group_name="ProcessingGroup",
    consumer_name="Worker1"
)
"""

__version__ = "0.1.0"

from .core import (
    AcknowledgeError,
    ConnectionError,
    ConsumerGroupError,
    DeserializationError,
    ErrorMessages,
    EventBusError,
    EventEnvelope,
    IEventBus,
    PublishError,
    RedisConstants,
    SubscribeError,
    build_event_envelope,
    get_logger,
    logger,
)

# 导入 Redis Streams 实现
from .adapters import RedisStreamsEventBus, MessageHandlerLoopThread

__all__ = [
    "IEventBus",
    "RedisStreamsEventBus",
    "MessageHandlerLoopThread",
    "EventEnvelope",
    "EventBusError",
]
