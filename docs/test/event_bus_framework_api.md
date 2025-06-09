# Event Bus Framework - 外部接口文档

## 概述

Event Bus Framework 是 AI-RE 系统的核心消息传递组件，基于 Redis Streams 实现分布式事件驱动架构。该框架提供统一的事件发布、订阅和处理机制。

## 版本信息

- **版本**: 0.1.0
- **协议**: 基于 Redis Streams
- **支持的序列化格式**: JSON

## 核心接口

### 1. IEventBus 接口

事件总线的核心抽象接口，定义了事件发布和订阅的标准方法。

#### 方法签名

```python
class IEventBus(Protocol):
    def publish(self, topic: str, event_data: Dict[str, Any], **kwargs) -> Optional[str]
    def subscribe(self, topic: str, consumer_group: str, **kwargs) -> Iterator[Dict[str, Any]]
    def create_consumer_group(self, topic: str, consumer_group: str, **kwargs) -> bool
    def close(self) -> None
```

#### 方法详细说明

##### publish()

**功能**: 发布事件到指定主题

**参数**:
- `topic` (str): 目标主题名称
- `event_data` (Dict[str, Any]): 事件数据，必须可JSON序列化
- `**kwargs`: 额外的发布选项

**返回值**: 
- `Optional[str]`: 成功时返回消息ID，失败时返回None

**示例**:
```python
message_id = event_bus.publish(
    topic="user_message_raw",
    event_data={
        "user_id": "user123",
        "content": {"text": "Hello, AI!"},
        "meta": {"source": "mattermost", "timestamp": 1677123456}
    }
)
```

##### subscribe()

**功能**: 订阅指定主题的事件流

**参数**:
- `topic` (str): 订阅的主题名称
- `consumer_group` (str): 消费者组名称
- `**kwargs`: 额外的订阅选项

**返回值**: 
- `Iterator[Dict[str, Any]]`: 事件数据迭代器

**示例**:
```python
for event in event_bus.subscribe("user_message_raw", "processing-service"):
    process_event(event)
```

##### create_consumer_group()

**功能**: 创建消费者组

**参数**:
- `topic` (str): 主题名称
- `consumer_group` (str): 消费者组名称
- `**kwargs`: 额外的创建选项

**返回值**: 
- `bool`: 创建成功返回True，否则返回False

### 2. RedisStreamEventBus 实现

Redis Streams 的具体实现类，提供高性能的事件传递能力。

#### 初始化参数

```python
def __init__(
    self,
    redis_client: redis.Redis,
    stream_prefix: str = "ai-re",
    event_source_name: str = "default-service",
    logger: Optional[logging.Logger] = None
)
```

**参数说明**:
- `redis_client`: Redis客户端实例
- `stream_prefix`: 流名称前缀，默认"ai-re"
- `event_source_name`: 事件源服务名称
- `logger`: 可选的日志记录器

#### 配置示例

```python
import redis
from event_bus_framework import RedisStreamEventBus

# 创建Redis连接
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# 初始化事件总线
event_bus = RedisStreamEventBus(
    redis_client=redis_client,
    stream_prefix="ai-re",
    event_source_name="input-service"
)
```

## 事件模型

### 1. 基础事件结构

所有事件都遵循统一的基础结构：

```json
{
  "event_id": "uuid-string",
  "event_type": "input|output|error|status|system",
  "event_time": "2023-12-01T10:30:00Z",
  "source_service": "service-name",
  "status": "pending|processing|completed|failed|unknown",
  "priority": 0-3
}
```

### 2. 输入事件 (InputEvent)

用于表示从外部系统接收到的事件：

```json
{
  "event_type": "input",
  "source_service": "input-service",
  "source_platform": "mattermost",
  "source_type": "webhook",
  "user_id": "user123",
  "user_name": "john_doe",
  "content": "Hello, AI assistant!",
  "raw_content": "原始未处理内容",
  "attachments": [
    {
      "type": "image",
      "url": "http://example.com/image.png"
    }
  ]
}
```

### 3. 输出事件 (OutputEvent)

用于表示发送到外部系统的事件：

```json
{
  "event_type": "output",
  "source_service": "response-service",
  "target_platform": "mattermost",
  "target_id": "channel123",
  "content": "AI响应内容",
  "content_type": "text|rich|markdown",
  "attachments": []
}
```

