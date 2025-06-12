"""
FastAPI 应用创建模块

此模块负责创建和配置 FastAPI 应用实例，设置路由和依赖项。
"""
from typing import Optional, Dict, Any
import os
import sys

from fastapi import FastAPI

# 导入事件总线框架
from event_bus_framework import get_logger

# 创建应用模块日志器
logger = get_logger("app")

# 导入事件总线框架
from event_bus_framework import (
    IEventBus, 
    RedisStreamEventBus,  # 确保这个名称与__init__.py中的一致
)

# 导入配置
from event_bus_framework.common.config import get_service_config, get_event_bus_config


def create_app(
    event_bus: Optional[IEventBus] = None,
    config_override: Optional[Dict[str, Any]] = None,
    event_bus_config_override: Optional[Dict[str, Any]] = None,
    topics_override: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """
    创建并配置 FastAPI 应用实例
    
    Args:
        event_bus: 事件总线实例，如果为 None 则创建默认的 Redis 实现
        config_override: 配置覆盖，主要用于测试
        event_bus_config_override: 事件总线配置覆盖，主要用于测试
        topics_override: 主题配置覆盖，主要用于测试
        
    Returns:
        配置好的 FastAPI 应用实例
    """
    # 避免循环导入
    from .webhook_handler import MattermostWebhookHandler
    from .service import MessageProcessingService
    
    # 获取配置，支持测试时的配置覆盖
    if config_override is not None:
        config = config_override
    else:
        config = get_service_config('input_service')
    
    if event_bus_config_override is not None:
        event_bus_config = event_bus_config_override
    else:
        event_bus_config = get_event_bus_config()
    
    # 获取应用配置
    app_title = config.get('app_title', 'AI-RE 输入服务')
    app_description = config.get('app_description', 'AI-RE 助手系统的统一外部消息入口')
    app_version = config.get('app_version', '0.1.0')
    service_name = config.get('service_name', 'input-service')
    
    # 获取API配置
    api_config = config.get('api', {})
    docs_url = api_config.get('docs_url', '/docs')
    redoc_url = api_config.get('redoc_url', '/redoc')
    openapi_url = api_config.get('openapi_url', '/openapi.json')
    
    # 获取API路径配置
    api_paths = config.get('api_paths', {
        'mattermost_webhook': '/api/v1/webhook/mattermost',
        'health': '/health',
        'loki_status': '/loki-status'
    })
    
    logger.info(f"开始创建 FastAPI 应用: {app_title} v{app_version}")
    
    # 创建 FastAPI 应用
    app = FastAPI(
        title=app_title,
        description=app_description,
        version=app_version,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url
    )
    
    # 如果没有提供事件总线实例，则创建默认的 Redis 实现
    if event_bus is None:
        # 构建Redis URL
        redis_config = event_bus_config.get('redis', {})
        redis_host = redis_config.get('host', 'redis')
        redis_port = redis_config.get('port', 6379)
        redis_db = redis_config.get('db', 0)
        redis_password = redis_config.get('password', '')
        
        auth = f":{redis_password}@" if redis_password else ""
        redis_url = f"redis://{auth}{redis_host}:{redis_port}/{redis_db}"
        
        logger.info(f"创建默认 Redis 事件总线: {redis_url}")
        event_bus = RedisStreamEventBus(
            redis_url=redis_url,
            event_source_name=service_name
        )
    else:
        logger.info(f"使用提供的事件总线: {type(event_bus).__name__}")
    
    # 创建消息处理服务
    logger.info("创建消息处理服务")
    message_processor = MessageProcessingService(
        event_bus=event_bus,
        topics_override=topics_override
    )
    
    # 创建 Webhook 处理器并注册路由
    logger.info("创建 Webhook 处理器并注册路由")
    webhook_handler = MattermostWebhookHandler(message_processor=message_processor)
    app.include_router(webhook_handler.router, prefix="")
    
    # 添加健康检查端点
    @app.get(api_paths["health"], tags=["Health"])
    async def health_check():
        """健康检查端点"""
        logger.debug("收到健康检查请求")
        return {"status": "ok", "service": service_name, "version": app_version}
    
    # 添加Loki状态端点
    @app.get(api_paths["loki_status"], tags=["Health"])
    async def loki_status():
        """Loki连接状态端点"""
        logger.debug("收到Loki状态检查请求")
        logging_config = config.get('logging', {})
        loki_enabled = str(logging_config.get('enable_loki', 'false')).lower() == 'true'
        loki_url = logging_config.get('loki_url', 'http://loki:3100/loki/api/v1/push')
        return {
            "status": "ok", 
            "loki_enabled": loki_enabled,
            "loki_url": loki_url
        }
    
    logger.info(f"FastAPI 应用创建完成: {service_name}")
    return app 