"""
事件总线框架使用的常量定义。
"""


class RedisConstants:
    """Redis相关常量"""
    # Redis Streams 常量
    STREAM_ID_LATEST = ">"  # 只消费新消息
    STREAM_ID_BEGINNING = "0"  # 从头开始消费
    STREAM_ID_AUTO = "*"  # 让Redis自动生成ID
    
    # 默认值
    DEFAULT_BLOCK_TIME_MS = 5000  # 阻塞读取超时时间 (毫秒)
    DEFAULT_COUNT = 10  # 每次读取的最大消息数
    DEFAULT_TOPIC_PREFIX = ""  # 默认主题前缀
    DEFAULT_EVENT_SOURCE = "UnknownService"  # 默认事件源
    DEFAULT_CONSUMER_GROUP = "DefaultGroup"  # 默认消费者组
    DEFAULT_CONSUMER_NAME = "DefaultConsumer"  # 默认消费者名称
    
    # Redis键名称规则
    PAYLOAD_FIELD = "payload"  # 载荷字段名


class ErrorMessages:
    """错误消息常量"""
    REDIS_CONNECTION_ERROR = "无法连接到Redis服务器"
    PUBLISH_ERROR = "发布事件时发生错误"
    SUBSCRIBE_ERROR = "订阅事件时发生错误"
    ACKNOWLEDGE_ERROR = "确认事件时发生错误"
    CREATE_GROUP_ERROR = "创建消费者组时发生错误"
    XREADGROUP_ERROR = "从消费者组读取消息时发生错误"
    INVALID_JSON = "无效的JSON数据" 