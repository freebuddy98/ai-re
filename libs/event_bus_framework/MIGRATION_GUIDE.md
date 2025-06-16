# Event Bus Framework 通用组件迁移指南

## 概述

本指南说明如何使用 `event_bus_framework` 中新增的通用组件来快速创建微服务，避免重复编写相同的事件订阅和服务管理代码。

## 新增的通用组件

### 1. EventSubscriptionManager
通用的事件订阅管理器，提供：
- 主题处理器注册
- 同步/异步消息处理
- 消息确认机制
- 调试模式支持
- 异常处理

### 2. BaseServiceManager
微服务管理器基类，提供：
- 标准的服务生命周期管理
- 配置加载
- 事件总线初始化
- 事件订阅设置
- 服务启动/停止

### 3. MessageHandlerRegistry
消息处理器注册表，提供：
- 主题到处理器的映射管理
- 默认处理器支持
- 批量注册功能

## 快速开始

### 创建新的微服务

只需要继承 `BaseServiceManager` 并实现三个抽象方法：

```python
from event_bus_framework import BaseServiceManager, MessageHandlerRegistry
from typing import Dict, Any

class MyServiceManager(BaseServiceManager):
    def get_service_name(self) -> str:
        return "my_service"
    
    def initialize_business_components(self) -> None:
        # 初始化你的业务组件
        self.processor = MyMessageProcessor()
        self.registry = MessageHandlerRegistry("my_service")
        self.registry.register_handlers({
            'topic1': self.processor.handle_topic1,
            'topic2': self.processor.handle_topic2,
        })
    
    def get_message_handlers(self) -> Dict[str, Any]:
        return self.registry.get_all_handlers()
```

### 消息处理器

消息处理器函数签名：

```python
def handle_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
    """
    处理消息
    
    Args:
        message_id: 消息ID
        message_data: 消息数据
        
    Returns:
        bool: True表示成功处理，False表示处理失败
    """
    try:
        # 处理业务逻辑
        return True
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return False
```

### 配置文件

在 `config/config.yml` 中添加服务配置：

```yaml
my_service:
  topics:
    subscribe: ['topic1', 'topic2']
    publish: ['output_topic']
  consumer_group: 'my-service-group'
  consumer_name: 'my-worker'
  debug_mode: true  # 开发时启用
```

### 启动服务

```python
async def main():
    service_manager = MyServiceManager()
    
    # 可选：覆盖配置
    service_manager.set_consumer_config(
        consumer_group="custom-group",
        debug_mode=True
    )
    
    await service_manager.start_async()
    
    # 保持运行
    while service_manager.is_running():
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## 从现有代码迁移

### 迁移 NLU Service

**之前的代码：**
```python
# 需要手动管理事件订阅、消息处理、服务生命周期
class NLUServiceManager:
    def __init__(self):
        self.config = None
        self.event_bus = None
        self.event_manager = None
        # ... 大量重复的初始化代码
    
    def load_configuration(self):
        # 重复的配置加载逻辑
        pass
    
    def initialize_event_bus(self):
        # 重复的事件总线初始化逻辑
        pass
    
    def setup_event_subscriptions(self):
        # 重复的订阅设置逻辑
        pass
```

**迁移后的代码：**
```python
# 继承BaseServiceManager，专注于业务逻辑
class NLUServiceManager(BaseServiceManager):
    def get_service_name(self) -> str:
        return "nlu_service"
    
    def initialize_business_components(self) -> None:
        # 只需要初始化NLU特定的组件
        self.nlu_processor = NLUProcessorFactory.create_nlu_processor(...)
        self.message_handlers = MessageHandlers(self.nlu_processor)
        # ...
    
    def get_message_handlers(self) -> Dict[str, Any]:
        return self.handler_registry.get_all_handlers()
```

### 代码减少量

- **配置管理**: 从 ~50 行减少到 0 行（由基类处理）
- **事件总线初始化**: 从 ~30 行减少到 0 行
- **事件订阅管理**: 从 ~80 行减少到 ~10 行
- **服务生命周期**: 从 ~40 行减少到 0 行

**总计减少约 200 行重复代码**

## 高级功能

### 异步消息处理

```python
async def handle_async_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
    """异步消息处理器"""
    await some_async_operation()
    return True

# 框架会自动检测并正确处理异步函数
```

### 调试模式

```python
# 启用调试模式会在服务启动时重置消费者组
service_manager.set_consumer_config(debug_mode=True)
```

### 自定义消费者配置

```python
service_manager.set_consumer_config(
    consumer_group="custom-group",
    consumer_name="custom-worker",
    debug_mode=False
)
```

### 默认处理器

```python
def handle_unknown_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
    """处理未知消息类型"""
    logger.warning(f"Unknown message: {message_data}")
    return True

registry.set_default_handler(handle_unknown_message)
```

## 最佳实践

### 1. 错误处理
```python
def handle_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
    try:
        # 业务逻辑
        return True
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return True  # 确认无效消息，避免重复处理
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return False  # 不确认，允许重试
```

### 2. 消息验证
```python
def handle_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
    # 验证必需字段
    required_fields = ['user_id', 'action']
    if not all(field in message_data for field in required_fields):
        logger.error(f"Missing required fields: {message_data}")
        return True  # 确认无效消息
    
    # 处理有效消息
    return self.process_valid_message(message_data)
```

### 3. 日志记录
```python
def handle_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
    logger.info(f"[{self.service_name}] Processing message {message_id}")
    
    try:
        result = self.process_message(message_data)
        logger.info(f"[{self.service_name}] Successfully processed {message_id}")
        return True
    except Exception as e:
        logger.error(f"[{self.service_name}] Failed to process {message_id}: {e}")
        return False
```

## 示例项目

查看 `examples/simple_service.py` 获取完整的示例代码。

## 测试

框架提供了完整的单元测试：
- `tests/unit/test_subscription_manager.py`
- `tests/unit/test_service_manager.py`

运行测试：
```bash
cd libs/event_bus_framework
python -m pytest tests/unit/test_subscription_manager.py tests/unit/test_service_manager.py -v
```

## 总结

使用新的通用组件，创建微服务的代码量减少了约 80%，同时获得了：

- ✅ 标准化的服务架构
- ✅ 统一的错误处理
- ✅ 自动的消息确认
- ✅ 调试模式支持
- ✅ 完整的测试覆盖
- ✅ 详细的日志记录

这使得开发者可以专注于业务逻辑，而不是重复的基础设施代码。 