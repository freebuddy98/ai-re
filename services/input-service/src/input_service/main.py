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
from event_bus_framework.common.config import get_input_service_config

# 获取配置
config = get_input_service_config()

# 创建主模块日志器
logger = get_logger("main")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="AI-RE 输入服务")
    parser.add_argument(
        "--host", 
        type=str, 
        default=config.API_HOST, 
        help=f"服务监听的主机地址 (默认: {config.API_HOST})"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=config.API_PORT, 
        help=f"服务监听的端口 (默认: {config.API_PORT})"
    )
    parser.add_argument(
        "--redis-url", 
        type=str, 
        default=config.REDIS_URL,
        help=f"Redis连接URL (默认: {config.REDIS_URL})"
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
    logger.info(f"启动 {config.SERVICE_NAME} 服务, 版本: {config.APP_VERSION}")
    logger.info(f"主机: {args.host}, 端口: {args.port}")
    logger.info(f"Redis: {args.redis_url}")
    
    if args.config_file:
        logger.info(f"使用配置文件: {args.config_file}")
    
    # 创建应用实例
    app = create_app()
    
    try:
        # 启动服务
        logger.info(f"正在启动 {config.SERVICE_NAME} 服务...")
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