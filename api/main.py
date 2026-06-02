"""
main.py - Memory Palace API Server

FastAPI 应用，监听本地 127.0.0.1。

启动方式:
  python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

环境变量:
  MEMORY_PALACE_API_TOKEN - API 访问令牌（可选，生产环境建议设置）
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 路由
from .routes import capture, inbox, search, ask, brief, health, jobs, metrics

app = FastAPI(
    title="Memory Palace API",
    description="本地知识操作系统的统一 API 接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置（仅允许本地访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"],
)

# 注册路由
app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(metrics.router)
app.include_router(capture.router)
app.include_router(inbox.router)
app.include_router(search.router)
app.include_router(ask.router)
app.include_router(brief.router)


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "Memory Palace API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.on_event("startup")
async def startup_event():
    """启动时检查"""
    print("Memory Palace API 启动中...")
    print(f"项目目录: {os.environ.get('MEMORY_PALACE_PROJECT_ROOT', '未设置')}")
    print(f"API Token: {'已配置' if os.environ.get('MEMORY_PALACE_API_TOKEN') else '未配置（开发模式）'}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )