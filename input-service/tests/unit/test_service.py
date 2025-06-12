"""
消息处理服务单元测试
"""
import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from input_service.service import MessageProcessingService
from input_service.webhook_handler import MattermostOutgoingWebhook
from event_bus_framework import IEventBus


class TestMessageProcessingService:
    """消息处理服务单元测试"""
    
    @pytest.fixture
    def mock_event_bus(self):
        """创建模拟的事件总线"""
        mock_bus = MagicMock(spec=IEventBus)
        mock_bus.publish.return_value = "message-id-123"
        return mock_bus
    
    @pytest.fixture
    def service(self, mock_event_bus):
        """创建用于测试的消息处理服务实例"""
        topics_config = {
            'publish': ['user_message_raw', 'test_topic'],
            'subscribe': ['system_status']
        }
        return MessageProcessingService(
            mock_event_bus,
            topics_override=topics_config
        )
    
    @pytest.fixture
    def valid_webhook_data(self):
        """创建有效的 Webhook 数据"""
        return MattermostOutgoingWebhook(
            token="test-token",
            team_id="team123",
            team_domain="test-team",
            channel_id="channel456",
            channel_name="general",
            timestamp=1622548800000,
            user_id="user123",
            user_name="testuser",
            post_id="post456",
            text="Hello, AI assistant!",
            trigger_word="",
            file_ids="",
            create_at=1622548800000
        )
    
    def test_service_initialization(self, mock_event_bus):
        """测试服务初始化"""
        topics_config = {
            'publish': ['user_message_raw', 'test_topic'],
            'subscribe': ['system_status']
        }
        
        service = MessageProcessingService(
            mock_event_bus,
            topics_override=topics_config
        )
        
        assert service.event_bus == mock_event_bus
        assert service.publish_topics == ['user_message_raw', 'test_topic']
        assert service.subscribe_topics == ['system_status']
    
    def test_process_and_publish_webhook_data_success(self, service, valid_webhook_data, mock_event_bus):
        """测试成功处理和发布 Webhook 数据"""
        result = service.process_and_publish_webhook_data(valid_webhook_data)
        
        assert result is True
        mock_event_bus.publish.assert_called_once()
        
        # 验证发布参数
        call_args = mock_event_bus.publish.call_args
        assert call_args[1]['topic'] == 'user_message_raw'
        
        event_data = call_args[1]['event_data']
        assert event_data['user_id'] == 'user123'
        assert event_data['username'] == 'testuser'
        assert event_data['platform'] == 'mattermost'
        assert event_data['channel_id'] == 'channel456'
        assert event_data['content']['text'] == 'Hello, AI assistant!'
        assert event_data['meta']['source'] == 'mattermost'
    
    def test_process_and_publish_webhook_data_publish_failure(self, service, valid_webhook_data, mock_event_bus):
        """测试发布失败的情况"""
        mock_event_bus.publish.return_value = None
        
        result = service.process_and_publish_webhook_data(valid_webhook_data)
        
        assert result is False
        mock_event_bus.publish.assert_called_once()
    
    def test_process_and_publish_webhook_data_topic_not_configured(self, mock_event_bus, valid_webhook_data):
        """测试主题未配置的情况"""
        topics_config = {
            'publish': ['other_topic'],  # 不包含 user_message_raw
            'subscribe': ['system_status']
        }
        
        service = MessageProcessingService(
            mock_event_bus,
            topics_override=topics_config
        )
        result = service.process_and_publish_webhook_data(valid_webhook_data)
        
        assert result is False
        mock_event_bus.publish.assert_not_called()
    
    def test_process_and_publish_webhook_data_exception_handling(self, service, mock_event_bus):
        """测试异常处理"""
        # 创建无效的 Webhook 数据（缺少必需字段）
        invalid_webhook_data = MagicMock()
        invalid_webhook_data.channel_name = None
        invalid_webhook_data.channel_id = "channel123"
        invalid_webhook_data.user_name = None
        invalid_webhook_data.user_id = "user123"
        invalid_webhook_data.text = "test message"
        invalid_webhook_data.post_id = "post123"
        invalid_webhook_data.timestamp = 1622548800000
        invalid_webhook_data.create_at = 1622548800000
        
        # 模拟序列化失败
        invalid_webhook_data.model_dump.side_effect = Exception("Serialization error")
        invalid_webhook_data.dict.side_effect = Exception("Dict conversion error")
        
        result = service.process_and_publish_webhook_data(invalid_webhook_data)
        
        assert result is False
        # 确保没有调用发布方法
        mock_event_bus.publish.assert_not_called()
    
    def test_event_creation_with_minimal_webhook_data(self, service, mock_event_bus):
        """测试使用最小 Webhook 数据创建事件"""
        minimal_webhook_data = MattermostOutgoingWebhook(
            token="test-token",
            team_id="team123",
            channel_id="channel456",
            user_id="user123",
            text="  Minimal message  ",  # 包含空格，测试 strip 功能
            post_id="post789"
        )
        
        result = service.process_and_publish_webhook_data(minimal_webhook_data)
        
        assert result is True
        mock_event_bus.publish.assert_called_once()
        
        event_data = mock_event_bus.publish.call_args[1]['event_data']
        assert event_data['content']['text'] == 'Minimal message'  # 验证 strip 功能
        assert event_data['username'] is None
        assert event_data['content']['attachments'] is None
    
    def test_event_timestamp_handling(self, service, mock_event_bus):
        """测试时间戳处理"""
        webhook_data = MattermostOutgoingWebhook(
            token="test-token",
            team_id="team123",
            channel_id="channel456",
            user_id="user123",
            text="Test timestamp",
            post_id="post789",
            timestamp=1622548800000,
            create_at=1622548900000
        )
        
        result = service.process_and_publish_webhook_data(webhook_data)
        
        assert result is True
        
        event_data = mock_event_bus.publish.call_args[1]['event_data']
        # 应该优先使用 timestamp
        assert event_data['meta']['timestamp'] == 1622548800000
    
    def test_event_timestamp_fallback(self, service, mock_event_bus):
        """测试时间戳回退处理"""
        webhook_data = MattermostOutgoingWebhook(
            token="test-token",
            team_id="team123",
            channel_id="channel456",
            user_id="user123",
            text="Test timestamp fallback",
            post_id="post789",
            timestamp=None,  # 没有 timestamp
            create_at=1622548900000
        )
        
        result = service.process_and_publish_webhook_data(webhook_data)
        
        assert result is True
        
        event_data = mock_event_bus.publish.call_args[1]['event_data']
        # 应该回退到 create_at
        assert event_data['meta']['timestamp'] == 1622548900000
    
    def test_event_timestamp_both_none(self, service, mock_event_bus):
        """测试时间戳都为 None 的情况"""
        webhook_data = MattermostOutgoingWebhook(
            token="test-token",
            team_id="team123",
            channel_id="channel456",
            user_id="user123",
            text="Test no timestamp",
            post_id="post789",
            timestamp=None,
            create_at=None
        )
        
        result = service.process_and_publish_webhook_data(webhook_data)
        
        assert result is True
        
        event_data = mock_event_bus.publish.call_args[1]['event_data']
        # 应该是 0
        assert event_data['meta']['timestamp'] == 0
    
    @patch('input_service.service.logger')
    def test_logging_behavior(self, mock_logger, service, valid_webhook_data, mock_event_bus):
        """测试日志记录行为"""
        service.process_and_publish_webhook_data(valid_webhook_data)
        
        # 验证记录了接收消息的日志
        mock_logger.info.assert_called()
        
        # 检查日志调用包含预期信息
        log_calls = mock_logger.info.call_args_list
        assert len(log_calls) >= 2  # 至少有接收消息和发布成功的日志
        
        # 验证第一个日志包含消息信息
        first_log_message = log_calls[0][0][0]
        assert "收到 Mattermost 消息" in first_log_message
        assert "channel=general" in first_log_message
        assert "user=testuser" in first_log_message
    
    @patch('input_service.service.logger')
    def test_error_logging(self, mock_logger, service, mock_event_bus):
        """测试错误日志记录"""
        # 创建会引发异常的 Webhook 数据
        problematic_webhook_data = MagicMock()
        problematic_webhook_data.text = "test"
        problematic_webhook_data.channel_name = None
        problematic_webhook_data.channel_id = "channel123"
        problematic_webhook_data.user_name = None
        problematic_webhook_data.user_id = "user123"
        problematic_webhook_data.post_id = "post123"
        problematic_webhook_data.timestamp = None
        problematic_webhook_data.create_at = None
        problematic_webhook_data.model_dump.side_effect = Exception("Model dump error")
        problematic_webhook_data.dict.side_effect = Exception("Dict error")
        
        result = service.process_and_publish_webhook_data(problematic_webhook_data)
        
        assert result is False
        mock_logger.exception.assert_called_once()
        
        # 验证错误日志包含预期信息
        error_log_message = mock_logger.exception.call_args[0][0]
        assert "处理 Webhook 数据失败" in error_log_message 