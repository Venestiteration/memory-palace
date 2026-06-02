# 备份策略

## 核心原则

- **本地优先**：所有数据存储在本地，不依赖云服务
- **增量备份**：利用 Git 管理文档，向量数据单独备份
- **定期验证**：每月验证备份可恢复性

## 需要备份的内容

```
memory_palace/
├── .memory_palace/
│   ├── index.sqlite          # ✅ 必须备份（核心元数据）
│   └── vector_index/          # ✅ 必须备份（向量数据）
├── 00_Inbox/                  # ✅ 必须备份（未处理内容）
├── 01_Sources/                # ✅ 必须备份（来源库）
├── 02_Atomic_Notes/           # ✅ 必须备份（核心知识）
├── 03_Maps/                    # ✅ 必须备份（结构化地图）
├── 04_Cards/                  # ✅ 必须备份（间隔重复）
├── 05_Projects/                # ✅ 必须备份（项目）
├── 06_Daily_Briefs/            # ✅ 必须备份（每日简报）
├── 07_Weekly_Synthesis/        # ✅ 必须备份（周总结）
└── 08_Outputs/                  # ✅ 必须备份（输出）
```

## 不需要备份的内容

以下内容不应包含在备份中（已在 .gitignore 中）：

```
# 不备份
.memory_palace/runtime_status.json  # 运行状态，可重建
.env                                 # API keys，绝对不备份
logs/                                # 日志文件
.DS_Store
__pycache__/
*.pyc
```

## 备份方案

### 方案 1：Git + 外部硬盘（推荐）

```bash
# 1. 初始化 Git（如果还没有）
cd ~/Program/memory_palace
git init
git remote add origin your-git-server:path/memory_palace.git

# 2. 添加需要追踪的目录（排除不需要的）
# 编辑 .gitignore，确保以下内容：
# .memory_palace/index.sqlite
# .memory_palace/vector_index/
# 这两个文件太大或可重建，先不提交

# 3. 提交文档内容
git add 00_Inbox/ 01_Sources/ 02_Atomic_Notes/ 03_Maps/ 04_Cards/ 05_Projects/ 06_Daily_Briefs/ 07_Weekly_Synthesis/ 08_Outputs/
git commit -m "备份知识库内容"

# 4. 单独备份数据库和向量
BACKUP_DIR=~/Backups/memory_palace/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR
cp .memory_palace/index.sqlite $BACKUP_DIR/
cp -r .memory_palace/vector_index $BACKUP_DIR/
tar -czf $BACKUP_DIR/vector_index.tar.gz .memory_palace/vector_index/

# 5. 定期同步到外部硬盘
rsync -avz ~/Backups/memory_palace/ /Volumes/BackupDrive/memory_palace/
```

### 方案 2：Time Machine + 定期导出

```bash
# 使用 macOS Time Machine 备份整个 home 目录
# 确保 memory_palace 在被保护的目录中

# 额外：定期导出关键数据到加密存储
python3 scripts/vault_metrics.py --json > ~/Backups/memory_palace/metrics_$(date +%Y%m%d).json
```

### 方案 3：Git LFS（大文件）

如果向量文件需要版本化管理：

```bash
# 安装 Git LFS
git lfs install

# 追踪向量文件
git lfs track "*.npy"
git add .gitattributes

# 向量文件将通过 LFS 存储
```

## 灾难恢复

### 恢复步骤

1. **恢复代码和文档**
```bash
git clone your-git-server:path/memory_palace.git ~/Program/memory_palace
```

2. **恢复索引数据**
```bash
cp backup/index.sqlite .memory_palace/
cp -r backup/vector_index .memory_palace/
```

3. **重建索引（如果需要）**
```bash
python3 scripts/build_index.py --rebuild
python3 scripts/build_vector_index.py --rebuild
```

## 备份频率

| 数据类型 | 备份频率 | 说明 |
|---------|---------|------|
| 文档内容 | 实时（Git）| 每次 commit 后自动备份 |
| SQLite 索引 | 每日 | 通过 launchd run_daily 触发 |
| 向量索引 | 每周 | 或在 run_weekly 中 |
| 完整备份 | 每月 | 导出到外部存储 |

## 验证备份

```bash
# 验证备份完整性
python3 scripts/build_index.py  # 索引正常
python3 scripts/build_vector_index.py  # 向量正常
python3 scripts/vault_metrics.py  # 健康评分正常
```

## 注意事项

- **绝对不要**把 `.env` 文件提交到 Git
- 向量索引较大（每条笔记 ~4KB），考虑使用 Git LFS 或单独备份
- 如果使用 GitHub/GitLab 等远程仓库，确保仓库是 **Private**