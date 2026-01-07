"""
对话相关的 Pydantic 模型

定义的模型:
- ChatMessage: 单条消息 (角色, 内容, 时间戳)
- ChatRequest: 对话请求 (消息, 会话ID, 论文上下文)
- ChatResponse: 对话响应 (回复, 来源引用, 推荐问题)
- ChatSession: 对话会话 (消息历史)

使用示例:
    request = ChatRequest(message="这篇论文的主要贡献是什么?")
"""

# TODO: 实现对话相关模型

