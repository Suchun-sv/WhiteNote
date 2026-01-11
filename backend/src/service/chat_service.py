# src/service/chat_service.py

"""
Chat Service - 论文问答服务

功能：
- 创建会话（注入论文内容作为 system prompt）
- 发送问题并获取回复
- 自动生成会话标题
"""

from typing import List, Dict, Optional, Generator
import re
from litellm import completion

from src.config import Config
from src.database.chat_repository import ChatRepository
from src.model.chat import ChatSession, ChatMessage


def _convert_latex_format(text: str) -> str:
    """
    将 LaTeX 格式转换为 Streamlit markdown 支持的格式
    \\[...\\] -> $$...$$
    \\(...\\) -> $...$
    """
    # 块级公式：\[...\] -> $$...$$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    # 行内公式：\(...\) -> $...$
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    return text


def build_system_prompt(
    paper_title: str,
    paper_abstract: str,
    paper_full_text: Optional[str] = None,
    paper_summary: Optional[str] = None,
    language: str = "en",
) -> str:
    """
    构建 system prompt
    
    优先使用 full_text，其次 summary，最后只用 abstract
    """
    content_section = ""
    
    if paper_full_text:
        # 限制长度，避免 token 超限
        max_chars = 50000  # 约 12k tokens
        if len(paper_full_text) > max_chars:
            content_section = f"""
Full Paper Content (truncated):
{paper_full_text[:max_chars]}
... [content truncated for length]
"""
        else:
            content_section = f"""
Full Paper Content:
{paper_full_text}
"""
    elif paper_summary:
        content_section = f"""
Paper Summary:
{paper_summary}
"""
    else:
        content_section = f"""
Abstract:
{paper_abstract}
"""

    return f"""You are an expert research assistant helping to understand and discuss a paper.

Paper Title:
{paper_title}

{content_section}

Guidelines:
- Answer questions based ONLY on the paper content provided above
- If something is not mentioned or cannot be inferred from the paper, clearly say "I don't find this in the paper"
- Be precise and cite specific sections when possible
- Respond in {language}
- Be helpful and educational, explain technical concepts clearly
- For math formulas, use $...$ for inline math and $$...$$ for block math (NOT \\[...\\] or \\(...\\))
"""


class ChatService:
    """论文聊天服务"""
    
    def __init__(self):
        self.repo = ChatRepository()
    
    def create_session(
        self,
        paper_id: str,
        paper_title: str,
        paper_abstract: str,
        paper_full_text: Optional[str] = None,
        paper_summary: Optional[str] = None,
        language: str = "en",
    ) -> ChatSession:
        """
        创建新的聊天会话
        
        Args:
            paper_id: 论文 ID
            paper_title: 论文标题
            paper_abstract: 论文摘要
            paper_full_text: 论文全文（可选）
            paper_summary: AI 总结（可选）
            language: 回复语言
        
        Returns:
            新创建的会话
        """
        system_prompt = build_system_prompt(
            paper_title=paper_title,
            paper_abstract=paper_abstract,
            paper_full_text=paper_full_text,
            paper_summary=paper_summary,
            language=language,
        )
        
        return self.repo.create_session(
            paper_id=paper_id,
            system_prompt=system_prompt,
            title=None,  # 第一次提问后自动生成
        )
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        return self.repo.get_session(session_id)
    
    def get_sessions_by_paper(self, paper_id: str) -> List[ChatSession]:
        """获取论文的所有会话"""
        return self.repo.get_sessions_by_paper(paper_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return self.repo.delete_session(session_id)
    
    def ask(self, session_id: str, question: str) -> Optional[str]:
        """
        发送问题并获取回复（非流式）
        
        Args:
            session_id: 会话 ID
            question: 用户问题
        
        Returns:
            AI 回复，如果会话不存在返回 None
        """
        # 获取会话
        session = self.repo.get_session(session_id)
        if not session:
            return None
        
        # 添加用户消息
        self.repo.add_message(session_id, "user", question)
        
        # 构建消息列表
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]
        messages.append({"role": "user", "content": question})
        
        # 调用 LLM
        try:
            resp = completion(
                model=Config.chat_litellm.model,
                messages=messages,
            )
            answer = resp.choices[0].message.content
        except Exception as e:
            answer = f"⚠️ Error: {str(e)}"
        
        # 保存 AI 回复
        self.repo.add_message(session_id, "assistant", answer)
        
        # 如果是第一个问题，自动生成标题
        if session.title is None:
            self.repo.auto_generate_title(session_id)
        
        return answer

    def ask_stream(self, session_id: str, question: str) -> Generator[str, None, str]:
        """
        发送问题并流式获取回复（SSE）
        
        Args:
            session_id: 会话 ID
            question: 用户问题
        
        Yields:
            逐块返回的回复内容
        
        Returns:
            完整的 AI 回复
        """
        # 获取会话
        session = self.repo.get_session(session_id)
        if not session:
            yield "❌ 会话不存在"
            return "❌ 会话不存在"
        
        # 添加用户消息
        self.repo.add_message(session_id, "user", question)
        
        # 构建消息列表
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]
        messages.append({"role": "user", "content": question})
        
        # 流式调用 LLM
        full_response = ""
        try:
            resp = completion(
                model=Config.chat_litellm.model,
                messages=messages,
                stream=True,  # 启用流式
            )
            
            for chunk in resp:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
                    
        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            full_response = error_msg
            yield error_msg
        
        # 保存完整的 AI 回复
        self.repo.add_message(session_id, "assistant", full_response)
        
        # 如果是第一个问题，自动生成标题
        if session.title is None:
            self.repo.auto_generate_title(session_id)
        
        return full_response
    
    def get_session_count(self, paper_id: str) -> int:
        """获取论文的会话数量"""
        return self.repo.get_session_count(paper_id)

