"""
对话服务 (RAG)

职责:
1. 管理对话会话
2. 检索相关论文上下文 (RAG)
3. 调用 LLM 生成回复

主要方法:
- create_session(): 创建新会话
- chat(message, session_id, paper_context): 发送消息
- get_relevant_context(query, paper_ids): 获取 RAG 上下文
- generate_response(messages, context): 调用 LLM
"""

# TODO: 实现对话服务

