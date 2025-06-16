"""
Service Manager

Manages the lifecycle and initialization of the NLU service components.
Uses the BaseServiceManager from event_bus_framework to reduce code duplication.
"""
from typing import Optional, Dict, Any

from event_bus_framework import (
    BaseServiceManager,
    MessageHandlerRegistry,
    get_logger
)

from .core.nlu_processor import NLUProcessor
from .config import NLUServiceConfig, load_config_from_dict
from .factory import NLUProcessorFactory
from .message_handlers import MessageHandlers

logger = get_logger("nlu_service.service_manager")


class NLUServiceManager(BaseServiceManager):
    """
    NLU服务管理器
    
    继承BaseServiceManager，专注于NLU特定的业务逻辑初始化。
    通用的服务生命周期管理由基类处理。
    """
    
    def __init__(self):
        super().__init__()
        
        # NLU特定组件
        self.nlu_config: Optional[NLUServiceConfig] = None
        self.nlu_processor: Optional[NLUProcessor] = None
        self.message_handlers: Optional[MessageHandlers] = None
        self.handler_registry: Optional[MessageHandlerRegistry] = None
    
    def get_service_name(self) -> str:
        """返回服务名称"""
        return "nlu_service"
    
    def initialize_business_components(self) -> None:
        """初始化NLU特定的业务组件"""
        try:
            # 转换配置格式
            self._convert_config()
            
            # 初始化NLU处理器
            self._initialize_nlu_processor()
            
            # 初始化消息处理器
            self._initialize_message_handlers()
            
            logger.debug("[nlu_service] Initialized all business components")
            
        except Exception as e:
            logger.error(f"[nlu_service] Failed to initialize business components: {e}")
            raise
    
    def get_message_handlers(self) -> Dict[str, Any]:
        """返回消息处理器映射"""
        if not self.handler_registry:
            raise ValueError("Handler registry not initialized")
        
        return self.handler_registry.get_all_handlers()
    
    def _convert_config(self) -> None:
        """将通用配置转换为NLU特定配置"""
        try:
            # 转换为NLUServiceConfig
            self.nlu_config = load_config_from_dict(self.config)
            logger.debug("[nlu_service] Converted configuration to NLUServiceConfig")
            
        except Exception as e:
            logger.error(f"[nlu_service] Failed to convert configuration: {e}")
            raise
    
    def _initialize_nlu_processor(self) -> None:
        """初始化NLU处理器"""
        try:
            # 获取主题配置
            topics_config = self.config.get('topics', {})
            input_topics = topics_config.get('subscribe', ['user_message_raw'])
            output_topics = topics_config.get('publish', ['nlu_uar_result'])
            
            # 使用工厂创建NLU处理器
            self.nlu_processor = NLUProcessorFactory.create_nlu_processor(
                event_bus=self.event_bus,
                config=self.nlu_config,
                input_topics=input_topics,
                output_topics=output_topics
            )
            
            logger.debug(f"[nlu_service] Initialized NLU processor with topics: subscribe={input_topics}, publish={output_topics}")
            
        except Exception as e:
            logger.error(f"[nlu_service] Failed to initialize NLU processor: {e}")
            raise
    
    def _initialize_message_handlers(self) -> None:
        """初始化消息处理器和注册表"""
        try:
            # 创建消息处理器
            self.message_handlers = MessageHandlers(self.nlu_processor)
            
            # 创建处理器注册表
            self.handler_registry = MessageHandlerRegistry("nlu_service")
            
            # 注册默认处理器
            self.handler_registry.register_handlers({
                'user_message_raw': self.message_handlers.handle_user_message,
                'user_intent_request': self.message_handlers.handle_intent_request,
                'user_entity_extraction': self.message_handlers.handle_entity_extraction,
                'dialogue_context_update': self.message_handlers.handle_context_update,
            })
            
            # 设置默认处理器
            self.handler_registry.set_default_handler(self.message_handlers.handle_unknown_message)
            
            logger.debug("[nlu_service] Initialized message handlers and registry")
            
        except Exception as e:
            logger.error(f"[nlu_service] Failed to initialize message handlers: {e}")
            raise
    
    # 可选：提供NLU特定的便捷方法
    def get_nlu_processor(self) -> Optional[NLUProcessor]:
        """获取NLU处理器实例"""
        return self.nlu_processor
    
    def get_nlu_config(self) -> Optional[NLUServiceConfig]:
        """获取NLU配置"""
        return self.nlu_config 