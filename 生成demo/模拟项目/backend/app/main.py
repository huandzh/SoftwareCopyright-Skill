"""FastAPI 应用入口：注册路由、中间件与启动钩子。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import assets, auth, billing, chat, projects
from app.core.config import settings
from app.core.database import dispose_engine, init_engine

logger = logging.getLogger("studioagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库连接池，退出时释放连接。"""
    init_engine()
    logger.info("数据库连接池已初始化：%s", settings.database_url.split("@")[-1])
    try:
        yield
    finally:
        await dispose_engine()
        logger.info("数据库连接池已释放")


app = FastAPI(
    title="StudioAgent AI 视频制片平台",
    version="0.1.0",
    description="多智能体协作的 AI 视频制作服务",
    lifespan=lifespan,
)

# 允许本地开发地址跨域访问；生产环境通过网关收敛来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["项目"])
app.include_router(chat.router, prefix="/api/v1/projects", tags=["制片对话"])
app.include_router(assets.router, prefix="/api/v1", tags=["素材"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["计费"])


@app.get("/health", tags=["运维"])
async def health() -> dict[str, str]:
    """健康检查：网关据此判断实例是否可用。"""
    return {"status": "ok", "version": app.version}
