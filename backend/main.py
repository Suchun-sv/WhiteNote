import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.papers import router as papers_router
from api.routes.collections import router as collections_router
from src.database.db.models import Base
from src.database.db.session import engine


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


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
