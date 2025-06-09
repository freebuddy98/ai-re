"""
服务健康检查端到端测试
"""
import os
import sys
import time
import subprocess
import requests
import pytest
from fastapi.testclient import TestClient

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from input_service.app import create_app
from event_bus_framework.adapters.redis_streams import RedisStreamEventBus
from event_bus_framework.common.config import get_service_config

# 跳过标记 - 用于需要真实服务的测试
skip_e2e = pytest.mark.skipif(
    os.environ.get("SKIP_E2E_TESTS", "").lower() == "true",
    reason="E2E测试被环境变量 SKIP_E2E_TESTS 跳过"
)


class TestServiceHealth:
    """服务健康检查端到端测试 - 使用TestClient"""
    
    @pytest.fixture
    def config(self):
        """获取输入服务配置"""
        return get_service_config('input_service')
    
    @pytest.fixture
    def event_bus(self, config):
        """创建事件总线实例"""
        event_bus_config = config.get('event_bus', {})
        redis_config = event_bus_config.get('redis', {})
        
        # 构建Redis URL
        redis_host = redis_config.get('host', 'redis')
        redis_port = redis_config.get('port', 6379)
        redis_db = redis_config.get('db', 0)
        redis_password = redis_config.get('password', '')
        
        auth = f":{redis_password}@" if redis_password else ""
        redis_url = f"redis://{auth}{redis_host}:{redis_port}/{redis_db}"
        
        return RedisStreamEventBus(
            redis_url=redis_url,
            event_source_name="service-health-test"
        )
    
    @pytest.fixture
    def test_app(self, event_bus, config):
        """创建测试应用实例"""
        test_config = {
            'app_title': 'Service Health Test',
            'app_description': 'Service Health Test',
            'app_version': '1.0.0-health-test',
            'service_name': 'input-service-health-test',
            'api_paths': config.get('api_paths', {
                'mattermost_webhook': '/api/v1/webhook/mattermost',
                'health': '/health',
                'loki_status': '/loki-status'
            })
        }
        
        topics_config = {
            'publish': ['user_message_raw'],
            'subscribe': []
        }
        
        app = create_app(
            event_bus=event_bus,
            config_override=test_config,
            topics_override=topics_config
        )
        return app
    
    @pytest.fixture
    def test_client(self, test_app):
        """创建测试客户端"""
        return TestClient(test_app)
    
    def test_health_endpoint(self, test_client):
        """测试健康检查端点 - 使用TestClient"""
        # 发送请求到健康检查端点
        response = test_client.get("/health")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data

    def test_loki_status_endpoint(self, test_client):
        """测试Loki状态端点 - 使用TestClient"""
        # 发送请求到Loki状态端点
        response = test_client.get("/loki-status")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "loki_enabled" in data
        assert "loki_url" in data


# 以下是针对真实运行服务的测试 - 只有在服务真正运行时才会执行
class TestRealServiceHealth:
    """针对真实运行服务的健康检查测试"""
    
    @pytest.fixture
    def config(self):
        """获取输入服务配置"""
        return get_service_config('input_service')
    
    @pytest.fixture
    def api_base_url(self, config):
        """获取API基础URL - 从配置构建"""
        api_config = config.get('api', {})
        host = api_config.get('host', 'localhost')
        port = api_config.get('port', 8001)
        
        # 如果host是0.0.0.0，使用localhost进行测试
        if host == "0.0.0.0":
            host = "localhost"
        
        # 构建完整的URL
        base_url = f"http://{host}:{port}"
        return base_url
    
    @pytest.fixture
    def api_paths(self, config):
        """获取API路径配置"""
        return config.get('api_paths', {
            'mattermost_webhook': '/api/v1/webhook/mattermost',
            'health': '/health',
            'loki_status': '/loki-status'
        })
    
    @pytest.fixture
    def setup_test_env(self, api_base_url):
        """设置测试环境"""
        # 这里可以启动服务，但在真实测试中通常会使用docker-compose
        # 或者假设服务已经在运行
        
        # 示例：如何启动服务（如果需要）
        # process = subprocess.Popen(
        #     ["python", "-m", "services.input_service.src.input_service.main", "--host", "0.0.0.0", "--port", "8001"],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE
        # )
        # 
        # # 等待服务启动
        # time.sleep(5)
        
        # 返回需要的测试参数
        yield {
            "service_url": api_base_url,
            # "process": process
        }
        
        # 清理环境（如果需要）
        # process.terminate()
        # process.wait()
    
    @skip_e2e
    def test_real_service_health_endpoint(self, setup_test_env, api_paths):
        """测试真实服务的健康检查端点"""
        try:
            # 从配置获取健康检查路径
            health_path = api_paths['health']
            health_url = f"{setup_test_env['service_url']}{health_path}"
            
            # 发送请求到健康检查端点
            response = requests.get(health_url, timeout=10)
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "service" in data
            assert "version" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip(f"服务未运行在 {setup_test_env['service_url']}，跳过端到端测试")
        except requests.exceptions.Timeout:
            pytest.skip(f"连接超时 {setup_test_env['service_url']}，跳过端到端测试")

    @skip_e2e
    def test_real_service_loki_status_endpoint(self, setup_test_env, api_paths):
        """测试真实服务的Loki状态端点"""
        try:
            # 从配置获取Loki状态路径
            loki_status_path = api_paths['loki_status']
            loki_status_url = f"{setup_test_env['service_url']}{loki_status_path}"
            
            # 发送请求到Loki状态端点
            response = requests.get(loki_status_url, timeout=10)
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "loki_enabled" in data
            assert "loki_url" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip(f"服务未运行在 {setup_test_env['service_url']}，跳过端到端测试")
        except requests.exceptions.Timeout:
            pytest.skip(f"连接超时 {setup_test_env['service_url']}，跳过端到端测试") 