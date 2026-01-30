# WhiteNote 现代前后端架构升级方案

> 将 Streamlit 全栈架构升级为 Next.js + FastAPI 前后端分离架构

## 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    客户端 (Browser)                    │
│              Next.js 14+ (App Router)                │
│         React 19 + TailwindCSS + shadcn/ui          │
└──────────────────────┬──────────────────────────────┘
                       │  HTTP / WebSocket / SSE
                       ▼
┌─────────────────────────────────────────────────────┐
│                  API 网关 / BFF                       │
│              FastAPI (Python 3.12+)                   │
│         ┌──────────┬──────────┬──────────┐          │
│         │ REST API │   SSE    │ WebSocket│          │
│         │ (CRUD)   │ (流式AI) │ (实时通知)│          │
│         └──────────┴──────────┴──────────┘          │
└────┬──────────┬──────────┬──────────┬───────────────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
 PostgreSQL   Qdrant     Redis     MinIO/S3
 (结构数据)  (向量检索)  (队列+缓存) (PDF/图片)
                                     │
                                     ▼
                              Celery Workers
                           (后台任务: 爬取/AI生成)
```

## 一、前端：Next.js + React

**为什么选 Next.js：** 当前 Streamlit 无法实现真正的"刷论文"体验。Next.js 提供 SSR/SSG、App Router、流式渲染，非常适合内容密集型应用。

### 页面结构

```
app/
├── (feed)/
│   └── page.tsx              # 论文信息流（瀑布流/卡片流）
├── paper/[id]/
│   └── page.tsx              # 论文详情 + AI 对话
├── collections/
│   ├── page.tsx              # 收藏夹列表
│   └── [folderId]/page.tsx   # 收藏夹内容
├── explore/
│   └── page.tsx              # 语义搜索 + 筛选
└── tasks/
    └── page.tsx              # 任务监控面板
```

### 关键技术选型

| 关注点 | 方案 | 理由 |
|--------|------|------|
| UI 组件 | shadcn/ui + Tailwind | 可定制、轻量、美观 |
| 状态管理 | TanStack Query (React Query) | 服务端状态缓存、乐观更新、自动重获取 |
| 无限滚动 | `react-virtuoso` | 虚拟化长列表，"刷论文"的核心体验 |
| AI 流式输出 | `fetch` + ReadableStream | 接收 SSE 流，逐字渲染 AI 回复 |
| LaTeX 渲染 | KaTeX | 比 MathJax 更快，适合大量公式 |
| PDF 查看 | `react-pdf` | 内嵌 PDF 阅读器 |
| 漫画查看 | `framer-motion` + swiper | 滑动浏览漫画面板 |

### 信息流核心交互

```tsx
// 论文卡片 — 类小红书体验
<InfiniteScroll>
  <PaperCard>
    ├── 封面图 (AI 漫画首帧 / 论文首页截图)
    ├── 标题 + 作者标签
    ├── AI 一句话摘要
    └── 操作栏: [收藏] [AI问答] [详情] [不感兴趣]
  </PaperCard>
</InfiniteScroll>
```

## 二、后端：FastAPI

**为什么选 FastAPI：** 原生 async、自动 OpenAPI 文档、Pydantic 校验、SSE/WebSocket 原生支持，Python 生态无缝对接现有 LLM/ML 代码。

### API 设计

```
POST   /api/auth/login              # 用户认证（支持多用户）
GET    /api/papers?page=&keyword=   # 论文列表（分页+筛选）
GET    /api/papers/{id}             # 论文详情
POST   /api/papers/{id}/favorite    # 收藏（触发后台管线）
DELETE /api/papers/{id}/favorite    # 取消收藏
POST   /api/papers/{id}/dislike     # 标记不感兴趣

GET    /api/collections             # 收藏夹列表
POST   /api/collections             # 创建收藏夹
PUT    /api/collections/{id}        # 重命名
DELETE /api/collections/{id}        # 删除

POST   /api/chat/{paperId}         # 发起/继续对话
GET    /api/chat/{paperId}/stream   # SSE 流式 AI 回复

