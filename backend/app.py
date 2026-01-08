# app.py
import math
from datetime import datetime

import streamlit as st

from src.storage.json_store import JsonStore
from src.config import Config


@st.cache_resource
def get_store() -> JsonStore:
    return JsonStore(Config.paper_save_path)


def _get_year(paper) -> int | None:
    """
    尝试从 paper 上获取年份：
    - 优先 arxiv_published.year
    - 再尝试 published.year
    - 实在没有就 None
    """
    dt = getattr(paper, "arxiv_published", None) or getattr(paper, "published", None)
    if isinstance(dt, datetime):
        return dt.year
    return None


def _get_authors(paper):
    authors = getattr(paper, "authors", None)
    if not authors:
        return []
    return list(authors)


def _filter_papers(papers, search, author_filter, year_range):
    search = (search or "").strip().lower()
    y_min, y_max = year_range if year_range else (None, None)

    filtered = []
    for p in papers:
        # 年份过滤
        year = _get_year(p)
        if year is not None and y_min is not None and y_max is not None:
            if not (y_min <= year <= y_max):
                continue

        # 作者过滤
        authors = _get_authors(p)
        if author_filter:
            if not any(a in author_filter for a in authors):
                continue

        # 关键词搜索：标题 + 摘要 + 作者
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


# =========================================
#                  MAIN
# =========================================

def main():
    st.set_page_config(
        page_title="LavenderSentinel – Papers",
        layout="wide",
    )

    st.title("🌿 LavenderSentinel — Paper Library")

    store = get_store()
    papers = store.get_all_papers()

    if not papers:
        st.info("暂无论文，请先在命令行里运行抓取脚本。")
        st.stop()

    # ---------- 左上角：搜索 + 筛选 ----------
    with st.container():
        col_search, col_author, col_year = st.columns([2.2, 1.6, 1.6])

        with col_search:
            search = st.text_input(
                "🔍 搜索（标题 / 摘要 / 作者）",
                placeholder="例如：vector database, RAG, transformer...",
            )

        # 作者选项
        all_authors = sorted(
            {a for p in papers for a in _get_authors(p)}
        )
        with col_author:
            author_filter = st.multiselect(
                "👤 按作者筛选",
                options=all_authors,
                default=[],
            )

        # 年份范围
        all_years = sorted({y for p in papers if (y := _get_year(p)) is not None})
        if all_years:
            with col_year:
                year_range = st.slider(
                    "📅 按年份范围",
                    min_value=min(all_years),
                    max_value=max(all_years),
                    value=(min(all_years), max(all_years)),
                    step=1,
                )
        else:
            year_range = None

    st.divider()

    # ---------- 过滤 ----------
    filtered = _filter_papers(papers, search, author_filter, year_range)

    # ---------- 分页 ----------
    total = len(filtered)
    if total == 0:
        st.warning("没有符合条件的论文。可以尝试放宽搜索或筛选条件。")
        st.stop()

    with st.sidebar:
        st.markdown("### 📄 列表设置")
        page_size = st.selectbox("每页数量", [5, 10, 20, 50], index=1)
        total_pages = max(1, math.ceil(total / page_size))

        # 用 session_state 记住当前页
        if "current_page" not in st.session_state:
            st.session_state.current_page = 1

        col_prev, col_page, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("⬅️ 上一页") and st.session_state.current_page > 1:
                st.session_state.current_page -= 1
        with col_next:
            if st.button("下一页 ➡️") and st.session_state.current_page < total_pages:
                st.session_state.current_page += 1
        with col_page:
            st.markdown(
                f"<div style='text-align:center;'>第 {st.session_state.current_page} / {total_pages} 页</div>",
                unsafe_allow_html=True,
            )

    start_idx = (st.session_state.current_page - 1) * page_size
    end_idx = start_idx + page_size
    page_papers = filtered[start_idx:end_idx]

    st.caption(f"共 {total} 篇论文，当前显示第 {st.session_state.current_page} 页。")

    # ---------- 卡片列表（两列） ----------
    cols = st.columns(2)

    # 简单 Skeleton：如果非常多可以考虑先预留占位卡
    if total > 200:
        st.info("论文较多，筛选与分页已启用。")

    for i, p in enumerate(page_papers):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"### 📄 {p.title}")

                # Meta 信息：作者 + 年份
                meta_bits = []

                year = _get_year(p)
                if year is not None:
                    meta_bits.append(str(year))

                authors = _get_authors(p)
                if authors:
                    if len(authors) > 3:
                        meta_bits.append(", ".join(authors[:3]) + " ...")
                    else:
                        meta_bits.append(", ".join(authors))

                if meta_bits:
                    st.caption(" · ".join(meta_bits))

                # 摘要预览
                abstract = getattr(p, "abstract", "") or ""
                preview = abstract[:220] + ("…" if len(abstract) > 220 else "")
                st.write(preview or "_(No abstract)_")

                # 按钮区域：详情 + PDF
                c1, c2 = st.columns([1, 1])
                with c1:
                    # 跳转到详情页，带 query_params
                    st.page_link(
                        "pages/1_Page_Detail.py",
                        label="查看详情",
                        icon="🔍",
                        query_params={"id": p.id},
                    )
                with c2:
                    st.link_button(
                        "📥 PDF",
                        f"https://arxiv.org/pdf/{p.id}.pdf",
                        type="secondary",
                        use_container_width=True,
                    )


if __name__ == "__main__":
    main()