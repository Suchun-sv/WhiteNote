"""
llm_paper_tools.py

提供：
- 单轮 LLM 调用
- 多轮 chat 调用
- 摘要翻译
- 长文自动 chunk + 总结
- PaperChatState：带摘要+总结+历史对话的问答

依赖：
    pip install litellm
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

import litellm
from litellm import completion
from ..config import Config

def init_litellm():
    litellm.api_key = Config.chat_litellm.api_key
    litellm.api_base = Config.chat_litellm.api_base

# =========================================================
# 🔹 1. 基础 LLM 封装
# =========================================================

def llm_completion(prompt: str) -> str:
    """单轮对话"""
    resp = completion(
        model=Config.chat_litellm.model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def llm_chat(messages: List[Dict]) -> str:
    """多轮对话"""
    resp = completion(
        model=Config.chat_litellm.model,
        messages=messages,
    )
    return resp.choices[0].message.content


def translate_title(title_text: str, target_lang: str = "zh") -> str:
    prompt = f"""
你是一名严谨的学术翻译助手，请将下面的学术标题翻译成 {target_lang}，要求：
- 保持术语准确
- 不要添加个人评论

原文标题：
{title_text}
"""
    return llm_completion(prompt.strip())


# =========================================================
# 🔹 2. 摘要翻译
# =========================================================

def translate_summary(summary_text: str, target_lang: str = "zh") -> str:
    prompt = f"""
你是一名严谨的学术翻译助手，请将下面的学术摘要翻译成 {target_lang}，要求：
- 保持术语准确
- 数学符号保持不变
- 不要添加个人评论

原文摘要：
{summary_text}
"""
    return llm_completion(prompt.strip())


# =========================================================
# 🔹 3. 长文处理 —— 切 chunk + 分块总结 + 总总结
# =========================================================

def _split_text(text: str, max_chars: int = 6000) -> List[str]:
    """
    按字符长度+段落切块，粗略 proxy token。
    6000 字符 ~ 1500–2000 token
    """
    paragraphs = text.split("\n\n")
    chunks, buf = [], []
    buf_len = 0

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue

        if buf_len + len(p) + 2 <= max_chars:
            buf.append(p)
            buf_len += len(p) + 2
        else:
            if buf:
                chunks.append("\n\n".join(buf))
            buf = [p]
            buf_len = len(p)

    if buf:
        chunks.append("\n\n".join(buf))

    return chunks


def summarize_long_markdown(md_text: str, language: str = "en") -> str:
    """
    自动 chunk + 合并总结
    """
    chunks = [c for c in _split_text(md_text, max_chars=6000) if c.strip()]

    if not chunks:
        return ""

    # === 只有 1 块，直接总结 ===
    if len(chunks) == 1:
        prompt = f"""
You are an expert academic assistant. Please summarize the following paper content in {language}.

Requirements:
- Describe: problem → motivation → method → theory(if any) → experiments → conclusions
- 3–6 paragraphs
- Avoid copying sentences verbatim

Content:
{chunks[0]}
"""
        return llm_completion(prompt.strip())

    # === 多块总结 ===
    partial_summaries = []

    for i, chunk in enumerate(chunks, start=1):
        prompt = f"""
You are an expert academic assistant. This is part {i}/{len(chunks)} of a paper.
Summarize ONLY this part in {language}.

Requirements:
- 1–3 paragraphs
- Keep technical precision
- Do not guess other sections

Content:
{chunk}
"""
        summary = llm_completion(prompt.strip())
        partial_summaries.append(summary)

    # === 合并 summaries ===
    joined = "\n\n---\n\n".join(partial_summaries)

    final_prompt = f"""
You are an expert academic assistant.

Below are partial summaries of a paper.
Merge them into ONE coherent full-paper summary in {language}.

Requirements:
- Structure: problem → motivation → method → theory(if any) → experiments → conclusion/limitations
- 3–7 paragraphs
- Avoid redundancy and contradictions
- Do NOT invent content beyond these summaries

Partial summaries:
{joined}
"""
    return llm_completion(final_prompt.strip())


# =========================================================
# 🔹 4. Paper Chat 状态 —— Sidebar 问答支持
# =========================================================

@dataclass
class PaperChatState:
    """
    维护：
    - 标题
    - 摘要（可翻译后）
    - 全文总结
    - 历史问答
    """
    paper_title: str
    paper_abstract: str
    paper_full_summary: str
    history: List[Dict] = field(default_factory=list)


def ask_paper_question(
    state: PaperChatState,
    question: str,
    language: str = "en",
) -> str:
    """
    用于 sidebar 问答：
    - 将摘要 + 总结 + 历史作为上下文
    - 严格避免幻觉
    """

    system_prompt = f"""
You are an expert assistant helping interpret a research paper.

Paper Title:
{state.paper_title}

Abstract:
{state.paper_abstract}

Full Summary:
{state.paper_full_summary}

Rules:
- Answer ONLY using the above paper info + chat history
- If the answer is not implied, say you don't know
- Respond in {language}
"""

    messages = [{"role": "system", "content": system_prompt.strip()}]
    messages.extend(state.history)
    messages.append({"role": "user", "content": question})

    answer = llm_chat(messages)

    # 追加历史
    state.history.append({"role": "user", "content": question})
    state.history.append({"role": "assistant", "content": answer})

    return answer