GET    /api/search?q=              # 语义搜索（Qdrant）

GET    /api/tasks                  # 任务队列状态
POST   /api/tasks/{id}/retry       # 重试失败任务
```

### 后端项目结构

```
backend/
├── main.py                    # FastAPI 入口
├── api/
│   ├── routes/
│   │   ├── papers.py
│   │   ├── collections.py
│   │   ├── chat.py
│   │   ├── search.py
│   │   └── tasks.py
│   ├── deps.py                # 依赖注入 (DB session, auth)
│   └── middleware.py          # CORS, 限流, 日志
├── core/
│   ├── config.py              # Pydantic Settings
│   └── security.py            # JWT 认证
├── models/                    # SQLAlchemy ORM
├── schemas/                   # Pydantic 请求/响应模型
├── services/                  # 业务逻辑层
│   ├── paper_service.py
│   ├── llm_service.py
│   ├── chat_service.py
│   ├── comic_service.py
│   └── search_service.py
├── repositories/              # 数据访问层
├── workers/
│   ├── celery_app.py          # Celery 配置
│   ├── tasks/
│   │   ├── fetch_arxiv.py
│   │   ├── generate_summary.py
│   │   ├── generate_comic.py
│   │   └── download_pdf.py
│   └── scheduler.py           # Celery Beat 定时任务
└── alembic/                   # 数据库迁移
```

### 关键改进点

#### 1. 任务队列：RQ -> Celery

```python
# Celery 相比 RQ 的优势：
# - 任务链/编排 (chain, group, chord)
# - 定时任务内置 (Celery Beat，替代 APScheduler)
# - 更好的监控 (Flower 面板)
# - 任务优先级和路由

@celery_app.task(bind=True, max_retries=3)
def process_favorite_pipeline(self, paper_id: str):
    """收藏触发的自动化管线"""
    chain(
        download_pdf.s(paper_id),
        group(
            generate_summary.s(),
            generate_comic.s(),
        )
    ).apply_async()
```

#### 2. 流式 AI 对话：SSE 端点

```python
@router.get("/chat/{paper_id}/stream")
async def chat_stream(paper_id: str, message: str):
    async def event_generator():
        async for chunk in chat_service.stream_reply(paper_id, message):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

#### 3. 数据库迁移：Alembic

```bash
# 替代手动 init_db.py，支持版本化迁移
alembic revision --autogenerate -m "add user table"
alembic upgrade head
```

## 三、基础设施改进

| 现有方案 | 升级方案 | 理由 |
|----------|----------|------|
| 本地文件存 PDF/图片 | MinIO (S3 兼容) | 可扩展、CDN 友好、支持预签名 URL |
| Supervisor 管进程 | Docker Compose 全容器化 | 环境一致性、一键部署 |
| 无用户系统 | JWT 认证 + 多用户 | 每人独立的收藏/偏好/对话历史 |
| 无缓存层 | Redis 缓存热点数据 | 论文列表、搜索结果缓存 |
| 手动 init_db | Alembic 迁移 | 安全的 schema 演进 |

### Docker Compose（完整服务编排）

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]

  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis, qdrant, minio]

  worker:
    build: ./backend
    command: celery -A workers.celery_app worker -Q default,summary,comic
    depends_on: [redis, postgres]

  beat:
    build: ./backend
    command: celery -A workers.celery_app beat
    depends_on: [redis]

  flower:
    image: mher/flower
    ports: ["5555:5555"]        # 任务监控面板

  postgres:
    image: postgres:16
  redis:
    image: redis:7
  qdrant:
    image: qdrant/qdrant
  minio:
    image: minio/minio          # 对象存储
