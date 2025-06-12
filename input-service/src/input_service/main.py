"""
输入服务入口点

此模块提供了启动输入服务的命令行入口点。
"""
import argparse
import os
import sys
import uvicorn
from pathlib import Path

from .app import create_app
# 导入共享模块
from event_bus_framework import get_logger
from event_bus_framework.common.config import get_service_config

# 获取配置
config = get_service_config('input_service')

# 创建主模块日志器
logger = get_logger("main")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="AI-RE 输入服务")
    
    # 获取API配置
    api_config = config.get('api', {})
    
    parser.add_argument(
        "--host", 
        type=str, 
        default=api_config.get('host', '0.0.0.0'), 
        help=f"服务监听的主机地址 (默认: {api_config.get('host', '0.0.0.0')})"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=api_config.get('port', 8000), 
        help=f"服务监听的端口 (默认: {api_config.get('port', 8000)})"
    )
    
    # 获取Redis配置
    event_bus_config = config.get('event_bus', {})
    redis_config = event_bus_config.get('redis', {})
    redis_host = redis_config.get('host', 'redis')
    redis_port = redis_config.get('port', 6379)
    redis_db = redis_config.get('db', 0)
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
    
    parser.add_argument(
        "--redis-url", 
        type=str, 
        default=redis_url,
        help=f"Redis连接URL (默认: {redis_url})"
    )
    parser.add_argument(
        "--config-file",
        type=str,
        default=os.environ.get("CONFIG_PATH", ""),
        help="配置文件路径 (默认: 使用环境变量CONFIG_PATH或默认路径)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="启用调试模式"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="日志文件目录 (默认: logs)"
    )
    return parser.parse_args()


def main():
    """服务入口点函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 配置日志目录
    os.makedirs(args.log_dir, exist_ok=True)
    
    # 记录启动信息
    service_name = config.get('service_name', 'input-service')
    app_version = config.get('app_version', '0.1.0')
    
    logger.info(f"启动 {service_name} 服务, 版本: {app_version}")
    logger.info(f"主机: {args.host}, 端口: {args.port}")
    logger.info(f"Redis: {args.redis_url}")
    
    if args.config_file:
        logger.info(f"使用配置文件: {args.config_file}")
    
    # 创建应用实例
    app = create_app()
    
    try:
        # 启动服务
        logger.info(f"正在启动 {service_name} 服务...")
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="debug" if args.debug else "info"
        )
    except Exception as e:
        logger.exception(f"服务启动失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 