from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from API import chat, health
from config import Settings, print_config, validate_config
from fastapi import FastAPI

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("\n" + "=" * 60)
    print(f"🤖 Travel AI Service v{settings.app_version}")
    print("=" * 60)

    print_config()

    try:
        validate_config()
        print("\n✅ 配置验证通过")
    except ValueError as e:
        print(f"\n❌ 配置验证失败:\n{e}")
        raise

    print(f"\n📡 服务地址: http://{settings.host}:{settings.port}")
    print(f" API文档: http://{settings.host}:{settings.port}/docs")
    print("=" * 60 + "\n")

    yield

    print("\n👋 AI服务正在关闭...")


app = FastAPI(
    title="Travel AI Service",
    description="智能旅行助手 - AI服务（供 Java 后端调用）",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "service": "Travel AI Agent",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "API.main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )
