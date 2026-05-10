# 📖 WhiteNote

> **像刷小红书一样刷论文**  
> *Scroll through papers like you scroll through social media*

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.52+-red.svg" alt="Streamlit">
  <img src="https://img.shields.io/badge/PostgreSQL-16-blue.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7-red.svg" alt="Redis">
</p>

---

## ✨ Features

### 📚 论文获取 Paper Fetching
- **arXiv 自动抓取**：根据关键词定时从 arXiv 获取最新论文
- **关键词订阅**：自定义关注的研究方向（如 RAG、Agent、Vector Database）
- **定时任务**：每日自动更新，不错过任何重要论文

### 🎨 AI 漫画解读 AI Comic Interpretation
- **一键生成漫画**：将枯燥的论文转化为易懂的 10 格漫画
- **Gemini 驱动**：使用 Google Gemini 生成精美插图
- **全文理解**：基于论文全文内容生成，而非仅摘要

### 🧠 AI 智能分析 AI Analysis
- **摘要翻译**：将英文摘要翻译为中文
- **全文总结**：PDF 解析 + AI 生成结构化总结
- **论文问答**：基于论文内容的多轮对话，支持流式输出

### ⭐ 收藏管理 Collection Management
- **多文件夹收藏**：创建多个收藏夹分类管理论文
- **自动处理流水线**：收藏后自动下载 PDF → 生成总结 → 生成漫画
- **不喜欢标记**：过滤不感兴趣的论文

### 📋 任务监控 Task Monitoring
- **队列可视化**：查看 AI 总结和漫画生成任务状态
- **日志追踪**：实时查看后台任务日志
- **失败重试**：一键重试失败的任务

---

## 🚀 Quick Start (Docker Compose)

WhiteNote ships as a single `docker compose` stack — Postgres + Redis + Qdrant + the WhiteNote app (Streamlit UI, RQ worker, scheduler, and **MCP server**).

```bash
git clone https://github.com/your-repo/WhiteNote.git
cd WhiteNote

# 1. configure
cp .env.example .env
$EDITOR .env                              # fill in LLM / Gemini / Zotero keys

# (optional) tune non-secret settings
cp backend/settings.example.yaml backend/settings.yaml

# 2. up
docker compose up --build
```

What you get:

| URL | Purpose |
|-----|---------|
| http://localhost:8501              | Streamlit UI (human) |
| http://127.0.0.1:8765/mcp/         | MCP endpoint (streamable HTTP, for agents) |
| http://127.0.0.1:8765/sse/         | MCP endpoint (SSE, legacy clients) |

The database is initialised automatically on first run (the `db-init` service). The worker and scheduler start once the DB is ready.

---

## 🤖 Use as MCP server

WhiteNote exposes its arXiv crawler, paper store, chat, and Zotero adapter as MCP tools so any agent (Claude Desktop, Claude Code, custom agents) can read papers, decide what's interesting, and save keepers to Zotero.

### Add to Claude Desktop / Claude Code

```jsonc
{
  "mcpServers": {
    "whitenote": {
      "url": "http://127.0.0.1:8765/mcp/"
    }
  }
}
```

For older clients that only support SSE, use `http://127.0.0.1:8765/sse/`.

### Available tools

| Tool | What it does |
|------|--------------|
| `list_recent_papers` | Most recent papers (paginated) |
| `search_papers` | Title-substring search in the local DB |
| `fetch_arxiv_now` | On-demand crawl for given keywords |
| `get_paper` | Full paper record (optionally with extracted PDF text) |
| `get_paper_summary` | Returns cached AI summary, enqueues a job if missing |
| `generate_comic` | Enqueue a comic-generation job |
| `chat_with_paper` | Multi-turn Q&A grounded in the paper |
| `mark_paper` | `liked` / `disliked` / `later` / `folder:<name>` |
| `list_liked_papers`, `list_folders` | Read agent verdicts back |
| `job_status`, `queue_stats` | Poll the RQ queue |
| `list_zotero_collections` | Fetch the user's Zotero collections |
| `save_to_zotero` | Push a paper to Zotero (optionally attach the PDF) |

### Typical agent flow

