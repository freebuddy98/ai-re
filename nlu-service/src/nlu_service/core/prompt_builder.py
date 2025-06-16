"""
PromptBuilder component

This module implements the PromptBuilder class that constructs prompts for LLM
based on user messages, dialogue context, and predefined templates.
"""
import json
import logging
from typing import Dict, Optional, Any

from jinja2 import Environment, Template

# DialogueContext is now defined in config/dialogue_context.yml
# We work with Dict[str, Any] for dialogue context data
from ..models.uar import UAR


logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Prompt Builder component
    
    Responsible for building LLM prompts from templates and context data.
    As defined in design document section 2.1.
    """
    
    def __init__(self, prompt_templates: Optional[Dict[str, str]] = None):
        """
        Initialize PromptBuilder
        
        Args:
            prompt_templates: Dictionary of prompt templates. If None, uses default template.
        """
        self.prompt_templates = prompt_templates or self._get_default_templates()
        self.jinja_env = Environment()
    
    def build_llm_prompt(
        self,
        raw_message_payload: Dict,
        dialogue_context: Optional[Dict[str, Any]],
        uar_json_schema_def: str
    ) -> str:
        """
        Build LLM prompt from components
        
        Args:
            raw_message_payload: Raw message data from input service
            dialogue_context: Dialogue context from DPSS (can be None)
            uar_json_schema_def: UAR JSON schema definition string
            
        Returns:
            Complete prompt string ready for LLM
        """
        try:
            logger.debug("Building LLM prompt")
            
            # Get the main prompt template
            template_str = self.prompt_templates.get("main", self._get_default_main_template())
            template = self.jinja_env.from_string(template_str)
            
            # Prepare template variables
            template_vars = {
                "UAR_JSON_SCHEMA_DEFINITION_PLACEHOLDER": uar_json_schema_def,
                "DIALOGUE_CONTEXT_JSON_PLACEHOLDER": self._format_dialogue_context(dialogue_context),
                "CURRENT_USER_ID_PLACEHOLDER": raw_message_payload.get("user_id", "unknown"),
                "CURRENT_USER_UTTERANCE_PLACEHOLDER": raw_message_payload.get("raw_text", ""),
                "RAW_MESSAGE_ID_PLACEHOLDER": raw_message_payload.get("message_id", "unknown"),
                "CHANNEL_ID_PLACEHOLDER": raw_message_payload.get("channel_id", "unknown"),
            }
            
            # Render the template
            prompt = template.render(**template_vars)
            
            logger.debug(f"Successfully built prompt with length: {len(prompt)} characters")
            return prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            raise
    
    def _format_dialogue_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Format dialogue context as JSON string for template"""
        if context is None:
            return "{}"
        try:
            # Context is already a dictionary, just format as JSON
            return json.dumps(context, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Error formatting dialogue context: {e}")
            return "{}"
    
    def _get_default_templates(self) -> Dict[str, str]:
        """Get default prompt templates"""
        return {
            "main": self._get_default_main_template()
        }
    
    def _get_default_main_template(self) -> str:
        """
        Get the default main prompt template based on design document section 2.A
        This is the V1.3 prompt template from the design document.
        """
        return """您是一位经验丰富、技术精湛的 AI 需求工程分析师。您的核心任务是深度分析用户在需求讨论中的发言，精准识别其意图，并从中抽取结构化的**需求工程元素 (Requirements Engineering Elements, REIs)**，如高层目标 (Goal)、具体功能需求 (FunctionalRequirement)、非功能需求 (NonFunctionalRequirement)、用户角色/参与者 (Actor)、约束 (Constraint)、待讨论问题 (Issue) 以及重要数据对象 (DataObject)。这些需求工程元素是构建需求知识图谱的基本单元。

## 任务目标:
基于用户当前的发言，并参考提供的对话上下文（历史对话、当前焦点需求、待澄清问题），请完成以下分析：

1.  **意图识别 (Intent Recognition):** 判断用户此番发言的主要沟通意图。意图名称必须是预定义枚举中的一个。**特别注意，如果用户发言明显是对"当前讨论焦点 REI 摘要"或"最近对话历史"中提及的需求元素进行补充、修改或详细阐述，应优先考虑识别为 "ModifyExistingREI" 意图，并尝试在 UAR 的 `intent.target_rei_id_if_modifying` 字段中填入被修改的 REI 的 ID (从上下文中获取)。如果无法从提供的上下文中明确找到被修改的 REI ID，则此字段可为 null，但意图仍可判断为 "ModifyExistingREI" （后续系统将尝试更大范围匹配）。**
2.  **实体抽取 (Entity Extraction):** 识别并提取上述提及的各类**需求工程实体 (REIs)**。这些实体的内容会涉及用户讨论的具体业务领域，但其实体类型必须是预定义的枚举值。明确其实体类型、在原文中的具体表述 (text_span)、以及从发言中能推断出的核心属性。
3.  **关系抽取 (Relation Extraction):** 识别实体之间可能存在的、符合需求工程逻辑的关联关系。关系类型必须是预定义的枚举值。
4.  **模糊性标记 (Ambiguity Tagging):** 指出实体描述中任何模糊不清、需要进一步量化的表述，并提供具体原因和模糊文本片段。

## 输出格式 (严格遵循此 JSON Schema):
您的输出必须是一个结构良好、可被程序解析的 JSON 对象。请勿添加任何 JSON 之外的解释性文字。
```json
{{ UAR_JSON_SCHEMA_DEFINITION_PLACEHOLDER }} 
```
请确保您的输出严格符合此 Schema，包括所有必需字段和正确的数据类型。

## 意图名称枚举值及其含义与示例:
`intent.name` 字段必须从以下枚举值中选择：
* `"ProposeNewREI"`: 用户提出了一个新的、之前未明确讨论过的需求元素。
    * 示例: "系统应该允许用户自定义界面主题。"
* `"ModifyExistingREI"`: 用户对一个**已提及或已存在于上下文（特别是"当前讨论焦点 REI"或"最近对话历史"）**的需求元素进行了补充、修改、提供了更多细节或修正。
    * 示例: (上下文有 FR-101: "用户登录") 用户说: "关于用户登录，我们还需要支持手机号验证码登录。" -> 此时应尝试在 UAR 的 `intent.target_rei_id_if_modifying` 字段填入 "FR-101"。
* `"ProvideClarification"`: 用户针对系统或他人的提问，提供了澄清信息。
    * 示例: (系统问: "您说的快速具体指什么？") 用户答: "我的意思是页面加载时间应少于1秒。"
* `"ConfirmUnderstanding"`: 用户确认了系统或其他人的理解。
    * 示例: "对，就是这个意思。"
* `"DenyUnderstanding"`: 用户否认或不同意系统或其他人的理解。
    * 示例: "不完全是，我的侧重点在于..."
* `"AskQuestion"`: 用户提出了一个问题。
    * 示例: "这个新功能会影响性能吗？"
* `"GeneralStatement"`: 用户做了一个一般性陈述，与具体需求元素关联较弱。
    * 示例: "这个项目很有挑战性。"
* `"ChitChat"`: 闲聊或与需求无关的对话。
    * 示例: "午饭吃什么？"
* `"Unknown"`: 无法明确判断用户意图。

## 需求工程实体类型 (Entity Types) 参考与示例:
`entities.type` 字段必须从以下枚举值中选择：
* `"Goal"`: 用户或业务的高层目标或期望达成的成果。
    * 含义: 描述系统或项目要达成的战略性目的。
    * 示例发言片段: "我们的主要目标是**提升客户留存率**。"
* `"FunctionalRequirement"` (FR): 系统必须执行的具体功能或提供的服务。
    * 含义: 描述系统应该"做什么"。
    * 示例发言片段: "用户**应该能够在线支付订单**。"
* `"NonFunctionalRequirement"` (NFR): 系统的质量属性，如性能、安全性、易用性等。
    * 含义: 描述系统应该"做得多好"或具备何种特性。
    * 示例发言片段: "**系统响应时间必须在2秒以内**。"
* `"Actor"`: 与系统交互的用户角色、人员、外部系统或组织。
    * 含义: 谁会使用或与系统互动。
    * 示例发言片段: "**注册会员**可以查看历史购买记录。"
* `"Constraint"`: 对系统设计、实现或项目执行的限制或约束。
    * 含义: 必须遵守的限制条件。
    * 示例发言片段: "**项目预算不得超过50万**。" 或 "**系统必须使用Java开发**。"
* `"Issue"`: 用户在讨论中提出的疑问、关注点、潜在风险或待解决的问题。
    * 含义: 对话中出现的需要注意或解决的点。
    * 示例发言片段: "我担心**数据迁移的风险会很高**。"
* `"DataObject"`: 系统需要处理、存储或引用的重要数据实体或信息。
    * 含义: 系统操作的数据对象。
    * 示例发言片段: "我们需要存储**用户的订单信息和收货地址**。"
* `"SystemComponent"`: 系统的某个主要模块或组成部分。
    * 含义: 系统的逻辑或物理构成单元。
    * 示例发言片段: (如果用户提及) "**支付模块**需要对接银行接口。"
* `"UserStory"`: 一种特定的需求表达方式，通常格式为"作为<角色>, 我想要<活动>, 以便<商业价值>"。
    * 含义: 从用户视角描述其目标和动机。
    * 示例发言片段: "**作为普通顾客，我想要将商品添加到购物车，以便我稍后可以一起结算。**"
* `"UseCase"`: 描述一组用户与系统交互以达成特定目标的场景。
    * 含义: 用户如何使用系统完成特定任务。
    * 示例发言片段: (如果用户按用例方式描述) "用户**通过登录、搜索商品、加入购物车、结算步骤完成购买**。"
* `"Stakeholder"`: 对项目结果有兴趣或会受其影响的个人或团体。
    * 含义: 需求的相关方。
    * 示例发言片段: "**市场部**希望系统能提供用户行为分析报告。"

## 关系类型 (Relation Types) 参考与示例:
`relations.type` 字段必须从以下枚举值中选择，用于连接上述抽取的实体：
* `"REFINES"`: 一个需求元素是对另一个更高层元素的细化或具体化。
    * 含义: A 是 B 的具体化。
    * 示例: `FR("在线支付")` --REFINES--> `Goal("提升购物便捷性")`
* `"CONTAINS"` / `"PART_OF"`: 一个元素在逻辑上包含另一个元素，或另一个元素是其组成部分。
    * 含义: A 包含 B 或 B 是 A 的一部分。
    * 示例: `FR("用户管理")` --CONTAINS--> `FR("修改用户密码")`
* `"DEPENDS_ON"`: 一个需求元素的实现或存在依赖于另一个。
    * 含义: A 的实现需要 B。
    * 示例: `FR("生成报告")` --DEPENDS_ON--> `DataObject("销售数据")`
* `"AFFECTS"`: 一个元素（如约束、NFR、Issue）对另一个元素产生影响。
    * 含义: A 影响 B。
    * 示例: `Constraint("特定加密算法")` --AFFECTS--> `FR("用户认证")`
* `"CONFLICTS_WITH"`: 两个需求元素之间存在逻辑冲突或矛盾。
    * 含义: A 与 B 存在冲突。
    * 示例: `FR("允许匿名评论")` --CONFLICTS_WITH--> `NFR("所有内容需实名追溯")`
* `"INVOLVES"`: 某个场景或功能涉及到某个角色或数据对象。
    * 含义: A 涉及到 B。
    * 示例: `FR("查看订单")` --INVOLVES--> `Actor("注册用户")`
* `"QUALIFIES"`: 一个 NFR 用来限定或修饰一个 FR 或 Goal。
    * 含义: A 对 B 进行了质量限定。
    * 示例: `NFR("响应时间小于1秒")` --QUALIFIES--> `FR("搜索商品")`
* `"ADDRESSES"`: 一个 FR 或系统方案旨在解决某个 Issue 或达成某个 Goal。
    * 含义: A 旨在解决/达成 B。
    * 示例: `FR("增加客服入口")` --ADDRESSES--> `Issue("用户反馈渠道不畅通")`
* `"RELATES_TO"`: 当其他关系类型不适用时，表示两个元素之间存在某种一般性关联。
    * 含义: A 与 B 相关。
    * 示例: `DataObject("用户信息")` --RELATES_TO--> `DataObject("地址信息")`

## 对话上下文 (由 DPSS 实际提供):
```json
{{ DIALOGUE_CONTEXT_JSON_PLACEHOLDER }}
```

## 用户当前发言 (源自 RawMessage 的核心内容，需要您分析):
发言者 (User ID): {{ CURRENT_USER_ID_PLACEHOLDER }}
发言内容: {{ CURRENT_USER_UTTERANCE_PLACEHOLDER }}
(原始消息 ID，用于填充 original_message_ref: {{ RAW_MESSAGE_ID_PLACEHOLDER }})
(频道 ID，用于填充 channel_id: {{ CHANNEL_ID_PLACEHOLDER }})

## 您的分析结果 (严格按照上述 JSON Schema 输出):
```json
{{EXPECTED_JSON_OUTPUT_STARTS_HERE}}
```""" 