import pytest
from typing import Any, Callable, Dict
import sys

# 动态导入 Protocol 兼容性
try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol

try:
    from event_bus_framework.interfaces import IEventBus
except ImportError:
    IEventBus = None

def test_ibus_interface_methods():
    class DummyEventBus:
        def publish(self, envelope: Any) -> None:
            pass
        def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
            pass
        def unsubscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
            pass
        def close(self) -> None:
            pass
    # 检查 DummyEventBus 是否实现了 IEventBus 协议
    if IEventBus is not None:
        assert issubclass(DummyEventBus, IEventBus) 