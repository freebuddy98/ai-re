"""
Redis Streams适配器

基于Redis Streams实现的事件总线，提供高可靠性的事件发布和订阅功能。
"""
import json
import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import redis

# 导入相关模块
from ..common.logger import get_logger
from ..core.constants import RedisConstants
from ..core.exceptions import (
    ConnectionError as EventBusConnectionError,
    SubscribeError as EventBusSubscriptionError,
    PublishError as EventBusPublishError,
    EventBusError as EventBusTimeoutError,
)
from ..core.interfaces import (
    IEventBus,
    IEventHandler,
    IEventStorage,
)

# 定义消息处理器类型
MessageHandlerCallback = Callable[[str, Dict[str, Any], Dict[str, Any]], None]

class IMessageHandler:
    """消息处理器接口"""
    def handle_message(self, topic: str, message_data: Dict[str, Any]) -> None:
        """处理消息"""
        pass

# 定义消息模型
class EventMessageMetadata:
    """事件消息元数据"""
    pass

class EventMessage:
    """事件消息"""
    pass

class EventMessageBatch:
    """事件消息批次"""
    pass

# 获取日志记录器
logger = get_logger("redis_streams")


class RedisStreamEventBus(IEventBus):
    """
    Redis Streams实现的事件总线
    
    基于Redis Streams实现的事件总线，提供高可靠性的事件发布和订阅功能。
    """
    
    def __init__(
        self,
        redis_url: str,
        event_source_name: str = RedisConstants.DEFAULT_EVENT_SOURCE,
        topic_prefix: str = RedisConstants.DEFAULT_TOPIC_PREFIX
    ):
        """
        初始化Redis Streams事件总线
        
        Args:
            redis_url: Redis连接URL
            event_source_name: 事件源名称，用于标识事件的来源
            topic_prefix: 主题前缀，所有主题都会加上此前缀
        """
        self.redis_url = redis_url
        self.event_source_name = event_source_name
        self.topic_prefix = topic_prefix
        
        # 初始化Redis连接
        try:
            self.redis_client = redis.from_url(redis_url)
            logger.info(f"已连接到Redis: {redis_url}")
        except Exception as e:
            logger.error(f"连接Redis失败: {str(e)}")
            raise EventBusConnectionError(f"无法连接到Redis: {str(e)}")
    
    def _build_topic_key(self, topic: str) -> str:
        """
        构建Redis中的主题键名
        
        Args:
            topic: 原始主题名
            
        Returns:
            str: 带前缀的主题键名
        """
        if self.topic_prefix:
            return f"{self.topic_prefix}:{topic}"
        return topic
    
    def publish(
        self, 
        topic: str, 
        event_data: Dict[str, Any]
    ) -> str:
        """
        发布事件到指定主题
        
        Args:
            topic: 事件主题
            event_data: 事件数据
            
        Returns:
            str: 事件ID
        """
        try:
            # 构建完整主题键名
            topic_key = self._build_topic_key(topic)
            
            # 添加元数据
            event_envelope = {
                "source": self.event_source_name,
                "timestamp": int(time.time() * 1000),
                "id": str(uuid.uuid4()),
                "data": json.dumps(event_data)
            }
            
            # 发布到Redis Stream
            message_id = self.redis_client.xadd(
                topic_key,
                event_envelope
            )
            
            logger.debug(f"已发布事件到 {topic_key}, ID: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"发布事件失败: {str(e)}")
            raise EventBusPublishError(f"发布事件失败: {str(e)}")
    
    def subscribe(
        self,
        topic: str,
        handler: Union[Callable, IEventHandler],
        group_name: str,
        consumer_name: Optional[str] = None
    ) -> None:
        """
        订阅主题
        
        Args:
            topic: 事件主题
            handler: 事件处理器或处理函数
            group_name: 消费者组名称
            consumer_name: 消费者名称，如果为None则自动生成
        """
        # 使用消费者组创建订阅
        consumer_group = RedisStreamConsumerGroup(
            redis_client=self.redis_client,
            topic=self._build_topic_key(topic),
            group_name=group_name,
            consumer_name=consumer_name or f"{RedisConstants.DEFAULT_CONSUMER_NAME}-{uuid.uuid4().hex[:8]}"
        )
        
        # 启动消费者组
        consumer_group.create_group()
        
        # 记录订阅信息
        logger.info(f"已创建订阅: 主题={topic}, 组={group_name}, 消费者={consumer_name}")
    
    def acknowledge(
        self,
        topic: str,
        group_name: str,
        message_ids: List[str]
    ) -> None:
        """
        确认消息已处理
        
        Args:
            topic: 事件主题
            group_name: 消费者组名称
            message_ids: 消息ID列表
        """
        try:
            # 构建完整主题键名
            topic_key = self._build_topic_key(topic)
            
            # 确认消息
            self.redis_client.xack(
                topic_key,
                group_name,
                *message_ids
            )
            
            logger.debug(f"已确认消息: 主题={topic}, 组={group_name}, 消息ID={message_ids}")
        except Exception as e:
            logger.error(f"确认消息失败: {str(e)}")
            raise EventBusSubscriptionError(f"确认消息失败: {str(e)}")


class RedisStreamConsumerGroup:
    """Redis Stream消费者组"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        topic: str,
        group_name: str,
        consumer_name: str,
        block_ms: int = RedisConstants.DEFAULT_BLOCK_MS,
        batch_size: int = RedisConstants.DEFAULT_BATCH_SIZE
    ):
        """
        初始化Redis Stream消费者组
        
        Args:
            redis_client: Redis客户端
            topic: 主题名称
            group_name: 消费者组名称
            consumer_name: 消费者名称
            block_ms: 阻塞读取超时时间（毫秒）
            batch_size: 每次读取的最大消息数
        """
        self.redis_client = redis_client
        self.topic = topic
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.block_ms = block_ms
        self.batch_size = batch_size
    
    def create_group(self) -> None:
        """
        创建消费者组
        
        如果组已存在，则忽略错误
        """
        try:
            # 尝试创建Stream（如果不存在）
            self.redis_client.xgroup_create(
                name=self.topic,
                groupname=self.group_name,
                id=RedisConstants.REDIS_STREAM_FIRST_ID,
                mkstream=True
            )
            logger.info(f"已创建消费者组: {self.group_name} (主题: {self.topic})")
        except redis.exceptions.ResponseError as e:
            # 忽略"组已存在"错误
            if "BUSYGROUP" in str(e):
                logger.debug(f"消费者组已存在: {self.group_name} (主题: {self.topic})")
            else:
                logger.error(f"创建消费者组失败: {str(e)}")
                raise EventBusConnectionError(f"创建消费者组失败: {str(e)}")
    
    def read_messages(self) -> List[Dict[str, Any]]:
        """
        读取消息
        
        Returns:
            List[Dict[str, Any]]: 消息列表
        """
        try:
            # 从Stream读取消息
            messages = self.redis_client.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.topic: RedisConstants.REDIS_STREAM_NEXT_ID},
                count=self.batch_size,
                block=self.block_ms
            )
            
            if not messages:
                return []
            
            # 解析消息
            result = []
            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    # 解析事件数据
                    event_data = message_data.get("data", "{}")
                    try:
                        parsed_data = json.loads(event_data)
                    except json.JSONDecodeError:
                        logger.error(f"解析消息数据失败: {event_data}")
                        parsed_data = {}
                    
                    # 构建消息对象
                    result.append({
                        "message_id": message_id,
                        "source": message_data.get("source", "unknown"),
                        "timestamp": int(message_data.get("timestamp", 0)),
                        "id": message_data.get("id", ""),
                        "data": parsed_data
                    })
            
            return result
        except Exception as e:
            logger.error(f"读取消息失败: {str(e)}")
            return []
    
    def acknowledge(self, message_ids: List[str]) -> None:
        """
        确认消息已处理
        
        Args:
            message_ids: 消息ID列表
        """
        try:
            # 确认消息
            self.redis_client.xack(
                self.topic,
                self.group_name,
                *message_ids
            )
            logger.debug(f"已确认消息: {message_ids}")
        except Exception as e:
            logger.error(f"确认消息失败: {str(e)}")
            raise EventBusSubscriptionError(f"确认消息失败: {str(e)}")


class MessageHandlerLoopThread(threading.Thread):
    """
    消息处理循环线程
    
    此线程负责从 Redis Stream 读取消息并调用相应的处理器进行处理。
    """
    
    def __init__(
        self,
        event_bus: RedisStreamEventBus,
        topic: str,
        handlers: List[IMessageHandler],
        consumer_group: Optional[str] = None,
        consumer_name: Optional[str] = None,
    ):
        """
        初始化消息处理循环线程
        
        Args:
            event_bus: 事件总线实例
            topic: 要处理的主题
            handlers: 消息处理器列表
            consumer_group: 消费者组名称，如果指定则使用消费者组模式
            consumer_name: 消费者名称，仅在使用消费者组模式时有效
        """
        super().__init__(name=f"MessageHandler-{topic}")
        self.daemon = True  # 设置为守护线程，主线程退出时自动终止
        
        self._event_bus = event_bus
        self._topic = topic
        self._handlers = handlers
        self._consumer_group = consumer_group
        self._consumer_name = consumer_name or f"consumer-{uuid.uuid4()}"
        self._running = False
        self._last_id = "0"  # 从头开始消费
    
    def run(self) -> None:
        """线程主循环，不断读取消息并处理"""
        self._running = True
        logger.info(f"消息处理线程已启动: topic={self._topic}")
        
        while self._running:
            try:
                # 读取消息
                messages = self._event_bus._read_messages(
                    topic=self._topic,
                    count=10,
                    block=1000,  # 阻塞 1 秒
                    consumer_group=self._consumer_group,
                    consumer_name=self._consumer_name,
                    last_id=self._last_id
                )
                
                # 如果使用消费者组模式，messages 的格式是 [(topic, [(id, fields), ...])]
                # 否则，messages 的格式是 [(id, fields), ...]
                if self._consumer_group and messages:
                    # 提取消息列表
                    messages = messages[0][1]
                
                # 处理消息
                for message_id, fields in messages:
                    try:
                        # 解析消息
                        message_str = fields.get(b"message", b"{}")
                        if isinstance(message_str, bytes):
                            message_str = message_str.decode("utf-8")
                        
                        message_data = json.loads(message_str)
                        
                        # 调用所有处理器
                        for handler in self._handlers:
                            try:
                                handler.handle_message(self._topic, message_data)
                            except Exception as e:
                                logger.error(
                                    f"处理器异常: topic={self._topic}, "
                                    f"handler={handler.__class__.__name__}, error={str(e)}"
                                )
                        
                        # 更新最后处理的消息 ID
                        self._last_id = message_id
                        
                        # 如果使用消费者组模式，确认消息已处理
                        if self._consumer_group:
                            self._event_bus._acknowledge_message(
                                self._topic,
                                self._consumer_group,
                                message_id
                            )
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"解析消息失败: {str(e)}")
                    except Exception as e:
                        logger.error(f"处理消息时发生未知错误: {str(e)}")
                
            except Exception as e:
                if self._running:  # 只在线程仍在运行时记录错误
                    logger.error(f"消息处理循环异常: {str(e)}")
                    time.sleep(1)  # 避免在错误情况下过快重试
    
    def stop(self) -> None:
        """停止处理循环"""
        self._running = False
        logger.info(f"消息处理线程正在停止: topic={self._topic}") 