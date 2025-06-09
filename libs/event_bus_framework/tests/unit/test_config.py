"""
配置文件加载单元测试
"""
import os
import sys
import tempfile
import yaml
import pytest

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from event_bus_framework.common.config import (
    load_config, 
    get_service_config, 
    get_topics_for_service,
    _resolve_env_vars,
    _resolve_dict
)

# 测试用的配置文件内容
TEST_CONFIG = """
# 输入服务配置
input_service:
  service_name: "input-service-test"
  app_title: "测试输入服务"
  app_version: "1.0.0-test"
  
  topics:
    publish:
      - "user_message_raw"
      - "test_topic"
    subscribe:
      - "system_status"

# 事件总线配置
event_bus:
  stream_prefix: "test-ai-re"
  
  redis:
    host: "${REDIS_HOST:-redis-test}"
    port: "${REDIS_PORT:-6379}"
    db: "${REDIS_DB:-0}"
    password: "${REDIS_PASSWORD:-}"

# 日志配置
logging:
  level: "${LOG_LEVEL:-DEBUG}"
  enable_loki: "${LOKI_ENABLED:-false}"
"""


class TestConfigUnit:
    """配置文件加载单元测试"""
    
    @pytest.fixture
    def setup_test_config(self):
        """创建临时测试配置文件"""
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        # 创建测试配置文件
        config_path = os.path.join(temp_dir, "config.yml")
        with open(config_path, "w", encoding='utf-8') as f:
            f.write(TEST_CONFIG)
        
        # 设置环境变量使load_config使用我们的测试文件
        original_config_path = os.environ.get("CONFIG_PATH")
        os.environ["CONFIG_PATH"] = config_path
        
        yield {
            "temp_dir": temp_dir,
            "config_path": config_path
        }
        
        # 恢复原环境变量
        if original_config_path:
            os.environ["CONFIG_PATH"] = original_config_path
        elif "CONFIG_PATH" in os.environ:
            del os.environ["CONFIG_PATH"]
        
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_load_config(self, setup_test_config):
        """测试配置文件加载"""
        config = load_config()
        
        # 验证配置结构
        assert "input_service" in config
        assert "event_bus" in config
        assert "logging" in config
        
        # 验证输入服务配置
        input_config = config["input_service"]
        assert input_config["service_name"] == "input-service-test"
        assert input_config["app_title"] == "测试输入服务"
    
    def test_get_service_config(self, setup_test_config):
        """测试获取服务配置"""
        service_config = get_service_config("input_service")
        
        # 验证服务配置包含合并的事件总线配置
        assert "event_bus" in service_config
        assert service_config["event_bus"]["stream_prefix"] == "test-ai-re"
        
        # 验证服务配置包含合并的日志配置
        assert "logging" in service_config
    
    def test_get_topics_for_service(self, setup_test_config):
        """测试获取服务主题配置"""
        topics = get_topics_for_service("input_service")
        
        assert "publish" in topics
        assert "subscribe" in topics
        assert "user_message_raw" in topics["publish"]
        assert "test_topic" in topics["publish"]
        assert "system_status" in topics["subscribe"]
    
    def test_resolve_env_vars(self):
        """测试环境变量解析功能"""
        # 设置测试环境变量
        os.environ["TEST_VAR"] = "test_value"
        
        # 测试基本环境变量替换
        result = _resolve_env_vars("${TEST_VAR}")
        assert result == "test_value"
        
        # 测试带默认值的环境变量
        result = _resolve_env_vars("${NONEXISTENT_VAR:default_value}")
        assert result == "default_value"
        
        # 测试非字符串值
        result = _resolve_env_vars(123)
        assert result == 123
        
        # 清理环境变量
        del os.environ["TEST_VAR"]
    
    def test_resolve_dict(self):
        """测试字典环境变量解析"""
        # 设置测试环境变量
        os.environ["TEST_HOST"] = "test-host"
        os.environ["TEST_PORT"] = "9999"
        
        test_dict = {
            "host": "${TEST_HOST}",
            "port": "${TEST_PORT:-6379}",
            "db": "${TEST_DB:-0}",
            "nested": {
                "key": "${TEST_HOST}"
            }
        }
        
        result = _resolve_dict(test_dict)
        
        assert result["host"] == "test-host"
        assert result["port"] == 9999  # Now returns integer
        assert result["db"] == 0  # Now returns integer
        assert result["nested"]["key"] == "test-host"
        
        # 清理环境变量
        del os.environ["TEST_HOST"]
        del os.environ["TEST_PORT"] 