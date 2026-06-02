# DEV_STATE.md

## 项目概览
memory_palace - 本地个人知识操作系统（PKB），目标是自动摄入、加工、联想、反馈。

**用户背景**：金融市场投资者（期权期货、美股、A股）+ AI产品经理 + 全栈开发工程师

**当前状态**：阶段 1-8 全部完成（2026-05-28）

**阶段进度**：
- 阶段 1：工程稳定化 ✅ 完成（2026-05-24）
- 阶段 2：知识内容体系补强 ✅ 完成（2026-05-24）
- 阶段 3：本地 API 服务层 ✅ 完成（2026-05-24）
- 阶段 4：PWA 移动 UI ✅ 完成（手机端验证保留）
- 阶段 5：多输入源扩展 ✅ 完成（2026-05-28）
- 阶段 6：自动化运营与反馈闭环 ✅ 完成（2026-05-28）
- 阶段 7：可扩展架构抽象 ✅ 完成（2026-05-28）
- 阶段 8：质量评估、安全与备份 ✅ 完成（2026-05-28）

---

## 系统架构

| Layer | 名称 | 状态 |
|-------|------|------|
| Layer 0 | 骨架层 | ✅ 完成 |
| Layer 1 | 数据层 | ✅ 完成 |
| Layer 2 | 捕获层 | ✅ 完成 |
| Layer 3 | 加工层 | ✅ 完成 |
| Layer 4 | 索引层 | ✅ 完成 |
| Layer 5 | 反馈层 | ✅ 完成 |
| Layer 6 | 界面层 | ✅ 完成 |

| 模块 | 名称 | 状态 |
|------|------|------|
| 模块一 | 运行配置与安全治理 | ✅ 完成 |
| 模块二 | 统一调用入口 mp.py | ✅ 完成 |
| 模块三 | Ask Vault 对话层 | ✅ 完成 |
| 模块四 | 真实 Telegram Bot 服务 | ✅ 完成 |
| 模块五 | 自动调度与日志 | ✅ 完成 |

| 工具 | 名称 | 状态 |
|------|------|------|
| check_system.py | 系统健康检查 | ✅ 完成 |
| run_regression_tests.py | 回归测试 | ✅ 完成 |
| api/main.py | FastAPI 服务 | ✅ 完成 |

---

## Layer 0：骨架层（完成于 2026-05-12）
- 目录结构（32个目录）
- 6个模板文件：source, atomic_note, map, project, daily_brief, weekly_synthesis
- CLAUDE.md, README.md, DEV_STATE.md, **OPERATION_GUIDE.md**

---

## Layer 1：数据层（完成于 2026-05-13）

### frontmatter 规范
- 定义在 `memory_palace_PKB_core.md`
- 6种笔记类型：source, atomic_note, map, project, daily_brief, weekly_synthesis

### validate_note.py
```
位置：scripts/validate_note.py
功能：验证 Markdown frontmatter 规范
退出码：0（通过）/ 1（失败）/ 2（致命错误）
支持：source_type 枚举包含 telegram
```

---

## Layer 2：捕获层（完成于 2026-05-13）

### capture_telegram.py
```
位置：scripts/capture_telegram.py
输入：Telegram message JSON 文件（sys.argv[1]）
输出：00_Inbox/telegram/YYYYMMDD-HHMMSS-telegram-{message_id}.md
参数：--help, --test
frontmatter：source 类型，source_type=telegram
```

### sync_readwise.py
```
位置：scripts/sync_readwise.py
输入：环境变量 READWISE_TOKEN
参数：--since YYYY-MM-DD, --dry-run
输出：01_Sources/{articles,books,tweets}/readwise-{source_id}.md
幂等：已存在文件不覆盖
```

---

## Layer 3：加工层（完成于 2026-05-13）

