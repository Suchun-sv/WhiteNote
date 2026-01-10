import streamlit as st
from datetime import datetime
from pathlib import Path

from src.database.paper_repository import PaperRepository
from src.scheduler.scheduler_service import SchedulerService
from src.service.llm_service import (
    init_litellm,
    translate_summary,
    summarize_long_markdown,
    ask_paper_question,
    PaperChatState,
)
from src.service.pdf_parser_service import extract_pdf_markdown
from src.service.pdf_download_service import PdfDownloader
from src.jobs.paper_summary_job import SummaryJobStatus
from src.config import Config
from src.queue import enqueue_summary_job, get_queue_size, get_pending_jobs

from streamlit_pdf_viewer import pdf_viewer


# ======================================================
# Cached singletons
# ======================================================

@st.cache_resource
def get_repo() -> PaperRepository:
    return PaperRepository()


@st.cache_resource
def get_scheduler() -> SchedulerService:
    """Get the shared scheduler instance."""
    scheduler = SchedulerService()
    scheduler.start()
    return scheduler


@st.cache_resource
def setup_llm():
    init_litellm()
    return True


# ======================================================
# Helper: Favorite & Dislike UI
# ======================================================

def _render_favorite_dislike_section(paper, repo: PaperRepository, scheduler: SchedulerService):
    """Render the favorite folders and dislike section."""
    from src.model.paper import Paper

    col_fav, col_dislike = st.columns([3, 1])

    with col_fav:
        # Show current folders
        if paper.favorite_folders:
            folder_tags = " ".join([f"`{f}`" for f in paper.favorite_folders])
            st.markdown(f"⭐ **已收藏到**: {folder_tags}")

        # Add to folder
        with st.expander("📁 收藏到文件夹", expanded=False):
            all_folders = repo.get_all_folders()

            # Select existing folder
            if all_folders:
                selected_folder = st.selectbox(
                    "选择收藏夹",
                    options=[""] + all_folders,
                    format_func=lambda x: "-- 选择收藏夹 --" if x == "" else x,
                    key="select_folder",
                )

                if selected_folder and st.button("➕ 添加到此收藏夹", key="add_to_folder"):
                    _add_paper_to_folder(paper.id, selected_folder, repo)
                    st.rerun()

            # Create new folder
            st.markdown("---")
            new_folder_name = st.text_input("或创建新收藏夹", key="new_folder_name")
            if new_folder_name and st.button("✨ 创建并添加", key="create_folder"):
                _add_paper_to_folder(paper.id, new_folder_name.strip(), repo)
                st.rerun()

            # Remove from folder
            if paper.favorite_folders:
                st.markdown("---")
                remove_folder = st.selectbox(
                    "从收藏夹移除",
                    options=[""] + paper.favorite_folders,
                    format_func=lambda x: "-- 选择要移除的收藏夹 --" if x == "" else x,
                    key="remove_folder",
                )
                if remove_folder and st.button("🗑️ 移除", key="remove_from_folder"):
                    repo.remove_from_folder(paper.id, remove_folder)
                    st.success(f"已从「{remove_folder}」移除")
                    st.rerun()

    with col_dislike:
        if paper.is_disliked:
            st.warning("👎 已标记不喜欢")
            if st.button("↩️ 取消不喜欢", key="unmark_dislike"):
                repo.unmark_disliked(paper.id)
                st.success("已取消标记")
                st.rerun()
        else:
            if st.button("👎 不喜欢", key="mark_dislike"):
                repo.mark_disliked(paper.id)
                st.info("已标记为不喜欢，在主列表中将默认隐藏")
                st.rerun()


def _add_paper_to_folder(paper_id: str, folder_name: str, repo: PaperRepository):
    """Add paper to folder and trigger auto tasks if configured (via RQ)."""
    from pathlib import Path

    added = repo.add_to_folder(paper_id, folder_name)

    if added:
        st.success(f"✅ 已添加到「{folder_name}」")

        # Check config for auto tasks
        if Config.favorite.auto_download_pdf:
            pdf_path = Path(Config.pdf_save_path) / f"{paper_id}.pdf"
            if not pdf_path.exists():
                st.info("📥 正在后台下载 PDF...")
                # Download PDF in background (or inline for simplicity)
                downloader = PdfDownloader()
                try:
                    downloader.download_one(
                        f"https://arxiv.org/pdf/{paper_id}.pdf",
                        paper_id,
                    )
                    st.success("✅ PDF 下载完成")
                except Exception as e:
                    st.warning(f"⚠️ PDF 下载失败: {e}")

        if Config.favorite.auto_generate_summary:
            paper = repo.get_paper_by_id(paper_id)
            if paper and not paper.ai_summary:
                repo.update_summary_job_status(paper_id, SummaryJobStatus.PENDING)
                enqueue_summary_job(paper_id)  # 使用 RQ 队列
                st.info("🧠 已提交 AI 总结任务到 RQ 队列")
    else:
        st.info(f"论文已在「{folder_name}」中")


# ======================================================
# Page entry
# ======================================================