> *"What new papers came in today? Pick the most interesting one and save it to my Zotero 'Inbox' collection."*

```
fetch_arxiv_now(keywords=["RAG"])
  → list_recent_papers(limit=10)
  → get_paper(id=...)            # for the top few
  → get_paper_summary(id=...)    # may enqueue + poll
  → chat_with_paper(...)         # optional follow-up
  → mark_paper(id=..., action="liked")
  → list_zotero_collections()
  → save_to_zotero(id=..., collection_key="...")
```

### Expose for a test session (Cloudflare quick tunnel)

```bash
./scripts/tunnel.sh           # tunnel just Streamlit (safe)
./scripts/tunnel.sh mcp       # ⚠ exposes MCP — no auth, kill when done
./scripts/tunnel.sh both
```

Requires `cloudflared` on PATH (`brew install cloudflared` / apt / docker). You get a random `https://*.trycloudflare.com` URL live until you Ctrl-C — no signup needed.

### Security note

By default the MCP port is bound to **127.0.0.1** on the host (see `MCP_BIND` in `.env`). The server has no auth — set `MCP_BIND=0.0.0.0` only if you trust the network or put a reverse proxy with auth in front.

---

## 🛠️ Local development (without Docker)

Still supported:

```bash
docker compose up -d postgres redis qdrant   # infra only
cd backend
uv sync
uv run python -m src.scripts.init_db
uv run python worker.py            # terminal 1
uv run python -m src.scheduler.main  # terminal 2
uv run streamlit run app.py        # terminal 3
uv run python -m src.mcp_server.server --transport http --port 8765  # terminal 4
```

---

## 📁 项目结构

```
WhiteNote/
├── docker-compose.yaml      # PostgreSQL + Redis + Qdrant
├── backend/
│   ├── app.py               # 主应用入口
│   ├── settings.yaml        # 配置文件
│   ├── supervisord.conf     # RQ Worker 管理
│   ├── worker.py            # RQ Worker 入口
│   ├── pages/
│   │   ├── 1_Page_Detail.py # 论文详情页
│   │   └── 2_Task_Monitor.py# 任务监控页
│   └── src/
│       ├── config/          # 配置管理
│       ├── crawler/         # arXiv 爬虫
│       ├── database/        # 数据库操作
│       ├── jobs/            # 后台任务
│       ├── model/           # 数据模型
│       ├── queue/           # RQ 队列
│       ├── scheduler/       # APScheduler 定时任务
│       └── service/         # 业务服务
│           ├── chat_service.py           # 论文问答
│           ├── image_generation_service.py # 漫画生成
│           ├── llm_service.py            # LLM 封装
│           ├── pdf_download_service.py   # PDF 下载
│           └── pdf_parser_service.py     # PDF 解析
└── cache/
    ├── pdfs/                # PDF 缓存
    └── imgs/                # 漫画缓存
```

---

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | Streamlit |
| 后端 | Python 3.11+ |
| 数据库 | PostgreSQL 16 |
| 向量库 | Qdrant |
| 任务队列 | Redis + RQ |
| 定时任务 | APScheduler |
| PDF 解析 | Marker |
| LLM | LiteLLM (支持 OpenAI/Claude/...) |
| 图片生成 | Google Gemini |

---

## 📝 常用命令

```bash
# 手动抓取 arXiv 论文
uv run python -c "from src.crawler.fetch_task import run_fetch; run_fetch()"

# 查看 RQ Worker 状态
uv run supervisorctl -c supervisord.conf status

# 重启 RQ Worker
uv run supervisorctl -c supervisord.conf restart rq-worker

# 查看 Worker 日志
tail -f logs/rq-worker.log
```

---

## 📄 License

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">
  <img alt="Creative Commons License" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" />
</a>

This work is licensed under a [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-nc-sa/4.0/).

**您可以自由地：**
- ✅ 共享 — 复制、发行本作品
- ✅ 改编 — 修改、转换或基于本作品创作

**但须遵守以下条件：**
- 📝 署名 — 注明原作者
- 🚫 非商业性使用 — 不得用于商业目的
- 🔄 相同方式共享 — 衍生作品须采用相同许可证

---

<p align="center">
  Made with ❤️ for researchers who love papers
</p>
