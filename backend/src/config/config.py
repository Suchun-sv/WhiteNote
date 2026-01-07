from __future__ import annotations
from typing import Any, Dict, Callable, List
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


class QdrantConfig(BaseModel):
    host: Annotated[str, Field(default="localhost")]
    port: Annotated[int, Field(default=6333)]
    collection: Annotated[str, Field(default="lavender_papers")]


class Settings(BaseSettings):
    source_list: Annotated[List[str], Field(default=["arXiv"])]
    keywords: Annotated[List[str], Field(default=["vector database", "RAG", "agent"])]

    paper_save_path: Annotated[str, Field(default="cache/papers.json")]
    embedding_save_path: Annotated[str, Field(default="cache/embeddings/")] 

    chat_litellm: ChatLiteLLMConfig = Field(default_factory=ChatLiteLLMConfig)
    qdrant_database: QdrantConfig = Field(default_factory=QdrantConfig)

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