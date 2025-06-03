from typing import Protocol, Callable, Any, runtime_checkable

@runtime_checkable
class IEventBus(Protocol):
    def publish(self, envelope: Any) -> None:
        ...

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        ...

    def unsubscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        ...

    def close(self) -> None:
        ... 