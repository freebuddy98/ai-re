#!/usr/bin/env python3
"""
简单微服务示例

演示如何使用event_bus_framework的通用组件快速创建一个新的微服务。
这个示例展示了最小化的代码量来实现一个功能完整的微服务。
"""
import asyncio
from typing import Dict, Any

from event_bus_framework import (
    BaseServiceManager,
    MessageHandlerRegistry,
    get_logger
)

logger = get_logger("simple_service")


class SimpleMessageProcessor:
    """简单的消息处理器"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
    
    def handle_greeting(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """处理问候消息"""
        try:
            user_name = message_data.get('user_name', 'Unknown')
            message = message_data.get('message', '')
            
            logger.info(f"[{self.service_name}] Received greeting from {user_name}: {message}")
            
            # 这里可以添加业务逻辑
            response = f"Hello {user_name}! I received your message: {message}"
            logger.info(f"[{self.service_name}] Response: {response}")
            
            return True  # 成功处理
            
        except Exception as e:
            logger.error(f"[{self.service_name}] Error processing greeting: {e}")
            return False
    
    def handle_notification(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """处理通知消息"""
        try:
            notification_type = message_data.get('type', 'general')
            content = message_data.get('content', '')
            
            logger.info(f"[{self.service_name}] Received {notification_type} notification: {content}")
            
            # 这里可以添加通知处理逻辑
            return True
            
        except Exception as e:
            logger.error(f"[{self.service_name}] Error processing notification: {e}")
            return False
    
    def handle_unknown(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """处理未知消息类型"""
        logger.warning(f"[{self.service_name}] Received unknown message type: {message_data}")
        return True  # 即使是未知消息也确认，避免重复处理


class SimpleServiceManager(BaseServiceManager):
    """
    简单服务管理器
    
    继承BaseServiceManager，只需要实现三个抽象方法即可获得完整的服务功能：
    - 配置加载
    - 事件总线初始化  
    - 事件订阅管理
    - 服务生命周期管理
    """
    
    def __init__(self):
        super().__init__()
        self.message_processor = None
        self.handler_registry = None
    
    def get_service_name(self) -> str:
        """返回服务名称"""
        return "simple_service"
    
    def initialize_business_components(self) -> None:
        """初始化业务组件"""
        try:
            # 创建消息处理器
            self.message_processor = SimpleMessageProcessor("simple_service")
            
            # 创建处理器注册表
            self.handler_registry = MessageHandlerRegistry("simple_service")
            
            # 注册消息处理器
            self.handler_registry.register_handlers({
                'greeting': self.message_processor.handle_greeting,
                'notification': self.message_processor.handle_notification,
            })
            
            # 设置默认处理器
            self.handler_registry.set_default_handler(self.message_processor.handle_unknown)
            
            logger.info("[simple_service] Business components initialized")
            
        except Exception as e:
            logger.error(f"[simple_service] Failed to initialize business components: {e}")
            raise
    
    def get_message_handlers(self) -> Dict[str, Any]:
        """返回消息处理器映射"""
        if not self.handler_registry:
            raise ValueError("Handler registry not initialized")
        
        return self.handler_registry.get_all_handlers()


async def main():
    """主函数"""
    logger.info("Starting Simple Service...")
    
    # 创建服务管理器
    service_manager = SimpleServiceManager()
    
    # 可选：设置自定义消费者配置
    service_manager.set_consumer_config(
        consumer_group="simple-service-group",
        consumer_name="simple-worker",
        debug_mode=True  # 开发时启用调试模式
    )
    
    try:
        # 启动服务
        await service_manager.start_async()
        
        logger.info("Simple Service started successfully!")
        logger.info(f"Subscribed to topics: {service_manager.get_subscribed_topics()}")
        
        # 保持服务运行
        while service_manager.is_running():
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        # 停止服务
        await service_manager.stop_async()
        logger.info("Simple Service stopped")


if __name__ == "__main__":
    # 运行服务
    asyncio.run(main()) 