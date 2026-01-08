import streamlit as st
import pandas as pd
from src.storage.json_store import JsonStore
from src.config import Config


@st.cache_resource
def get_store():
    return JsonStore(Config.paper_save_path)


def main():
    st.set_page_config(layout="wide", page_title="LavenderSentinel")

    store = get_store()
    papers = store.get_all_papers()

    rows = []
    for p in papers:
        rows.append({
            "Arxiv ID": p.id,
            "Title": p.title[:100],
        })

    df = pd.DataFrame(rows)

    st.title("📚 LavenderSentinel — Paper Library")

    st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("### 🔍 选择论文查看详情")

    for p in papers:
        st.page_link(
            "pages/1_Page_Detail.py",
            label=f"➡️ {p.id} — {p.title[:60]}...",
            icon="📄",
             query_params={"id": p.id}
        )


if __name__ == "__main__":
    main()