### process_inbox.py
```
位置：scripts/process_inbox.py
功能：扫描 00_Inbox/，输出待处理 JSON 清单
参数：--limit N, --json, --move-archive
输出字段：file, created, source, type, title, suggested_action, content_length

suggested_action 规则：
  - rating >= 4 → archive
  - 内容 < 30 字符 → needs_manual_review
  - source_type == telegram 且内容 < 200 字符 → keep_in_inbox
  - 内容 >= 200 字符 → promote_to_atomic

默认不修改任何文件。--move-archive 将 archive 文件移至 09_Archive/。
文件名冲突处理：自动追加 -1, -2 后缀。
```

### atomize_note.py
```
位置：scripts/atomize_note.py
输入：source/inbox Markdown 文件路径
环境变量：MINIMAX_API_KEY 或 ANTHROPIC_API_KEY（必填）
参数：--write

输出 JSON 字段：title, core_claim, evidence, related_topics, suggested_links, counter_argument

--write 模式：
  - 写入 02_Atomic_Notes/{atomic_type}/
  - 原子写策略：temp file → validate_note.py → commit（失败删除 temp）
  - 防覆盖：目标文件存在则跳过
  - frontmatter 必填字段自动补全（id, title）

atomic_type 推断：根据标题/内容关键词匹配（concept/claim/mental_model/question/people/case/method/tool/resource）

Prompt 独立文件：scripts/prompts/atomize_note.md

错误处理：
  - 无 API key → 清晰报错（exit code 2）
  - LLM 调用失败 → 不产生半成品
  - 验证失败 → 删除 temp 文件

API 配置：MiniMax-M2.7 Chat API
```

---

## Layer 4：索引层（完成于 2026-05-14）

### build_index.py
```
位置：scripts/build_index.py
功能：扫描全库 Markdown，生成 SQLite 元数据索引
参数：--rebuild, --db PATH
输出：JSON 格式索引报告

数据库：.memory_palace/index.sqlite
三张表：
  - notes: id, path, title, type, status, source, created, updated, word_count, body_summary, has_vector
  - links: id, from_note_path, to_title（记录 [[wikilinks]]）
  - tags: id, note_id(FK), tag

幂等性：重复运行不会产生重复记录（INSERT OR IGNORE）
```

### build_vector_index.py
```
位置：scripts/build_vector_index.py
功能：读取 SQLite，对笔记生成 embedding 向量
参数：--rebuild, --db PATH
依赖：embedding_provider.py

向量库：.memory_palace/vector_index/
  - manifest.json：note_id → vector_file 映射
  - {note_id}.npy：numpy 二进制向量文件（1024 维）

可重复运行：增量构建，跳过已有向量（除非 --rebuild）
```

### search_notes.py
```
位置：scripts/search_notes.py
功能：语义搜索笔记
用法：python search_notes.py "查询文本" [--limit N] [--type TYPE] [--project PROJECT]

输出 JSON：{query, results: [{path, title, score, snippet, type, source}], total, provider}

搜索流程：
  1. 对查询文本生成 embedding（via EmbeddingProvider）
  2. 加载 manifest 和所有 .npy 向量
  3. 计算 cosine similarity
  4. 按 type/project 过滤
  5. 排序返回 top N

过滤参数：--type（笔记类型）, --project（来源/项目）
```

### embedding_provider.py
```
位置：scripts/embedding_provider.py
功能：Embedding Provider 抽象层

Provider 选择（按环境变量优先级）：
  - DASHSCOPE_API_KEY → DashScopeEmbeddingProvider（text-embedding-v4, 1024维）✅ 优先
  - ANTHROPIC_API_KEY → MiniMaxEmbeddingProvider（备选）

抽象接口：
  class EmbeddingProvider(ABC):
      def embed(text: str) -> list[float]: ...
      def dimension() -> int: ...

未来可替换为 Ollama 等本地模型，无需修改调用方代码。
```

---

## Layer 5：反馈层（完成于 2026-05-14）

### generate_daily_brief.py
```
位置：scripts/generate_daily_brief.py
功能：生成每日简报
参数：--date YYYY-MM-DD, --dry-run, --db PATH
输出：06_Daily_Briefs/YYYY-MM-DD.md
环境变量：MINIMAX_API_KEY 或 ANTHROPIC_API_KEY（必填）
```

