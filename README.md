# memory-palace

> 本地个人知识操作系统：自动摄入、加工、联想与反馈。/ A local personal knowledge operating system for capture, processing, association, and feedback.
> 
## 中文说明

### 项目简介

项目把 Markdown 知识库、LLM 原子化、SQLite 元数据、numpy 向量检索、每日/每周反馈和本地 Web 服务串成六层流水线。输入可以来自手动文本、网页剪藏、Telegram、Readwise 或语音转录，最终形成可搜索、可追问、可复盘的个人知识库。

### 六层流程

```text
capture_text/web/voice/telegram -> 00_Inbox
sync_readwise -> 01_Sources
process_inbox -> archive/keep/promote
atomize_note -> 02_Atomic_Notes
build_index + build_vector_index -> SQLite/.npy
search/ask/brief/scheduler -> 08_Outputs + local API/PWA
```

### 主要能力

- frontmatter 模板、笔记验证和原子写入（临时文件→验证→重命名，避免覆盖）。
- SQLite notes/links/tags 索引与增量向量 manifest；DashScope/MiniMax/Anthropic provider 可替换。
- Daily Brief、Weekly Synthesis、Ask Vault 和健康指标（孤岛、未打标签、stale、向量化率等）。
- FastAPI 本地接口、React/Vite PWA、Obsidian Dataview 健康视图与调度脚本。

### 快速开始

```bash
python scripts/check_system.py
python scripts/validate_note.py _templates/atomic_note.md
python scripts/mp.py --help
python scripts/mp.py capture --help
python scripts/mp.py index
python scripts/mp.py search "关键词"
```

启动 API：

```bash
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

启动 Web：

```bash
cd web
npm install
npm run dev
```

`.env` 至少应按实际使用情况配置 `MINIMAX_API_KEY`、`ANTHROPIC_API_KEY`、`DASHSCOPE_API_KEY`、`READWISE_TOKEN`；Telegram 还需要 `TELEGRAM_BOT_TOKEN`，API 认证使用 `MEMORY_PALACE_API_TOKEN`，这两个变量当前未写入 `.env.example`。

### 安全与已知限制

- API 绑定 `127.0.0.1`，但 health/jobs/metrics 路由没有认证依赖；路径穿越检查函数也未完整接入路由。
- 前端发送 `Authorization: Bearer <token>`，后端当前直接比较 header 值，Bearer 前缀约定需统一。
- LLM、Embedding、Readwise、Telegram 会接触个人内容或凭据；请做好本地权限、备份与日志管理。
- 运行时目录和笔记库可能由脚本创建，README 中的示例层级不代表全部目录已提交。

## English

### Overview

`memory-palace` is a local personal knowledge operating system. Markdown templates and validation, multi-source capture, LLM atomization, SQLite metadata, NumPy vector search, daily/weekly feedback, a local API, and a React PWA form one pipeline.

### Workflow and features

```text
capture -> Inbox -> process/atomize -> indexed notes
-> vector search / Ask Vault -> briefs, outputs, health metrics, schedules
```

The project supports manual text, web clips, Telegram, Readwise, and voice transcripts. It provides safe atomic note writes, incremental SQLite/vector indexes, replaceable model providers, FastAPI routes, a PWA, and Obsidian health views.

### Quick start

```bash
python scripts/check_system.py
python scripts/mp.py --help
python scripts/mp.py index
python scripts/mp.py search "keyword"
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
cd web && npm install && npm run dev
```

Configure model, Readwise, Telegram, and API-token variables in `.env`. `TELEGRAM_BOT_TOKEN` and `MEMORY_PALACE_API_TOKEN` are used by the source but are not currently listed in the example file.

### Security and limitations

The API is localhost-oriented but several operational routes lack authentication. The frontend/backend Bearer-token convention is inconsistent. Personal content may leave the machine through model, embedding, Readwise, or Telegram providers. Review path checks and runtime-created directories before exposing the service.

## License

No license file was found in the repository. Add one before redistribution.
