"""
全局测试配置
"""
import os
import sys
import pytest
from unittest.mock import MagicMock

# 确保能导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 创建通用的模拟对象
@pytest.fixture
def mock_event_bus():
    """模拟事件总线"""
    mock_bus = MagicMock()
    mock_bus.publish.return_value = "mock-message-id-123"
    return mock_bus 