"""
通用事件订阅管理器

提供统一的事件订阅和消息处理功能，支持同步和异步处理器。
可被各个微服务复用，避免重复实现相同的订阅逻辑。
"""
import asyncio
import threading
from typing import Dict, Any, Callable, Optional, Union

from .interfaces import IEventBus
from .logging import get_logger

logger = get_logger("event_bus_framework.subscription_manager")


class EventSubscriptionManager:
    """
    通用的事件订阅管理器
    
    负责管理多个主题的事件订阅，支持同步和异步消息处理。
    提供统一的消息确认、错误处理和调试功能。
    
    主要职责：
    1. 注册主题处理器映射关系
    2. 设置事件总线订阅
    3. 处理消息确认逻辑
    4. 管理调试模式（重置消费者组）
    5. 控制消费生命周期
    """
    
    def __init__(
        self,
        event_bus: IEventBus,
        consumer_group: str,
        consumer_name: str,
        debug_mode: bool = False,
        service_name: Optional[str] = None
    ):
        """
        初始化事件订阅管理器
        
        Args:
            event_bus: 实现IEventBus接口的事件总线实例
            consumer_group: 消费者组名称
            consumer_name: 消费者名称
            debug_mode: 是否启用调试模式（重置消费者组）
            service_name: 服务名称，用于日志标识
        """
        self.event_bus = event_bus
        self.consumer_group_name = consumer_group
        self.consumer_name = consumer_name
        self.debug_mode = debug_mode
        self.service_name = service_name or "unknown_service"
        
        # 主题处理器映射：topic -> handler_function
        self.topic_handlers: Dict[str, Union[Callable, Callable]] = {}
        
        # 线程安全锁（用于同步确认）
        self._sync_lock = threading.Lock()
        
        # 异步锁（用于异步确认）
        self._async_lock = asyncio.Lock()
        
        if self.debug_mode:
            logger.info(f"[{self.service_name}] 调试模式已启用 - 启动时将重置消费者组")
    
    def register_handler(
        self, 
        topic: str, 
        handler: Union[
            Callable[[str, Dict[str, Any]], bool], 
            Callable[[str, Dict[str, Any]], bool]
        ]
    ) -> None:
        """
        注册主题的消息处理器
        
        Args:
            topic: 主题名称
            handler: 消息处理函数（同步或异步）
                    签名: (message_id: str, message_data: Dict[str, Any]) -> bool
        """
        self.topic_handlers[topic] = handler
        logger.debug(f"[{self.service_name}] 已注册主题处理器: {topic}")
    
    def register_handlers(self, handlers: Dict[str, Callable]) -> None:
        """
        批量注册主题处理器
        
        Args:
            handlers: 主题到处理器的映射字典
        """
        for topic, handler in handlers.items():
            self.register_handler(topic, handler)
    
    def _reset_consumer_groups_for_debug(self) -> None:
        """
        调试模式下重置消费者组
        
        这允许从头开始消费，避免Redis消费者组的"最后交付ID"状态，
        这对调试很有用。
        """
        if not self.debug_mode:
            return
        
        logger.info(f"[{self.service_name}] 调试模式：正在重置消费者组...")
        
        # 检查事件总线是否有直接的Redis访问权限
        if hasattr(self.event_bus, 'redis_client'):
            redis_client = self.event_bus.redis_client
            
            for topic in self.topic_handlers.keys():
                try:
                    # 构建完整的主题键（假设事件总线有此方法）
                    if hasattr(self.event_bus, '_build_topic_key'):
                        topic_key = self.event_bus._build_topic_key(topic)
                    else:
                        topic_key = topic
                    
                    # 销毁消费者组
                    redis_client.xgroup_destroy(topic_key, self.consumer_group_name)
                    logger.info(f"[{self.service_name}] 已销毁消费者组 '{self.consumer_group_name}' 用于主题 '{topic}' (调试模式)")
                    
                except Exception as e:
                    # 组可能不存在，这是正常的
                    logger.debug(f"[{self.service_name}] 无法销毁主题 '{topic}' 的消费者组: {e}")
        else:
            logger.warning(f"[{self.service_name}] 无法重置消费者组：事件总线未暴露Redis客户端")
    
    def _create_message_handler(self, topic: str, handler: Union[Callable, Callable]) -> Callable:
        """
        创建消息处理包装器
        
        将业务处理器包装成符合事件总线接口的处理器，
        负责参数转换、异常处理和消息确认。
        
        Args:
            topic: 主题名称
            handler: 业务处理器函数
            
        Returns:
            包装后的处理器函数
        """
        def message_wrapper(message_id: str, event_envelope: Dict[str, Any], actual_payload: Dict[str, Any]) -> None:
            """
            消息处理包装器
            
            Args:
                message_id: 事件总线的消息ID
                event_envelope: 完整的事件信封
                actual_payload: 从信封中提取的业务负载
            """
            try:
                logger.debug(f"[{self.service_name}] 处理来自主题 {topic} 的消息 {message_id}")
                
                # 判断是否为异步处理器
                if asyncio.iscoroutinefunction(handler):
                    # 异步处理
                    self._handle_async_message(message_id, topic, handler, actual_payload)
                else:
                    # 同步处理
                    self._handle_sync_message(message_id, topic, handler, actual_payload)
                    
            except Exception as e:
                logger.error(f"[{self.service_name}] 消息处理器中发生错误，消息ID {message_id}: {e}")
                # 不确认导致异常的消息
        
        return message_wrapper
    
    def _handle_sync_message(self, message_id: str, topic: str, handler: Callable, actual_payload: Dict[str, Any]) -> None:
        """
        处理同步消息
        
        Args:
            message_id: 消息ID
            topic: 主题名称
            handler: 同步处理器
            actual_payload: 消息负载
        """
        try:
            # 调用业务处理器
            success = handler(message_id, actual_payload)
            
            if success:
                # 线程安全的消息确认
                with self._sync_lock:
                    ack_result = self.event_bus.acknowledge(
                        topic=topic,
                        group_name=self.consumer_group_name,
                        message_ids=[message_id]
                    )
                    if ack_result:
                        logger.debug(f"[{self.service_name}] 成功确认消息 {message_id}")
                    else:
                        logger.warning(f"[{self.service_name}] 确认消息失败 {message_id}")
            else:
                logger.error(f"[{self.service_name}] 消息处理失败，消息ID {message_id}")
                # 不确认失败的消息 - 它们将被重试
                
        except Exception as e:
            logger.error(f"[{self.service_name}] 同步消息处理器中发生错误，消息ID {message_id}: {e}")
            # 不确认导致异常的消息
    
    def _handle_async_message(self, message_id: str, topic: str, async_handler: Callable, actual_payload: Dict[str, Any]) -> None:
        """
        处理异步消息
        
        Args:
            message_id: 消息ID
            topic: 主题名称
            async_handler: 异步处理器
            actual_payload: 消息负载
        """
        async def process_async():
            try:
                logger.debug(f"[{self.service_name}] 异步处理来自主题 {topic} 的消息 {message_id}")
                
                # 调用异步业务处理器
                success = await async_handler(message_id, actual_payload)
                
                if success:
                    # 异步安全的消息确认
                    async with self._async_lock:
                        ack_result = self.event_bus.acknowledge(
                            topic=topic,
                            group_name=self.consumer_group_name,
                            message_ids=[message_id]
                        )
                        if ack_result:
                            logger.debug(f"[{self.service_name}] 成功确认异步消息 {message_id}")
                        else:
                            logger.warning(f"[{self.service_name}] 确认异步消息失败 {message_id}")
                else:
                    logger.error(f"[{self.service_name}] 异步消息处理失败，消息ID {message_id}")
                    # 不确认失败的消息 - 它们将被重试
                    
            except Exception as e:
                logger.error(f"[{self.service_name}] 异步消息处理器中发生错误，消息ID {message_id}: {e}")
                # 不确认导致异常的消息
        
        # 调度异步任务
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            # 在当前循环中创建任务
            loop.create_task(process_async())
        except RuntimeError:
            # 没有运行的事件循环，创建新的
            asyncio.run(process_async())
    
    def setup_subscriptions(self) -> None:
        """
        设置所有已注册主题的订阅
        
        这是核心方法，负责：
        1. 调试模式下重置消费者组
        2. 为每个主题创建消息处理包装器
        3. 调用事件总线的subscribe方法建立订阅
        """
        if not self.topic_handlers:
            logger.warning(f"[{self.service_name}] 没有注册的主题处理器")
            return
        
        try:
            # 调试模式下重置消费者组
            self._reset_consumer_groups_for_debug()
            
            for topic, handler in self.topic_handlers.items():
                logger.debug(f"[{self.service_name}] 设置主题订阅: {topic}")
                
                # 创建消息处理包装器
                message_wrapper = self._create_message_handler(topic, handler)
                
                # 使用事件总线接口建立订阅
                self.event_bus.subscribe(
                    topic=topic,
                    handler=message_wrapper,
                    group_name=self.consumer_group_name,
                    consumer_name=f"{self.consumer_name}-{topic}"
                )
                
                logger.debug(f"[{self.service_name}] 成功设置主题订阅: {topic}")
                
        except Exception as e:
            logger.error(f"[{self.service_name}] 设置订阅失败: {e}")
            raise
    
    def get_registered_topics(self) -> list:
        """获取已注册的主题列表"""
        return list(self.topic_handlers.keys())
    
    def unregister_handler(self, topic: str) -> bool:
        """
        取消注册主题处理器
        
        Args:
            topic: 主题名称
            
        Returns:
            bool: 是否成功取消注册
        """
        if topic in self.topic_handlers:
            del self.topic_handlers[topic]
            logger.debug(f"[{self.service_name}] 已取消注册主题处理器: {topic}")
            return True
        return False
    
    def clear_handlers(self) -> None:
        """清除所有已注册的处理器"""
        self.topic_handlers.clear()
        logger.debug(f"[{self.service_name}] 已清除所有主题处理器")


# 为了向后兼容，保留别名
AsyncEventSubscriptionManager = EventSubscriptionManager 