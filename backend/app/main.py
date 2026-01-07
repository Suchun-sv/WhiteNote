"""
FastAPI Application Entry Point

Responsibilities:
1. Create FastAPI application instance
2. Register all API routers
3. Configure middleware (CORS, logging, etc.)
4. Setup startup/shutdown events (database connections, etc.)

Run:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager
    
    Handles startup and shutdown events:
    - Startup: Initialize database connections, load models, etc.
    - Shutdown: Close connections, cleanup resources
    """
    # === Startup ===
    print("🚀 Starting LavenderSentinel API...")
    print(f"   LLM Model: {settings.llm.model}")
    print(f"   Embedding Model: {settings.embedding.model}")

    from app.db.database import get_connections
    connections = get_connections()

    yield  # Application runs here
    
    # === Shutdown ===
    print("👋 Shutting down LavenderSentinel API...")
    from app.db.database import close_db
    await close_db()
    # TODO: Cleanup resources


app = FastAPI(
    title="LavenderSentinel API",
    description="Academic literature automation system - collect, index, summarize, and chat with research papers",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Health Check Routes ==============

@app.get("/")
async def root():
    """Root endpoint - basic info"""
    return {
        "name": "LavenderSentinel API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)"""
    return {
        "llm": {
            "model": settings.llm.model,
            "temperature": settings.llm.temperature,
            "max_tokens": settings.llm.max_tokens,
        },
        "embedding": {
            "model": settings.embedding.model,
            "dimension": settings.embedding.dimension,
            "use_litellm": settings.embedding.use_litellm,
        },
        "qdrant": {
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
            "collection": settings.qdrant_collection,
        },
    }


# ============== Test Routes ==============

@app.get("/test/llm")
async def test_llm(prompt: str = "Say hello in one sentence."):
    """
    Test LLM connection
    
    Args:
        prompt: Test prompt to send to LLM
    
    Returns:
        LLM response
    """
    from litellm import completion
    
    try:
        response = completion(
            messages=[{"role": "user", "content": prompt}],
            **settings.llm.to_litellm_params()
        )
        return {
            "status": "success",
            "model": settings.llm.model,
            "response": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "model": settings.llm.model,
            "error": str(e),
        }


# TODO: Add routers
# from app.routers import papers, search, chat
# app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
# app.include_router(search.router, prefix="/api/search", tags=["search"])
# app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