### generate_weekly_synthesis.py
```
位置：scripts/generate_weekly_synthesis.py
功能：生成每周总结
参数：--week YYYY-Www, --dry-run, --db PATH
输出：07_Weekly_Synthesis/YYYY-Www.md
环境变量：MINIMAX_API_KEY 或 ANTHROPIC_API_KEY（必填）
```

### Prompt 文件
```
scripts/prompts/daily_brief.md - Daily Brief LLM prompt
scripts/prompts/weekly_synthesis.md - Weekly Synthesis LLM prompt
```

---

## Layer 6：界面层（完成于 2026-05-14）

### Obsidian Dataview 仪表盘

| 文件 | 作用 |
|------|------|
| 03_Maps/dashboard.md | PKB 总览：新增笔记、Daily Brief、Weekly Synthesis、活跃项目、最近输出 |
| 03_Maps/health_monitor.md | 健康监控：Inbox 积压、孤岛笔记、90天未更新、无标签笔记、status 分布 |
| 03_Maps/review_queue.md | 复习队列：待加工 Inbox、候选 evergreen、可转 card、需要补链接的笔记 |

依赖：Obsidian Dataview 插件

---

## 模块一：运行配置与安全治理（完成于 2026-05-14）

### 新增文件

| 文件 | 作用 |
|------|------|
| `.env` | 环境变量配置（含真实 API key，不提交） |
| `.env.example` | 环境变量模板（不包含真实 key） |
| `.gitignore` | 忽略 .env、索引文件、缓存、日志 |
| `requirements.txt` | Python 依赖清单 |
| `scripts/config.py` | 统一配置加载模块 |

### scripts/config.py
```
位置：scripts/config.py
功能：统一加载项目根目录和环境变量

主要接口：
  get_settings() -> Settings
    返回项目配置（project_root, minimax_api_key, dashscope_api_key, 等）

  load_env_file(env_path) -> None
    加载 .env 文件到环境变量（如果存在）

使用示例：
  from scripts.config import get_settings
  settings = get_settings()
  print(settings.project_root)
```

### 环境变量（通过 scripts/config.py 管理）

| 变量名 | 必填 | 说明 |
|--------|------|------|
| MINIMAX_API_KEY | 是 | MiniMax Chat API |
| DASHSCOPE_API_KEY | 是 | DashScope Embedding API |
| READWISE_TOKEN | 否 | Readwise 同步 |
| TELEGRAM_BOT_TOKEN | 否 | Telegram Bot（模块四） |

### 安全治理

- ✅ 真实 API key 不存在于任何代码或文档中
- ✅ `.gitignore` 已配置，索引数据和 .env 不会被提交
- ✅ `.env.example` 作为模板，用户复制后自行填入真实 key

### 验证命令
```bash
python -c "from scripts.config import get_settings; print(get_settings().project_root)"
# 预期输出：/Users/venest/Program/memory_palace
```

---

## 模块二：统一调用入口 mp.py（完成于 2026-05-14）

### scripts/mp.py
```
位置：scripts/mp.py
功能：Memory Palace 统一 CLI 入口

子命令：
  validate    验证笔记 frontmatter
  capture     捕获 Telegram 消息
  sync        同步 Readwise 高亮
  inbox       扫描 Inbox
  atomize     LLM 原子化笔记
  index       构建 SQLite 元数据索引
  vector      构建向量索引
  search      语义搜索
  brief       生成简报
  ask         Ask Vault 问答
  bot         Telegram Bot 轮询服务
  scheduler   调度任务（daily/weekly/sync）
  launchd     安装 launchd 定时任务

用法示例：
  python mp.py validate _templates/atomic_note.md
  python mp.py inbox --json
  python mp.py search "SPY" --limit 3
  python mp.py brief daily --dry-run
  python mp.py brief weekly --dry-run
  python mp.py ask "SPY相关"
  python mp.py bot --once
  python mp.py scheduler daily --dry-run
  python mp.py launchd --list
```

