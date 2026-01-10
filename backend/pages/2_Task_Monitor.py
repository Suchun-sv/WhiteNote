# pages/2_Task_Monitor.py

"""
任务监控页面

展示：
- arXiv Daily 定时任务状态（APScheduler）
- AI Summary 队列状态（RQ）
- 任务日志
"""

import streamlit as st
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.scheduler.scheduler_service import SchedulerService
from src.queue import (
    get_queue_stats,
    get_pending_jobs,
    get_started_jobs,
    get_recent_finished_jobs,
    get_failed_jobs,
    cancel_job,
    retry_failed_job,
)


# ======================================================
# Cached singletons
# ======================================================

@st.cache_resource
def get_scheduler() -> SchedulerService:
    """Get the shared scheduler instance."""
    scheduler = SchedulerService()
    scheduler.start()
    return scheduler


# ======================================================
# Helper functions
# ======================================================

def _format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _read_log_file(log_path: Path, tail_lines: int = 100) -> str:
    """Read last N lines of a log file."""
    if not log_path.exists():
        return f"日志文件不存在: {log_path}"
    
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-tail_lines:])
    except Exception as e:
        return f"读取日志失败: {e}"


# ======================================================
# Main UI
# ======================================================

def main():
    st.set_page_config(
        page_title="Task Monitor – LavenderSentinel",
        layout="wide",
        page_icon="📊",
    )
    
    st.title("📊 任务监控中心")
    st.caption("监控 arXiv 抓取任务和 AI 总结队列")
    
    # 刷新按钮
    col_refresh, col_spacer = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # ========================================
    # 1. 概览统计
    # ========================================
    st.subheader("📈 队列概览")
    
    try:
        stats = get_queue_stats()
        recent_finished = get_recent_finished_jobs(hours=24)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="⏳ 等待中",
                value=stats["queued"],
                help="队列中等待执行的任务数",
            )
        
        with col2:
            st.metric(
                label="🔄 执行中",
                value=stats["started"],
                help="正在执行的任务数",
            )
        
        with col3:
            st.metric(
                label="✅ 24h 完成",
                value=len(recent_finished),
                help="最近 24 小时完成的任务数",
            )
        
        with col4:
            st.metric(
                label="❌ 失败",
                value=stats["failed"],
                help="失败的任务数",
            )
        
        with col5:
            st.metric(
                label="📊 总计（含历史）",
                value=stats["total"],
                help="所有任务数（包含已完成和失败）",
            )
    
    except Exception as e:
        st.error(f"⚠️ 无法连接 Redis: {e}")
        st.info("请确保 Redis 服务已启动")
    
    st.divider()
    
    # ========================================
    # 2. 定时任务（APScheduler）
    # ========================================
    st.subheader("⏰ 定时任务（APScheduler）")
    
    scheduler = get_scheduler()
    jobs = scheduler.scheduler.get_jobs()
    
    if not jobs:
        st.info("暂无定时任务")
    else:
        for job in jobs:
            with st.container(border=True):
                col_info, col_action = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"**{job.id}**")
                    st.caption(f"下次执行: {_format_datetime(job.next_run_time)}")
                    
                    # 显示触发器信息
                    trigger_str = str(job.trigger)
                    st.caption(f"触发器: `{trigger_str}`")
                
                with col_action:
                    if st.button("▶️ 立即执行", key=f"run_{job.id}", use_container_width=True):
                        try:
                            job.func()
                            st.success("任务已触发")
                            st.rerun()
                        except Exception as e:
                            st.error(f"执行失败: {e}")
    
    st.divider()
    
    # ========================================
    # 3. RQ 队列详情
    # ========================================
    st.subheader("📋 AI 总结队列（RQ）")
    
    tab_pending, tab_running, tab_finished, tab_failed = st.tabs([
        "⏳ 等待中", "🔄 执行中", "✅ 已完成", "❌ 失败"
    ])
    
    # --- 等待中的任务 ---
    with tab_pending:
        try:
            pending_jobs = get_pending_jobs()
            
            if not pending_jobs:
                st.info("队列为空，没有等待中的任务")
            else:
                for i, job in enumerate(pending_jobs):
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.markdown(f"**Paper ID**: `{job['paper_id']}`")
                        
                        with col2:
                            st.caption(f"入队时间: {_format_datetime(job['enqueued_at'])}")
                        
                        with col3:
                            if st.button("❌ 取消", key=f"cancel_{job['job_id']}", use_container_width=True):
                                if cancel_job(job['job_id']):
                                    st.success("已取消")
                                    st.rerun()
                                else:
                                    st.error("取消失败")
        except Exception as e:
            st.error(f"获取队列失败: {e}")
    
    # --- 执行中的任务 ---
    with tab_running:
        try:
            started_jobs = get_started_jobs()
            
            if not started_jobs:
                st.info("当前没有正在执行的任务")
            else:
                for job in started_jobs:
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 2])
                        
                        with col1:
                            st.markdown(f"**Paper ID**: `{job['paper_id']}`")
                        
                        with col2:
                            st.caption(f"开始时间: {_format_datetime(job['started_at'])}")
                            
                            # 计算运行时长
                            if job['started_at']:
                                duration = datetime.now(job['started_at'].tzinfo) - job['started_at']
                                st.caption(f"已运行: {duration.seconds // 60} 分 {duration.seconds % 60} 秒")
        except Exception as e:
            st.error(f"获取执行中任务失败: {e}")
    
    # --- 已完成的任务 ---
    with tab_finished:
        try:
            finished_jobs = get_recent_finished_jobs(hours=24)
            
            if not finished_jobs:
                st.info("最近 24 小时没有完成的任务")
            else:
                st.caption(f"显示最近 24 小时完成的 {len(finished_jobs)} 个任务")
                
                for job in finished_jobs[:20]:  # 只显示最近 20 个
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 2])
                        
                        with col1:
                            st.markdown(f"**Paper ID**: `{job['paper_id']}`")
                        
                        with col2:
                            st.caption(f"完成时间: {_format_datetime(job['ended_at'])}")
                        
                        with col3:
                            # 计算执行时长
                            if job['started_at'] and job['ended_at']:
                                duration = job['ended_at'] - job['started_at']
                                st.caption(f"耗时: {duration.seconds // 60}分{duration.seconds % 60}秒")
        except Exception as e:
            st.error(f"获取完成任务失败: {e}")
    
    # --- 失败的任务 ---
    with tab_failed:
        try:
            failed_jobs = get_failed_jobs()
            
            if not failed_jobs:
                st.success("没有失败的任务 🎉")
            else:
                st.warning(f"共有 {len(failed_jobs)} 个失败的任务")
                
                for job in failed_jobs:
                    with st.container(border=True):
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            st.markdown(f"**Paper ID**: `{job['paper_id']}`")
                            st.caption(f"失败时间: {_format_datetime(job['ended_at'])}")
                            
                            # 显示错误信息
                            if job.get('exc_info'):
                                with st.expander("查看错误详情"):
                                    st.code(job['exc_info'], language="python")
                        
                        with col2:
                            if st.button("🔄 重试", key=f"retry_{job['job_id']}", use_container_width=True):
                                result = retry_failed_job(job['job_id'])
                                if result:
                                    st.success("已重新入队")
                                    st.rerun()
                                else:
                                    st.error("重试失败")
        except Exception as e:
            st.error(f"获取失败任务失败: {e}")
    
    st.divider()
    
    # ========================================
    # 4. 日志查看
    # ========================================
    st.subheader("📜 日志")
    
    log_dir = Path(__file__).parent.parent / "logs"
    
    log_tab1, log_tab2 = st.tabs([
        "🔵 RQ Worker", "⚙️ Supervisor"
    ])
    
    # 日志行数选择
    with st.sidebar:
        st.markdown("### 📜 日志设置")
        tail_lines = st.slider("显示最近行数", min_value=20, max_value=500, value=100, step=20)
    
    with log_tab1:
        log_path = log_dir / "rq-worker-error.log"
        log_content = _read_log_file(log_path, tail_lines)
        st.code(log_content, language="log", line_numbers=True)
    
    with log_tab2:
        log_path = log_dir / "supervisord.log"
        log_content = _read_log_file(log_path, tail_lines)
        st.code(log_content, language="log", line_numbers=True)


if __name__ == "__main__":
    main()

