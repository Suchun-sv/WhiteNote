"""
对话 API 路由

端点:
- POST /chat            发送消息并获取回复
- POST /chat/stream     流式响应 (SSE)
- GET  /chat/sessions   获取会话列表
- GET  /chat/sessions/{id}  获取会话详情

使用示例:
    POST /api/v1/chat
    {"message": "解释一下这篇论文的方法", "paper_context": ["paper_id_1"]}
"""

# TODO: 实现对话相关 API

