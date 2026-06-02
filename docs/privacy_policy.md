# 隐私策略

## 数据存储

memory_palace 是一个**本地优先**的个人知识操作系统。

| 数据类型 | 存储位置 | 隐私级别 |
|---------|---------|---------|
| 笔记内容 | 本地 `02_Atomic_Notes/` | 高度敏感 |
| 来源 URL | 本地 `01_Sources/` | 中等敏感 |
| Daily Brief | 本地 `06_Daily_Briefs/` | 中等敏感 |
| API keys | 本地 `.env` | 最高敏感 |
| 向量索引 | 本地 `.memory_palace/` | 低敏感 |

## 数据流动

```
输入 → Inbox → 加工层 → Atomic Notes → 向量索引 → 输出
```

**关键原则**：所有数据都在本地处理，不上传到任何外部服务。

## 外部 API 调用

以下 API 会与外部服务器通信：

| API | 数据发送 | 说明 |
|-----|---------|------|
| MiniMax API | 问题文本 + 笔记内容 | 用于 LLM 生成回答 |
| DashScope API | 笔记文本 | 用于生成 embedding 向量 |
| Readwise API | 无（只拉取） | 拉取高亮，不上传数据 |
| Telegram Bot | 消息内容 | 接收你发送的消息 |

**你发送给 API 的内容可能包含你的笔记内容。**

## MiniMax / DashScope

当使用 `ask_vault.py`、`atomize_note.py`、`generate_daily_brief.py` 时：
- 你的问题文本
- 相关笔记的完整内容
- CLAUDE.md 中的上下文信息

都会被发送到 MiniMax 或 DashScope 服务器。

## Telegram Bot

Telegram Bot 接收的消息会：
- 存储到 `00_Inbox/telegram/`
- 经过加工层处理

**建议**：不要通过 Telegram 发送高度敏感信息（如密码、银行卡号等）。

## 不上传的内容

以下内容**不会**上传到任何服务：
- `.env` 文件（包含 API keys）
- `08_Outputs/` 中的决策记录
- `04_Cards/` 中的间隔重复卡片
- 任何自定义文档模板

## 本地运行的 API 服务

`api/main.py` 启动的服务：
- **监听地址**：`127.0.0.1`（仅本地）
- **不暴露**到公网
- PWA 前端通过 `localhost` 访问

如果需要远程访问，需要自行配置反向代理（如 nginx）和 HTTPS。

## 安全建议

1. **不要提交 `.env` 到 Git**
   ```bash
   # .gitignore 已包含
   .env
   ```

2. **使用 Private Git 仓库**
   ```bash
   git init --initial-branch=main
   # 创建 Private 仓库
   git remote add origin git@github.com:your-name/memory_palace.git
   ```

3. **定期检查文件权限**
   ```bash
   # 确保 .env 只有你可见
   chmod 600 .env
   ```

4. **API Key 轮换**
   - 定期更换 API keys
   - 不在代码中硬编码 key

## 数据删除

删除笔记不会自动删除向量索引中的对应向量。如需完全删除：

```bash
# 删除笔记
rm 02_Atomic_Notes/some_note.md

# 重建索引
python3 scripts/build_index.py --rebuild
python3 scripts/build_vector_index.py --rebuild
```

## 合规性

作为个人用户，你需要确保：
- 你对使用的 API 服务有合法的使用权
- 不存储他人的隐私信息（除非你有合法授权）
- 遵守你所在地区的数据保护法规