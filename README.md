# Memory Palace

本地个人知识操作系统，自动摄入、加工、联想、反馈。

## 系统架构

| Layer | 名称 | 功能 |
|-------|------|------|
| Layer 0 | 骨架层 | 目录结构 + 模板 + CLAUDE.md |
| Layer 1 | 数据层 | frontmatter 规范 + 验证脚本 |
| Layer 2 | 捕获层 | Telegram Bot + Readwise 同步 |
| Layer 3 | 加工层 | Inbox 处理脚本 + LLM 原子化 |
| Layer 4 | 索引层 | SQLite 元数据 + 向量库 |
| Layer 5 | 反馈层 | Daily Brief + Weekly Synthesis |
| Layer 6 | 界面层 | Dataview 仪表盘 + 健康监控 |

## 目录结构

```
memory_palace/
├── CLAUDE.md
├── README.md
├── 00_Inbox/              # 捕获入口
│   ├── quick_capture/      # 快速捕获
│   ├── telegram/           # Telegram Bot
│   ├── voice/             # 语音笔记
│   └── web_clips/         # 网页剪藏
├── 01_Sources/            # 原始来源
│   ├── articles/
│   ├── books/
│   ├── podcasts/
│   ├── tweets/
│   ├── videos/
│   └── meetings/
├── 02_Atomic_Notes/        # 原子化笔记
│   ├── concepts/
│   ├── claims/
│   ├── mental_models/
│   ├── questions/
│   ├── people/
│   └── cases/
├── 03_Maps/               # 知识地图
│   ├── topics/
│   ├── projects/
│   └── domains/
├── 04_Cards/              # 记忆卡片
│   ├── anki/
│   └── spaced_repetition/
├── 05_Projects/           # 项目
├── 06_Daily_Briefs/       # 日报
├── 07_Weekly_Synthesis/   # 周报
├── 08_Outputs/            # 输出
│   ├── essays/
│   ├── reports/
│   ├── decisions/
│   └── scripts/
├── 09_Archive/            # 归档
└── _templates/            # 模板
```

## 快速开始

1. 克隆本仓库
2. 运行 `python scripts/check_system.py` 检查系统状态
3. 运行 `python scripts/validate_note.py _templates/atomic_note.md` 验证模板
4. 开始捕获知识

## 技术栈

- Python 3.9+
- SQLite + 向量索引
- MiniMax API（LLM）+ DashScope（Embedding）
- Obsidian + Dataview