### 验证命令
```bash
python scripts/mp.py --help           # 显示帮助
python scripts/mp.py inbox --json     # 扫描 Inbox
python scripts/mp.py search "SPY"     # 语义搜索
python scripts/mp.py ask "期权策略"    # Ask Vault 问答
python scripts/mp.py launchd --list   # 查看定时任务
```

---

## 模块三：Ask Vault 对话层（完成于 2026-05-14）

### scripts/ask_vault.py
```
位置：scripts/ask_vault.py
功能：接收自然语言问题，通过向量搜索获取相关笔记，调用 LLM 生成回答

用法：
  python ask_vault.py "SPY相关笔记有哪些？"
  python ask_vault.py "期权希腊字母" --limit 5
  python ask_vault.py "帮我分析交易" --save decisions

参数：
  query              自然语言问题
  --limit N          搜索的笔记数量（默认: 5）
  --save {category}  保存到 08_Outputs/{decisions,reports,essays}/
  --json             JSON 输出

输出：
  默认输出到 stdout（带来源引用）
  --save 参数保存到 08_Outputs/{category}/YYYYMMDD-HHMMSS-*.md
```

### scripts/prompts/ask_vault.md
```
位置：scripts/prompts/ask_vault.md
功能：Ask Vault LLM prompt 模板

要点：
  - 直接回答问题
  - 引用来源（格式：来源：path/to/note.md）
  - 指出知识缺口
  - 中文回答
```

### 实现要点
- 调用 embedding_provider.py 获取向量搜索能力
- 读取 CLAUDE.md 作为用户上下文
- 向量搜索结果取 Top K 后读取完整内容
- LLM 调用使用 MiniMax-M2.7 API
- 回答包含引用路径
- --save 支持 decisions/reports/essays 三种分类

### 验证命令
```bash
python scripts/ask_vault.py --help           # 显示帮助
python scripts/ask_vault.py "SPY" --limit 3 # 搜索并回答
python scripts/mp.py ask "SPY" --json        # 通过 mp.py 调用
```

---

## 模块四：真实 Telegram Bot 服务（完成于 2026-05-14）

### scripts/telegram_bot_service.py
```
位置：scripts/telegram_bot_service.py
功能：Telegram Bot 轮询服务，从 Telegram 获取消息并写入 Inbox

用法：
  python telegram_bot_service.py              # 持续轮询（5秒间隔）
  python telegram_bot_service.py --once       # 执行一次后退出
  python telegram_bot_service.py --interval 10 # 10秒间隔
  python scripts/mp.py bot --once             # 通过 mp.py 调用

参数：
  --once              执行一次后退出
  --interval N        轮询间隔秒数（默认: 5）
  --dry-run           不写入文件，只打印会处理的消息

环境变量：
  TELEGRAM_BOT_TOKEN - Telegram Bot Token（必填）

日志：
  logs/telegram_bot.log
```

### 实现要点
- 使用 Telegram getUpdates API 轮询消息
- 保存 last_update_id 到 `.memory_palace/telegram_last_update_id`，避免重复处理
- 将消息转换为 capture_telegram.py 支持的 JSON 格式
- 原子写入：temp file → validate_note.py → commit（失败删除 temp）
- 防覆盖：文件已存在则跳过
- 不打印完整 token（只显示前10位）
- 支持 Unix 时间戳和 ISO 字符串格式的日期

### 验证命令
```bash
python scripts/telegram_bot_service.py --help # 显示帮助
python scripts/telegram_bot_service.py --once # 单次执行
python scripts/mp.py bot --once              # 通过 mp.py 调用

# 测试无 token 错误
unset TELEGRAM_BOT_TOKEN
python scripts/telegram_bot_service.py --once
# 预期：错误提示 "环境变量 TELEGRAM_BOT_TOKEN 未设置"
```

---

## 模块五：自动调度与日志（完成于 2026-05-14）

### scripts/run_daily.py
```
位置：scripts/run_daily.py
功能：每日例行任务
流程：build_index → build_vector_index → generate_daily_brief
用法：
  python run_daily.py              # 执行全流程
  python run_daily.py --dry-run    # 预览模式
```