```

## 四、额外可考虑的增强

- **推荐系统**：基于用户收藏/阅读历史，利用 Qdrant 的向量相似度做个性化论文推荐
- **社交功能**：论文评论、笔记分享、关注学者
- **PWA 支持**：Next.js 配合 Service Worker，支持离线缓存和移动端安装
- **国际化 (i18n)**：`next-intl` 支持中英双语界面

## 五、实施路径建议（Phase 概览）

### Phase 1 — 后端 API 化
- [ ] 搭建 FastAPI 项目骨架
- [ ] 迁移现有数据模型到新结构
- [ ] 实现核心 REST API（papers, collections）
- [ ] 集成 Alembic 数据库迁移
- [ ] 配置 Celery + Beat 替代 RQ + APScheduler

### Phase 2 — 前端搭建
- [ ] 初始化 Next.js 项目 (App Router)
- [ ] 实现论文信息流页面（无限滚动）
- [ ] 实现论文详情页 + PDF 查看
- [ ] 实现收藏夹管理页面
- [ ] 接入 AI 流式对话（SSE）

### Phase 3 — 基础设施升级
- [ ] 全服务 Docker Compose 编排
- [ ] MinIO 对象存储集成
- [ ] JWT 用户认证系统
- [ ] Redis 缓存策略

### Phase 4 — 增强功能
- [ ] 个性化推荐系统
- [ ] 漫画解读交互优化
- [ ] PWA 离线支持
- [ ] 国际化

---

## 六、细粒度 Milestone 开发计划

> 将上述 Phase 拆分为 10 个可独立运行、独立测试的小里程碑。
> 每个 Milestone 完成后都有明确的验收标准，确保"做一步、测一步"。

### 开发顺序总览

```
M0 (项目骨架)  →  M1 (论文列表)  →  M2 (收藏功能)  →  M3 (AI 对话)
                                                         ↓
M9 (增强功能)  ←  M8 (JWT 认证)  ←  M7 (Docker 容器化)  ←  M6 (无限滚动/搜索)
                                                         ↑
                              M4 (流式对话)  →  M5 (Celery/Alembic) ─┘
