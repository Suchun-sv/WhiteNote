"""
数据库连接管理

职责:
1. 创建数据库连接 (PostgreSQL, Redis, Qdrant)
2. 提供数据库会话
3. 初始化/关闭数据库连接

使用方式:
    # 初始化
    await init_db(settings)
    
    # 使用
    async with get_db_session() as session:
        # 使用 PostgreSQL session
    
    # 关闭
    await close_db()
"""

from typing import TYPE_CHECKING, Optional, AsyncGenerator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import Settings

# 类型检查时导入（避免循环导入和延迟加载）
if TYPE_CHECKING:
    from redis.asyncio import Redis
    from qdrant_client import QdrantClient


# ============================================
# 连接对象容器
# ============================================
@dataclass
class DatabaseConnections:
    """存储所有数据库连接对象"""
    postgres_engine: Optional[AsyncEngine] = None
    postgres_session_factory: Optional[sessionmaker] = None
    redis: Optional["Redis"] = None  # type: ignore
    qdrant: Optional["QdrantClient"] = None  # type: ignore


# 全局连接对象
_connections: DatabaseConnections = DatabaseConnections()


# ============================================
# PostgreSQL
# ============================================
def _create_postgres_engine(database_url: str) -> AsyncEngine:
    """创建 PostgreSQL 异步引擎"""
    # 确保使用异步驱动
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return create_async_engine(
        database_url,
        echo=False,  # 设为 True 可打印 SQL 语句 (调试用)
        pool_size=5,
        max_overflow=10,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取 PostgreSQL 数据库会话 (用于 FastAPI 依赖注入)"""
    if _connections.postgres_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _connections.postgres_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ============================================
# Redis
# ============================================
def _create_redis_client(redis_url: str) -> "Redis":
    """创建 Redis 异步客户端"""
    from redis.asyncio import Redis
    return Redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


# ============================================
# Qdrant
# ============================================
def _create_qdrant_client(host: str, port: int) -> "QdrantClient":
    """创建 Qdrant 客户端"""
    from qdrant_client import QdrantClient
    return QdrantClient(host=host, port=port)


# ============================================
# 初始化 & 关闭
# ============================================
async def init_db(settings: Settings) -> DatabaseConnections:
    """
    初始化所有数据库连接
    
    Args:
        settings: 应用配置
        
    Returns:
        DatabaseConnections: 连接对象容器
    """
    global _connections
    
    # PostgreSQL
    if settings.database_url:
        _connections.postgres_engine = _create_postgres_engine(settings.database_url)
        _connections.postgres_session_factory = sessionmaker(
            bind=_connections.postgres_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        # 测试连接
        async with _connections.postgres_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✓ PostgreSQL connected")
    
    # Redis
    if settings.redis_url:
        _connections.redis = _create_redis_client(settings.redis_url)
        # 测试连接
        await _connections.redis.ping()
        print("✓ Redis connected")
    
    # Qdrant
    if settings.qdrant_host and settings.qdrant_port:
        _connections.qdrant = _create_qdrant_client(
            settings.qdrant_host, 
            settings.qdrant_port
        )
        # 测试连接 (Qdrant 客户端是同步的，但可以用)
        _connections.qdrant.get_collections()
        print("✓ Qdrant connected")
    
    return _connections


async def close_db() -> None:
    """关闭所有数据库连接"""
    global _connections
    
    # PostgreSQL
    if _connections.postgres_engine:
        await _connections.postgres_engine.dispose()
        _connections.postgres_engine = None
        _connections.postgres_session_factory = None
        print("✓ PostgreSQL disconnected")
    
    # Redis
    if _connections.redis:
        await _connections.redis.close()
        _connections.redis = None
        print("✓ Redis disconnected")
    
    # Qdrant (同步客户端，无需特殊关闭)
    if _connections.qdrant:
        _connections.qdrant = None
        print("✓ Qdrant disconnected")


# ============================================
# 快捷访问
# ============================================
def get_postgres() -> Optional[AsyncEngine]:
    """获取 PostgreSQL 引擎"""
    return _connections.postgres_engine


def get_redis() -> Optional["Redis"]:
    """获取 Redis 客户端"""
    return _connections.redis


def get_qdrant() -> Optional["QdrantClient"]:
    """获取 Qdrant 客户端"""
    return _connections.qdrant


def get_connections() -> DatabaseConnections:
    """获取所有连接"""
    return _connections
