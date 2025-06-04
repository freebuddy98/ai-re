"""
Redis Streams 事件总线实现模块。

此模块提供了 RedisStreamsEventBus 类，用于实现基于 Redis Streams 的事件总线。
"""
import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union

import redis
from redis import Redis

from event_bus_framework.core.constants import RedisConstants
from event_bus_framework.core.exceptions import (
    AcknowledgeError, 
    ConnectionError, 
    ConsumerGroupError, 
    DeserializationError, 
    EventBusError, 
    PublishError, 
    SubscribeError
)
from event_bus_framework.core.interfaces import IEventBus
from event_bus_framework.core.logging import logger
from event_bus_framework.core.models import EventEnvelope, build_event_envelope
from event_bus_framework.core.utils import (
    build_topic_key, 
    decode_redis_stream_message, 
    deserialize_from_json, 
    serialize_to_json
)


class MessageHandlerLoopThread(threading.Thread):
    """
    后台消息处理循环线程。
    
    每个订阅都会创建一个此类的实例来处理消息。
    """
    
    def __init__(
        self,
        bus_instance: 'RedisStreamsEventBus',
        topic: str,
        handler_function: Callable[[str, Dict[str, Any], Dict[str, Any]], None],
        group_name: str,
        consumer_name: str,
        start_id: str = '>',
        auto_acknowledge: bool = False,
        **kwargs
    ):
        """
        初始化消息处理循环线程。
        
        Args:
            bus_instance: RedisStreamsEventBus 实例的引用
            topic: 订阅的主题
            handler_function: 消息处理回调函数
            group_name: 消费者组名称
            consumer_name: 消费者名称
            start_id: 开始消费的消息ID
            auto_acknowledge: 是否自动确认消息
            **kwargs: 传递给 Thread 构造函数的参数
        """
        super().__init__(**kwargs)
        self.daemon = True  # 设置为守护线程，主程序退出时自动终止
        
        self.bus_instance = bus_instance
        self.topic = topic
        self.handler_function = handler_function
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.start_id = start_id
        self.auto_acknowledge = auto_acknowledge
        
        # 完整主题键（包含前缀）
        self.full_topic_key = build_topic_key(self.bus_instance.topic_prefix, self.topic)
        
        # 线程控制标志
        self.running = False
    
    def run(self):
        """
        线程主循环，不断从 Redis Stream 读取消息并处理。
        """
        self.running = True
        redis_client = self.bus_instance.redis_client
        
        # 注意：这里直接使用内部实现的 Redis 命令，而不是通过适配器
        logger.info(f"开始监听主题 '{self.full_topic_key}' 上的消息 [组: {self.group_name}, 消费者: {self.consumer_name}]")
        
        streams_dict = {self.full_topic_key: self.start_id}
        
        while self.running:
            try:
                # 从流中读取消息
                messages = redis_client.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams=streams_dict,
                    count=RedisConstants.DEFAULT_COUNT,
                    block=RedisConstants.DEFAULT_BLOCK_TIME_MS
                )
                
                # 如果收到消息，处理它们
                if messages:
                    self._process_messages(messages, redis_client)
                
                # 短暂休眠，避免CPU过度使用
                time.sleep(0.01)
                
            except redis.RedisError as e:
                logger.error(f"Redis错误: {e}")
                # 短暂休眠后重试
                time.sleep(1)
            except Exception as e:
                logger.exception(f"处理消息时发生未预期错误: {e}")
                # 短暂休眠后重试
                time.sleep(1)
    
    def _process_messages(self, messages: List, redis_client: Redis):
        """
        处理从Redis Stream接收到的消息。
        
        Args:
            messages: Redis xreadgroup 返回的消息列表
            redis_client: Redis客户端实例
        """
        # 解码消息
        decoded_message = decode_redis_stream_message(messages)
        if not decoded_message:
            logger.warning("收到无法解码的消息")
            return
        
        message_id = decoded_message["message_id"]
        # 确保消息ID是字符串
        if isinstance(message_id, bytes):
            message_id = message_id.decode('utf-8')
            
        message_fields = decoded_message["fields"]
        
        # 尝试获取payload字段
        payload_field = RedisConstants.PAYLOAD_FIELD
        # 检查字段名称是否被编码为字节
        if isinstance(list(message_fields.keys())[0], bytes) and payload_field not in message_fields:
            payload_field = payload_field.encode('utf-8')
        
        if payload_field not in message_fields:
            logger.warning(f"消息 {message_id} 缺少 '{RedisConstants.PAYLOAD_FIELD}' 字段")
            return
        
        # 尝试反序列化消息
        try:
            # 解析事件信封
            payload_json = message_fields[payload_field]
            if isinstance(payload_json, bytes):
                payload_json = payload_json.decode('utf-8')
            
            event_envelope = deserialize_from_json(payload_json)
            actual_payload = event_envelope.get("actual_payload", {})
            
            # 调用用户提供的处理函数
            self.handler_function(message_id, event_envelope, actual_payload)
            
            # 如果配置为自动确认，则确认消息
            if self.auto_acknowledge:
                try:
                    redis_client.xack(
                        self.full_topic_key,
                        self.group_name,
                        message_id
                    )
                except redis.RedisError as e:
                    logger.error(f"确认消息 {message_id} 失败: {e}")
            
        except json.JSONDecodeError as e:
            logger.error(f"消息 {message_id} 反序列化失败: {e}")
        except Exception as e:
            logger.exception(f"处理消息 {message_id} 时发生错误: {e}")
    
    def stop(self):
        """
        停止消息处理循环。
        """
        self.running = False
        logger.info(f"停止监听主题 '{self.full_topic_key}'")