```

> **关键节点：** M0–M3 完成后即可替代现有 Streamlit 系统，具备基本可用性。

---

### Milestone 0 — 开发环境 & 项目骨架

**对应 Phase：** Phase 1 + Phase 2 的初始化部分

**目标：** FastAPI 和 Next.js 项目能跑起来，前后端能通信。

**任务清单：**
- [ ] 在 `backend/` 中创建 `main.py`（FastAPI 入口），添加 FastAPI 依赖
- [ ] 配置 CORS 中间件，允许前端 `localhost:3000` 访问
- [ ] 实现 `GET /api/health` 健康检查端点
- [ ] 用 `create-next-app` 初始化 `frontend/` 项目（App Router + TailwindCSS）
- [ ] 安装并配置 shadcn/ui
- [ ] 前端首页调用 `/api/health` 验证前后端通信

**验收标准：**
- [ ] `uvicorn main:app` 启动后，访问 `localhost:8000/docs` 能看到 Swagger UI
- [ ] `npm run dev` 启动后，访问 `localhost:3000` 能看到页面
- [ ] 页面上显示 "API 连接成功"

---

### Milestone 1 — 论文列表 API + 前端卡片流

**对应 Phase：** Phase 1（papers API）+ Phase 2（信息流页面）

**目标：** 在新前端上看到论文列表——核心功能的最小闭环。

**任务清单：**
- [ ] 后端：实现 `GET /api/papers?page=&size=&keyword=`（分页 + 筛选），复用现有 `paper_repository`
- [ ] 后端：实现 `GET /api/papers/{id}`（论文详情）
- [ ] 后端：定义 Pydantic response schema（`PaperListResponse`、`PaperDetail`）
- [ ] 后端：实现 `api/deps.py`（数据库 session 依赖注入）
- [ ] 前端：安装 TanStack Query（React Query）
- [ ] 前端：实现 `<PaperCard>` 组件（标题 + 作者 + AI 摘要）
- [ ] 前端：首页请求论文列表，用按钮翻页（先不做无限滚动）

**验收标准：**
- [ ] 打开前端首页，能看到从数据库加载的论文卡片列表
- [ ] 点击"下一页"能翻页
- [ ] 打开 `localhost:8000/docs` 能测试所有 API

---

### Milestone 2 — 收藏 & 收藏夹管理

**对应 Phase：** Phase 1（collections API）+ Phase 2（收藏夹页面）

**目标：** 能在新前端上收藏论文、管理收藏夹。

**任务清单：**
- [ ] 后端：`POST /api/papers/{id}/favorite`（收藏，指定收藏夹）
- [ ] 后端：`DELETE /api/papers/{id}/favorite`（取消收藏）
- [ ] 后端：`POST /api/papers/{id}/dislike`（标记不感兴趣）
- [ ] 后端：`GET /api/collections`（收藏夹列表）
- [ ] 后端：`POST /api/collections`（创建收藏夹）
- [ ] 后端：`PUT /api/collections/{id}`（重命名）
- [ ] 后端：`DELETE /api/collections/{id}`（删除）
- [ ] 前端：论文卡片上的收藏按钮（TanStack Query 乐观更新）
- [ ] 前端：收藏夹列表页 `/collections`
- [ ] 前端：收藏夹详情页 `/collections/[folderId]`

**验收标准：**
- [ ] 点击收藏按钮，论文出现在收藏夹中
- [ ] 能创建、重命名、删除收藏夹
- [ ] 刷新页面后收藏状态保持不变

---

### Milestone 3 — AI 对话（非流式）

**对应 Phase：** Phase 2（AI 对话初版）

**目标：** 能在论文详情页跟 AI 进行问答。先做非流式，降低复杂度。

**任务清单：**
- [ ] 后端：`POST /api/chat/{paperId}`（发送消息 + 返回 AI 完整回复）
- [ ] 后端：`GET /api/chat/{paperId}/history`（获取对话历史）
- [ ] 后端：复用现有 `chat_service` 和 `llm_service`
- [ ] 前端：论文详情页 `/paper/[id]`（展示论文元信息）
- [ ] 前端：聊天面板组件（消息气泡 + 输入框）
- [ ] 前端：调用 chat API 并展示 AI 回复

**验收标准：**
- [ ] 进入论文详情页，能看到论文标题、摘要等信息
- [ ] 输入问题后，能收到 AI 文字回复
- [ ] 刷新页面后对话历史保留

---

### Milestone 4 — AI 流式对话 + LaTeX 渲染

**对应 Phase：** Phase 2（SSE 流式对话）

**目标：** 升级为流式输出，AI 回复逐字出现，体验大幅提升。

**任务清单：**
- [ ] 后端：`GET /api/chat/{paperId}/stream?message=`（SSE 端点，`StreamingResponse`）
- [ ] 前端：用 `fetch` + `ReadableStream` 接收 SSE 事件流
- [ ] 前端：逐字渲染 AI 回复（打字机效果）
- [ ] 前端：集成 `react-markdown` 渲染 Markdown 格式
- [ ] 前端：集成 KaTeX 渲染数学公式（`rehype-katex` + `remark-math`）

**验收标准：**
- [ ] 提问后 AI 回复逐字出现，而非等待全部生成
- [ ] 回复中的数学公式（如 `$E=mc^2$`）正确渲染
- [ ] Markdown 标题、列表、代码块格式正确

---

### Milestone 5 — Alembic 迁移 + Celery 替换 RQ

**对应 Phase：** Phase 1（Alembic + Celery）

**目标：** 后端基础设施现代化，为生产环境做准备。

**任务清单：**
- [ ] 集成 Alembic，从现有表结构生成初始 migration
- [ ] 替换 RQ 为 Celery + Redis broker
- [ ] 实现 Celery Beat 替代 APScheduler（定时抓取 arXiv）
- [ ] 收藏触发管线改为 Celery chain：`download_pdf → (generate_summary | generate_comic)`
- [ ] 后端：`GET /api/tasks`（任务列表 + 状态查询）
- [ ] 后端：`POST /api/tasks/{id}/retry`（重试失败任务）
- [ ] 前端：任务监控页 `/tasks`（展示任务队列状态）

**验收标准：**
- [ ] `alembic upgrade head` 能正确初始化数据库
- [ ] 收藏论文后，Celery worker 日志显示任务在执行
- [ ] 访问 `/api/tasks` 能查看任务状态
- [ ] 前端任务页能显示正在运行/已完成/失败的任务

---

### Milestone 6 — 无限滚动 + 语义搜索

**对应 Phase：** Phase 2（无限滚动 + 搜索页）

**目标：** 实现"刷论文"核心体验，支持语义搜索。

**任务清单：**
- [ ] 前端：用 `react-virtuoso` 替换按钮翻页，实现无限滚动
- [ ] 后端：`GET /api/search?q=`（基于 Qdrant 的语义搜索）
- [ ] 前端：搜索页 `/explore`（搜索框 + 结果列表）
- [ ] 前端：筛选功能（按日期范围、关键词分类）
- [ ] 前端：搜索结果高亮

**验收标准：**
- [ ] 首页向下滚动自动加载更多论文，无需手动翻页
- [ ] 搜索框输入语义关键词（如 "transformer attention"），返回相关论文
- [ ] 列表滚动流畅，无明显卡顿（虚拟化生效）

---

### Milestone 7 — Docker 全容器化 + MinIO

**对应 Phase：** Phase 3（Docker + MinIO）

**目标：** 一条命令启动所有服务。

**任务清单：**
- [ ] 编写 `frontend/Dockerfile`（多阶段构建：build + nginx）
- [ ] 编写 `backend/Dockerfile`（Python + uvicorn）
- [ ] 完善 `docker-compose.yaml`：加入 frontend、api、worker、beat、flower、minio
- [ ] PDF 和漫画图片存储从本地文件系统迁移到 MinIO
- [ ] 后端：MinIO 客户端封装（上传、下载、预签名 URL）
- [ ] 配置 Flower 面板（任务监控 Web UI）

**验收标准：**
- [ ] `docker-compose up` 一条命令启动全部服务
- [ ] 上传的 PDF 和生成的漫画图片存储在 MinIO 中
- [ ] 访问 `localhost:5555` 能看到 Flower 任务监控面板
- [ ] 访问 `localhost:3000` 前端正常工作

---

### Milestone 8 — JWT 认证 + 多用户

**对应 Phase：** Phase 3（用户认证）

**目标：** 支持多用户，每人拥有独立的收藏、对话和偏好。

**任务清单：**
- [ ] 后端：用户表（Alembic migration）
- [ ] 后端：`POST /api/auth/register`（注册）
- [ ] 后端：`POST /api/auth/login`（登录，返回 JWT token）
- [ ] 后端：JWT 验证中间件（`api/deps.py` 中的 `get_current_user`）
- [ ] 后端：所有业务 API 加上用户隔离（收藏、对话、偏好按用户区分）
- [ ] 前端：登录 / 注册页面
- [ ] 前端：请求拦截器自动携带 `Authorization: Bearer <token>`
- [ ] 前端：未登录时重定向到登录页

**验收标准：**
- [ ] 注册新用户，登录后能正常使用
- [ ] 两个不同用户的收藏和对话互不影响
- [ ] 未登录状态访问 API 返回 401
- [ ] Token 过期后需要重新登录

---

### Milestone 9（可选）— 增强功能

**对应 Phase：** Phase 4

**目标：** 锦上添花的体验优化，按需选做。

**任务清单：**
- [ ] **个性化推荐：** 基于用户收藏/阅读历史，利用 Qdrant 向量相似度推荐论文
- [ ] **漫画查看器：** `framer-motion` + swiper 实现滑动浏览漫画面板
- [ ] **PDF 内嵌阅读：** `react-pdf` 在详情页内嵌 PDF 查看器
- [ ] **PWA 离线支持：** Service Worker 缓存已读论文
- [ ] **国际化 (i18n)：** `next-intl` 支持中英双语界面
- [ ] **Redis 缓存：** 论文列表、搜索结果热点缓存

**验收标准：**
- [ ] 推荐列表根据用户偏好变化
- [ ] 漫画面板可左右滑动浏览
- [ ] 断网后仍可查看已缓存论文
