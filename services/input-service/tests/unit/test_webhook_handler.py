"""
Webhook 处理器单元测试
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 导入服务模块
from input_service.app import create_app
from input_service.webhook_handler import MattermostOutgoingWebhook
from input_service.service import MessageProcessingService

# 导入事件总线框架
from event_bus_framework import (
    input_service_config as config
)


@pytest.fixture
def mock_event_bus():
    """创建模拟的事件总线"""
    mock_bus = MagicMock()
    # 模拟成功发布消息
    mock_bus.publish.return_value = "message-id-123"
    return mock_bus


@pytest.fixture
def test_client(mock_event_bus):
    """创建测试客户端"""
    # 创建测试配置
    test_config = {
        'app_title': 'Test Input Service',
        'api_paths': {
            'mattermost_webhook': '/api/v1/webhook/mattermost',
            'health': '/health',
            'loki_status': '/loki-status'
        }
    }
    
    # 创建主题配置
    topics_config = {
        'publish': ['user_message_raw'],
        'subscribe': []
    }
    
    app = create_app(
        event_bus=mock_event_bus,
        config_override=test_config,
        topics_override=topics_config
    )
    return TestClient(app)


@pytest.fixture
def json_data_valid():
    """创建有效的JSON数据"""
    return {
        "token": "some-token",
        "team_id": "team789",
        "team_domain": "test-team",
        "channel_id": "channel456",
        "channel_name": "test-channel",
        "timestamp": 1622548800000,
        "user_id": "user123",
        "user_name": "testuser",
        "post_id": "post123",
        "text": "Hello, AI-RE!",
        "trigger_word": ""
    }


@pytest.fixture
def json_data_empty_message():
    """创建空消息的JSON数据"""
    return {
        "token": "some-token",
        "user_id": "user123",
        "channel_id": "channel456",
        "text": "   ",  # 空白消息
        "post_id": "post123"
    }


def test_handle_webhook_valid_payload(test_client, json_data_valid, mock_event_bus):
    """测试处理有效的 Webhook 负载"""
    # 获取WebhookAPI路径
    webhook_path = "/api/v1/webhook/mattermost"
    
    # 发送 POST 请求 (JSON 格式)
    response = test_client.post(
        webhook_path,
        json=json_data_valid
    )
    
    # 验证响应
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Webhook processed successfully"}
    
    # 验证事件总线调用
    mock_event_bus.publish.assert_called_once()
    
    # 验证发布的消息包含预期内容
    args, kwargs = mock_event_bus.publish.call_args
    assert "topic" in kwargs
    assert "event_data" in kwargs
    
    # 验证消息内容
    event_data = kwargs["event_data"]
    assert "content" in event_data
    assert event_data["content"]["text"] == "Hello, AI-RE!"
    assert event_data["user_id"] == "user123"
    assert event_data["channel_id"] == "channel456"


def test_handle_webhook_empty_message(test_client, json_data_empty_message):
    """测试处理空消息"""
    # 获取WebhookAPI路径
    webhook_path = "/api/v1/webhook/mattermost"
    
    # 发送 POST 请求
    response = test_client.post(
        webhook_path,
        json=json_data_empty_message
    )
    
    # 验证响应
    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "reason": "empty_message"}


def test_handle_webhook_publish_failure(test_client, json_data_valid, mock_event_bus):
    """测试发布失败的情况"""
    # 模拟发布失败
    mock_event_bus.publish.return_value = None
    
    # 获取WebhookAPI路径
    webhook_path = "/api/v1/webhook/mattermost"
    
    # 发送 POST 请求
    response = test_client.post(
        webhook_path,
        json=json_data_valid
    )
    
    # 验证响应
    assert response.status_code == 200
    assert response.json() == {"status": "error", "message": "Failed to process webhook"}


def test_health_endpoint(test_client):
    """测试健康检查端点"""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "ok"
    assert "service" in response.json()
    assert "version" in response.json() 