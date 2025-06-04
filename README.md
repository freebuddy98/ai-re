# AI-RE 项目

AI-RE是一个基于事件驱动架构的智能助手系统，通过多个微服务协同工作，提供高效、可靠的人工智能响应能力。

## 项目结构

AI-RE项目由以下主要模块组成：

- **事件总线框架 (Event Bus Framework)**: 基于Redis Streams的消息传递系统，为各服务提供可靠的异步通信机制
- **输入服务 (Input Service)**: 处理来自各种渠道的用户输入
- **自然语言理解服务 (NLU Service)**: 分析和理解用户意图
- **对话策略服务 (DPSS)**: 管理对话流程和决策
- **响应生成服务 (RIMS)**: 生成适当的响应内容
- **输出服务 (Output Service)**: 将响应传递给用户

## 事件总线框架

事件总线框架为AI-RE系统中的各个服务提供一个统一的、高可靠的、支持事件溯源与重放的异步消息传递机制。

### 核心特性

- **服务解耦**: 发布者和订阅者互不依赖，通过事件实现松耦合通信
- **异步通信**: 非阻塞的事件传递提高系统的整体响应性
- **可靠性**: 至少一次消息处理语义 (At-Least-Once Semantics)
- **事件溯源**: 通过消息持久化支持事件历史追踪和状态重建
- **按需重放**: 从任意位置开始消费事件，支持调试和故障恢复
- **消费者组**: 支持消费者组负载均衡与故障转移

### 快速开始

#### 安装依赖

```bash
pip install -e .
```

#### 发布事件

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

#### 订阅事件

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

## 开发环境设置

### 前提条件

- Python 3.8+
- Redis服务器

### 安装步骤

1. 克隆仓库
   ```bash
   git clone https://github.com/yourusername/ai-re.git
   cd ai-re
   ```

2. 创建并激活虚拟环境
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate  # Windows
   ```

3. 安装项目依赖
   ```bash
   pip install -e .
   ```

4. 安装开发依赖
   ```bash
   pip install -e ".[dev]"
   ```

## 运行测试

```bash
# 运行单元测试
pytest tests/unit

# 运行集成测试
pytest tests/integration

# 运行特定模块的测试
pytest tests/unit/test_redis_streams.py
```

## 许可证

本项目采用MIT许可证 - 详见 LICENSE 文件 