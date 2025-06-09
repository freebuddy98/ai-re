"""
API工作流端到端测试

测试完整的API调用流程，包括webhooks和健康检查。
"""
import os
import sys
import time
import json
import requests
import pytest
from typing import Dict
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


class TestAPIWorkflow:
    """API工作流测试类"""
    
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
            event_source_name="api-workflow-test"
        )
    
    @pytest.fixture
    def test_app(self, event_bus, config):
        """创建测试应用实例"""
        test_config = {
            'app_title': 'API Workflow Test Service',
            'app_description': 'API Workflow Test Service',
            'app_version': '1.0.0-api-test',
            'service_name': 'input-service-api-test',
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
    
    @pytest.fixture
    def webhook_payload(self):
        """创建webhook测试负载"""
        return {
            "token": "test-token",
            "team_id": "T12345",
            "team_domain": "test-team",
            "channel_id": "C12345",
            "channel_name": "test-channel",
            "timestamp": int(time.time() * 1000),
            "user_id": "U12345",
            "user_name": "test-user",
            "post_id": "P12345",
            "text": "Hello, AI-RE! This is an e2e test.",
            "trigger_word": ""
        }

    def test_health_endpoint(self, test_client):
        """测试健康检查端点 - 使用TestClient"""
        # 发送请求
        response = test_client.get("/health")
        
        # 验证响应
        assert response.status_code == 200, f"健康检查应返回200状态码，实际返回：{response.status_code}"
        
        # 解析响应体
        data = response.json()
        
        # 验证响应内容
        assert "status" in data, "响应应包含status字段"
        assert data["status"] == "ok", f"status应为ok，实际为：{data['status']}"
        assert "service" in data, "响应应包含service字段"
        assert "version" in data, "响应应包含version字段"
    
    def test_loki_status_endpoint(self, test_client):
        """测试Loki状态端点 - 使用TestClient"""
        # 发送请求
        response = test_client.get("/loki-status")
        
        # 验证响应
        assert response.status_code == 200, f"Loki状态检查应返回200状态码，实际返回：{response.status_code}"
        
        # 解析响应体
        data = response.json()
        
        # 验证响应内容
        assert "status" in data, "响应应包含status字段"
        assert data["status"] == "ok", f"status应为ok，实际为：{data['status']}"
        assert "loki_enabled" in data, "响应应包含loki_enabled字段"
        assert "loki_url" in data, "响应应包含loki_url字段"
    
    def test_webhook_endpoint(self, test_client, webhook_payload):
        """测试webhook端点 - 使用TestClient"""
        # 发送请求
        response = test_client.post(
            "/api/v1/webhook/mattermost",
            json=webhook_payload
        )
        
        # 验证响应
        assert response.status_code == 200, f"Webhook请求应返回200状态码，实际返回：{response.status_code}"
        
        # 解析响应体
        data = response.json()
        
        # 验证响应内容
        assert "status" in data, "响应应包含status字段"
        assert data["status"] == "success", f"status应为success，实际为：{data['status']}"
        assert "message" in data, "响应应包含message字段"
    
    def test_webhook_empty_message(self, test_client, webhook_payload):
        """测试空消息webhook - 使用TestClient"""
        # 创建空消息负载
        empty_payload = webhook_payload.copy()
        empty_payload["text"] = "   "  # 空白消息
        
        # 发送请求
        response = test_client.post(
            "/api/v1/webhook/mattermost",
            json=empty_payload
        )
        
        # 验证响应
        assert response.status_code == 200, f"空消息Webhook请求应返回200状态码，实际返回：{response.status_code}"
        
        # 解析响应体
        data = response.json()
        
        # 验证响应内容
        assert "status" in data, "响应应包含status字段"
        assert data["status"] == "ignored", f"status应为ignored，实际为：{data['status']}"
        assert "reason" in data, "响应应包含reason字段"
        assert data["reason"] == "empty_message", f"reason应为empty_message，实际为：{data['reason']}"


# 以下是针对真实运行服务的测试 - 只有在服务真正运行时才会执行
class TestRealServiceWorkflow:
    """针对真实运行服务的API工作流测试"""
    
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
    def webhook_payload(self):
        """创建webhook测试负载"""
        return {
            "token": "test-token",
            "team_id": "T12345",
            "team_domain": "test-team",
            "channel_id": "C12345",
            "channel_name": "test-channel",
            "timestamp": int(time.time() * 1000),
            "user_id": "U12345",
            "user_name": "test-user",
            "post_id": "P12345",
            "text": "Hello, AI-RE! This is a real service e2e test.",
            "trigger_word": ""
        }

    @skip_e2e
    def test_real_service_health_endpoint(self, api_base_url, api_paths):
        """测试真实服务的健康检查端点"""
        try:
            # 从配置获取健康检查路径
            health_path = api_paths['health']
            health_url = f"{api_base_url}{health_path}"
            
            # 发送请求
            response = requests.get(health_url, timeout=10)
            
            # 验证响应
            assert response.status_code == 200, f"健康检查应返回200状态码，实际返回：{response.status_code}"
            
            # 解析响应体
            data = response.json()
            
            # 验证响应内容
            assert "status" in data, "响应应包含status字段"
            assert data["status"] == "ok", f"status应为ok，实际为：{data['status']}"
            assert "service" in data, "响应应包含service字段"
            assert "version" in data, "响应应包含version字段"
            
        except requests.exceptions.ConnectionError:
            pytest.skip(f"无法连接到真实服务 {api_base_url}，跳过测试")
        except requests.exceptions.Timeout:
            pytest.skip(f"连接超时 {api_base_url}，跳过测试")

    @skip_e2e
    def test_real_service_loki_status_endpoint(self, api_base_url, api_paths):
        """测试真实服务的Loki状态端点"""
        try:
            # 从配置获取Loki状态路径
            loki_status_path = api_paths['loki_status']
            loki_status_url = f"{api_base_url}{loki_status_path}"
            
            # 发送请求
            response = requests.get(loki_status_url, timeout=10)
            
            # 验证响应
            assert response.status_code == 200, f"Loki状态检查应返回200状态码，实际返回：{response.status_code}"
            
            # 解析响应体
            data = response.json()
            
            # 验证响应内容
            assert "status" in data, "响应应包含status字段"
            assert data["status"] == "ok", f"status应为ok，实际为：{data['status']}"
            assert "loki_enabled" in data, "响应应包含loki_enabled字段"
            assert "loki_url" in data, "响应应包含loki_url字段"
            
        except requests.exceptions.ConnectionError:
            pytest.skip(f"无法连接到真实服务 {api_base_url}，跳过测试")
        except requests.exceptions.Timeout:
            pytest.skip(f"连接超时 {api_base_url}，跳过测试")

    @skip_e2e
    def test_real_service_webhook_endpoint(self, api_base_url, api_paths, webhook_payload):
        """测试真实服务的webhook端点"""
        try:
            # 从配置获取webhook路径
            webhook_path = api_paths['mattermost_webhook']
            webhook_url = f"{api_base_url}{webhook_path}"
            
            # 发送请求
            response = requests.post(
                webhook_url,
                json=webhook_payload,
                timeout=10
            )
            
            # 验证响应
            assert response.status_code == 200, f"Webhook请求应返回200状态码，实际返回：{response.status_code}"
            
            # 解析响应体
            data = response.json()
            
            # 验证响应内容
            assert "status" in data, "响应应包含status字段"
            assert data["status"] == "success", f"status应为success，实际为：{data['status']}"
            assert "message" in data, "响应应包含message字段"
            
        except requests.exceptions.ConnectionError:
            pytest.skip(f"无法连接到真实服务 {api_base_url}，跳过测试")
        except requests.exceptions.Timeout:
            pytest.skip(f"连接超时 {api_base_url}，跳过测试") 