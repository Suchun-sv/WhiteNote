# app.py
import math
from datetime import datetime
from typing import Optional

import streamlit as st

from src.config import Config
from src.database.paper_repository import PaperRepository
from src.scheduler.scheduler_service import SchedulerService


# =====================================================
# Global singletons (cached across Streamlit reruns)
# =====================================================

@st.cache_resource
def get_repo() -> PaperRepository:
    """
    Database repository (Postgres).
    """
    return PaperRepository()


@st.cache_resource
def get_scheduler() -> SchedulerService:
    """
    Background scheduler (APScheduler).

    This is started ONCE when Streamlit boots.
    """
    scheduler = SchedulerService()
    scheduler.start()
    return scheduler


# =====================================================
# Helper functions (UI-level logic only)
# =====================================================

def _get_year(paper) -> int | None:
    """
    Try to extract year from paper.
    """
    dt = getattr(paper, "arxiv_published", None)
    if isinstance(dt, datetime):
        return dt.year
    return None


def _get_authors(paper):
    authors = getattr(paper, "authors", None)
    if not authors:
        return []
    return list(authors)


def _trigger_favorite_auto_tasks(paper_id: str, repo: PaperRepository, scheduler: SchedulerService):
    """Trigger auto download PDF and summary when favoriting a paper."""
    from pathlib import Path
    from src.service.pdf_download_service import PdfDownloader
    from src.jobs.paper_summary_job import SummaryJobStatus

    if Config.favorite.auto_download_pdf:
        pdf_path = Path(Config.pdf_save_path) / f"{paper_id}.pdf"
        if not pdf_path.exists():
            try:
                downloader = PdfDownloader()
                downloader.download_one(f"https://arxiv.org/pdf/{paper_id}.pdf", paper_id)
            except Exception:
                pass  # Silent fail for quick action

    if Config.favorite.auto_generate_summary:
        paper = repo.get_paper_by_id(paper_id)
        if paper and not paper.ai_summary:
            repo.update_summary_job_status(paper_id, SummaryJobStatus.PENDING)
            scheduler.add_paper_summary_job(paper_id)


def _go_prev_page():
    """回调：上一页"""
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1


def _go_next_page(total_pages: int):
    """回调：下一页"""
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1


def _on_page_size_change():
    """回调：每页数量变化时重置到第一页"""
    st.session_state.current_page = 1


def _render_pagination(total: int, position: str = "top") -> int:
    """
    Render pagination controls with page size selector.
    
    Args:
        total: Total number of items
        position: 'top' or 'bottom' - used for unique keys
    
    Returns:
        page_size: Selected page size
    """
    # 获取当前值（使用 get 避免与 widget key 冲突）
    page_size = st.session_state.get("page_size", 10)
    current_page = st.session_state.get("current_page", 1)
    
    total_pages = max(1, math.ceil(total / page_size))
    
    # Reset page if out of bounds
    if current_page > total_pages:
        current_page = 1
        st.session_state.current_page = 1
    
    # Layout: info | page_size | prev | page_select | next
    col_info, col_size, col_prev, col_page_select, col_next = st.columns([2, 1.2, 1, 1.2, 1])
    
    with col_info:
        start = (current_page - 1) * page_size + 1
        end = min(current_page * page_size, total)
        st.caption(f"共 **{total}** 篇，显示 {start}-{end}")
    
    with col_size:
        # 只在 top 位置渲染 selectbox，避免重复 key
        if position == "top":
            page_size_options = [5, 10, 20, 50]
            default_index = page_size_options.index(page_size) if page_size in page_size_options else 1
            st.selectbox(
                "每页显示",
                options=page_size_options,
                index=default_index,
                key="page_size",
                format_func=lambda x: f"每页 {x} 篇",
                on_change=_on_page_size_change,
                label_visibility="collapsed",
            )
        else:
            # bottom 位置只显示文字
            st.caption(f"每页 {page_size} 篇")
    
    with col_prev:
        st.button(
            "⬅ 上一页",
            key=f"prev_{position}",
            disabled=current_page <= 1,
            use_container_width=True,
            on_click=_go_prev_page,
        )
    
    with col_page_select:
        # 只在 top 位置渲染页码选择，避免重复 key
        if position == "top":
            page_options = list(range(1, total_pages + 1))
            default_page_index = current_page - 1 if current_page <= total_pages else 0
            st.selectbox(
                "页码",
                options=page_options,
                index=default_page_index,
                key="current_page",
                label_visibility="collapsed",
                format_func=lambda x: f"第 {x}/{total_pages} 页",
            )
        else:
            st.caption(f"第 {current_page}/{total_pages} 页")
    
    with col_next:
        st.button(
            "下一页 ➡",
            key=f"next_{position}",
            disabled=st.session_state.current_page >= total_pages,
            use_container_width=True,
            on_click=_go_next_page,
            args=(total_pages,),
        )
    
    return st.session_state.page_size


