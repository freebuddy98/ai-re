"""
事件总线框架的日志配置和工具函数。
"""
import json
import logging
import sys
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    获取配置好的日志记录器。
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # 如果已经有处理器，不重复添加
    if logger.handlers:
        return logger
    
    # 创建处理器
    handler = logging.StreamHandler(sys.stdout)
    
    # 创建JSON格式化器
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    )
    handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(handler)
    
    return logger


# 创建框架的默认日志记录器
logger = get_logger("event_bus_framework")


def log_event(
    event_data: Dict[str, Any], 
    log_level: str = "INFO", 
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """
    记录事件日志。
    
    Args:
        event_data: 事件数据
        log_level: 日志级别
        additional_context: 额外的上下文信息
    """
    log_data = {
        "event": event_data,
    }
    
    if additional_context:
        log_data.update(additional_context)
    
    log_method = getattr(logger, log_level.lower(), logger.info)
    log_method(json.dumps(log_data)) 