class RedisStreamsEventBus(IEventBus):
    """
    基于Redis Streams的事件总线实现。
    
    此类实现了IEventBus接口，提供了基于Redis Streams的发布-订阅功能。
    """
    
    def __init__(
        self,
        redis_url: str,
        topic_prefix: str = "",
        event_source_name: str = "UnknownService",
        default_consumer_group: str = "DefaultGroup",
        default_consumer_instance_name: str = "DefaultConsumer",
        redis_connection_pool_kwargs: Optional[Dict[str, Any]] = None
    ):
        """
        初始化Redis Streams事件总线。
        
        Args:
            redis_url: Redis连接URL
            topic_prefix: 主题名称前缀
            event_source_name: 事件源服务名称
            default_consumer_group: 默认消费者组名称
            default_consumer_instance_name: 默认消费者实例名称
            redis_connection_pool_kwargs: Redis连接池的额外参数
        """
        # 存储配置
        self.redis_url = redis_url
        self.topic_prefix = topic_prefix
        self.event_source_name = event_source_name
        self.default_consumer_group = default_consumer_group
        self.default_consumer_instance_name = default_consumer_instance_name
        
        # 创建Redis连接池
        redis_pool_kwargs = redis_connection_pool_kwargs or {}
        try:
            self.redis_connection_pool = redis.ConnectionPool.from_url(
                redis_url, **redis_pool_kwargs
            )
            # 直接创建一个Redis客户端实例
            self.redis_client = redis.Redis(connection_pool=self.redis_connection_pool)
        except redis.RedisError as e:
            raise ConnectionError(f"无法创建Redis连接池: {e}") from e
        
        # 用于跟踪活跃的订阅
        self.active_subscriptions = {}
    
    def _get_redis_client(self) -> Redis:
        """
        获取Redis客户端实例。
        
        Returns:
            Redis客户端实例
            
        Raises:
            ConnectionError: 如果无法连接到Redis
        """
        # 为了向后兼容保留此方法，但现在只返回已存在的客户端实例
        return self.redis_client
    
    def _build_event_envelope(
        self, 
        message_data: Dict[str, Any], 
        topic: str,
        event_type_hint: Optional[str] = None,
        dialogue_session_id_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建事件信封。
        
        Args:
            message_data: 业务载荷数据
            topic: 主题名称
            event_type_hint: 事件类型提示
            dialogue_session_id_hint: 对话会话ID提示
            
        Returns:
            事件信封字典
        """
        # 从主题名称提取事件类型提示（如果未提供）
        if not event_type_hint and ":" in topic:
            # 尝试从主题格式中提取：stream:<timestamp>:<domain>:<event_type>
            parts = topic.split(":")
            if len(parts) >= 4:
                event_type_hint = parts[-1]
        
        # 构建标准事件信封
        event_envelope = build_event_envelope(
            message_data=message_data,
            source_service=self.event_source_name,
            event_type_hint=event_type_hint,
            dialogue_session_id_hint=dialogue_session_id_hint
        )
        
        return event_envelope.model_dump()
    
    def xadd(
        self, 
        topic: str, 
        message_fields: Dict[str, Any], 
        message_id: str = '*'
    ) -> str:
        """
        向 Redis Stream 添加消息。
        
        Args:
            topic: Stream 名称。
            message_fields: 消息字段和值的字典。
            message_id: 消息 ID，默认为 '*'，表示由 Redis 自动生成。
            
        Returns:
            添加的消息 ID。
            
        Raises:
            EventBusError: 如果添加消息失败。
        """
        try:
            result = self.redis_client.xadd(
                name=topic,
                fields=message_fields,
                id=message_id
            )
            # 处理可能返回的字节类型
            if isinstance(result, bytes):
                return result.decode('utf-8')
            return result
        except redis.RedisError as e:
            raise EventBusError(f"Failed to add message to stream '{topic}': {str(e)}") from e
    
    def xreadgroup(
        self,
        group: str,
        consumer: str,
        streams: Dict[str, str],
        count: int = 1,
        block: int = 0
    ) -> Optional[List[Any]]:
        """
        从 Redis Stream 读取消息，使用消费者组模式。
        
        Args:
            group: 消费者组名称。
            consumer: 消费者名称。
            streams: 要读取的 Stream 和起始 ID 的字典，例如 {'stream1': '>'} 表示从未传递的消息开始。
            count: 一次读取的最大消息数量。
            block: 阻塞读取的毫秒数，0 表示无限期阻塞。
            
        Returns:
            读取到的消息列表，如果没有消息则返回 None。
            
        Raises:
            EventBusError: 如果读取消息失败。
        """
        try:
            result = self.redis_client.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams=streams,
                count=count,
                block=block
            )
            return result if result else None
        except redis.RedisError as e:
            streams_str = ', '.join(f"{k}:{v}" for k, v in streams.items())
            raise EventBusError(
                f"Failed to read from streams {streams_str} for group '{group}': {str(e)}"
            ) from e
    
    def xack(
        self, 
        stream_key: str, 
        group: str, 
        message_ids: List[str]
    ) -> int:
        """
        确认消息已被处理。
        
        Args:
            stream_key: Stream 名称。
            group: 消费者组名称。
            message_ids: 要确认的消息 ID 列表。
            
        Returns:
            成功确认的消息数量。
            
        Raises:
            EventBusError: 如果确认消息失败。
        """
        try:
            # 修复参数传递方式
            return self.redis_client.xack(
                stream_key,  # 直接传递位置参数
                group,       # 直接传递位置参数
                *message_ids
            )
        except redis.RedisError as e:
            ids_str = ', '.join(message_ids[:5]) + (f"... (and {len(message_ids) - 5} more)" if len(message_ids) > 5 else "")
            raise EventBusError(
                f"Failed to acknowledge messages {ids_str} in stream '{stream_key}' for group '{group}': {str(e)}"
            ) from e
    
    def xgroup_create_if_not_exists(
        self, 
        topic: str, 
        group_name: str, 
        start_id: str = '$', 
        mkstream: bool = True
    ) -> None:
        """
        如果消费者组不存在，则创建它。
        
        Args:
            topic: Stream 名称。
            group_name: 消费者组名称。
            start_id: 起始消息 ID，'$' 表示只消费新消息，'0' 表示从头开始。
            mkstream: 如果 Stream 不存在，是否创建它。
            
        Raises:
            EventBusError: 如果创建消费者组失败（不包括组已存在的情况）。
        """
        try:
            self.redis_client.xgroup_create(
                name=topic,
                groupname=group_name,
                id=start_id,
                mkstream=mkstream
            )
        except redis.ResponseError as e:
            # 忽略"组已存在"的错误
            if "BUSYGROUP" not in str(e):
                raise EventBusError(
                    f"Failed to create consumer group '{group_name}' for stream '{topic}': {str(e)}"
                ) from e
        except redis.RedisError as e:
            raise EventBusError(
                f"Failed to create consumer group '{group_name}' for stream '{topic}': {str(e)}"
            ) from e
    
    def publish(
        self, 
        topic: str, 
        message_data: Dict[str, Any],
        event_type_hint: Optional[str] = None,
        dialogue_session_id_hint: Optional[str] = None
    ) -> Optional[str]:
        """
        发布事件到指定主题。
        
        Args:
            topic: 事件主题
            message_data: 事件载荷数据
            event_type_hint: 事件类型提示
            dialogue_session_id_hint: 对话会话ID
            
        Returns:
            消息ID
            
        Raises:
            PublishError: 如果发布失败
        """
        try:
            # 构建事件信封
            event_envelope = self._build_event_envelope(
                message_data=message_data,
                topic=topic,
                event_type_hint=event_type_hint,
                dialogue_session_id_hint=dialogue_session_id_hint
            )
            
            # 序列化为JSON
            payload_json = serialize_to_json(event_envelope)
            
            # 构建完整主题键（带前缀）
            full_topic_key = build_topic_key(self.topic_prefix, topic)
            
            # 发布到Redis Stream
            message_id = self.redis_client.xadd(
                name=full_topic_key,
                fields={RedisConstants.PAYLOAD_FIELD: payload_json},
                id=RedisConstants.STREAM_ID_AUTO
            )
            
            # 处理可能返回的字节类型
            if isinstance(message_id, bytes):
                message_id = message_id.decode('utf-8')
            
            logger.debug(f"消息已发布到主题 '{full_topic_key}', ID: {message_id}")
            return message_id
            
        except redis.RedisError as e:
            error_msg = f"发布消息到主题 '{topic}' 失败: {e}"
            logger.error(error_msg)
            raise PublishError(error_msg) from e
        except Exception as e:
            error_msg = f"发布消息时发生未预期错误: {e}"
            logger.exception(error_msg)
            raise PublishError(error_msg) from e
    
    def subscribe(
        self,
        topic: str,
        handler_function: Callable[[str, Dict[str, Any], Dict[str, Any]], None],
        group_name: Optional[str] = None,
        consumer_name: Optional[str] = None,
        create_group_if_not_exists: bool = True,
        start_from_id: str = '>',
        auto_acknowledge: bool = False
    ) -> None:
        """
        订阅主题并处理收到的事件。
        
        Args:
            topic: 事件主题
            handler_function: 处理函数
            group_name: 消费者组名称，如果为None则使用默认值
            consumer_name: 消费者名称，如果为None则使用默认值
            create_group_if_not_exists: 如果组不存在是否创建
            start_from_id: 开始消费的消息ID
            auto_acknowledge: 是否自动确认消息
            
        Raises:
            SubscribeError: 如果订阅失败
        """
        try:
            # 使用默认值（如果未提供）
            group_name = group_name or self.default_consumer_group
            consumer_name = consumer_name or self.default_consumer_instance_name
            
            # 构建完整主题键
            full_topic_key = build_topic_key(self.topic_prefix, topic)
            
            # 如果需要，创建消费者组
            if create_group_if_not_exists:
                try:
                    self.redis_client.xgroup_create(
                        name=full_topic_key,
                        groupname=group_name,
                        id=start_from_id if start_from_id != '>' else '$',
                        mkstream=True
                    )
                    logger.info(f"已创建消费者组 '{group_name}' (主题: '{full_topic_key}')")
                except redis.ResponseError as e:
                    # 忽略"组已存在"的错误
                    if "BUSYGROUP" not in str(e):
                        raise ConsumerGroupError(f"创建消费者组 '{group_name}' 失败: {e}") from e
            
            # 创建并启动处理线程
            subscription_key = f"{full_topic_key}:{group_name}:{consumer_name}"
            
            # 如果已经有相同的订阅，先停止并移除
            if subscription_key in self.active_subscriptions:
                logger.warning(f"正在替换现有的订阅: {subscription_key}")
                self.active_subscriptions[subscription_key].stop()
                # 给线程一些时间来停止
                time.sleep(0.1)
            
            # 创建新的处理线程
            handler_thread = MessageHandlerLoopThread(
                bus_instance=self,
                topic=topic,
                handler_function=handler_function,
                group_name=group_name,
                consumer_name=consumer_name,
                start_id=start_from_id,
                auto_acknowledge=auto_acknowledge,
                name=f"EventBus-{subscription_key}"
            )
            
            # 保存引用并启动线程
            self.active_subscriptions[subscription_key] = handler_thread
            handler_thread.start()
            
            logger.info(f"已启动订阅 '{subscription_key}'")
            
        except redis.RedisError as e:
            error_msg = f"订阅主题 '{topic}' 失败: {e}"
            logger.error(error_msg)
            raise SubscribeError(error_msg) from e
        except Exception as e:
            error_msg = f"订阅时发生未预期错误: {e}"
            logger.exception(error_msg)
            raise SubscribeError(error_msg) from e
    
    def acknowledge(
        self, 
        topic: str, 
        group_name: Optional[str], 
        message_ids: List[str]
    ) -> Optional[int]:
        """
        确认消息已被处理。
        
        Args:
            topic: 事件主题
            group_name: 消费者组名称，如果为None则使用默认值
            message_ids: 消息ID列表
            
        Returns:
            确认的消息数量
            
        Raises:
            AcknowledgeError: 如果确认失败
        """
        if not message_ids:
            return 0
        
        try:
            # 使用默认值（如果未提供）
            group_name = group_name or self.default_consumer_group
            
            # 构建完整主题键
            full_topic_key = build_topic_key(self.topic_prefix, topic)
            
            # 确认消息
            result = self.redis_client.xack(
                full_topic_key,
                group_name,
                *message_ids
            )
            
            logger.debug(f"已确认 {result} 条消息 (主题: '{full_topic_key}', 组: '{group_name}')")
            return result
            
        except redis.RedisError as e:
            ids_str = ', '.join(message_ids[:5]) + (f"... (共 {len(message_ids)} 条)" if len(message_ids) > 5 else "")
            error_msg = f"确认消息 [{ids_str}] 失败: {e}"
            logger.error(error_msg)
            raise AcknowledgeError(error_msg) from e
        except Exception as e:
            error_msg = f"确认消息时发生未预期错误: {e}"
            logger.exception(error_msg)
            raise AcknowledgeError(error_msg) from e
    
    def __del__(self):
        """
        对象销毁时清理资源。
        """
        # 停止所有活跃的订阅线程
        try:
            if hasattr(self, 'active_subscriptions'):
                for subscription_key, handler_thread in self.active_subscriptions.items():
                    logger.info(f"停止订阅 '{subscription_key}'")
                    handler_thread.stop()
                
                # 清空订阅字典
                self.active_subscriptions.clear()
            
            # 关闭Redis连接池
            if hasattr(self, 'redis_connection_pool'):
                try:
                    self.redis_connection_pool.disconnect()
                    logger.info("已关闭Redis连接池")
                except:
                    pass
        except:
            # 在析构函数中捕获所有异常，以防止崩溃
            pass 