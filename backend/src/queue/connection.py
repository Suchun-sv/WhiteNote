# src/queue/connection.py

"""
Redis 连接和队列定义
"""

from typing import Optional
from redis import Redis
from rq import Queue

from src.config import Config


# 队列名称常量
QUEUE_SUMMARY = "summary"
QUEUE_COMIC = "comic"
QUEUE_DEFAULT = "default"


_redis_conn: Optional[Redis] = None


def get_redis_connection() -> Redis:
    """
    获取 Redis 连接（单例模式）
    """
    global _redis_conn
    
    if _redis_conn is None:
        _redis_conn = Redis(
            host=Config.redis.host,
            port=Config.redis.port,
            db=Config.redis.db,
            password=Config.redis.password,
            decode_responses=False,  # RQ 需要 bytes
        )
    
    return _redis_conn


def get_queue(name: str = QUEUE_DEFAULT) -> Queue:
    """
    获取指定名称的队列
    
    Args:
        name: 队列名称，如 'summary', 'default'
    """
    conn = get_redis_connection()
    return Queue(name, connection=conn)


# 预定义队列（延迟初始化）
def get_summary_queue() -> Queue:
    """获取 summary 队列"""
    return get_queue(QUEUE_SUMMARY)


def get_comic_queue() -> Queue:
    """获取 comic 队列"""
    return get_queue(QUEUE_COMIC)


def get_default_queue() -> Queue:
    """获取 default 队列"""
    return get_queue(QUEUE_DEFAULT)