### 4. 错误事件 (ErrorEvent)

用于表示系统中发生的错误：

```json
{
  "event_type": "error",
  "source_service": "processing-service",
  "error_type": "ValidationError",
  "error_message": "输入验证失败",
  "error_details": {
    "field": "user_input",
    "expected": "string",
    "actual": "null"
  },
  "related_event_id": "parent-event-uuid"
}
```

## 配置接口

### 1. 配置加载

```python
from event_bus_framework.common.config import (
    load_config,
    get_service_config,
    get_topics_for_service,
    get_event_bus_config
)

# 加载完整配置
config = load_config()

# 获取特定服务配置
service_config = get_service_config("input_service")

# 获取服务主题配置
topics = get_topics_for_service("input_service")
# 返回: {"publish": ["topic1"], "subscribe": ["topic2"]}

# 获取事件总线配置
event_bus_config = get_event_bus_config()
```

### 2. 环境变量支持

配置支持环境变量替换：

```yaml
redis:
  host: "${REDIS_HOST:-redis}"
  port: "${REDIS_PORT:-6379}"
  password: "${REDIS_PASSWORD:-}"
```

## 日志接口

### 1. 日志记录器获取

```python
from event_bus_framework.common.logger import get_logger

logger = get_logger("my-service")
logger.info("服务已启动")
logger.error("处理失败", extra={"user_id": "123"})
```

### 2. 日志配置

```python
# 配置文件中的日志设置
logging:
  level: "INFO"
  format: "json"
  file: "app.log"
  dir: "/app/logs"
  enable_loki: "true"
  loki_url: "http://loki:3100/loki/api/v1/push"
```

## 异常处理

### 1. 异常层次结构

```
EventBusException (基类)
├── ConnectionException (连接异常)
├── PublishException (发布异常)
├── SubscribeException (订阅异常)
├── ConfigurationException (配置异常)
├── SerializationException (序列化异常)
└── ValidationException (验证异常)
```

### 2. 异常处理示例

```python
from event_bus_framework.core.exceptions import PublishException

try:
    message_id = event_bus.publish("topic", event_data)
    if not message_id:
        raise PublishException("消息发布失败")
except PublishException as e:
    logger.error(f"发布错误: {e}")
    # 执行错误处理逻辑
```

## 工具函数

### 1. 事件验证

```python
from event_bus_framework.core.utils import (
    validate_event_data,
    serialize_event,
    deserialize_event
)

# 验证事件数据
is_valid = validate_event_data(event_data)

# 序列化事件
json_str = serialize_event(event_obj)

# 反序列化事件
event_obj = deserialize_event(json_str)
```

### 2. 主题管理

```python
from event_bus_framework.core.utils import generate_stream_name

# 生成流名称
stream_name = generate_stream_name("ai-re", "user_message_raw")
# 返回: "ai-re:user_message_raw"
```

## 性能考虑

### 1. 连接池配置

```python
import redis

# Redis连接池配置
redis_client = redis.Redis(
    connection_pool=redis.ConnectionPool(
        host='redis',
        port=6379,
        max_connections=20,
        socket_timeout=5,
        socket_connect_timeout=5
    )
)
```

### 2. 批量操作

```python
# 批量发布（如果支持）
event_bus.publish_batch([
    ("topic1", event_data1),
    ("topic2", event_data2)
])
```

## 监控指标

### 1. 内置指标

- 发布成功/失败计数
- 订阅消息处理延迟
- 连接状态
- 队列深度

### 2. 健康检查

```python
from event_bus_framework.core.utils import health_check

status = health_check(event_bus)
# 返回: {"status": "healthy", "details": {...}}
```

## 最佳实践

### 1. 错误处理

- 始终检查发布操作的返回值
- 实现适当的重试机制
- 使用死信队列处理失败消息

### 2. 性能优化

- 使用连接池避免频繁连接
- 合理设置消费者组大小
- 监控队列积压情况

### 3. 安全考虑

- 验证事件数据格式
- 实施访问控制
- 记录审计日志

## 兼容性

- **Python版本**: 3.8+
- **Redis版本**: 5.0+
- **依赖项**: 参见 `pyproject.toml`

## 变更日志

### v0.1.0 (2023-12-01)
- 初始版本发布
- 基础事件发布/订阅功能
- Redis Streams 适配器
- 配置管理系统
- 日志系统集成 