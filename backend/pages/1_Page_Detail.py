import streamlit as st
from datetime import datetime
from src.storage.json_store import JsonStore
from src.service.llm_service import (
    init_litellm,
    translate_summary,
    summarize_long_markdown,
    ask_paper_question,
    PaperChatState,
)
from src.service.pdf_parser_service import extract_pdf_markdown
from src.config import Config


# ---------- 资源缓存 ----------
@st.cache_resource
def get_store():
    return JsonStore(Config.paper_save_path)

@st.cache_resource
def setup_llm():
    init_litellm()
    return True


def main():
    st.set_page_config(layout="wide", page_title="Paper Detail")
    setup_llm()
    store = get_store()

    # ---------- 读取 URL 参数 ----------
    params = st.query_params
    if "id" not in params:
        st.error("❌ 缺少参数 id")
        return
    paper_id = params["id"]

    paper = store.get_paper_by_id(paper_id)
    if not paper:
        st.error("未找到该论文")
        return

    # ---------- 页面布局 ----------
    left, right = st.columns([2, 1])

    with left:
        st.title(paper.title)
        st.markdown(f"**📎 ArXiv ID:** `{paper.id}`")
        st.markdown(f"🕒 Updated: `{paper.updated_at}`")

        st.divider()

        # ===== 原文摘要 =====
        st.subheader("📄 原文摘要")
        st.write(paper.abstract)

        # ===== AI 摘要翻译 =====
        st.subheader("🤖 AI 摘要翻译")
        if paper.ai_abstract:
            st.info(paper.ai_abstract)
        else:
            if st.button("✨ 生成摘要翻译"):
                translated = translate_summary(paper.abstract)
                store.update_paper_field(paper_id, "ai_abstract", translated)
                store.update_paper_field(paper_id, "ai_abstract_provider", Config.chat_litellm.model)
                store.update_paper_field(paper_id, "updated_at", datetime.now())
                st.success("已生成 AI 摘要翻译，请刷新页面")
        
        st.divider()

        # ===== 全文总结 =====
        st.subheader("📚 AI 全文总结")

        if paper.ai_summary:
            st.success("以下为 AI 总结内容：")
            st.write(paper.ai_summary)

        else:
            if st.button("🧠 生成全文总结"):
                pdf_path = f"cache/pdfs/{paper.id}.pdf"
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                full_text = extract_pdf_markdown(pdf_bytes)
                store.update_paper_field(paper_id, "full_text", full_text)

                summary = summarize_long_markdown(full_text, language=Config.language)
                store.update_paper_field(paper_id, "ai_summary", summary)
                store.update_paper_field(paper_id, "ai_summary_provider", Config.chat_litellm.model)
                store.update_paper_field(paper_id, "updated_at", datetime.now())

                st.success("已生成全文总结，请刷新页面")

    # ---------- Sidebar Chat ----------
    with right:
        st.header("💬 Paper Chat")

        if not paper.ai_summary:
            st.warning("⚠️ 请先生成全文总结")
            return

        if "chat_state" not in st.session_state:
            st.session_state.chat_state = PaperChatState(
                paper_title=paper.title,
                paper_abstract=paper.ai_abstract or paper.abstract,
                paper_full_summary=paper.ai_summary,
            )

        for msg in st.session_state.chat_state.history:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

        user_input = st.chat_input("向论文提问…")

        if user_input:
            answer = ask_paper_question(
                st.session_state.chat_state,
                user_input,
                language=Config.language,
            )
            st.chat_message("user").write(user_input)
            st.chat_message("assistant").write(answer)

    st.markdown("---")
    st.page_link("app.py", label="⬅️ 返回主页")


if __name__ == "__main__":
    main()