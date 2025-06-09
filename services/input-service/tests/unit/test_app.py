"""
FastAPI 应用单元测试
"""
import sys
import os
from unittest.mock import MagicMock, patch, Mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from input_service.app import create_app
from event_bus_framework import IEventBus


class TestAppCreation:
    """应用创建单元测试"""
    
    @pytest.fixture
    def mock_event_bus(self):
        """创建模拟的事件总线"""
        mock_bus = MagicMock(spec=IEventBus)
        return mock_bus
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        return {
            'app_title': '测试输入服务',
            'app_description': '测试描述',
            'app_version': '1.0.0-test',
            'api': {
                'docs_url': '/docs',
                'redoc_url': '/redoc',
                'openapi_url': '/openapi.json'
            },
            'api_paths': {
                'mattermost_webhook': '/api/v1/webhook/mattermost',
                'health': '/health',
                'loki_status': '/loki-status'
            }
        }
    
    def test_create_app_with_event_bus(self, mock_config, mock_event_bus):
        """测试使用事件总线创建应用"""
        app = create_app(
            event_bus=mock_event_bus,
            config_override=mock_config,
            topics_override={'publish': ['user_message_raw'], 'subscribe': []}
        )
        
        assert isinstance(app, FastAPI)
        assert app.title == '测试输入服务'
        assert app.description == '测试描述'
        assert app.version == '1.0.0-test'
        assert app.docs_url == '/docs'
        assert app.redoc_url == '/redoc'
        assert app.openapi_url == '/openapi.json'
    
    def test_create_app_without_event_bus(self, mock_config):
        """测试不提供事件总线创建应用"""
        app = create_app(
            config_override=mock_config,
            topics_override={'publish': ['user_message_raw'], 'subscribe': []}
        )
        
        assert isinstance(app, FastAPI)
        assert app.title == '测试输入服务'
    
    def test_create_app_with_default_config(self, mock_event_bus):
        """测试使用默认配置创建应用"""
        # 模拟配置缺少某些字段的情况
        minimal_config = {
            'app_title': '最小配置应用'
        }
        
        app = create_app(
            event_bus=mock_event_bus,
            config_override=minimal_config,
            topics_override={'publish': ['user_message_raw'], 'subscribe': []}
        )
        
        assert isinstance(app, FastAPI)
        assert app.title == '最小配置应用'
        # FastAPI 应该使用默认值
        assert app.description is not None
        assert app.version is not None


class TestAppIntegration:
    """应用集成测试"""
    
    @pytest.fixture
    def mock_event_bus(self):
        """创建模拟的事件总线"""
        mock_bus = MagicMock(spec=IEventBus)
        mock_bus.publish.return_value = "message-id-123"
        return mock_bus

    def test_app_basic_functionality(self, mock_event_bus):
        """测试应用基本功能"""
        mock_config = {
            'app_title': '集成测试应用',
            'app_description': '集成测试描述',
            'app_version': '1.0.0-test',
            'api': {
                'docs_url': '/docs',
                'redoc_url': '/redoc',
                'openapi_url': '/openapi.json'
            },
            'api_paths': {
                'mattermost_webhook': '/api/v1/webhook/mattermost',
                'health': '/health',
                'loki_status': '/loki-status'
            }
        }
        
        app = create_app(
            event_bus=mock_event_bus,
            config_override=mock_config,
            topics_override={'publish': ['user_message_raw'], 'subscribe': []}
        )
        client = TestClient(app)
        
        # 测试健康检查端点
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "ok"
        assert "service" in health_data
        assert "version" in health_data

    def test_app_openapi_docs_available(self, mock_event_bus):
        """测试 OpenAPI 文档可用性"""
        mock_config = {
            'app_title': '文档测试应用',
            'app_description': '文档测试描述',
            'app_version': '1.0.0-test',
            'api': {
                'docs_url': '/docs',
                'redoc_url': '/redoc',
                'openapi_url': '/openapi.json'
            },
            'api_paths': {
                'mattermost_webhook': '/api/v1/webhook/mattermost',
                'health': '/health',
                'loki_status': '/loki-status'
            }
        }
        
        app = create_app(
            event_bus=mock_event_bus,
            config_override=mock_config,
            topics_override={'publish': ['user_message_raw'], 'subscribe': []}
        )
        client = TestClient(app)
        
        # 测试 OpenAPI JSON 端点
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        assert openapi_data["info"]["title"] == "文档测试应用"
        assert openapi_data["info"]["description"] == "文档测试描述"
        assert openapi_data["info"]["version"] == "1.0.0-test"

    @patch('input_service.app.logger')
    def test_app_startup_logging(self, mock_logger, mock_event_bus):
        """测试应用启动日志"""
        mock_config = {
            'app_title': '日志测试应用',
            'api_paths': {
                'mattermost_webhook': '/api/v1/webhook/mattermost',
                'health': '/health',
                'loki_status': '/loki-status'
            }
        }
        
        app = create_app(
            event_bus=mock_event_bus,
            config_override=mock_config,
            topics_override={'publish': ['user_message_raw'], 'subscribe': []}
        )
        
        # 验证启动日志被调用
        mock_logger.info.assert_called()
        
        # 检查是否记录了应用创建完成的日志
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("FastAPI 应用创建完成" in call for call in log_calls)

    def test_app_error_handling_missing_config(self, mock_event_bus):
        """测试配置缺失时的错误处理"""
        # 使用空配置测试默认值行为
        empty_config = {}
        
        app = create_app(
            event_bus=mock_event_bus,
            config_override=empty_config,
            topics_override={'publish': ['user_message_raw'], 'subscribe': []}
        )
        
        # 应该使用默认值成功创建应用
        assert isinstance(app, FastAPI)
        assert app.title == 'AI-RE 输入服务'  # 默认标题

    def test_app_with_custom_api_paths(self, mock_event_bus):
        """测试自定义 API 路径配置"""
        mock_config = {
            'app_title': '自定义路径应用',
            'api_paths': {
                'mattermost_webhook': '/custom/webhook',
                'health': '/custom/health',
                'loki_status': '/custom/loki'
            }
        }
        
        app = create_app(
            event_bus=mock_event_bus,
            config_override=mock_config,
            topics_override={'publish': ['user_message_raw'], 'subscribe': []}
        )
        client = TestClient(app)
        
        # 测试自定义健康检查路径
        response = client.get("/custom/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "ok" 