import streamlit as st
from datetime import datetime
from pathlib import Path

from src.storage.json_store import JsonStore
from src.service.llm_service import (
    init_litellm,
    translate_summary,
    summarize_long_markdown,
    ask_paper_question,
    PaperChatState,
)
from src.service.pdf_parser_service import extract_pdf_markdown
from src.service.pdf_download_service import PdfDownloader
from src.config import Config


from streamlit_pdf_viewer import pdf_viewer



# ---------- 缓存 ----------
@st.cache_resource
def get_store():
    return JsonStore(Config.paper_save_path)


@st.cache_resource
def setup_llm():
    init_litellm()
    return True


# ---------- 页面入口 ----------
def main():

    st.set_page_config(
        page_title="Paper Detail – LavenderSentinel",
        layout="wide",
    )

    setup_llm()
    store = get_store()

    params = st.query_params
    if "id" not in params:
        st.error("❌ 缺少参数 id")
        st.stop()

    paper_id = params["id"]
    paper = store.get_paper_by_id(paper_id)

    if not paper:
        st.error("📄 未找到该论文")
        return

    # ---------------- Header ----------------
    st.title(paper.title)
    st.caption(f"Arxiv ID: `{paper.id}`")

    st.divider()

    # ---------------- Layout ----------------
    col_left, col_right = st.columns([2, 2])

    # ======================================================
    # LEFT — PDF VIEWER
    # ======================================================
    with col_left:
        st.subheader("📄 Paper PDF")

        # pdf_path = Path("cache/pdfs") / f"{paper.id}.pdf"
        pdf_path = Path(Config.pdf_save_path) / f"{paper.id}.pdf"

        if not pdf_path.exists():
            st.warning("⚠ 当前 PDF 尚未下载")
            if st.button("📥 立即下载 PDF"):
                # st.info("（TODO：连接你的 PdfDownloader 后端任务）")
                downloader = PdfDownloader()
                print(f"https://arxiv.org/pdf/{paper.id}.pdf", paper.id)
                downloader.download_one(f"https://arxiv.org/pdf/{paper.id}.pdf", paper.id)
                st.success("已下载 PDF")
                with st.spinner("⏳ 正在加载 PDF..."):
                    pdf_viewer(pdf_path, width=900, height=2000)
        else:
            with st.spinner("⏳ 正在加载 PDF..."):
                pdf_viewer(pdf_path, width=900, height=2000)

        # st.divider()



    # ======================================================
    # RIGHT — SIDEBAR PANEL
    # ======================================================
    with col_right:
        st.subheader("📝 原文摘要")
        st.write(paper.abstract)

        # # st.markdown("### 🤖 AI Summary & Chat")
        # # st.caption("LLM Powered — LavenderSentinel 🌿")
        # st.divider()

        # ---------- AI ABSTRACT ----------
        st.markdown("#### 📘 AI Abstract (翻译摘要)")

        if getattr(paper, "ai_abstract", ""):
            with st.expander("查看 AI 摘要翻译", expanded=False):
                st.write(paper.ai_abstract)

        if st.button("✨ 生成 / 更新 AI 摘要翻译"):
            translated = translate_summary(paper.abstract)
            store.update_paper_field(paper.id, "ai_abstract", translated)
            store.update_paper_field(paper.id, "ai_abstract_provider", Config.chat_litellm.model)
            store.update_paper_field(paper.id, "updated_at", datetime.now())
            st.success("已更新 AI 摘要")

        st.divider()

        # ---------- AI SUMMARY ----------
        st.markdown("#### 📕 AI Full-text Summary")

        if getattr(paper, "ai_summary", ""):
            with st.expander("查看 AI 全文总结", expanded=False):
                st.write(paper.ai_summary)

        if st.button("🧠 生成 / 更新全文总结"):
            pdf_path = Path("cache/pdfs") / f"{paper.id}.pdf"

            if not pdf_path.exists():
                st.error("❌ 需要 PDF 才能生成全文总结，请先下载")
            else:
                with open(pdf_path, "rb") as f:
                    md = extract_pdf_markdown(f.read())

                store.update_paper_field(paper.id, "full_text", md)

                summary = summarize_long_markdown(md, language=Config.language)

                store.update_paper_field(paper.id, "ai_summary", summary)
                store.update_paper_field(paper.id, "ai_summary_provider", Config.chat_litellm.model)
                store.update_paper_field(paper.id, "updated_at", datetime.now())

                st.success("已生成全文总结")

        st.divider()

        # ---------- CHAT ----------
        st.markdown("#### 💬 Paper Chat Assistant")

        if "chat_state" not in st.session_state:
            st.session_state.chat_state = PaperChatState(
                paper_title=paper.title,
                paper_abstract=getattr(paper, "ai_abstract", paper.abstract),
                paper_full_summary=getattr(paper, "ai_summary", ""),
            )

        for msg in st.session_state.chat_state.history:
            role = "🧑" if msg["role"] == "user" else "🤖"
            st.markdown(f"**{role} {msg['role']}**: {msg['content']}")

        user_q = st.text_area("你的问题：", key="qa_input")

        if st.button("🚀 发送问题"):
            if not st.session_state.chat_state.paper_full_summary:
                st.error("❌ 需要先生成 AI Summary 才能问答")
            else:
                ans = ask_paper_question(st.session_state.chat_state, user_q, language=Config.language)
                st.rerun()


if __name__ == "__main__":
    main()