import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routes.papers import router as papers_router
from api.routes.collections import router as collections_router
from api.routes.chat import router as chat_router
from src.database.db.models import Base
from src.database.db.session import engine
from src.config import Config
from src.service.image_generation_service import get_existing_comic_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create any missing tables (e.g. folders) on startup
    Base.metadata.create_all(bind=engine)
    yield


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


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/papers/{paper_id}/comic")
async def get_comic(paper_id: str):
    """获取论文漫画图片"""
    from src.service.image_generation_service import get_comic_path
    
    # 获取漫画路径（可能是相对路径）
    comic_path = get_comic_path(paper_id)
    jpg_path = comic_path.with_suffix(".jpg")
    
    # 确保路径是绝对路径
    base_path = Path(Config.image_save_path)
    if not base_path.is_absolute():
        # 如果配置路径是相对的，基于项目根目录（backend/）
        base_path = Path(__file__).parent / base_path
    
    # 检查 PNG 和 JPG 两种格式
    png_full_path = base_path / comic_path.name
    jpg_full_path = base_path / jpg_path.name
    
    final_path = None
    if png_full_path.exists():
        final_path = png_full_path
    elif jpg_full_path.exists():
        final_path = jpg_full_path
    
    if not final_path:
        raise HTTPException(
            status_code=404,
            detail=f"Comic not found for paper {paper_id}. Checked paths:\n- {png_full_path}\n- {jpg_full_path}"
        )
    
    return FileResponse(
        str(final_path),
        media_type="image/png" if final_path.suffix == ".png" else "image/jpeg",
    )
