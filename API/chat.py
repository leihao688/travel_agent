from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import requests
from agent.main_agent.MainAgent import MainAgent
from utils.logger_tool import get_logger
from config import settings

router = APIRouter(prefix="/api", tags=["AI对话服务"])
log = get_logger(__name__)


def get_main_agent():
    """获取 MainAgent 实例（每次请求创建新实例）"""
    return MainAgent()


# API Key 验证（从环境变量读取）
API_KEY = os.getenv("AI_SERVICE_API_KEY", "your-secret-key")


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """验证 API Key"""
    # if x_api_key != API_KEY:
    #    log.warning(f"[API认证] 无效的 API Key: {x_api_key[:10]}...")
    #    raise HTTPException(status_code=401, detail="无效的 API Key")
    return True


class UserProfile(BaseModel):
    """用户画像（由 Java 注入）"""
    nickname: str = Field(default="", description="用户昵称")
    level: int = Field(default=1, description="用户等级 1-5")
    bio: str = Field(default="", description="个人简介")


class ChatRequest(BaseModel):
    """对话请求（Java 调用）"""
    query: str = Field(..., description="用户问题", min_length=1, max_length=2000)
    session_id: str = Field(default="default", description="会话ID（由 Java 生成）")
    user_id: str = Field(default="default", description="用户ID")
    enable_stream: bool = Field(default=False, description="是否启用流式输出")
    user_profile: Optional[UserProfile] = Field(default=None, description="用户画像（由 Java 注入）")


class ImageRequest(BaseModel):
    """图片搜索请求模型"""
    query: str = Field(..., description="搜索关键词")
    count: int = Field(default=1, description="图片数量")


class MessageItem(BaseModel):
    """消息项"""
    role: str = Field(description="角色：user/assistant")
    content: str = Field(description="内容")


class ChatResponse(BaseModel):
    """统一响应格式（面向 Java）"""
    code: int = Field(description="状态码：200成功，500失败")
    message: str = Field(description="提示信息")
    data: dict = Field(description="响应数据")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, _: bool = Depends(verify_api_key)):
    """
    对话接口（供 Java 后端调用）

    Java 调用示例：
    POST /api/chat
    Headers: X-API-Key: your-secret-key
    Body: {
        "query": "我想去三亚玩3天",
        "session_id": "session_123",
        "user_id": "user_456"
    }
    """
    # 🔥 修改：为每个请求创建独立的 MainAgent 实例
    main_agent = get_main_agent()
    try:
        log.info(f"[Chat API] Java调用: user_id={request.user_id}, session_id={request.session_id}")
        log.info(f"[Chat API] 用户问题: {request.query}")

        # 调用 MainAgent 获取完整响应
        full_response = ""
        async for chunk in main_agent.get_stream(
                query=request.query,
                session_id=request.session_id,
                user_id=request.user_id,
                user_profile=request.user_profile
        ):
            full_response += chunk

        log.info(f"[Chat API] 响应成功，内容长度: {len(full_response)}")

        return ChatResponse(
            code=200,
            message="success",
            data={
                "content": full_response,
                "session_id": request.session_id,
                "user_id": request.user_id
            }
        )

    except Exception as e:
        log.error(f"[Chat API] 处理异常: {str(e)}", exc_info=True)
        return ChatResponse(
            code=500,
            message=f"AI服务异常: {str(e)}",
            data={
                "content": "",
                "session_id": request.session_id,
                "error": str(e)
            }
        )


@router.post("/chat/stream", response_model=ChatResponse)
async def chat_stream(request: ChatRequest, _: bool = Depends(verify_api_key)):
    """
    流式对话接口（SSE，供前端直接调用或 Java 转发）
    """
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    # 🔥 修改：为每个请求创建独立的 MainAgent 实例
    main_agent = get_main_agent()

    async def event_generator():
        try:
            async for chunk in main_agent.get_stream(
                    query=request.query,
                    session_id=request.session_id,
                    user_id=request.user_id,
                    user_profile=request.user_profile
            ):
                data = json.dumps({
                    "code": 200,
                    "data": {"content": chunk, "done": False}
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.01)

            done_data = json.dumps({
                "code": 200,
                "data": {"content": "", "done": True, "session_id": request.session_id}
            }, ensure_ascii=False)
            yield f"data: {done_data}\n\n"
        except asyncio.CancelledError:
            # 🔥 新增：处理客户端断开连接的情况
            log.warning(f"[Chat Stream] 客户端断开连接: session_id={request.session_id}")
            raise
        except Exception as e:
            log.error(f"[Chat Stream] 异常: {str(e)}")
            error_data = json.dumps({
                "code": 500,
                "data": {"error": str(e), "done": True}
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.post("/images/search")
async def search_images(request: ImageRequest):
    """图片搜索接口（供前端直接调用）"""
    if not settings.unsplash_access_key:
        log.error("[图片搜索] Unsplash API Key 未配置")
        return {"code": 500, "message": "图片服务未配置", "data": None}

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": request.query,
        "client_id": settings.unsplash_access_key,
        "count": min(request.count, 10),
        "orientation": "landscape"
    }

    try:
        log.info(f"[图片搜索] 查询: {request.query}, 数量: {request.count}")
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = [{
                "url": item.get("urls", {}).get("regular"),
                "alt": item.get("alt_description", ""),
                "author": item.get("user", {}).get("name")
            } for item in data.get("results", [])]

            log.info(f"[图片搜索] 成功获取 {len(results)} 张图片")
            return {"code": 200, "message": "success", "data": results}
        else:
            log.error(f"[图片搜索] API 请求失败: {response.status_code}")
            return {"code": 500, "message": f"图片服务请求失败: {response.status_code}", "data": None}
    except Exception as e:
        log.error(f"[图片搜索] 异常: {str(e)}", exc_info=True)
        return {"code": 500, "message": f"图片搜索异常: {str(e)}", "data": None}


class BatchChatRequest(BaseModel):
    """批量对话请求（可选）"""
    messages: List[MessageItem] = Field(..., description="消息列表")
    session_id: str = Field(default="default")
    user_id: str = Field(default="default")


@router.post("/chat/batch", response_model=ChatResponse)
async def batch_chat(request: BatchChatRequest, _: bool = Header(verify_api_key)):
    """
    批量对话接口（传入完整消息历史）

    适用于 Java 需要传递完整对话上下文的场景
    """
    main_agent = get_main_agent()
    try:
        # 将消息列表转换为 query
        last_user_message = next(
            (msg.content for msg in reversed(request.messages) if msg.role == "user"),
            ""
        )

        if not last_user_message:
            return ChatResponse(
                code=400,
                message="缺少用户消息",
                data={"content": "", "session_id": request.session_id}
            )

        full_response = ""
        async for chunk in main_agent.get_stream(
                query=last_user_message,
                session_id=request.session_id,
                user_id=request.user_id,
                user_profile=None
        ):
            full_response += chunk

        return ChatResponse(
            code=200,
            message="success",
            data={
                "content": full_response,
                "session_id": request.session_id
            }
        )

    except Exception as e:
        log.error(f"[Batch Chat] 异常: {str(e)}")
        return ChatResponse(
            code=500,
            message=str(e),
            data={"content": "", "session_id": request.session_id}
        )
