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
        
        # 存储消费者组和处理器
        self._consumer_groups = {}
        self._message_handlers = {}
        self._running_threads = {}
        
        # 初始化Redis连接
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            logger.debug(f"已连接到Redis: {redis_url}")
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
                "data": json.dumps(event_data, ensure_ascii=False)
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
        topic_key = self._build_topic_key(topic)
        consumer_name = consumer_name or f"{RedisConstants.DEFAULT_CONSUMER_NAME}-{uuid.uuid4().hex[:8]}"
        
        # 创建消费者组
        consumer_group = RedisStreamConsumerGroup(
            redis_client=self.redis_client,
            topic=topic_key,
            group_name=group_name,
            consumer_name=consumer_name
        )
        
        # 启动消费者组
        consumer_group.create_group()
        
        # 存储消费者组和处理器
        subscription_key = f"{topic}:{group_name}:{consumer_name}"
        self._consumer_groups[subscription_key] = consumer_group
        self._message_handlers[subscription_key] = handler
        
        # 启动消息处理线程
        self._start_message_processing_thread(topic, group_name, consumer_name, handler, consumer_group)
        
        # 记录订阅信息
        logger.debug(f"已创建订阅: 主题={topic}, 组={group_name}, 消费者={consumer_name}")
    
    def _start_message_processing_thread(
        self, 
        topic: str, 
        group_name: str, 
        consumer_name: str, 
        handler: Union[Callable, IEventHandler],
        consumer_group: 'RedisStreamConsumerGroup'
    ) -> None:
        """启动消息处理线程"""
        subscription_key = f"{topic}:{group_name}:{consumer_name}"
        
        # 如果线程已经在运行，先停止它
        if subscription_key in self._running_threads:
            self._running_threads[subscription_key].stop()
        
        # 创建并启动新线程
        thread = MessageProcessingThread(
            topic=topic,
            group_name=group_name,
            consumer_name=consumer_name,
            handler=handler,
            consumer_group=consumer_group,
            event_bus=self
        )
        
        self._running_threads[subscription_key] = thread
        thread.start()
        
        logger.debug(f"已启动消息处理线程: {subscription_key}")
    
    def acknowledge(
        self,
        topic: str,
        group_name: str,
        message_ids: List[str]
    ) -> bool:
        """
        确认消息已处理
        
        Args:
            topic: 事件主题
            group_name: 消费者组名称
            message_ids: 消息ID列表
            
        Returns:
            bool: 确认是否成功
        """
        try:
            # 构建完整主题键名
            topic_key = self._build_topic_key(topic)
            
            # 确认消息
            result = self.redis_client.xack(
                topic_key,
                group_name,
                *message_ids
            )
            
            logger.debug(f"已确认消息: 主题={topic}, 组={group_name}, 消息ID={message_ids}")
            return result > 0
        except Exception as e:
            logger.error(f"确认消息失败: {str(e)}")
            return False
    
    def stop_all_subscriptions(self) -> None:
        """停止所有订阅的消息处理线程"""
        for subscription_key, thread in self._running_threads.items():
            thread.stop()
            logger.debug(f"已停止消息处理线程: {subscription_key}")
        
        self._running_threads.clear()
        self._consumer_groups.clear()
        self._message_handlers.clear()


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
            logger.debug(f"已创建消费者组: {self.group_name} (主题: {self.topic})")
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
                    # 解析事件数据 - 处理bytes键
                    event_data = message_data.get(b"data") or message_data.get("data", "{}")
                    if isinstance(event_data, bytes):
                        event_data = event_data.decode('utf-8')
                    try:
                        parsed_data = json.loads(event_data)
                    except json.JSONDecodeError:
                        logger.error(f"解析消息数据失败: {event_data}")
                        parsed_data = {}
                    
                    # 获取其他字段 - 处理bytes键
                    def get_field(data, field_name, default=""):
                        value = data.get(field_name.encode()) or data.get(field_name, default)
                        if isinstance(value, bytes):
                            return value.decode('utf-8')
                        return str(value) if value else default
                    
                    # 构建消息对象
                    result.append({
                        "message_id": message_id.decode('utf-8') if isinstance(message_id, bytes) else str(message_id),
                        "source": get_field(message_data, "source", "unknown"),
                        "timestamp": int(get_field(message_data, "timestamp", "0")),
                        "id": get_field(message_data, "id", ""),
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


class MessageProcessingThread(threading.Thread):
    """
    消息处理线程
    
    负责从Redis Stream读取消息并调用处理器处理
    """
    
    def __init__(
        self,
        topic: str,
        group_name: str,
        consumer_name: str,
        handler: Union[Callable, IEventHandler],
        consumer_group: 'RedisStreamConsumerGroup',
        event_bus: 'RedisStreamEventBus'
    ):
        super().__init__(name=f"MessageProcessor-{topic}-{consumer_name}")
        self.daemon = True
        
        self.topic = topic
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.handler = handler
        self.consumer_group = consumer_group
        self.event_bus = event_bus
        self._running = False
    
    def run(self) -> None:
        """线程主循环"""
        self._running = True
        logger.debug(f"消息处理线程已启动: {self.name}")
        
        while self._running:
            try:
                # 读取消息
                messages = self.consumer_group.read_messages()
                
                # 处理每条消息
                for message in messages:
                    if not self._running:
                        break
                    
                    try:
                        message_id = message["message_id"]
                        message_data = message["data"]
                        
                        logger.debug(f"MessageProcessingThread: message_id={message_id}")
                        logger.debug(f"MessageProcessingThread: message_data={message_data}")
                        logger.debug(f"MessageProcessingThread: message keys={list(message.keys())}")
                        
                        # 调用处理器
                        if callable(self.handler):
                            # 如果是函数处理器，调用时传递三个参数
                            if hasattr(self.handler, '__code__') and self.handler.__code__.co_argcount >= 3:
                                # 处理器期望 (message_id, event_envelope, actual_payload) 格式
                                event_envelope = {
                                    "source": message.get("source", "unknown"),
                                    "timestamp": message.get("timestamp", 0),
                                    "id": message.get("id", ""),
                                }
                                self.handler(message_id, event_envelope, message_data)
                            else:
                                # 简单处理器，只传递消息数据
                                self.handler(message_data)
                        elif hasattr(self.handler, 'handle_message'):
                            # IEventHandler接口
                            self.handler.handle_message(self.topic, message_data)
                        else:
                            logger.error(f"未知的处理器类型: {type(self.handler)}")
                            continue
                        
                        # 确认消息
                        self.event_bus.acknowledge(
                            topic=self.topic.replace(self.event_bus.topic_prefix + ":", ""),  # 移除前缀
                            group_name=self.group_name,
                            message_ids=[message_id]
                        )
                        
                    except Exception as e:
                        logger.error(f"处理消息失败: {e}, 消息ID: {message.get('message_id', 'unknown')}")
                        # 不确认失败的消息，让它们可以重试
                
                # 如果没有消息，短暂休眠
                if not messages:
                    time.sleep(0.1)
                    
            except Exception as e:
                if self._running:
                    logger.error(f"消息处理循环异常: {e}")
                    time.sleep(1)  # 避免在错误情况下过快重试
        
        logger.debug(f"消息处理线程已停止: {self.name}")
    
    def stop(self) -> None:
        """停止线程"""
        self._running = False 