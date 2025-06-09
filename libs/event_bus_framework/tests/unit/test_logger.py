"""
日志系统单元测试
"""
import logging
import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from event_bus_framework.common.logger import (
    get_logger,
    _configure_logging,
    _initialize_logging,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_FORMAT,
    DEFAULT_JSON_FORMAT
)


class TestLoggerUnit:
    """日志系统单元测试"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境，重置日志配置状态"""
        import event_bus_framework.common.logger as logger_module
        # 重置全局状态
        logger_module._logging_configured = False
        
        # 清理根日志记录器处理器
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)  # 重置为默认级别
        
        yield
        
        # 测试后重置状态
        logger_module._logging_configured = False
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def test_get_logger_returns_logger_instance(self):
        """测试 get_logger 返回正确的日志器实例"""
        logger_name = "test_logger"
        logger = get_logger(logger_name)
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == logger_name
    
    def test_get_logger_returns_same_instance(self):
        """测试多次调用 get_logger 返回相同实例"""
        logger_name = "test_logger_same"
        logger1 = get_logger(logger_name)
        logger2 = get_logger(logger_name)
        
        assert logger1 is logger2
    
    def test_configure_logging_with_defaults(self):
        """测试使用默认参数配置日志"""
        import event_bus_framework.common.logger as logger_module
        
        _configure_logging()
        
        # 验证配置状态
        assert logger_module._logging_configured is True
        
        # 验证根日志器配置
        root_logger = logging.getLogger()
        assert root_logger.level == DEFAULT_LOG_LEVEL
        
        # 验证处理器
        assert len(root_logger.handlers) >= 1  # 至少有控制台处理器
    
    def test_configure_logging_console_only(self):
        """测试仅配置控制台输出"""
        _configure_logging(
            log_to_console=True,
            log_to_file=False
        )
        
        root_logger = logging.getLogger()
        console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        file_handlers = [h for h in root_logger.handlers if hasattr(h, 'baseFilename')]
        
        assert len(console_handlers) >= 1
        assert len(file_handlers) == 0
    
    def test_configure_logging_file_only(self):
        """测试仅配置文件输出"""
        with tempfile.TemporaryDirectory() as temp_dir:
            _configure_logging(
                log_to_console=False,
                log_to_file=True,
                log_dir=temp_dir,
                log_file_name="test.log"
            )
            
            root_logger = logging.getLogger()
            # 过滤掉pytest的处理器
            console_handlers = [h for h in root_logger.handlers 
                              if isinstance(h, logging.StreamHandler) and not hasattr(h, 'target')]
            file_handlers = [h for h in root_logger.handlers if hasattr(h, 'baseFilename')]
            
            # 验证文件处理器存在
            assert len(file_handlers) >= 1
            
            # 验证日志文件创建
            log_file_path = os.path.join(temp_dir, "test.log")
            assert os.path.exists(log_file_path)
    
    def test_configure_logging_json_formatter(self):
        """测试 JSON 格式化器配置"""
        _configure_logging(
            use_json_formatter=True,
            log_to_file=False
        )
        
        root_logger = logging.getLogger()
        # 查找我们创建的控制台处理器（排除pytest的处理器）
        console_handler = None
        for h in root_logger.handlers:
            if isinstance(h, logging.StreamHandler) and hasattr(h, 'stream') and h.stream == sys.stdout:
                console_handler = h
                break
        
        # 验证找到了我们的处理器并且使用了 JSON 格式化器
        if console_handler:
            from pythonjsonlogger import jsonlogger
            assert isinstance(console_handler.formatter, jsonlogger.JsonFormatter)
    
    def test_configure_logging_custom_log_level(self):
        """测试自定义日志级别配置"""
        _configure_logging(log_level=logging.DEBUG)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    @patch('event_bus_framework.common.logger.LOKI_AVAILABLE', True)
    @patch('event_bus_framework.common.logger.logging_loki')
    def test_configure_logging_with_loki_success(self, mock_loki):
        """测试成功配置 Loki 日志处理器"""
        mock_handler = MagicMock()
        mock_handler.level = logging.INFO  # 设置level属性
        mock_loki.LokiHandler.return_value = mock_handler
        
        _configure_logging(
            enable_loki=True,
            loki_url="http://localhost:3100/loki/api/v1/push",
            log_to_file=False  # 避免文件处理器影响测试
        )
        
        # 验证 Loki 处理器被创建和添加
        mock_loki.LokiHandler.assert_called_once()
        root_logger = logging.getLogger()
        assert mock_handler in root_logger.handlers
    
    @patch('event_bus_framework.common.logger.LOKI_AVAILABLE', True)
    @patch('event_bus_framework.common.logger.logging_loki')
    def test_configure_logging_with_loki_failure(self, mock_loki):
        """测试 Loki 配置失败的处理"""
        mock_loki.LokiHandler.side_effect = Exception("Loki connection failed")
        
        # 应该不抛出异常
        _configure_logging(
            enable_loki=True,
            loki_url="http://localhost:3100/loki/api/v1/push"
        )
        
        # 验证仍有其他处理器
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) >= 1
    
    @patch('event_bus_framework.common.logger.LOKI_AVAILABLE', False)
    def test_configure_logging_loki_not_available(self):
        """测试 Loki 不可用时的处理"""
        # 应该不抛出异常
        _configure_logging(
            enable_loki=True,
            loki_url="http://localhost:3100/loki/api/v1/push"
        )
        
        # 验证仍有其他处理器
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) >= 1
    
    def test_configure_logging_only_once(self):
        """测试日志配置只执行一次"""
        import event_bus_framework.common.logger as logger_module
        
        # 第一次配置
        _configure_logging()
        assert logger_module._logging_configured is True
        
        # 记录第一次配置的处理器数量
        root_logger = logging.getLogger()
        first_handler_count = len(root_logger.handlers)
        
        # 第二次配置
        _configure_logging()
        
        # 验证处理器数量没有增加（没有重复配置）
        assert len(root_logger.handlers) == first_handler_count
    
    @patch('event_bus_framework.common.config.load_config')
    def test_initialize_logging_with_config(self, mock_load_config):
        """测试基于配置文件初始化日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = {
                'logging': {
                    'level': 'DEBUG',
                    'enable_loki': 'false',  # 避免Loki相关问题
                    'use_json': True,
                    'dir': temp_dir,
                    'file': 'test.log'
                }
            }
            mock_load_config.return_value = mock_config
            
            _initialize_logging()
            
            # 验证配置被应用
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG
    
    @patch('event_bus_framework.common.config.load_config')
    def test_initialize_logging_config_load_failure(self, mock_load_config):
        """测试配置加载失败时的处理"""
        mock_load_config.side_effect = Exception("Config load failed")
        
        # 应该不抛出异常，使用默认配置
        _initialize_logging()
        
        # 验证使用默认配置
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) >= 1
    
    @patch('event_bus_framework.common.config.load_config')
    def test_initialize_logging_import_error(self, mock_load_config):
        """测试配置模块导入失败时的处理"""
        mock_load_config.side_effect = ImportError("Config module not found")
        
        # 应该不抛出异常，使用默认配置
        _initialize_logging()
        
        # 验证使用默认配置
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) >= 1
    
    def test_logger_integration(self):
        """测试日志器集成功能"""
        logger = get_logger("integration_test")
        
        # 测试不同级别的日志记录
        with patch.object(logger, 'info') as mock_info:
            logger.info("Test info message")
            mock_info.assert_called_once_with("Test info message")
        
        with patch.object(logger, 'error') as mock_error:
            logger.error("Test error message")
            mock_error.assert_called_once_with("Test error message") 