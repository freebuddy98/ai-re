"""
输入服务 (Input Service)

输入服务是 AI-RE 助手系统的统一外部消息入口。
在 V1.0 版本中，其核心职责是接收 Mattermost Webhook 消息，
进行处理后通过事件总线框架发布给下游服务。
"""
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

__version__ = "0.1.0"

from .webhook_handler import MattermostWebhookHandler, MattermostOutgoingWebhook
from .service import MessageProcessingService
from .app import create_app

# 从event_bus_framework导入共享模块
from event_bus_framework import (
    UserMessageRawEvent,
    EventMeta,
    MessageContent,
    get_logger
)
from event_bus_framework.common.config import get_input_service_config

# 获取配置
config = get_input_service_config()

__all__ = [
    "MattermostWebhookHandler",
    "MattermostOutgoingWebhook",
    "MessageProcessingService",
    "create_app",
    "config",
    "UserMessageRawEvent",
    "EventMeta",
    "MessageContent",
    "get_logger",
] 