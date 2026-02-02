#!/usr/bin/env python3
# worker.py

"""
RQ Worker 启动脚本

使用方式:
    python worker.py
    
或者直接用 rq 命令:
    rq worker summary default
    
监控队列状态:
    rq info
"""

import sys
import logging

# 确保可以导入 src 模块
sys.path.insert(0, '.')

from rq import Worker

from src.queue.connection import (
    get_redis_connection,
    get_queue,
    QUEUE_SUMMARY,
    QUEUE_ENRICH,
    QUEUE_COMIC,
    QUEUE_DEFAULT,
)


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """启动 Worker"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 获取 Redis 连接
    conn = get_redis_connection()
    
    # 定义要监听的队列（按优先级排序）
    queues = [
        get_queue(QUEUE_SUMMARY),
        get_queue(QUEUE_ENRICH),
        get_queue(QUEUE_COMIC),
        get_queue(QUEUE_DEFAULT),
    ]
    
    queue_names = [q.name for q in queues]
    logger.info(f"🚀 Starting RQ Worker...")
    logger.info(f"📋 Listening on queues: {queue_names}")
    
    # 创建并启动 Worker
    worker = Worker(queues, connection=conn)
    
    try:
        worker.work(with_scheduler=True)
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped by user")


if __name__ == '__main__':
    main()