### scripts/run_weekly.py
```
位置：scripts/run_weekly.py
功能：每周例行任务
流程：build_index → build_vector_index → generate_weekly_synthesis
用法：
  python run_weekly.py              # 执行全流程
  python run_weekly.py --dry-run    # 预览模式
```

### scripts/run_sync.py
```
位置：scripts/run_sync.py
功能：同步任务
流程：sync_readwise（失败继续）→ telegram_bot_service --once
用法：
  python run_sync.py              # 执行全流程
  python run_sync.py --dry-run    # 预览模式
```

### scripts/install_launchd.py
```
位置：scripts/install_launchd.py
功能：安装/卸载 macOS launchd 定时任务
用法：
  python install_launchd.py --dry-run          # 预览将安装的任务
  python install_launchd.py --install          # 安装所有任务
  python install_launchd.py --install daily    # 只安装每日任务
  python install_launchd.py --uninstall        # 卸载所有任务

定时任务：
  - daily:  每天 08:00 执行 index → vector → daily brief
  - weekly: 每周一 08:30 执行 index → vector → weekly synthesis
  - sync:   每天 07:00, 19:00 执行 Readwise + Telegram 同步

日志：
  logs/run_daily_YYYYMMDD.log
  logs/run_weekly_YYYYMMDD.log
  logs/run_sync_YYYYMMDD.log
```

### 实现要点
- 所有 runner 支持 --dry-run
- load_env() 自动加载 .env 文件
- 命令失败时日志记录完整错误信息（退出码、stdout、stderr）
- API key 不写入 plist，通过 .env 读取
- 任务失败时终止执行，不继续下一步

### 验证命令
```bash
python scripts/run_daily.py --dry-run
python scripts/run_weekly.py --dry-run
python scripts/run_sync.py --dry-run
python scripts/install_launchd.py --install --dry-run
python scripts/mp.py scheduler daily --dry-run
python scripts/mp.py launchd --list
```

---

## 目录结构

```
memory_palace/
├── .memory_palace/               # 系统索引数据（不要提交到 Git）
│   ├── index.sqlite             # SQLite 元数据索引
│   ├── vector_index/            # 向量索引
│   │   ├── manifest.json
│   │   └── *.npy                # numpy 向量文件
│   └── telegram_last_update_id   # Telegram Bot 状态文件
├── .env                          # 环境变量配置（含真实 API key）
├── .env.example                  # 环境变量模板
├── .gitignore                    # Git 忽略配置
├── requirements.txt               # Python 依赖
├── logs/                         # 运行日志
│   ├── telegram_bot.log
│   ├── run_daily_YYYYMMDD.log
│   ├── run_weekly_YYYYMMDD.log
│   └── run_sync_YYYYMMDD.log
├── 00_Inbox/                     # 原始捕获
│   └── telegram/                 # Telegram 捕获
├── 01_Sources/                   # 来源库
│   ├── articles/
│   ├── books/
│   └── tweets/
├── 02_Atomic_Notes/              # 原子笔记
├── 03_Maps/                      # 内容地图
│   ├── dashboard.md              # PKB 总览仪表盘
│   ├── health_monitor.md         # 健康监控
│   └── review_queue.md          # 复习队列
├── 04_Cards/                     # 间隔重复卡片
├── 05_Projects/                  # 项目
├── 06_Daily_Briefs/              # 日简报
├── 07_Weekly_Synthesis/          # 周总结
├── 08_Outputs/                   # 输出成果
│   ├── decisions/
│   ├── reports/
│   └── essays/
├── 09_Archive/                   # 归档
├── _templates/                   # 6 种笔记模板
├── scripts/
│   ├── mp.py                    # 统一 CLI 入口
│   ├── config.py                # 配置加载模块
│   ├── validate_note.py         # frontmatter 验证
│   ├── capture_telegram.py      # Telegram 捕获（JSON 文件）
│   ├── telegram_bot_service.py  # Telegram Bot 轮询服务
│   ├── sync_readwise.py         # Readwise 同步
│   ├── process_inbox.py         # Inbox 处理
│   ├── atomize_note.py          # LLM 原子化
│   ├── build_index.py           # SQLite 索引
│   ├── build_vector_index.py    # 向量索引
│   ├── search_notes.py         # 语义搜索
│   ├── embedding_provider.py    # Embedding 抽象层
│   ├── generate_daily_brief.py  # 每日简报
│   ├── generate_weekly_synthesis.py  # 每周总结
│   ├── ask_vault.py            # Ask Vault 问答
│   ├── run_daily.py            # 每日例行任务
│   ├── run_weekly.py           # 每周例行任务
│   ├── run_sync.py             # 同步任务
│   ├── install_launchd.py      # launchd 安装器
│   └── prompts/
│       ├── atomize_note.md
│       ├── daily_brief.md
│       ├── weekly_synthesis.md
│       └── ask_vault.md
├── memory_palace_PKB_core.md    # 核心构建文档
├── OPERATION_GUIDE.md           # 完整操作指南
└── DEV_STATE.md                # 项目状态文档
```

