"""
Mattermost Webhook 处理模块

此模块定义了接收和处理 Mattermost Webhook 请求的处理器和数据模型。
"""
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# 避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .service import MessageProcessingService

# 导入共享模块
from event_bus_framework import get_logger
from event_bus_framework.common.config import get_service_config

# 获取配置
config = get_service_config('input_service')
api_paths = config.get('api_paths', {
    "mattermost_webhook": "/api/v1/webhook/mattermost",
    "health": "/health",
})

# 创建webhook模块日志器
logger = get_logger("webhook_handler")


class MattermostOutgoingWebhook(BaseModel):
    """
    Mattermost 外发 Webhook 模型
    
    根据 https://developers.mattermost.com/integrate/webhooks/outgoing/ 文档定义
    使用 JSON 格式发送
    """
    channel_id: str
    channel_name: Optional[str] = None
    team_domain: Optional[str] = None
    team_id: Optional[str] = None
    post_id: Optional[str] = None
    text: str
    timestamp: Optional[int] = None
    create_at: Optional[int] = None  # 消息创建时间
    token: Optional[str] = None
    trigger_word: Optional[str] = None
    user_id: str
    user_name: Optional[str] = None


class MattermostWebhookHandler:
    """
    Mattermost Webhook 处理器类
    
    负责接收、验证和处理来自 Mattermost 的 Webhook 请求。
    """
    
    def __init__(self, message_processor: 'MessageProcessingService'):
        """
        初始化 Webhook 处理器
        
        Args:
            message_processor: 消息处理服务实例，用于处理和发布消息
        """
        self.message_processor = message_processor
        self.router = APIRouter()
        self._setup_routes()
        logger.info("Mattermost Webhook 处理器初始化完成")
    
    def _setup_routes(self) -> None:
        """设置路由处理函数"""
        webhook_path = api_paths["mattermost_webhook"]
        self.router.add_api_route(
            webhook_path,
            self.handle_webhook,
            methods=["POST"],
            response_class=JSONResponse,
            status_code=200,
            summary="处理 Mattermost Webhook",
            description="接收并处理来自 Mattermost 的 Webhook 推送消息"
        )
        logger.info(f"注册 Mattermost Webhook 路由: {webhook_path}")
    
    async def handle_webhook(self, request: Request) -> JSONResponse:
        """
        处理 Mattermost Webhook 请求
        
        Args:
            request: FastAPI请求对象，包含JSON格式的webhook数据
            
        Returns:
            JSON 响应，表示处理状态
        """
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"收到 Webhook 请求: 客户端IP={client_host}")
        
        try:
            # 解析JSON请求体
            payload = await request.json()
            logger.debug(f"Webhook 请求体: {payload}")
            
            # 构建webhook数据
            webhook_data = MattermostOutgoingWebhook(
                channel_id=payload.get("channel_id"),
                channel_name=payload.get("channel_name"),
                team_domain=payload.get("team_domain"),
                team_id=payload.get("team_id"),
                post_id=payload.get("post_id"),
                text=payload.get("text", ""),
                timestamp=payload.get("timestamp"),
                create_at=payload.get("create_at"),
                token=payload.get("token"),
                trigger_word=payload.get("trigger_word"),
                user_id=payload.get("user_id"),
                user_name=payload.get("user_name")
            )
            
            # 基础验证 - 例如检查必要字段
            if not webhook_data.text.strip():
                logger.warning("忽略空消息")
                return JSONResponse(
                    status_code=200,  # 仍返回200以不中断Mattermost
                    content={"status": "ignored", "reason": "empty_message"}
                )
            
            # 处理消息
            success = self.message_processor.process_and_publish_webhook_data(webhook_data)
            
            if success:
                logger.info("Webhook 处理成功")
                return JSONResponse(
                    content={"status": "success", "message": "Webhook processed successfully"}
                )
            else:
                logger.error("Webhook 处理失败")
                return JSONResponse(
                    content={"status": "error", "message": "Failed to process webhook"}
                )
                
        except Exception as e:
            # 记录错误但不向客户端暴露详细信息
            logger.exception(f"处理 Webhook 异常: {str(e)}")
            
            return JSONResponse(
                status_code=200,  # 仍返回200以不中断Mattermost
                content={"status": "error", "message": "Internal server error"}
            ) 