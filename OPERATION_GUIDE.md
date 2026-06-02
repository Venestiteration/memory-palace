# memory_palace 完整操作指南

## 一、环境初始化（一次性配置）

### 设置环境变量
```bash
# LLM Chat API（必填）
export MINIMAX_API_KEY="your_minimax_api_key_here"

# 向量 Embedding API（必填）
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"

# Readwise 同步（可选）
export READWISE_TOKEN="your_readwise_token"
```

> 建议将上述配置写入 `~/.zshrc` 或 `~/.bashrc`，永久生效。

### 验证依赖
```bash
python3 scripts/validate_note.py _templates/atomic_note.md
# 预期：返回 {"ok": true}
```

---

## 二、日常捕获流程（Layer 2）

### 2.1 Telegram 消息捕获
**目的**：将 Telegram 消息转为 Markdown 笔记，进入 Inbox 待处理。

```bash
# 处理 Telegram 消息 JSON 文件
python3 scripts/capture_telegram.py <message.json>

# 示例
python3 scripts/capture_telegram.py sample_telegram_message.json
```

**输出**：生成 `00_Inbox/telegram/YYYYMMDD-HHMMSS-telegram-{id}.md`

---

### 2.2 Readwise 高亮同步
**目的**：从 Readwise 拉取书籍/文章高亮，存入来源库。

```bash
# 同步所有高亮
python3 scripts/sync_readwise.py

# 只同步指定日期后的
python3 scripts/sync_readwise.py --since 2026-05-01

# 预览模式（不写文件）
python3 scripts/sync_readwise.py --dry-run
```

**输出**：`01_Sources/articles/`, `01_Sources/books/`, `01_Sources/tweets/`

---

## 三、日常加工流程（Layer 3）

### 3.1 Inbox 扫描
**目的**：分析 Inbox 中所有笔记，生成处理建议。

```bash
# 查看待处理清单
python3 scripts/process_inbox.py --json

# 带处理动作（移动到 Archive）
python3 scripts/process_inbox.py --move-archive
```

**输出示例**：
```json
{
  "file": "00_Inbox/telegram/xxx.md",
  "suggested_action": "keep_in_inbox",  // 或 promote_to_atomic / archive
  "content_length": 128
}
```

---

### 3.2 LLM 原子化
**目的**：将 source/inbox 笔记拆解为原子笔记（一个笔记 = 一个核心主张）。

```bash
# 仅预览（不写文件）
python3 scripts/atomize_note.py 00_Inbox/telegram/xxx.md

# 写入原子笔记
python3 scripts/atomize_note.py 00_Inbox/telegram/xxx.md --write
```

**输出字段**：`title`, `core_claim`, `evidence`, `related_topics`, `suggested_links`, `counter_argument`

**输出位置**：`02_Atomic_Notes/{atomic_type}/`

---

## 四、索引构建流程（Layer 4）

### 4.1 构建元数据索引
**目的**：扫描全库 Markdown，生成 SQLite 索引（标题、标签、链接等）。

```bash
# 增量构建
python3 scripts/build_index.py

# 重建（重新扫描所有文件）
python3 scripts/build_index.py --rebuild
```

**输出**：`.memory_palace/index.sqlite`

---

### 4.2 构建向量索引
**目的**：为笔记生成 embedding 向量，支持语义搜索。

```bash
# 增量构建
python3 scripts/build_vector_index.py

# 重建
python3 scripts/build_vector_index.py --rebuild
```

**输出**：`.memory_palace/vector_index/{note_id}.npy`

---

### 4.3 语义搜索
**目的**：用自然语言搜索相关笔记。

```bash
# 基本搜索
python3 scripts/search_notes.py "期权波动率交易策略"

# 限制结果数
python3 scripts/search_notes.py "SPY" --limit 5

# 按笔记类型过滤
python3 scripts/search_notes.py "投资" --type concept
```

---

## 五、反馈生成流程（Layer 5）

### 5.1 生成每日简报
**目的**：基于过去24小时的新增/更新笔记，生成洞见简报。

```bash
# 生成本日简报
python3 scripts/generate_daily_brief.py

# 指定日期
python3 scripts/generate_daily_brief.py --date 2026-05-14

# 预览模式（不写文件）
python3 scripts/generate_daily_brief.py --dry-run
```

**输出**：`06_Daily_Briefs/YYYY-MM-DD.md`

---

### 5.2 生成每周总结
**目的**：基于过去一周的笔记，生成综合总结。

```bash
# 生成本周总结
python3 scripts/generate_weekly_synthesis.py

# 指定周
python3 scripts/generate_weekly_synthesis.py --week 2026-W20

# 预览模式
python3 scripts/generate_weekly_synthesis.py --dry-run
```

**输出**：`07_Weekly_Synthesis/YYYY-Www.md`

---

## 六、仪表盘监控（Layer 6）

在 Obsidian 中打开以下文件查看：

| 文件 | 作用 |
|------|------|
| `03_Maps/dashboard.md` | PKB 总览：新增笔记、Daily Brief、Weekly Synthesis、活跃项目 |
| `03_Maps/health_monitor.md` | 健康监控：Inbox 积压、孤岛笔记、90天未更新、无标签笔记 |
| `03_Maps/review_queue.md` | 复习队列：待加工 Inbox、候选 evergreen、需要补链接的笔记 |

> 需要 Obsidian + Dataview 插件

---

## 七、完整日常流程示例

```bash
#!/bin/bash
# === 每日流程示例 ===

# 1. 环境变量
export MINIMAX_API_KEY="sk-cp-..."
export DASHSCOPE_API_KEY="sk-..."

# 2. 同步 Readwise（如果有）
python3 scripts/sync_readwise.py --since $(date -v-1d +%Y-%m-%d)

# 3. 构建/更新索引
python3 scripts/build_index.py
python3 scripts/build_vector_index.py

# 4. 处理 Inbox
echo "=== Inbox 状态 ==="
python3 scripts/process_inbox.py --json

# 5. 原子化重要笔记（手动选择）
# python3 scripts/atomize_note.py 00_Inbox/telegram/xxx.md --write

# 6. 生成每日简报
python3 scripts/generate_daily_brief.py --dry-run
```

---

## 八、问题排查

| 问题 | 解决方法 |
|------|----------|
| `MINIMAX_API_KEY 未设置` | 确认环境变量已设置 `echo $MINIMAX_API_KEY` |
| 向量搜索报 `DASHSCOPE_API_KEY` 错误 | 确认已设置 `export DASHSCOPE_API_KEY=...` |
| `index.sqlite` 不存在 | 运行 `python3 scripts/build_index.py` |
| 笔记验证失败 | 检查 frontmatter 是否符合规范 |
| LLM 调用超时 | 增加 timeout 或检查网络 |