---

## 技术约束
- 操作系统：macOS
- 主要语言：Python 3.9+
- 外部依赖：requests, pyyaml, numpy
- LLM API：MiniMax-M2.7（Chat）via MINIMAX_API_KEY
- Embedding API：DashScope text-embedding-v4（1024维）via DASHSCOPE_API_KEY
- 禁止：Docker、ORM

---

## 环境变量配置

```bash
# .env 文件（不提交到 Git）
MINIMAX_API_KEY="sk-cp-..."
DASHSCOPE_API_KEY="sk-..."
READWISE_TOKEN="your_token"
TELEGRAM_BOT_TOKEN="your_token"
```

---

## 健康检查结果（2026-05-24）

| 检查项 | 状态 |
|--------|------|
| check_system.py | ✅ 正常运行 |
| run_regression_tests.py | ✅ 3/3 通过 |
| 模板验证（6/6） | ✅ 全部通过（已修复 daily_brief/weekly_synthesis） |
| build_index.py | ✅ 索引正常 |
| build_vector_index.py | ✅ 向量正常（28 vectors） |
| search_notes.py | ✅ 语义搜索正常 |
| generate_daily_brief.py | ✅ MiniMax API 正常 |
| generate_weekly_synthesis.py | ✅ MiniMax API 正常 |
| ask_vault.py | ✅ LLM 回答正常 |
| telegram_bot_service.py | ✅ Bot API 正常 |
| run_daily.py --dry-run | ✅ 成功 |
| run_weekly.py --dry-run | ✅ 成功 |
| run_sync.py --dry-run | ✅ 成功 |
| install_launchd.py | ✅ 已安装并加载（daily/weekly/sync） |
| Obsidian 仪表盘文件 | ✅ 全部存在 |

### 阶段 1 工程稳定化（完成于 2026-05-24）

| 任务 | 状态 |
|------|------|
| 新增 scripts/check_system.py | ✅ 完成 |
| 新增 scripts/run_regression_tests.py | ✅ 完成 |
| 统一目录命名 concept→concepts | ✅ 完成 |
| 清理 README.md 过期命令 | ✅ 完成 |
| 确认核心脚本 --help | ✅ 全部通过 |
| .gitignore 检查 | ✅ 配置正确 |
| 回归测试流程 | ✅ 建立完成 |
| 修复模板警告 | ✅ daily_brief/weekly_synthesis |
| 安装 launchd 服务 | ✅ daily/weekly/sync 已加载 |

### 阶段 2 知识内容体系补强（完成于 2026-05-24）

| 任务 | 状态 |
|------|------|
| 强化 CLAUDE.md | ✅ 添加项目/MAP/AI协作规则 |
| 创建核心项目页 | ✅ 3 个（投资研究/AI产品/memory_palace） |
| 创建核心主题 MAP | ✅ 3 个（期权交易/AI-Agent/美股） |
| 定义标签体系 | ✅ docs/tag_taxonomy.md |
| 定义笔记生命周期 | ✅ docs/note_lifecycle.md |
| 更新验收清单 | ✅ 全部通过 |

