"""
事件总线框架的工具函数。
"""
import json
import socket
from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from .exceptions import DeserializationError
from .logging import logger


def serialize_to_json(data: Any) -> str:
    """
    将数据序列化为JSON字符串。
    
    Args:
        data: 要序列化的数据
        
    Returns:
        JSON字符串
    """
    try:
        return json.dumps(data)
    except (TypeError, ValueError) as e:
        logger.error(f"JSON序列化失败: {e}")
        raise DeserializationError(f"无法序列化为JSON: {e}")


def deserialize_from_json(json_str: str) -> Any:
    """
    从JSON字符串反序列化数据。
    
    Args:
        json_str: JSON字符串
        
    Returns:
        反序列化后的数据
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON反序列化失败: {e}")
        raise DeserializationError(f"无效的JSON: {e}")


def get_machine_hostname() -> str:
    """
    获取当前机器的主机名。
    
    Returns:
        主机名
    """
    return socket.gethostname()


def generate_unique_id() -> str:
    """
    生成唯一标识符。
    
    Returns:
        唯一ID字符串
    """
    return str(uuid4())


def get_utc_timestamp() -> str:
    """
    获取UTC时间戳，ISO 8601格式。
    
    Returns:
        ISO 8601格式的UTC时间戳
    """
    return datetime.utcnow().isoformat()


def build_topic_key(
    topic_prefix: str, 
    topic: str
) -> str:
    """
    构建完整的主题键。
    
    Args:
        topic_prefix: 主题前缀
        topic: 逻辑主题名
        
    Returns:
        完整的主题键
    """
    if not topic_prefix:
        return topic
    
    # 确保前缀和主题之间只有一个分隔符
    if topic_prefix.endswith(':') and topic.startswith(':'):
        return f"{topic_prefix}{topic[1:]}"
    elif topic_prefix.endswith(':') or topic.startswith(':'):
        return f"{topic_prefix}{topic}"
    else:
        return f"{topic_prefix}:{topic}"


def decode_redis_stream_message(
    redis_message: Union[Dict, Any]
) -> Optional[Dict[str, Any]]:
    """
    解码Redis Stream消息为Python字典。
    
    Args:
        redis_message: Redis Stream返回的消息
        
    Returns:
        解码后的消息，如果无法解码则返回None
    """
    try:
        # Redis streams消息格式: [[stream_name, [(message_id, {field: value, ...}), ...]], ...]
        if isinstance(redis_message, list) and len(redis_message) > 0:
            # 获取第一个流的消息
            stream_messages = redis_message[0][1]
            
            if stream_messages:
                # 返回消息ID和消息内容
                message_id = stream_messages[0][0]
                message_fields = stream_messages[0][1]
                return {
                    "message_id": message_id,
                    "fields": message_fields
                }
    except (IndexError, TypeError) as e:
        logger.error(f"解码Redis消息失败: {e}")
    
    return None 