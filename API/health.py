from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
import os
import psutil

router = APIRouter(prefix="/api", tags=["服务监控"])

API_KEY = os.getenv("AI_SERVICE_API_KEY", "your-secret-key")


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    uptime: float
    memory_usage: dict


@router.get("/health", response_model=HealthResponse)
async def health_check(_: bool = Header(verify_api_key)):
    """健康检查接口（供 Java 定时调用）"""
    import time

    process = psutil.Process(os.getpid())
    memory = process.memory_info()

    return HealthResponse(
        status="healthy",
        service="travel-ai-agent",
        version="1.0.0",
        uptime=time.time() - process.create_time(),
        memory_usage={
            "rss_mb": round(memory.rss / 1024 / 1024, 2),
            "vms_mb": round(memory.vms / 1024 / 1024, 2)
        }
    )