### 阶段 3 本地 API 服务层（完成于 2026-05-24）

| 任务 | 状态 |
|------|------|
| API 服务层 | ✅ api/ 目录结构 |
| 核心接口 | ✅ health/capture/inbox/search/ask/brief |
| 安全验证 | ✅ Token 验证（写操作需要 token） |
| 监听地址 | ✅ 127.0.0.1（不暴露公网） |
| 依赖更新 | ✅ requirements.txt 添加 fastapi/uvicorn/pydantic |

---

## 阶段 4：PWA 移动 UI（完成于 2026-05-25）

### web/ 前端应用

| 文件 | 作用 |
|------|------|
| `web/src/App.tsx` | 路由 + BottomNav |
| `web/src/lib/types.ts` | TypeScript 接口镜像 backend schemas |
| `web/src/lib/api.ts` | fetch 封装，自动注入 Bearer token |
| `web/src/contexts/SettingsContext.tsx` | localStorage 读写 apiUrl + token |
| `web/src/components/BottomNav.tsx` | 固定底部导航 |
| `web/src/components/Header.tsx` | 顶部栏 + 设置入口 |
| `web/src/pages/CapturePage.tsx` | 文本捕获 → POST /capture/text |
| `web/src/pages/AskPage.tsx` | 问答 + 引用来源展示 |
| `web/src/pages/BriefPage.tsx` | 日报/周报切换展示 |
| `web/src/pages/InboxPage.tsx` | 待处理队列 |
| `web/src/pages/HealthPage.tsx` | 系统健康状态 |
| `web/src/pages/SettingsPage.tsx` | API URL + Token 配置 |

### 技术栈
- Vite + React + TypeScript
- vite-plugin-pwa（PWA manifest + service worker）
- Tailwind CSS v4（@tailwindcss/postcss）
- React Router

### PWA 配置
- `theme_color: "#0f0f23"`, `background_color: "#0f0f23"`
- `display: "standalone"`, `start_url: "/"`
- NetworkFirst 策略缓存 API 请求

### 验证命令
```bash
cd web && npm run build        # 构建成功
# 启动 backend: python -m uvicorn api.main:app --reload
# 启动 frontend: npm run preview
```

---

## 阶段 5：多输入源扩展（完成于 2026-05-28）

### 新增 Capture Provider 结构

| 文件 | 作用 |
|------|------|
| `scripts/capture_provider.py` | CaptureResult 数据类 + 辅助函数 |
| `scripts/capture_text.py` | 快速文本捕获 → 00_Inbox/quick_capture/ |
| `scripts/capture_web_clip.py` | 网页剪藏 → 00_Inbox/web_clips/ |
| `scripts/capture_voice.py` | 语音转录文本 → 00_Inbox/voice/ |

### CaptureResult 统一格式
```python
{
    "id": "manual-20260528111212-cd34",
    "source_type": "manual|web|voice",
    "title": "标题",
    "content": "内容",
    "created": "2026-05-28T11:12:12.311863",
    "tags": ["manual"],
    "source_url": "https://...",
    "author": "作者",
    "rating": 0,
}
```

### 新增 API 端点
- `POST /capture/text` - 文本捕获
- `POST /capture/web` - 网页剪藏
- `POST /capture/voice` - 语音转录

### source_type 枚举扩展
- 新增 `manual`、`voice` 到 `validate_note.py` 允许列表

### 验证命令
```bash
python scripts/capture_text.py "文本" "标题"
python scripts/capture_web_clip.py <url> <title> <content>
python scripts/capture_voice.py <transcript> [title]
python scripts/mp.py capture text "内容" "标题"
python scripts/mp.py capture web <url> <title> <content>
python scripts/mp.py capture voice <transcript> [title]
```

---

## 阶段 6：自动化运营与反馈闭环（完成于 2026-05-28）

### 新增运行时状态记录

