# 标签体系规范

## 标签命名规则

1. **小写英文 + 斜杠分隔**：如 `trading/options`、`ai/product`
2. **层级不超过 3 层**：如 `trading/options/theta` 而非 `trading/options/theta/decay`
3. **使用缩写时注明**：如 `llm`（Large Language Model）

---

## 一级标签

| 标签 | 用途 | 说明 |
|------|------|------|
| `trading` | 交易相关 | 股票、期权、期货相关知识 |
| `ai` | AI 相关 | AI 技术、产品、行业 |
| `tech` | 技术相关 | 开发、系统架构、工具 |
| `business` | 商业相关 | 商业模式、市场、运营 |
| `learning` | 学习相关 | 读书笔记、课程、概念 |
| `people` | 人物相关 | 投资者、企业家、从业者 |
| `project` | 项目相关 | 正在进行的项目 |

---

## 二级标签

### trading/

```
trading/options        - 期权相关
trading/futures        - 期货相关
trading/stocks         - 股票相关
trading/strategy       - 交易策略
trading/risk           - 风险管理
trading/market         - 市场分析
```

### ai/

```
ai/agent              - AI Agent
ai/llm                - 大语言模型
ai/product            - AI 产品管理
ai/research           - AI 研究
ai/nlp                - 自然语言处理
```

### tech/

```
tech/python           - Python 相关
tech/architecture      - 系统架构
tech/devops           - 运维部署
tech/database         - 数据库
```

---

## 标签使用规则

1. **每条笔记至少 1 个标签**，不超过 5 个
2. **优先使用二级标签**，一级标签仅在无法归类时使用
3. **跨领域笔记可多标签**：如 AI 产品经理的笔记同时打 `ai/product` 和 `trading`
4. **避免创建新标签**：先搜索现有标签，无法满足时再申请

---

## 特殊标签

| 标签 | 用途 |
|------|------|
| `evergreen` | 长期有价值的笔记 |
| `inbox` | 待处理的原始笔记 |
| `blocker` | 当前阻塞项目的问题 |
| `question` | 待解答的问题 |
| `archived` | 已归档的笔记 |

---

## 禁止事项

- ❌ 不使用中文标签（如 `交易`）
- ❌ 不使用空格（用 `-` 替代）
- ❌ 不创建一次性标签（用完即弃）
- ❌ 不超过 3 层嵌套