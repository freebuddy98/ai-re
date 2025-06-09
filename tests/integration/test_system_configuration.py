"""
系统配置集成测试

测试整个系统的配置加载和组件交互。
"""
import os
import sys
import time
import redis
import pytest
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 导入配置管理模块
from event_bus_framework.common.config import get_config, load_config


class TestSystemConfigurationIntegration:
    """系统配置集成测试类"""
    
    @pytest.fixture
    def config(self):
        """加载系统配置"""
        # 从配置文件加载配置
        config_path = Path("config/base.yml")
        environment = os.environ.get("ENVIRONMENT", "development")
        
        if not config_path.exists():
            pytest.skip("配置文件不存在，跳过测试")
        
        # 加载配置
        return get_config(
            base_config_path=config_path,
            env=environment
        )
    
    @pytest.fixture
    def redis_client(self, config):
        """创建Redis客户端"""
        try:
            # 从配置获取Redis连接信息
            redis_config = config.get("redis", {})
            host = redis_config.get("host", "localhost")
            port = int(redis_config.get("port", 6379))
            db = int(redis_config.get("db", 0))
            password = redis_config.get("password", None) or None
            
            # 创建Redis客户端
            client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=5,
                decode_responses=True
            )
            
            # 测试连接
            client.ping()
            
            yield client
            
            # 清理
            client.close()
            
        except redis.exceptions.ConnectionError:
            pytest.skip("无法连接到Redis，跳过测试")
    
    def test_config_loading(self, config):
        """测试配置加载"""
        # 验证基本配置项
        assert "app" in config, "配置中应包含app部分"
        assert "name" in config["app"], "app配置中应包含name"
        assert "version" in config["app"], "app配置中应包含version"
        
        # 验证输入服务配置
        assert "input_service" in config, "配置中应包含input_service部分"
        assert "service_name" in config["input_service"], "input_service配置中应包含service_name"
        
        # 验证Redis配置
        assert "redis" in config, "配置中应包含redis部分"
        assert "host" in config["redis"], "redis配置中应包含host"
        assert "port" in config["redis"], "redis配置中应包含port"
    
    def test_redis_connection(self, redis_client):
        """测试Redis连接"""
        # 设置一个测试键
        test_key = "test:integration:key"
        test_value = "integration_test_value"
        
        # 写入数据
        redis_client.set(test_key, test_value, ex=60)  # 60秒过期
        
        # 读取数据
        retrieved_value = redis_client.get(test_key)
        
        # 验证数据
        assert retrieved_value == test_value, "Redis写入和读取应匹配"
        
        # 清理测试数据
        redis_client.delete(test_key)
    
    def test_redis_streams(self, redis_client):
        """测试Redis Streams功能"""
        # 测试流名称
        test_stream = "test:integration:stream"
        
        # 清理可能存在的测试流
        try:
            redis_client.delete(test_stream)
        except:
            pass
        
        # 添加消息到流
        message_data = {
            "test_field": "test_value",
            "timestamp": str(int(time.time() * 1000))
        }
        
        message_id = redis_client.xadd(test_stream, message_data)
        
        # 读取消息
        messages = redis_client.xread({test_stream: "0"}, count=1)
        
        # 验证消息
        assert messages, "应该能够读取到流消息"
        assert len(messages) == 1, "应该有一个流"
        assert messages[0][0] == test_stream, "流名称应匹配"
        assert len(messages[0][1]) == 1, "应该有一条消息"
        
        # 验证消息内容
        retrieved_message = messages[0][1][0][1]
        assert retrieved_message["test_field"] == "test_value", "消息字段应匹配"
        
        # 清理测试流
        redis_client.delete(test_stream) 