from __future__ import annotations
from typing import Any, Dict, Callable, List, Optional
from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

class ChatLiteLLMConfig(BaseModel):
    model: Annotated[str, Field(default="gpt-4o-mini")]
    api_key: Annotated[str, Field(default="sk-proj-xxxx")]
    api_base: Annotated[str, Field(default="https://api.openai.com/v1")]

class CocoIndexConfig(BaseModel):
    chunk_size: Annotated[int, Field(default=800)]
    embedding_model: Annotated[str, Field(default="openai/text-embedding-3-small")]
    embedding_api_key: Annotated[str, Field(default="sk-proj-xxxx")]
    embedding_api_base: Annotated[str, Field(default="https://api.openai.com/v1")]

class SchedulerConfig(BaseModel):
    enabled: Annotated[bool, Field(default=True)]
    timezone: Annotated[str, Field(default="Asia/Shanghai")]
    daily_arxiv_job: Annotated[str, Field(default="0 */1 * * *")]

class QdrantConfig(BaseModel):
    host: Annotated[str, Field(default="localhost")]
    port: Annotated[int, Field(default=6333)]
    collection: Annotated[str, Field(default="lavender_papers")]

class PdfDownloadConfig(BaseModel):
    max_concurrency: Annotated[int, Field(default=8)]
    timeout: Annotated[int, Field(default=30)]
    retries: Annotated[int, Field(default=3)]


class FavoriteConfig(BaseModel):
    """收藏功能配置"""
    auto_download_pdf: Annotated[bool, Field(default=True)]  # 收藏后自动下载PDF
    auto_generate_summary: Annotated[bool, Field(default=True)]  # 收藏后自动生成全文总结


class RedisConfig(BaseModel):
    """Redis 配置（用于 RQ 任务队列）"""
    host: Annotated[str, Field(default="localhost")]
    port: Annotated[int, Field(default=6379)]
    db: Annotated[int, Field(default=0)]
    password: Annotated[Optional[str], Field(default=None)]


class Settings(BaseSettings):
    language: Annotated[str, Field(default="en")]
    source_list: Annotated[List[str], Field(default=["arXiv"])]
    keywords: Annotated[List[str], Field(default=["vector database", "RAG", "agent"])]

    auto_ai_title: Annotated[bool, Field(default=True)]
    auto_ai_abstract: Annotated[bool, Field(default=True)]

    database_url: Annotated[str, Field(default="postgresql://postgres:postgres@localhost:5432/lavender_sentinel")]

    paper_save_path: Annotated[str, Field(default="cache/papers.json")]
    pdf_save_path: Annotated[str, Field(default="cache/pdfs/")]
    pdf_download: PdfDownloadConfig = Field(default_factory=PdfDownloadConfig)
    embedding_save_path: Annotated[str, Field(default="cache/embeddings/")] 

    chat_litellm: ChatLiteLLMConfig = Field(default_factory=ChatLiteLLMConfig)
    cocoindex: CocoIndexConfig = Field(default_factory=CocoIndexConfig)
    qdrant_database: QdrantConfig = Field(default_factory=QdrantConfig)

    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    favorite: FavoriteConfig = Field(default_factory=FavoriteConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,              # 👈 必须有
        init_settings,             # kwargs
        env_settings,              # env vars
        dotenv_settings,           # .env file
        file_secret_settings,      # /secrets/*
    ):
        def yaml_settings() -> Dict[str, Any]:
            path = Path("settings.yaml")
            if not path.exists():
                return {}
            return yaml.safe_load(path.read_text(encoding="utf-8"))

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_settings,
            file_secret_settings,
        )


Config = Settings()