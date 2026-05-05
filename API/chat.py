from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import os

from agent.main_agent.MainAgent import MainAgent
from utils.logger_tool import get_logger

router = APIRouter(prefix="/api", tags=["AI对话服务"])
log = get_logger(__name__)

main_agent = MainAgent()

# API Key 验证（从环境变量读取）
API_KEY = os.getenv("AI_SERVICE_API_KEY", "your-secret-key")


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """验证 API Key"""
    #if x_api_key != API_KEY:
    #    log.warning(f"[API认证] 无效的 API Key: {x_api_key[:10]}...")
    #    raise HTTPException(status_code=401, detail="无效的 API Key")
    return True


class ChatRequest(BaseModel):
    """对话请求（Java 调用）"""
    query: str = Field(..., description="用户问题", min_length=1, max_length=2000)
    session_id: str = Field(default="default", description="会话ID（由 Java 生成）")
    user_id: str = Field(default="default", description="用户ID")
    enable_stream: bool = Field(default=False, description="是否启用流式输出")


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
    try:
        log.info(f"[Chat API] Java调用: user_id={request.user_id}, session_id={request.session_id}")
        log.info(f"[Chat API] 用户问题: {request.query}")

        # 调用 MainAgent 获取完整响应
        full_response = ""
        async for chunk in main_agent.get_stream(
                query=request.query,
                session_id=request.session_id,
                user_id=request.user_id
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

    async def event_generator():
        try:
            async for chunk in main_agent.get_stream(
                    query=request.query,
                    session_id=request.session_id,
                    user_id=request.user_id
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
                user_id=request.user_id
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
