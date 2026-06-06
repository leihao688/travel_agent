from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter(prefix="/trip", tags=["行程管理"])


class TripPlanRequest(BaseModel):
    """行程规划请求"""
    city: str = Field(..., description="目的地城市")
    days: int = Field(..., description="旅行天数", ge=1, le=15)
    people_count: int = Field(default=1, description="出行人数", ge=1)
    budget_level: str = Field(default="中等", description="预算：穷游/经济/中等/豪华")
    preferences: List[str] = Field(default_factory=list, description="偏好标签")


class AttractionInfo(BaseModel):
    """景点信息"""
    name: str
    location: str
    duration: str
    description: str


class DailyPlan(BaseModel):
    """每日行程"""
    day: int
    date: str
    weather: str
    attractions: List[AttractionInfo]
    notes: str


class TripPlanResponse(BaseModel):
    """行程规划响应"""
    success: bool
    city: str
    days: int
    daily_plans: List[DailyPlan]
    recommended_hotels: List[str]
    total_budget_estimate: str


@router.post("/plan", response_model=TripPlanResponse)
async def plan_trip(request: TripPlanRequest):
    """
    行程规划接口（预留）

    这个接口可以用于直接生成行程，不经过对话
    """
    return TripPlanResponse(
        success=True,
        city=request.city,
        days=request.days,
        daily_plans=[],
        recommended_hotels=[],
        total_budget_estimate="待计算"
    )
