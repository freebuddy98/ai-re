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
    DEFAULT_TOPIC_PREFIX = "event-bus"  # 默认主题前缀
    DEFAULT_EVENT_SOURCE = "UnknownService"  # 默认事件源
    DEFAULT_CONSUMER_GROUP = "default-group"  # 默认消费者组
    DEFAULT_CONSUMER_NAME = "consumer-1"  # 默认消费者名称
    
    # Redis键名称规则
    PAYLOAD_FIELD = "payload"  # 载荷字段名

    # 默认连接超时时间（秒）
    DEFAULT_CONNECTION_TIMEOUT = 5
    
    # 默认连接重试次数
    DEFAULT_CONNECTION_RETRY_COUNT = 3
    
    # 默认连接重试延迟（秒）
    DEFAULT_CONNECTION_RETRY_DELAY = 2
    
    # 默认 Redis Stream 最大长度
    DEFAULT_MAX_STREAM_LENGTH = 1000
    
    # 默认消息批处理大小
    DEFAULT_BATCH_SIZE = 10
    
    # 默认阻塞等待时间（毫秒）
    DEFAULT_BLOCK_MS = 2000
    
    # 默认处理结果
    DEFAULT_PROCESS_RESULT = "OK"
    
    # Redis流特殊ID
    REDIS_STREAM_FIRST_ID = "0-0"
    REDIS_STREAM_LAST_ID = "$"
    REDIS_STREAM_NEXT_ID = ">"


class ErrorMessages:
    """错误消息常量"""
    REDIS_CONNECTION_ERROR = "无法连接到Redis服务器"
    PUBLISH_ERROR = "发布事件时发生错误"
    SUBSCRIBE_ERROR = "订阅事件时发生错误"
    ACKNOWLEDGE_ERROR = "确认事件时发生错误"
    CREATE_GROUP_ERROR = "创建消费者组时发生错误"
    XREADGROUP_ERROR = "从消费者组读取消息时发生错误"
    INVALID_JSON = "无效的JSON数据" 