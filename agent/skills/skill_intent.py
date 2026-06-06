from langchain_core.prompts import ChatPromptTemplate
from typing import Dict

import json
from utils.logger_tool import get_logger

from models.factor import chat_model

log = get_logger(__name__)


class IntentClassifier:
    def __init__(self):
        self.model = chat_model
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的旅行助手意图分类专家。
请分析用户输入，判断其真实意图，并返回最匹配的技能类别。

可用的技能类别：
{skill_descriptions}
⚠️ 严格约束：
1. "intent" 字段**必须**是上述列表中某个技能的名称（例如：plan, weather, hotel），严禁使用中文或其他别名。
请只返回 JSON 格式的结果，不要包含其他文字：
{{
    "intent": "技能名称",
    "confidence": 0.0-1.0之间的置信度,
    "reasoning": "简短的推理说明"
}}"""),
            ("user", "{query}")
        ])

    async def classify(self, query: str, available_skills: Dict[str, str]) -> Dict:
        """
        分类用户意图

        Args:
            query: 用户输入
            available_skills: {skill_name: skill_description} 字典

        Returns:
            包含 intent, confidence, reasoning 的字典
        """
        try:
            # 构建技能描述文本
            skill_desc_text = "\n".join([
                f"- {name}: {desc}"
                for name, desc in available_skills.items()
            ])

            chain = self.prompt | self.model
            response = await chain.ainvoke({
                "query": query,
                "skill_descriptions": skill_desc_text
            })
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            result = json.loads(content)
            log.info(f"[IntentClassifier] 查询: {query[:50]}...")
            log.info(f"[IntentClassifier] 意图: {result.get('intent')}, "
                     f"置信度: {result.get('confidence')}")

            return result

        except Exception as e:
            log.error(f"[IntentClassifier] 分类失败: {e}")
            # 出错时返回默认结果
            return {
                "intent": "plan",
                "confidence": 0.5,
                "reasoning": f"分类出错，使用默认规划技能: {str(e)}"
            }


intent_classifier = IntentClassifier()
