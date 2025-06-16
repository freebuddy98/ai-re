"""
通用服务管理器基类

提供标准的微服务生命周期管理功能，包括配置加载、事件总线初始化、
消息处理器设置等。各个微服务可以继承此基类来减少重复代码。
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from .interfaces import IEventBus
from .logging import get_logger
from .subscription_manager import EventSubscriptionManager
from ..factory import create_event_bus
from ..common.config import get_service_config

logger = get_logger("event_bus_framework.service_manager")


class BaseServiceManager(ABC):
    """
    微服务管理器基类
    
    提供标准的服务生命周期管理功能：
    - 配置加载
    - 事件总线初始化
    - 事件订阅管理
    - 服务启动/停止
    
    子类需要实现：
    - get_service_name(): 返回服务名称
    - initialize_business_components(): 初始化业务组件
    - get_message_handlers(): 返回消息处理器映射
    """
    
    def __init__(self):
        self.config: Optional[Dict[str, Any]] = None
        self.event_bus: Optional[IEventBus] = None
        self.event_manager: Optional[EventSubscriptionManager] = None
        self.running = False
        
        # 子类可以覆盖的配置
        self._consumer_group: Optional[str] = None
        self._consumer_name: Optional[str] = None
        self._debug_mode: Optional[bool] = None
    
    @abstractmethod
    def get_service_name(self) -> str:
        """
        返回服务名称
        
        Returns:
            str: 服务名称，用于配置加载和日志标识
        """
        pass
    
    @abstractmethod
    def initialize_business_components(self) -> None:
        """
        初始化业务组件
        
        子类在此方法中初始化特定的业务逻辑组件，
        如处理器、客户端、数据库连接等。
        """
        pass
    
    @abstractmethod
    def get_message_handlers(self) -> Dict[str, Any]:
        """
        返回消息处理器映射
        
        Returns:
            Dict[str, Any]: 主题名称到处理器函数的映射
        """
        pass
    
    def load_configuration(self) -> None:
        """从YAML文件加载服务配置"""
        try:
            service_name = self.get_service_name()
            
            # 加载服务特定配置
            service_config = get_service_config(service_name)
            
            if not service_config:
                logger.warning(f"[{service_name}] No {service_name} configuration found, using defaults")
                service_config = {}
            
            self.config = service_config
            logger.debug(f"[{service_name}] Loaded configuration")
            
        except Exception as e:
            logger.error(f"[{self.get_service_name()}] Failed to load configuration: {e}")
            raise
    
    def initialize_event_bus(self) -> None:
        """使用工厂模式初始化事件总线"""
        try:
            service_name = self.get_service_name()
            
            # 获取事件总线配置
            event_bus_config = get_service_config('event_bus')
            
            if not event_bus_config:
                logger.error(f"[{service_name}] No event_bus configuration found")
                raise ValueError("Event bus configuration is required")
            
            # 使用工厂模式创建事件总线
            self.event_bus = create_event_bus(
                config=event_bus_config,
                service_name=service_name
            )
            
            logger.debug(f"[{service_name}] Initialized event bus using factory pattern")
            
        except Exception as e:
            logger.error(f"[{self.get_service_name()}] Failed to initialize event bus: {e}")
            raise
    
    def get_subscription_config(self) -> Dict[str, Any]:
        """
        获取订阅配置
        
        Returns:
            Dict[str, Any]: 包含订阅相关配置的字典
        """
        service_name = self.get_service_name()
        
        # 从配置中获取订阅设置
        topics_config = self.config.get('topics', {})
        input_topics = topics_config.get('subscribe', [])
        
        consumer_group = self._consumer_group or self.config.get('consumer_group', f'{service_name}-group')
        consumer_name = self._consumer_name or self.config.get('consumer_name', f'{service_name}-worker')
        debug_mode = self._debug_mode
        if debug_mode is None:
            debug_mode = self.config.get('debug_mode', False)
        
        # 转换字符串布尔值
        if isinstance(debug_mode, str):
            debug_mode = debug_mode.lower() in ('true', '1', 'yes', 'on')
        
        return {
            'input_topics': input_topics,
            'consumer_group': consumer_group,
            'consumer_name': consumer_name,
            'debug_mode': debug_mode
        }
    
    def setup_event_subscriptions(self) -> None:
        """设置事件订阅"""
        try:
            service_name = self.get_service_name()
            subscription_config = self.get_subscription_config()
            
            input_topics = subscription_config['input_topics']
            consumer_group = subscription_config['consumer_group']
            consumer_name = subscription_config['consumer_name']
            debug_mode = subscription_config['debug_mode']
            
            logger.debug(f"[{service_name}] Setting up subscriptions to topics: {input_topics}")
            logger.debug(f"[{service_name}] Debug mode: {debug_mode}")
            
            # 创建事件订阅管理器
            self.event_manager = EventSubscriptionManager(
                event_bus=self.event_bus,
                consumer_group=consumer_group,
                consumer_name=consumer_name,
                debug_mode=debug_mode,
                service_name=service_name
            )
            
            # 获取消息处理器
            message_handlers = self.get_message_handlers()
            
            # 注册处理器
            for topic in input_topics:
                if topic in message_handlers:
                    handler = message_handlers[topic]
                    self.event_manager.register_handler(topic, handler)
                    logger.debug(f"[{service_name}] Registered handler for topic: {topic}")
                else:
                    logger.warning(f"[{service_name}] No handler found for topic: {topic}")
            
            # 设置订阅
            self.event_manager.setup_subscriptions()
            
            logger.debug(f"[{service_name}] Successfully set up subscriptions for topics: {input_topics}")
            
        except Exception as e:
            logger.error(f"[{self.get_service_name()}] Failed to setup event subscriptions: {e}")
            raise
    
    def set_consumer_config(self, consumer_group: str = None, consumer_name: str = None, debug_mode: bool = None) -> None:
        """
        设置消费者配置（可选，覆盖配置文件中的设置）
        
        Args:
            consumer_group: 消费者组名称
            consumer_name: 消费者名称
            debug_mode: 调试模式
        """
        if consumer_group is not None:
            self._consumer_group = consumer_group
        if consumer_name is not None:
            self._consumer_name = consumer_name
        if debug_mode is not None:
            self._debug_mode = debug_mode
    
    async def start_async(self) -> None:
        """异步启动服务"""
        try:
            service_name = self.get_service_name()
            logger.debug(f"[{service_name}] Starting service...")
            
            # 按顺序初始化所有组件
            self.load_configuration()
            self.initialize_event_bus()
            self.initialize_business_components()
            self.setup_event_subscriptions()
            
            # 事件消费在setup_subscriptions()后自动开始
            self.running = True
            
            logger.debug(f"[{service_name}] Service started successfully")
            
        except Exception as e:
            logger.error(f"[{self.get_service_name()}] Failed to start service: {e}")
            raise
    
    async def stop_async(self) -> None:
        """异步停止服务"""
        service_name = self.get_service_name()
        logger.debug(f"[{service_name}] Stopping service...")
        
        self.running = False
        
        # 停止事件总线（如果支持）
        if hasattr(self.event_bus, 'stop_all_subscriptions'):
            self.event_bus.stop_all_subscriptions()
        
        logger.debug(f"[{service_name}] Service stopped")
    
    def start(self) -> None:
        """启动服务（同步包装器）"""
        asyncio.run(self.start_async())
    
    def stop(self) -> None:
        """停止服务（同步包装器）"""
        if asyncio.get_event_loop().is_running():
            # 如果已经在异步上下文中，创建任务
            asyncio.create_task(self.stop_async())
        else:
            # 如果不在异步上下文中，运行它
            asyncio.run(self.stop_async())
    
    def is_running(self) -> bool:
        """检查服务是否正在运行"""
        return self.running
    
    def get_subscribed_topics(self) -> List[str]:
        """获取已订阅的主题列表"""
        if self.event_manager:
            return self.event_manager.get_registered_topics()
        return []


class MessageHandlerRegistry:
    """
    通用消息处理器注册表
    
    提供主题到处理器的映射管理，支持默认处理器和自定义处理器。
    """
    
    def __init__(self, service_name: str = "unknown"):
        self.service_name = service_name
        self._handlers: Dict[str, Any] = {}
        self._default_handler: Optional[Any] = None
    
    def register_handler(self, topic: str, handler: Any) -> None:
        """
        注册主题处理器
        
        Args:
            topic: 主题名称
            handler: 处理器函数
        """
        self._handlers[topic] = handler
        logger.debug(f"[{self.service_name}] Registered handler for topic: {topic}")
    
    def register_handlers(self, handlers: Dict[str, Any]) -> None:
        """
        批量注册处理器
        
        Args:
            handlers: 主题到处理器的映射
        """
        for topic, handler in handlers.items():
            self.register_handler(topic, handler)
    
    def set_default_handler(self, handler: Any) -> None:
        """
        设置默认处理器（用于未知主题）
        
        Args:
            handler: 默认处理器函数
        """
        self._default_handler = handler
        logger.debug(f"[{self.service_name}] Set default handler")
    
    def get_handler(self, topic: str) -> Any:
        """
        获取主题的处理器
        
        Args:
            topic: 主题名称
            
        Returns:
            处理器函数，如果没有找到则返回默认处理器
        """
        if topic in self._handlers:
            return self._handlers[topic]
        elif self._default_handler:
            logger.warning(f"[{self.service_name}] No specific handler for topic: {topic}, using default handler")
            return self._default_handler
        else:
            raise ValueError(f"No handler found for topic: {topic} and no default handler set")
    
    def get_all_handlers(self) -> Dict[str, Any]:
        """获取所有已注册的处理器"""
        return self._handlers.copy()
    
    def get_topics(self) -> List[str]:
        """获取所有已注册的主题"""
        return list(self._handlers.keys()) 