# LavenderSentinel Backend

FastAPI 后端服务，提供论文管理、搜索和 AI 对话 API。

## 📁 目录结构

```
backend/
├── pyproject.toml          # Python 依赖配置 (uv/pip)
├── Dockerfile              # Docker 镜像配置
├── README.md               # 本文件
│
└── app/                    # 应用代码
    ├── __init__.py         # 包初始化，定义版本号
    ├── main.py             # FastAPI 入口，注册路由和中间件
    ├── config.py           # Pydantic Settings 配置管理
    │
    ├── models/             # Pydantic 数据模型 (请求/响应)
    │   ├── __init__.py     # 导出所有模型
    │   ├── paper.py        # Paper, Author, PaperCreate 等
    │   ├── search.py       # SearchRequest, SearchResponse 等
    │   └── chat.py         # ChatMessage, ChatRequest 等
    │
    ├── api/                # API 路由定义
    │   ├── __init__.py     # 整合所有路由到 api_router
    │   ├── papers.py       # /papers - 论文 CRUD
    │   ├── search.py       # /search - 语义搜索
    │   └── chat.py         # /chat - RAG 对话
    │
    ├── services/           # 业务逻辑层
    │   ├── __init__.py     # 导出所有服务
    │   ├── paper_service.py    # 论文采集、管理、摘要生成
    │   ├── index_service.py    # CocoIndex 向量索引
    │   └── chat_service.py     # LLM 对话 + RAG
    │
    └── db/                 # 数据库层
        ├── __init__.py     # 导出数据库组件
        ├── database.py     # 数据库连接管理
        └── models.py       # SQLAlchemy ORM 模型
```

## 📄 文件说明

### 根目录

| 文件 | 说明 |
|------|------|
| `pyproject.toml` | Python 项目配置，定义依赖和构建设置 |
| `Dockerfile` | Docker 镜像构建配置 |

### app/ 目录

| 文件 | 说明 |
|------|------|
| `main.py` | **FastAPI 入口**，创建应用实例，注册路由，配置 CORS |
| `config.py` | **配置管理**，使用 Pydantic Settings 从环境变量加载配置 |

### app/models/ 目录

| 文件 | 说明 |
|------|------|
| `paper.py` | 论文相关模型: `Author`, `Paper`, `PaperCreate`, `PaperSummary` |
| `search.py` | 搜索相关模型: `SearchRequest`, `SearchResponse`, `SearchFilters` |
| `chat.py` | 对话相关模型: `ChatMessage`, `ChatRequest`, `ChatResponse` |

### app/api/ 目录

| 文件 | 说明 |
|------|------|
| `papers.py` | 论文 API: 列表、详情、创建、删除、生成摘要 |
| `search.py` | 搜索 API: 语义搜索、关键词搜索、相似论文 |
| `chat.py` | 对话 API: 发送消息、流式响应、会话管理 |

### app/services/ 目录

| 文件 | 说明 |
|------|------|
| `paper_service.py` | 论文业务逻辑: 从 arXiv 采集、CRUD、调用 LLM 生成摘要 |
| `index_service.py` | 索引服务: CocoIndex Pipeline 管理、向量搜索 |
| `chat_service.py` | 对话服务: 会话管理、RAG 上下文检索、LLM 调用 |

### app/db/ 目录

| 文件 | 说明 |
|------|------|
| `database.py` | 数据库连接: 异步引擎创建、会话管理 |
| `models.py` | ORM 模型: `PaperORM`, `ChatSessionORM` 等数据库表 |

## 🚀 快速开始

```bash
# 安装依赖
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 运行
uvicorn app.main:app --reload
```

## 🔗 API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/papers` | 获取论文列表 |
| POST | `/api/v1/search/semantic` | 语义搜索 |
| POST | `/api/v1/chat` | 发送对话消息 |

