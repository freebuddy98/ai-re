"""
日志系统模块

此模块提供系统统一的日志记录功能，支持控制台、文件和Loki输出，
并通过JSON格式方便地记录结构化信息。
"""
import logging
import os
import sys
import socket
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from pythonjsonlogger import jsonlogger

# Loki支持（可选）
try:
    import logging_loki
    LOKI_AVAILABLE = True
except ImportError:
    LOKI_AVAILABLE = False

# 默认日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_JSON_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

# 默认日志级别
DEFAULT_LOG_LEVEL = logging.INFO

# 默认日志目录
DEFAULT_LOG_DIR = "logs"

# 全局标记，确保只初始化一次
_logging_configured = False


def _configure_logging(
    log_level=DEFAULT_LOG_LEVEL,
    log_format=DEFAULT_LOG_FORMAT,
    json_format=DEFAULT_JSON_FORMAT,
    log_to_console=True,
    log_to_file=True,
    log_dir=DEFAULT_LOG_DIR,
    log_file_name="app.log",
    log_file_max_size=10 * 1024 * 1024,  # 10MB
    log_file_backup_count=5,
    use_rotating_file=True,
    use_json_formatter=False,
    enable_loki=False,
    loki_url=None,
):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
        log_format: 日志格式字符串
        json_format: JSON日志格式字符串
        log_to_console: 是否输出到控制台
        log_to_file: 是否输出到文件
        log_dir: 日志文件目录
        log_file_name: 日志文件名
        log_file_max_size: 日志文件最大大小（字节）
        log_file_backup_count: 日志文件备份数量
        use_rotating_file: 是否使用滚动文件
        use_json_formatter: 是否使用JSON格式
        enable_loki: 是否启用Loki日志输出
        loki_url: Loki服务URL
    """
    global _logging_configured
    
    # 如果已经配置过，不重复配置
    if _logging_configured:
        return
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有处理器
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    # 创建格式化器
    if use_json_formatter:
        formatter = jsonlogger.JsonFormatter(json_format)
    else:
        formatter = logging.Formatter(log_format)

    # 配置控制台输出
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 配置文件输出
    if log_to_file:
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, log_file_name)

        # 选择文件处理器类型
        if use_rotating_file:
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=log_file_max_size,
                backupCount=log_file_backup_count,
                encoding="utf-8"
            )
        else:
            file_handler = TimedRotatingFileHandler(
                log_file_path,
                when="midnight",
                backupCount=log_file_backup_count,
                encoding="utf-8"
            )

        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 配置Loki输出（如果启用）
    if enable_loki and LOKI_AVAILABLE and loki_url:
        try:
            service_name = os.environ.get("SERVICE_NAME", "ai-re-service")
            hostname = socket.gethostname()
            
            loki_handler = logging_loki.LokiHandler(
                url=loki_url,
                tags={"application": service_name, "hostname": hostname},
                version="1",
            )
            loki_handler.setLevel(log_level)
            root_logger.addHandler(loki_handler)
            
            # 记录成功配置
            root_logger.info(f"成功配置Loki日志处理器: {loki_url}")
        except Exception as e:
            root_logger.warning(f"配置Loki日志处理器失败: {str(e)}")
    elif enable_loki and not LOKI_AVAILABLE:
        root_logger.warning("logging_loki 模块不可用，跳过Loki日志配置")
    
    # 标记为已配置
    _logging_configured = True


def _initialize_logging():
    """初始化日志系统，基于配置文件进行一次性配置"""
    try:
        # 延迟导入避免循环依赖
        from .config import load_config
        config = load_config()
        
        if 'logging' in config:
            logging_config = config['logging']
            
            # 从配置中提取设置
            enable_loki = str(logging_config.get('enable_loki', 'false')).lower() == 'true'
            loki_url = logging_config.get('loki_url')
            use_json = logging_config.get('use_json', False)
            log_level = getattr(logging, logging_config.get('level', 'INFO').upper(), logging.INFO)
            log_dir = logging_config.get('dir', DEFAULT_LOG_DIR)
            log_file = logging_config.get('file', 'app.log')
            
            # 配置日志系统
            _configure_logging(
                log_level=log_level,
                log_dir=log_dir,
                log_file_name=log_file,
                use_json_formatter=use_json,
                enable_loki=enable_loki,
                loki_url=loki_url
            )
        else:
            # 使用默认配置
            _configure_logging()
    
    except ImportError:
        # 配置模块不可用，使用默认配置
        _configure_logging()
    except Exception as e:
        # 配置加载失败，记录错误并使用默认配置
        _configure_logging()
        logging.getLogger("config").warning(f"加载日志配置失败，使用默认配置: {e}")


# 系统启动时进行一次性初始化
_initialize_logging()


def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        配置好的日志记录器
    """
    return logging.getLogger(name) 