"""
消息处理服务

此模块负责处理从 Webhook 接收到的消息，
并将其转换为标准格式后通过事件总线发布。
"""
import json
from typing import Dict, Any, Optional, List

# 导入事件总线框架
from event_bus_framework import (
    IEventBus,
    EventMeta,
    UserMessageRawEvent,
    MessageContent,
    get_logger
)
from event_bus_framework.common.config import get_service_config, get_topics_for_service

# 创建服务模块日志器
logger = get_logger("input_service")

# 这里使用前向引用，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .webhook_handler import MattermostOutgoingWebhook


class MessageProcessingService:
    """
    消息处理服务
    
    负责处理、转换和发布从 Webhook 接收到的消息。
    """
    
    def __init__(
        self, 
        event_bus: IEventBus,
        topics_override: Optional[Dict[str, List[str]]] = None
    ):
        """
        初始化消息处理服务
        
        Args:
            event_bus: 事件总线实例，用于发布消息
            topics_override: 主题配置覆盖，主要用于测试
        """
        self.event_bus = event_bus
        
        # 获取主题配置，支持测试时的覆盖
        if topics_override is not None:
            topics = topics_override
        else:
            topics = get_topics_for_service('input_service')
        
        self.publish_topics = topics.get('publish', [])
        self.subscribe_topics = topics.get('subscribe', [])
        
        logger.debug(f"初始化消息处理服务，事件总线: {type(event_bus).__name__}")
        logger.debug(f"发布主题: {self.publish_topics}")
        logger.debug(f"订阅主题: {self.subscribe_topics}")
    
    def process_and_publish_webhook_data(self, webhook_data: 'MattermostOutgoingWebhook') -> bool:
        """
        处理并发布 Webhook 数据
        
        Args:
            webhook_data: Mattermost Outgoing Webhook 数据
            
        Returns:
            处理成功返回 True，否则返回 False
        """
        try:
            # 记录接收到的消息
            logger.debug(
                f"收到 Mattermost 消息: channel={webhook_data.channel_name or webhook_data.channel_id}, "
                f"user={webhook_data.user_name or webhook_data.user_id}, "
                f"text={webhook_data.text[:50]}{'...' if len(webhook_data.text) > 50 else ''}"
            )
            
            # 创建用户消息原始事件对象
            event = UserMessageRawEvent(
                meta=EventMeta(
                    event_id=webhook_data.post_id or "",
                    source="mattermost",
                    timestamp=webhook_data.timestamp or int(webhook_data.create_at or 0)
                ),
                user_id=webhook_data.user_id,
                username=webhook_data.user_name,
                platform="mattermost",
                channel_id=webhook_data.channel_id,
                content=MessageContent(
                    text=webhook_data.text.strip(),
                    attachments=None  # 暂不处理附件
                ),
                raw_data=webhook_data.model_dump(mode="json") if hasattr(webhook_data, "model_dump") else webhook_data.dict()
            )
            
            # 发布到配置的主题
            if "user_message_raw" in self.publish_topics:
                message_id = self.event_bus.publish(
                    topic="user_message_raw",
                    event_data=event.model_dump(mode="json") if hasattr(event, "model_dump") else event.dict()
                )
                
                # 记录发布结果
                if message_id:
                    logger.debug(f"消息发布成功: message_id={message_id}, topic=user_message_raw")
                    return True
                else:
                    logger.error("消息发布失败: 未获得消息ID")
                    return False
            else:
                logger.warning("user_message_raw 主题未在发布列表中配置")
                return False
            
        except Exception as e:
            # 记录错误并返回处理失败
            logger.exception(f"处理 Webhook 数据失败: {str(e)}")
            return False 