def _filter_papers(papers, search, author_filter, year_range):
    search = (search or "").strip().lower()
    y_min, y_max = year_range if year_range else (None, None)

    filtered = []
    for p in papers:
        # Year filter
        year = _get_year(p)
        if year is not None and y_min is not None and y_max is not None:
            if not (y_min <= year <= y_max):
                continue

        # Author filter
        authors = _get_authors(p)
        if author_filter:
            if not any(a in author_filter for a in authors):
                continue

        # Text search
        if search:
            blob = " ".join([
                p.title or "",
                p.abstract or "",
                " ".join(authors),
            ]).lower()
            if search not in blob:
                continue

        filtered.append(p)

    return filtered


# =====================================================
# Main UI
# =====================================================

def main():
    st.set_page_config(
        page_title="LavenderSentinel – Papers",
        layout="wide",
    )

    st.title("🌿 LavenderSentinel — Paper Library")

    # --- init services ---
    repo = get_repo()
    scheduler = get_scheduler()  # noqa: F841 (intentional side effect)

    # --- Sidebar: Folder filter & Settings ---
    with st.sidebar:
        st.markdown("### 📁 收藏夹")

        # Get all folders with counts
        folder_counts = repo.get_folder_counts()
        all_folders = sorted(folder_counts.keys())

        # 初始化 folder filter state
        if "folder_filter" not in st.session_state:
            st.session_state.folder_filter = None

        folder_filter = st.session_state.folder_filter

        # "全部论文" 选项
        if st.button(
            "📚 全部论文",
            key="folder_all",
            use_container_width=True,
            type="primary" if folder_filter is None else "secondary",
        ):
            st.session_state.folder_filter = None
            st.rerun()

        # 每个收藏夹一行：名称 + 管理按钮
        for folder in all_folders:
            col_name, col_manage = st.columns([4, 1])

            with col_name:
                is_selected = folder_filter == folder
                btn_type = "primary" if is_selected else "secondary"
                if st.button(
                    f"⭐ {folder} ({folder_counts[folder]})",
                    key=f"folder_select_{folder}",
                    use_container_width=True,
                    type=btn_type,
                ):
                    st.session_state.folder_filter = folder
                    st.rerun()

            with col_manage:
                with st.popover("⚙", use_container_width=True):
                    st.markdown(f"**管理「{folder}」**")

                    # 重命名
                    new_name = st.text_input(
                        "重命名为",
                        value=folder,
                        key=f"rename_{folder}",
                        label_visibility="visible",
                    )
                    if st.button("✏️ 确认重命名", key=f"do_rename_{folder}"):
                        if new_name and new_name.strip() and new_name.strip() != folder:
                            count = repo.rename_folder(folder, new_name.strip())
                            st.success(f"已重命名，影响 {count} 篇论文")
                            # 如果当前选中的是被重命名的文件夹，更新 filter
                            if st.session_state.folder_filter == folder:
                                st.session_state.folder_filter = new_name.strip()
                            st.rerun()
                        else:
                            st.warning("请输入新名称")

                    st.markdown("---")

                    # 删除
                    st.markdown("⚠️ **删除收藏夹**")
                    st.caption("论文不会被删除，只是从该收藏夹移除")
                    if st.button("🗑️ 删除此收藏夹", key=f"do_delete_{folder}", type="primary"):
                        count = repo.delete_folder(folder)
                        st.success(f"已删除，影响 {count} 篇论文")
                        if st.session_state.folder_filter == folder:
                            st.session_state.folder_filter = None
                        st.rerun()

        # 新建收藏夹
        st.markdown("---")
        with st.expander("➕ 新建收藏夹"):
            new_folder_name = st.text_input(
                "收藏夹名称",
                key="new_folder_name_sidebar",
                placeholder="输入名称...",
            )
            st.caption("💡 创建后，将论文添加到此收藏夹即可")
            if new_folder_name:
                st.info(f"收藏夹「{new_folder_name}」将在添加论文时自动创建")

        st.divider()

        st.markdown("### ⚙️ 显示设置")
        show_disliked = st.checkbox("显示不喜欢的论文", value=False, key="show_disliked")
        show_favorite = st.checkbox("显示收藏的论文", value=False, key="show_favorite")

        st.divider()

    # --- load papers from Postgres ---
    papers = repo.list_with_filters(
        page=1,
        page_size=10_000,  # UI-level fetch
        sort_by="created_at",
        order="desc",
        include_favorite=show_favorite,
        include_disliked=show_disliked,
        folder_filter=folder_filter,
    )

    # Show current filter status
    filter_info = []
    if folder_filter:
        filter_info.append(f"收藏夹: **{folder_filter}**")
    if show_disliked:
        filter_info.append("包含不喜欢的论文")

    if filter_info:
        st.info(" | ".join(filter_info))

    if not papers:
        if folder_filter:
            st.info(f"收藏夹「{folder_filter}」中暂无论文。")
        else:
            st.info("暂无论文，请等待定时任务抓取 arXiv。")
        st.stop()

    # ---------- 搜索 & 筛选 ----------
    with st.container():
        col_search, col_author, col_year = st.columns([2.2, 1.6, 1.6])

        with col_search:
            search = st.text_input(
                "🔍 搜索（标题 / 摘要 / 作者）",
                placeholder="例如：vector database, RAG, transformer...",
            )

        all_authors = sorted(
            {a for p in papers for a in _get_authors(p)}
        )

        with col_author:
            author_filter = st.multiselect(
                "👤 按作者筛选",
                options=all_authors,
                default=[],
            )

        all_years = sorted(
            {y for p in papers if (y := _get_year(p)) is not None}
        )

        if len(all_years) > 1:
            # 多个年份时显示滑块
            with col_year:
                year_range = st.slider(
                    "📅 按年份范围",
                    min_value=min(all_years),
                    max_value=max(all_years),
                    value=(min(all_years), max(all_years)),
                    step=1,
                )
        elif len(all_years) == 1:
            # 只有一个年份时显示提示
            with col_year:
                st.caption(f"📅 年份: {all_years[0]}")
            year_range = (all_years[0], all_years[0])
        else:
            year_range = None

    st.divider()

    # ---------- 过滤 ----------
    filtered = _filter_papers(papers, search, author_filter, year_range)

    total = len(filtered)
    if total == 0:
        st.warning("没有符合条件的论文。")
        st.stop()

    # ---------- 分页控件（卡片上方） ----------
    page_size = _render_pagination(total, position="top")

    start_idx = (st.session_state.current_page - 1) * page_size
    end_idx = start_idx + page_size
    page_papers = filtered[start_idx:end_idx]

    # ---------- 卡片列表 ----------
    cols = st.columns(2)

    for i, p in enumerate(page_papers):
        with cols[i % 2]:
            with st.container(border=True):
                # Title with status indicators
                title_prefix = ""
                if p.favorite_folders:
                    title_prefix += "⭐ "
                if p.is_disliked:
                    title_prefix += "👎 "

                st.markdown(f"### {title_prefix}📄 {p.title}")

                if p.ai_title:
                    st.caption(f"🤖 AI Title: {p.ai_title}")

                # Show favorite folders if any
                if p.favorite_folders:
                    folder_tags = " ".join([f"`{f}`" for f in p.favorite_folders])
                    st.caption(f"📁 {folder_tags}")

                meta_bits = []
                year = _get_year(p)
                if year:
                    meta_bits.append(str(year))

                authors = _get_authors(p)
                if authors:
                    meta_bits.append(
                        ", ".join(authors[:3]) + (" ..." if len(authors) > 3 else "")
                    )

                if meta_bits:
                    st.caption(" · ".join(meta_bits))

                preview = p.ai_abstract or p.abstract or ""
                st.write(preview or "_(No abstract)_")

                # Action buttons - 更紧凑的布局
                c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 0.8])
                with c1:
                    st.page_link(
                        "pages/1_Page_Detail.py",
                        label="详情",
                        icon="🔍",
                        query_params={"id": p.id},
                    )
                with c2:
                    st.link_button(
                        "PDF",
                        f"https://arxiv.org/pdf/{p.id}.pdf",
                        use_container_width=True,
                    )
                with c3:
                    # 收藏夹快速操作
                    with st.popover("⭐", use_container_width=True):
                        st.markdown("**添加到收藏夹**")
                        # 已有收藏夹
                        if all_folders:
                            for folder in all_folders:
                                is_in = folder in (p.favorite_folders or [])
                                label = f"{'✓ ' if is_in else ''}{folder}"
                                if st.button(
                                    label,
                                    key=f"toggle_fav_{p.id}_{folder}",
                                    use_container_width=True,
                                ):
                                    if is_in:
                                        repo.remove_from_folder(p.id, folder)
                                    else:
                                        repo.add_to_folder(p.id, folder)
                                        _trigger_favorite_auto_tasks(p.id, repo, scheduler)
                                    st.rerun()

                        # 新建收藏夹
                        st.markdown("---")
                        new_folder = st.text_input(
                            "新建",
                            key=f"new_fav_{p.id}",
                            placeholder="收藏夹名称",
                            label_visibility="collapsed",
                        )
                        if new_folder and st.button("➕ 创建", key=f"create_fav_{p.id}"):
                            repo.add_to_folder(p.id, new_folder.strip())
                            _trigger_favorite_auto_tasks(p.id, repo, scheduler)
                            st.rerun()

                with c4:
                    # 不喜欢按钮 - 更小
                    if p.is_disliked:
                        if st.button("↩", key=f"undislike_{p.id}", help="取消不喜欢"):
                            repo.unmark_disliked(p.id)
                            st.rerun()
                    else:
                        if st.button("👎", key=f"dislike_{p.id}", help="不喜欢"):
                            repo.mark_disliked(p.id)
                            st.rerun()

    # ---------- 分页控件（卡片下方） ----------
    st.divider()
    _render_pagination(total, position="bottom")


if __name__ == "__main__":
    main()