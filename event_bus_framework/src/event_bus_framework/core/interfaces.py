"""
事件总线框架的抽象接口定义。

此模块定义了事件总线的核心接口，所有具体实现类必须满足这些接口要求。
"""
from typing import Any, Callable, Dict, List, Optional, Protocol


class IEventBus(Protocol):
    """
    事件总线框架的抽象接口定义。
    
    提供了发布、订阅和确认消息的标准接口，允许不同的后端实现（如Redis Streams）。
    """
    
    def publish(
        self, 
        topic: str, 
        message_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        发布一个事件到指定的主题。框架会自动包装成标准事件信封。
        
        Args:
            topic: 作为主题的事件类型 (Stream 名称的一部分，如 "stream:<timestamp>:<topic>")。
            message_data: 事件的业务载荷数据 (将被包装在信封的 actual_payload 中)。
            
        Returns:
            成功时返回事件在 Stream 中的唯一 ID，失败时返回 None 或抛出异常。
        """
        ...

    def subscribe(
        self,
        topic: str,
        handler_function: Callable[[str, Dict[str, Any], Dict[str, Any]], None],
        group_name: Optional[str] = None,
        consumer_name: Optional[str] = None,
        create_group_if_not_exists: bool = True,
        start_from_id: str = '>',
        auto_acknowledge: bool = False
    ) -> None:
        """
        订阅一个主题的事件，并指定处理函数。
        此方法通常会启动一个或多个后台监听循环。
        
        Args:
            topic: 作为主题的事件类型 (Stream 名称的一部分，如 "stream:<timestamp>:<topic>")。
            handler_function: 处理事件的回调函数。接收参数：
                              - message_id (str): 消息的唯一ID。
                              - event_envelope (dict): 完整的事件信封。
                              - actual_payload (dict): 从信封中解析出的业务载荷。
            group_name: (可选) 消费者组名称。如果为 None，则使用客户端配置的默认组名。
            consumer_name: (可选) 当前消费者的唯一名称。如果为 None，则使用客户端配置的默认消费者名。
            create_group_if_not_exists: 如果组不存在是否自动创建。
            start_from_id: 从哪个消息 ID 开始消费 ('>' 新消息, '0' 从头, 或指定 ID)。用于事件重放。
            auto_acknowledge: (不推荐 V1.0 使用) 是否自动 ACK。建议为 False，由 handler 显式调用。
        """
        ...

    def acknowledge(
        self, 
        topic: str, 
        group_name: Optional[str], 
        message_ids: List[str]
    ) -> Optional[int]:
        """
        确认一个或多个消息已被成功处理。
        
        Args:
            topic: 作为主题的事件类型 (Stream 名称的一部分，如 "stream:<timestamp>:<topic>")。
            group_name: (可选) 消费者组名称。如果为 None，则使用客户端配置的默认组名。
            message_ids: 需要确认的消息 ID 列表。
            
        Returns:
            成功确认的消息数量，失败时返回 None 或抛出异常。
        """
        ... 