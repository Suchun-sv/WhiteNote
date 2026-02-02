import io
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from api.routes.papers import router as papers_router
from api.routes.collections import router as collections_router
from api.routes.chat import router as chat_router
from api.routes.feeds import router as feeds_router
from api.routes.tasks import router as tasks_router
from src.config import Config
from src.database.db.models import Base
from src.database.db.session import engine
from src.service.storage_service import get_storage
from src.scheduler.scheduler_service import SchedulerService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create any missing tables (e.g. folders) on startup
    Base.metadata.create_all(bind=engine)
    # Start scheduler when enabled (for cron + task API)
    scheduler = None
    if Config.scheduler.enabled:
        scheduler = SchedulerService()
        scheduler.start()
    app.state.scheduler = scheduler
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(title="WhiteNote API", lifespan=lifespan)

# CORS 配置：开发环境允许所有来源，生产环境限制为指定来源
is_dev = os.getenv("ENV", "development") == "development"
cors_origins = (
    ["*"]  # 开发环境允许所有来源
    if is_dev
    else [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True if not is_dev else False,  # 使用 "*" 时不能设置 credentials=True
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(papers_router)
app.include_router(collections_router)
app.include_router(chat_router)
app.include_router(feeds_router)
app.include_router(tasks_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/papers/{paper_id}/comic")
async def get_comic(paper_id: str):
    """获取论文漫画图片（从 MinIO 流式返回）"""
    storage = get_storage()
    try:
        image_bytes, content_type = storage.get_comic(paper_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Comic not found for paper {paper_id}",
        )
    return StreamingResponse(io.BytesIO(image_bytes), media_type=content_type)
