"""
配置管理模块

提供通用的配置加载功能，遵循开放-封闭原则。
"""
import os
import re
import yaml
from typing import Dict, Any, List
from pathlib import Path

from .logger import get_logger

logger = get_logger("config")

# 配置文件路径
def _get_config_path():
    """获取配置文件路径"""
    config_path = Path(os.environ.get("CONFIG_PATH", "/app/config/config.yml"))
    if not config_path.exists():
        config_path = Path("config/config.yml")
    return config_path


def _resolve_env_vars(value: str) -> str:
    """解析环境变量 ${VAR:default} 或 ${VAR:-default}"""
    if not isinstance(value, str):
        return value
    
    pattern = re.compile(r'\${([^}:]+)(?::(-?)([^}]*?))?}')
    
    def replace_var(match):
        var_name, dash, default = match.groups()
        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        # 处理 ${VAR:-default} 语法，忽略dash符号
        return default if default is not None else ""
    
    return pattern.sub(replace_var, value)


def _resolve_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """递归解析字典中的环境变量并转换数据类型"""
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _resolve_dict(value)
        elif isinstance(value, str):
            resolved_value = _resolve_env_vars(value)
            # 尝试转换为适当的数据类型
            if resolved_value.isdigit():
                result[key] = int(resolved_value)
            elif resolved_value.lower() in ('true', 'false'):
                result[key] = resolved_value.lower() == 'true'
            else:
                result[key] = resolved_value
        else:
            result[key] = value
    return result


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    try:
        config_file = _get_config_path()
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            config = _resolve_dict(config)
            logger.info(f"成功加载配置: {config_file}")
            return config
        else:
            logger.warning(f"配置文件不存在: {config_file}")
            return {}
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return {}


def get_service_config(service_name: str) -> Dict[str, Any]:
    """
    获取指定服务的配置
    
    Args:
        service_name: 服务名称
        
    Returns:
        服务配置字典
    """
    config = load_config()
    service_config = config.get(service_name, {})
    
    # 合并事件总线配置
    if 'event_bus' in config:
        service_config.setdefault('event_bus', {}).update(config['event_bus'])
    
    # 合并日志配置
    if 'logging' in config:
        service_config.setdefault('logging', {}).update(config['logging'])
    
    logger.debug(f"已加载服务配置: {service_name}")
    return service_config


def get_event_bus_config() -> Dict[str, Any]:
    """获取事件总线配置"""
    config = load_config()
    return config.get('event_bus', {})


def get_logging_config() -> Dict[str, Any]:
    """获取日志配置"""
    config = load_config()
    return config.get('logging', {})


def get_topics_for_service(service_name: str) -> Dict[str, List[str]]:
    """
    获取服务的主题配置
    
    Args:
        service_name: 服务名称
        
    Returns:
        包含 'publish' 和 'subscribe' 主题列表的字典
    """
    service_config = get_service_config(service_name)
    topics = service_config.get('topics', {})
    
    return {
        'publish': topics.get('publish', []),
        'subscribe': topics.get('subscribe', [])
    }


# 保持向后兼容的便捷函数
def get_config() -> Dict[str, Any]:
    """获取原始配置字典"""
    return load_config()


# 为了保持向后兼容性，保留原有的输入服务配置函数但标记为废弃
def get_input_service_config():
    """
    @deprecated 使用 get_service_config('input_service') 替代
    """
    logger.warning("get_input_service_config() 已废弃，请使用 get_service_config('input_service')")
    return get_service_config('input_service') 