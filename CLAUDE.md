# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhiteNote is an academic paper discovery platform — "像刷小红书一样刷论文" (scroll through papers like social media). It auto-fetches papers from arXiv, generates AI comic interpretations via Gemini, provides LLM-powered Q&A, and manages paper collections.

## Development Commands

```bash
# Start infrastructure (PostgreSQL 16, Redis 7, Qdrant)
docker-compose up -d

# Install dependencies
cd backend && uv sync

# Initialize database (first time only)
uv run python -m src.scripts.init_db

# Start RQ worker (background task processing)
uv run supervisord -c supervisord.conf
# Monitor: supervisorctl -c supervisord.conf status

# Start Streamlit app (http://localhost:8501)
uv run streamlit run app.py
```

No test suite exists yet.

## Architecture

```
Streamlit UI (app.py + pages/)
        │
  Service Layer (src/service/)
        │
  ┌─────┼──────────┬──────────┐
  ▼     ▼          ▼          ▼
Repository   Jobs (RQ)   Scheduler (APScheduler)
  │            │               │
  ▼            ▼               ▼
PostgreSQL   Redis          Cron triggers
+ Qdrant     queues         (daily_arxiv)
```

**Entry points:**
- `backend/app.py` — Main Streamlit UI (paper feed, collections, filtering)
- `backend/pages/1_Page_Detail.py` — Paper detail view, AI chat, comic display
- `backend/pages/2_Task_Monitor.py` — RQ queue monitoring dashboard
- `backend/worker.py` — RQ worker process (managed by supervisord)

**Key modules under `backend/src/`:**

| Module | Purpose |
|--------|---------|
| `config/config.py` | Pydantic Settings — loads from `settings.yaml` + `.env` + env vars. Access globally via `from src.config import Config` |
| `crawler/` | arXiv paper fetching (`ArxivClient` search + `fetch_task` orchestration) |
| `database/` | SQLAlchemy ORM models (`db/models.py`), session factory (`db/session.py`), repository classes for papers/chat/user-meta |
| `model/` | Pydantic data models (`Paper`, `ChatSession`, `ChatMessage`) |
| `service/` | Business logic — LLM calls (`llm_service`), chat (`chat_service`), PDF download/parse, Gemini comic generation |
| `jobs/` | RQ task functions — `paper_summary_job`, `paper_comic_job`, `daily_arxiv` |
| `queue/` | Redis connection + queue definitions (`summary`, `comic`, `default`) + task enqueueing helpers |
| `scheduler/` | APScheduler wrapper for cron and one-time jobs |

## Key Patterns

**Database access:** Always use `with SessionLocal() as db:` context manager. Papers are stored as JSONB in the `papers` table — serialize with `model.model_dump(mode="json")`, deserialize with `Paper.model_validate(row.paper)`. Use `_sanitize_for_jsonb()` to strip NULL bytes before writing.

**Background jobs:** RQ tasks are idempotent functions that track status via `summary_job_status` / `comic_job_status` fields (pending → running → completed/failed). Three queues exist with priority order: summary > comic > default.

**Favorite auto-pipeline:** When a user favorites a paper, it triggers: PDF download → enqueue summary job → enqueue comic job (controlled by `favorite.*` config flags).

**Streamlit singletons:** Use `@st.cache_resource` for long-lived objects (repos, scheduler, chat service). Use `st.session_state` for pagination and UI state, `st.rerun()` to trigger re-renders.

**LLM integration:** All LLM calls go through LiteLLM (`litellm` package), configured in `settings.yaml` under `chat_litellm`. Supports OpenAI, Claude, and other providers transparently.

**Configuration:** `settings.yaml` is the primary config file. Key sections: `keywords` (arXiv search terms), `chat_litellm` (LLM provider), `gemini` (comic generation), `scheduler` (cron expressions), `favorite` (auto-processing toggles), `redis`, `qdrant_database`.

## Planned Architecture Migration

See `docs/architecture-plan.md` for the planned migration from Streamlit to Next.js + FastAPI with Celery, MinIO, JWT auth, and full Docker containerization.