| 文件 | 作用 |
|------|------|
| `scripts/runtime_status.py` | 运行时状态管理（写入 runtime_status.json） |
| `api/routes/jobs.py` | GET /jobs/status API |
| `api/services/health_service.py` | 新增 get_job_status() |

### runtime_status.json 结构
```json
{
  "daily": {
    "job": "daily",
    "status": "success|failure|running",
    "date": "2026-05-28",
    "time": "13:32:46",
    "started_at": "2026-05-28T13:32:42",
    "ended_at": "2026-05-28T13:32:46",
    "duration_seconds": 98.2,
    "steps": [
      {"name": "build_index", "status": "success"},
      {"name": "build_vector_index", "status": "success"},
      {"name": "generate_daily_brief", "status": "success"}
    ],
    "error": "错误信息（失败时）"
  },
  "history": [...]
}
```

### 增强的 runner 脚本
- `run_daily.py` - 记录状态到 runtime_status.json
- `run_weekly.py` - 记录状态到 runtime_status.json
- `run_sync.py` - 记录状态到 runtime_status.json

### 诊断信息
失败时自动生成诊断建议：
- "数据库被占用" → 建议关闭其他访问进程
- "API key" → 检查 .env 配置
- "connection/timeout" → 检查网络

### 新增 API 端点
- `GET /jobs/status` - 返回 daily/weekly/sync 三个任务的状态
- `GET /health/detailed` - 已包含 jobs 状态

### 验证命令
```bash
python scripts/run_daily.py --dry-run
python scripts/runtime_status.py
# API: GET /jobs/status
```

---

## 阶段 7：可扩展架构抽象（进行中）

### Provider 抽象层

| 文件 | 作用 |
|------|------|
| `scripts/llm_provider.py` | LLM Provider 抽象层（新增） |
| `scripts/embedding_provider.py` | Embedding Provider 抽象层（已有） |

### LLM Provider 接口
```python
class LLMProvider(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, user_message: str, **kwargs) -> str: ...

    @abstractmethod
    def name(self) -> str: ...
```

### 已实现 Provider
- `MiniMaxLLMProvider` - MiniMax-M2.7（优先）
- `AnthropicLLMProvider` - Claude Sonnet（备选）

### 已迁移脚本
- `ask_vault.py` - 已使用 `get_llm_provider()` 替代硬编码 API 调用

### 未来扩展方向
- `OpenAILLMProvider` - OpenAI GPT 系列
- `LocalOllamaProvider` - Ollama 本地模型
- `StorageService` - 存储服务抽象
- `SearchService` - 搜索服务抽象

### 验证命令
```bash
python scripts/ask_vault.py "测试问题" --json
```

---

## 阶段 8：质量评估、安全与备份（完成于 2026-05-28）

### 新增文件

| 文件 | 作用 |
|------|------|
| `scripts/vault_metrics.py` | Vault 健康评分与质量指标 |
| `docs/backup_strategy.md` | 备份策略文档 |
| `docs/privacy_policy.md` | 隐私策略文档 |
| `api/routes/metrics.py` | GET /metrics API |
| `api/services/metrics_service.py` | 健康指标服务 |

### 健康评分维度
- Inbox 积压数
- 孤岛笔记比例
- 标签缺失率
- 过期 seedling 数量
- 向量化率
- 链接密度

### 健康评分公式
```
score = 100
- Inbox > 50: -30, > 20: -20, > 10: -10
- 孤岛比例 > 30%: -25, > 20%: -15, > 10%: -10
- 标签缺失 > 50%: -20, > 30%: -15, > 10%: -10
- 过期 seedling > 20: -15, > 10: -10, > 5: -5
- 向量化率 < 30%: -10, < 50%: -5
```

### API 端点
- `GET /metrics` - 返回 Vault 健康指标

### PWA Health 页面
- 新增"Vault 健康评分"卡片
- 显示评分、等级、数量统计

### 验证命令
```bash
python scripts/vault_metrics.py
# 输出: Vault 健康评分: 50/100 (一般)
```

---

## 下次会话入口

```
"运行 python scripts/run_regression_tests.py 检查系统状态"
```