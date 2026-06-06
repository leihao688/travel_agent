"""
Skill 注册中心 - 定义各种独立技能
每个 Skill = 专属提示词 + 专属工具集 + 触发条件
"""
import time
from typing import List, Optional, Dict
from langchain_core.tools import BaseTool

from utils.logger_tool import get_logger

log = get_logger(__name__)


class Skill:
    """独立技能单元"""

    def __init__(
            self,
            name: str,
            triggers: List[str],
            prompt: str,
            tools: List[BaseTool],
            description: str = "",
            priority: int = 0,
            examples: List[str] = None
    ):
        self.name = name
        self.triggers = triggers  # 支持多个触发关键词
        self.prompt = prompt
        self.tools = tools
        self.description = description
        self.priority = priority
        self.examples = examples or []
        self.match_count = 0  # 匹配次数
        self.success_count = 0  # 成功执行次数
        self.last_used = None  # 最后使用时间

    def match(self, query: str) -> bool:
        """判断用户输入是否匹配此 Skill"""
        query_lower = query.lower().strip()
        # 🔥 改进：避免否定句误匹配
        negative_words = ["不想", "不要", "别", "不查", "不订", "不推荐"]
        if any(neg in query_lower for neg in negative_words):
            return False
        return any(trigger.lower() in query_lower for trigger in self.triggers)

    def record_usage(self, success: bool = True):
        """记录使用情况，用于学习优化"""
        self.match_count += 1
        if success:
            self.success_count += 1
        self.last_used = time.time()

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.match_count == 0:
            return 0.0
        return self.success_count / self.match_count

    def to_dict(self) -> Dict:
        """转换为字典，用于意图分类"""
        return {
            "name": self.name,
            "description": self.description,
            "examples": self.examples[:3]  # 只提供前3个示例
        }


class SkillRegistry:
    """Skill 注册中心 - 单例模式"""

    _instance = None
    _skills = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, skill: Skill):
        """注册一个 Skill"""
        self._skills[skill.name] = skill
        log.info(f"[SkillRegistry] 注册技能: {skill.name} - {skill.description}")

    def get_skill(self, name: str) -> Optional[Skill]:
        """根据名称获取 Skill"""
        return self._skills.get(name)

    def match_skill(self, query: str) -> Optional[Skill]:
        """根据用户输入匹配最合适的 Skill（按优先级排序）"""
        matched_skills = []
        for skill in self._skills.values():
            if skill.match(query):
                matched_skills.append(skill)

        if not matched_skills:
            return None

        # 🔥 核心修复：返回优先级最高的 skill
        matched_skills.sort(key=lambda s: s.priority, reverse=True)
        return matched_skills[0]

    def get_all_skills(self) -> dict:
        """获取所有注册的 Skill"""
        return self._skills.copy()

    async def smart_match_skill(self, query: str, intent_classifier) -> Optional[Skill]:
        """
        智能匹配 Skill - 结合传统匹配和 LLM 意图识别

        Args:
            query: 用户输入
            intent_classifier: 意图分类器实例

        Returns:
            匹配的 Skill 或 None
        """
        # 1. 首先尝试传统关键词匹配
        traditional_match = self.match_skill(query)

        # 2. 使用 LLM 进行意图分类
        available_skills = {
            name: skill.description
            for name, skill in self._skills.items()
        }

        intent_result = await intent_classifier.classify(query, available_skills)
        intent_name = intent_result.get("intent")
        confidence = intent_result.get("confidence", 0)

        # 3. 决策逻辑
        llm_match = self._skills.get(intent_name)

        if traditional_match and llm_match:
            # 两者都有匹配结果
            if traditional_match.name == llm_match.name:
                # 一致，直接使用
                log.info(f"[SkillRegistry] 传统+LLM 一致匹配: {traditional_match.name}")
                return traditional_match
            else:
                # 不一致，根据置信度决定
                if confidence > 0.8:
                    log.info(f"[SkillRegistry] LLM 高置信度覆盖: {llm_match.name} (置信度: {confidence})")
                    return llm_match
                else:
                    log.info(f"[SkillRegistry] 使用传统匹配: {traditional_match.name}")
                    return traditional_match
        elif llm_match and confidence > 0.7:
            # 只有 LLM 匹配且置信度高
            log.info(f"[SkillRegistry] LLM 单独匹配: {llm_match.name} (置信度: {confidence})")
            return llm_match
        elif traditional_match:
            # 只有传统匹配
            log.info(f"[SkillRegistry] 传统匹配: {traditional_match.name}")
            return traditional_match
        else:
            # 都没有匹配
            log.info(f"[SkillRegistry] 无匹配技能")
            return None

    def get_skill_stats(self) -> Dict:
        """获取所有技能的使用统计"""
        stats = {}
        for name, skill in self._skills.items():
            stats[name] = {
                "match_count": skill.match_count,
                "success_count": skill.success_count,
                "success_rate": skill.get_success_rate(),
                "last_used": skill.last_used
            }
        return stats


# 全局单例
skill_registry = SkillRegistry()
