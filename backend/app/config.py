"""
Application Configuration Management

Uses Pydantic Settings to load configuration from environment variables.

Configuration includes:
- Database connection (DATABASE_URL)
- Redis connection (REDIS_URL)
- Qdrant vector database (QDRANT_HOST, QDRANT_PORT)
- LLM settings (via LiteLLM - supports OpenAI, Ollama, Anthropic, etc.)
- Embedding settings
- CocoIndex settings

Usage:
    from app.config import settings
    print(settings.llm.model)
    
    # Call LLM
    from litellm import completion
    response = completion(messages=[...], **settings.llm.to_litellm_params())
"""

from typing import Optional, Tuple, Type

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings, 
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)


class LLMSettings(BaseModel):
    """
    LLM Configuration using LiteLLM
    
    LiteLLM model format: "provider/model" or just "model" for OpenAI
    
    Examples:
    - OpenAI: "gpt-4o-mini" or "openai/gpt-4o-mini"
    - Ollama: "ollama/llama3.2"
    - Anthropic: "anthropic/claude-3-5-sonnet-20241022"
    - Azure: "azure/gpt-4"
    - Groq: "groq/llama3-70b-8192"
    - OneAPI/Custom: "openai/gpt-4o" + custom api_base
    
    See all supported models: https://docs.litellm.ai/docs/providers
    """
    
    model: str = Field(
        default="gpt-4o-mini",
        description="LiteLLM model identifier (e.g., gpt-4o-mini, ollama/llama3.2, anthropic/claude-3-5-sonnet)"
    )
    
    api_key: Optional[str] = Field(
        default=None,
        description="API key (not required for Ollama)"
    )
    
    api_base: Optional[str] = Field(
        default=None,
        description="Custom API endpoint (for OneAPI, Ollama, self-hosted, etc.)"
    )
    
    # Advanced options
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2000, ge=1)
    timeout: int = Field(default=60, description="Request timeout in seconds")
    
    def to_litellm_params(self) -> dict:
        """
        Convert to LiteLLM completion() parameters
        
        Usage:
            from litellm import completion
            response = completion(messages=[...], **settings.llm.to_litellm_params())
        """
        params = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        if self.api_base:
            params["api_base"] = self.api_base
        
        return params


class EmbeddingSettings(BaseModel):
    """
    Embedding Model Configuration
    
    LiteLLM also supports embeddings with similar format:
    - Local: Use sentence-transformers directly
    - OpenAI: "text-embedding-3-small"
    - Ollama: "ollama/nomic-embed-text"
    
    See: https://docs.litellm.ai/docs/embedding/supported_embedding
    """
    
    model: str = Field(
        default="BAAI/bge-base-en-v1.5",
        description="Embedding model (local sentence-transformers or LiteLLM format)"
    )
    
    api_base: Optional[str] = Field(
        default=None,
        description="Custom API endpoint"
    )
    
    api_key: Optional[str] = Field(
        default=None,
        description="API key (if using remote embedding API)"
    )
    
    dimension: int = Field(
        default=768,
        description="Embedding vector dimension"
    )
    
    use_litellm: bool = Field(
        default=False,
        description="Use LiteLLM for embeddings (vs local sentence-transformers)"
    )
    
    def to_litellm_params(self) -> dict:
        """Convert to LiteLLM embedding() parameters"""
        params = {"model": self.model}
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        if self.api_base:
            params["api_base"] = self.api_base
        
        return params


class Settings(BaseSettings):
    """Main configuration class"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Support nested config, e.g., LLM__MODEL
        yaml_file="settings.yaml",  # YAML 配置文件
        extra="ignore",
    )
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/lavender_sentinel"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0"
    )
    
    # Qdrant vector database
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="paper_embeddings")
    
    # LLM configuration (nested)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    
    # Embedding configuration (nested)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    
    # CocoIndex
    cocoindex_database_url: Optional[str] = Field(default=None)
    
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        配置加载优先级 (从高到低):
        1. init_settings - 初始化时传入的参数
        2. env_settings - 环境变量
        3. dotenv_settings - .env 文件
        4. yaml_settings - settings.yaml 文件
        5. file_secret_settings - secrets 文件
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
    
    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL (for CocoIndex)"""
        return self.cocoindex_database_url or str(self.database_url).replace("+asyncpg", "")


# Global singleton
settings = Settings()
