"""数据模型定义"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator
from datetime import date


class TripIntent(BaseModel):
    """MainAgent 意图提取模型"""
    city: Optional[str] = Field(default=None, description="目的地城市")
    start_date: Optional[str] = Field(default=None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="结束日期 YYYY-MM-DD")
    travel_days: Optional[int] = Field(default=None, description="旅行天数")
    # 🔥 新增字段
    people_count: int = Field(default=1, description="出行人数", ge=1)
    budget_level: str = Field(default="中等", description="预算水平：穷游/经济/中等/豪华")
    preferences: List[str] = Field(default_factory=list, description="偏好标签，如：历史、美食、自然风光")


class FormatterValidation(BaseModel):
    """FormatterAgent 输出校验模型"""
    is_valid: bool = Field(default=False, description="格式是否合格")
    error_type: Optional[str] = Field(default=None, description="错误类型：missing_title/too_short/missing_section")
    error_detail: Optional[str] = Field(default=None, description="错误详情")
    missing_sections: List[str] = Field(default_factory=list, description="缺失的关键章节")

    @classmethod
    def validate_markdown(cls, markdown_text: str) -> "FormatterValidation":
        """校验 Markdown 输出格式"""
        import re

        # weather_agent_prompt.txt. 检查标题
        if not re.search(r'^#{weather_agent_prompt.txt,3}\s', markdown_text, re.MULTILINE):
            return cls(
                is_valid=False,
                error_type="missing_title",
                error_detail="缺少 Markdown 标题（# 或 ##）"
            )

        # 2. 检查内容长度
        if len(markdown_text.strip()) < 100:
            return cls(
                is_valid=False,
                error_type="too_short",
                error_detail="输出内容过短（<100 字符），可能未完整生成"
            )

        # 3. 通过校验
        return cls(is_valid=True)


class WeatherQuerySchema(BaseModel):
    """天气查询工具参数"""
    city: str = Field(description="城市名，必填")
    date: Optional[str] = Field(default=None, description="可选日期")


class AttractionSearchSchema(BaseModel):
    """景点搜索工具参数"""
    city: str = Field(description="城市名，必填")
    days: int = Field(description="行程天数，从用户 query 中提取")


class HotelRecommendSchema(BaseModel):
    """酒店推荐工具参数"""
    city: str = Field(description="城市名，必填")
    budget: str = Field(default="中等", description="预算水平：穷游/经济/中等/豪华")


class IntentReflection(BaseModel):
    """意图提取的自我反思模型"""
    is_complete: bool = Field(description="参数是否完整，足以开始规划行程")
    missing_info: List[str] = Field(default_factory=list, description="缺失的关键信息列表，如：城市、天数")
    final_intent: Optional[TripIntent] = Field(default=None, description="如果完整，则填入提取的意图；否则为 null")
    question_for_user: Optional[str] = Field(default=None, description="如果需要追问，这里填写给用户的问句")


class RoutePlanSchema(BaseModel):
    """路线规划工具参数"""
    city: str = Field(description="城市名")
    days: int = Field(description="天数")
    weather: str = Field(description="天气信息")
    attractions: str = Field(description="景点列表")
    hotels: str = Field(description="酒店列表")
    people_count: int = Field(default=1, description="人数")
    budget: str = Field(default="中等", description="预算水平")


# 🔥 新增：RAG 知识检索 Schema
class RagQuerySchema(BaseModel):
    query: str = Field(description="需要检索的知识关键词，例如：故宫博物院门票价格")


class LogicReviewSchema(BaseModel):
    """逻辑评审工具参数"""
    content: str = Field(description="待评审的行程方案内容")
    user_query: str = Field(default="", description="用户的原始旅行需求（如果不传则使用系统当前上下文）")


class ContentGuardSchema(BaseModel):
    """逻辑评审工具参数"""
    content: str = Field(description="通过逻辑检验后的行程方案内容")
