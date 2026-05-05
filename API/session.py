from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

from agent.memory.SessionMemory import SessionMemory
from utils.logger_tool import get_logger

router = APIRouter(prefix="/session", tags=["会话管理"])
log = get_logger(__name__)

session_memory = SessionMemory()


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    user_id: str = Field(..., description="用户ID")
    session_name: Optional[str] = Field(default=None, description="会话名称")


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    success: bool
    session_id: str
    session_name: str
    created_at: str


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    session_name: str
    user_id: str
    message_count: int
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    """会话列表响应"""
    success: bool
    sessions: List[SessionInfo]
    total: int


@router.post("/create", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """创建新会话"""
    session_id = f"{request.user_id}_{uuid.uuid4().hex[:8]}"
    session_name = request.session_name or f"会话_{datetime.now().strftime('%Y%m%d_%H%M')}"

    log.info(f"[Session API] 创建会话: {session_id}, 用户: {request.user_id}")

    return CreateSessionResponse(
        success=True,
        session_id=session_id,
        session_name=session_name,
        created_at=datetime.now().isoformat()
    )


@router.get("/list/{user_id}", response_model=SessionListResponse)
async def list_sessions(user_id: str):
    """获取用户的会话列表"""
    try:
        sessions = session_memory.get_user_sessions(user_id)

        session_infos = []
        for session in sessions:
            session_infos.append(SessionInfo(
                session_id=session["session_id"],
                session_name=session.get("session_name", "未命名会话"),
                user_id=user_id,
                message_count=session.get("message_count", 0),
                created_at=session.get("created_at", ""),
                updated_at=session.get("updated_at", "")
            ))

        return SessionListResponse(
            success=True,
            sessions=session_infos,
            total=len(session_infos)
        )

    except Exception as e:
        log.error(f"[Session API] 获取会话列表失败: {str(e)}")
        return SessionListResponse(success=False, sessions=[], total=0)


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        session_memory.delete_session(session_id)
        log.info(f"[Session API] 删除会话: {session_id}")
        return {"success": True, "message": "会话已删除"}
    except Exception as e:
        log.error(f"[Session API] 删除会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
