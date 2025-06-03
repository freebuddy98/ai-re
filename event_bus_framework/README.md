# Event Bus Framework

事件总线框架 (Event Bus Framework) 为 AI-RE 助手系统中的各个服务提供一个统一的、高可靠的、支持事件溯源与重放的异步消息传递机制。

## 核心特性

- **服务解耦**: 发布者和订阅者互不依赖，通过事件实现松耦合通信
- **异步通信**: 非阻塞的事件传递提高系统的整体响应性
- **可靠性**: 至少一次消息处理语义 (At-Least-Once Semantics)
- **事件溯源**: 通过消息持久化支持事件历史追踪和状态重建
- **按需重放**: 从任意位置开始消费事件，支持调试和故障恢复
- **消费者组**: 支持消费者组负载均衡与故障转移

## 技术实现

框架基于 Redis Streams 实现，通过提供抽象接口 (`IEventBus`) 支持未来扩展到其他后端。

## 快速开始

### 安装

```bash
pip install event-bus-framework
```

### 发布事件

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
    message_data={"user_id": "123", "message": "Hello"},
    event_type_hint="UserMessage"
)
print(f"Published event with ID: {event_id}")
```

### 订阅事件

```python
def message_handler(message_id, event_envelope, actual_payload):
    print(f"Received message {message_id}")
    print(f"Event type: {event_envelope['event_type']}")
    print(f"Payload: {actual_payload}")
    
    # 处理完成后确认消息
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
    consumer_name="Worker1",
    auto_acknowledge=False  # 建议手动确认
)
```

## 开发文档

详细的开发文档请参考 `docs/` 目录。