def main():
    st.set_page_config(
        page_title="Paper Detail – LavenderSentinel",
        layout="wide",
    )

    setup_llm()
    repo = get_repo()
    scheduler = get_scheduler()

    # ---------- Params ----------
    params = st.query_params
    if "id" not in params:
        st.error("❌ 缺少参数 id")
        st.stop()

    paper_id = params["id"]
    paper = repo.get_paper_by_id(paper_id)

    if not paper:
        st.error("📄 未找到该论文")
        return

    # ---------------- Header ----------------
    st.title(paper.title)
    st.caption(f"ArXiv ID: `{paper.id}`")

    # ---------------- Favorite & Dislike Actions ----------------
    _render_favorite_dislike_section(paper, repo, scheduler)

    st.divider()

    # ======================================================
    # SIDEBAR — View Mode & Links
    # ======================================================
    with st.sidebar:
        st.markdown("### 📖 查看模式")
        view_mode = st.radio(
            "选择查看方式",
            options=["🌐 arXiv HTML", "📄 本地 PDF"],
            key="view_mode",
            label_visibility="collapsed",
        )
        
        st.markdown("### 🔗 快捷链接")
        arxiv_html_url = f"https://arxiv.org/html/{paper.id}"
        st.link_button("🌐 arXiv HTML", arxiv_html_url, use_container_width=True)
        st.link_button("📄 arXiv PDF", f"https://arxiv.org/pdf/{paper.id}.pdf", use_container_width=True)
        st.link_button("📋 arXiv Abstract", f"https://arxiv.org/abs/{paper.id}", use_container_width=True)
        
        st.divider()

    # ---------------- Layout ----------------
    pdf_path = Path(Config.pdf_save_path) / f"{paper.id}.pdf"
    col_left, col_right = st.columns([2, 2])

    # ======================================================
    # LEFT — INFO / AI PANEL
    # ======================================================
    with col_left:
        # ---------- Abstract ----------
        st.subheader("📝 原文摘要")
        st.write(paper.abstract)

        st.divider()

        # ---------- AI ABSTRACT ----------
        st.markdown("#### 📘 AI Abstract（翻译摘要）")

        if paper.ai_abstract:
            with st.expander("查看 AI 摘要翻译", expanded=False):
                st.write(paper.ai_abstract)

        if st.button("✨ 生成 / 更新 AI 摘要翻译"):
            translated = translate_summary(paper.abstract)

            repo.update_ai_abstract(
                paper_id=paper.id,
                ai_abstract=translated,
                provider=Config.chat_litellm.model,
            )

            st.success("已更新 AI 摘要")
            st.rerun()

        st.divider()

        # ---------- AI SUMMARY ----------
        st.markdown("#### 📕 AI Full-text Summary")

        # 显示已有的总结
        if paper.ai_summary:
            with st.expander("查看 AI 全文总结", expanded=False):
                st.write(paper.ai_summary)

        # 获取任务状态和队列信息（使用 RQ）
        job_status = paper.summary_job_status
        queue_size = get_queue_size()

        # 显示任务状态
        if job_status == SummaryJobStatus.RUNNING:
            st.info("⏳ 正在后台生成全文总结，请稍候...")
            if queue_size > 0:
                st.caption(f"📋 RQ 队列中还有 {queue_size} 个任务等待")
            if st.button("🔄 刷新状态"):
                st.rerun()

        elif job_status == SummaryJobStatus.PENDING:
            # 计算当前任务在队列中的位置
            queue_jobs = get_pending_jobs()
            position = next(
                (i + 1 for i, job in enumerate(queue_jobs) if job["paper_id"] == paper.id),
                None
            )
            if position:
                st.info(f"📋 任务排队中（第 {position}/{len(queue_jobs)} 位），等待执行...")
            else:
                st.info("📋 任务已加入 RQ 队列，等待执行...")
            if st.button("🔄 刷新状态"):
                st.rerun()

        elif job_status == SummaryJobStatus.FAILED:
            st.error("❌ 上次生成失败，可以重试")

        # 显示队列状态（仅当有任务在队列中时）
        if queue_size > 0 and job_status not in (SummaryJobStatus.RUNNING, SummaryJobStatus.PENDING):
            st.caption(f"ℹ️ RQ 队列中有 {queue_size} 个任务正在处理")

        # 提交任务按钮
        if job_status not in (SummaryJobStatus.RUNNING, SummaryJobStatus.PENDING):
            if st.button("🧠 生成 / 更新全文总结（后台任务）"):
                if not pdf_path.exists():
                    st.warning("⚠ PDF 不存在，任务会自动下载")

                # 设置状态为 pending 并提交到 RQ 队列
                repo.update_summary_job_status(paper.id, SummaryJobStatus.PENDING)
                enqueue_summary_job(paper.id)

                new_queue_size = get_queue_size()
                st.success(f"✅ 任务已提交到 RQ 队列（当前队列: {new_queue_size} 个任务）")
                st.rerun()

        st.divider()

        # ---------- CHAT ----------
        st.markdown("#### 💬 Paper Chat Assistant")

        if "chat_state" not in st.session_state:
            st.session_state.chat_state = PaperChatState(
                paper_title=paper.title,
                paper_abstract=paper.ai_abstract or paper.abstract,
                paper_full_summary=paper.ai_summary or "",
            )

        for msg in st.session_state.chat_state.history:
            role_icon = "🧑" if msg["role"] == "user" else "🤖"
            st.markdown(f"**{role_icon} {msg['role']}**: {msg['content']}")

        user_q = st.text_area("你的问题：", key="qa_input")

        if st.button("🚀 发送问题"):
            if not st.session_state.chat_state.paper_full_summary:
                st.error("❌ 需要先生成 AI Summary 才能问答")
            else:
                ask_paper_question(
                    st.session_state.chat_state,
                    user_q,
                    language=Config.language,
                )
                st.rerun()

    # ======================================================
    # RIGHT — PAPER VIEWER (HTML or PDF)
    # ======================================================
    with col_right:
        if view_mode == "🌐 arXiv HTML":
            st.subheader("🌐 arXiv HTML")
            
            # arXiv HTML 页面 URL
            arxiv_html_url = f"https://arxiv.org/html/{paper.id}"
            
            st.caption("💡 如果下方无法显示，请使用侧边栏的链接在新标签页打开")
            
            # 使用 HTML iframe 嵌入
            iframe_html = f'''
            <iframe 
                src="{arxiv_html_url}" 
                width="100%" 
                height="1200px" 
                style="border: 1px solid #ddd; border-radius: 8px;"
            ></iframe>
            '''
            st.components.v1.html(iframe_html, height=1220)
        
        else:
            st.subheader("📄 Paper PDF")

            if not pdf_path.exists():
                st.warning("⚠ 当前 PDF 尚未下载")
                if st.button("📥 立即下载 PDF"):
                    downloader = PdfDownloader()
                    downloader.download_one(
                        f"https://arxiv.org/pdf/{paper.id}.pdf",
                        paper.id,
                    )
                    st.success("已下载 PDF")
                    st.rerun()
            else:
                with st.spinner("⏳ 正在加载 PDF..."):
                    pdf_viewer(pdf_path, width=900, height=2000)


if __name__ == "__main__":
    main()