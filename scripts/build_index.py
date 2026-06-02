#!/usr/bin/env python3
"""
build_index.py - 构建 SQLite 元数据索引

扫描全库 Markdown 文件，提取 frontmatter、标题、正文摘要、wikilinks，
写入 .memory_palace/index.sqlite。

用法:
  python build_index.py                      # 增量索引
  python build_index.py --rebuild            # 全量重建
  python build_index.py --db PATH            # 指定数据库路径

输出 JSON 格式索引报告。
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import yaml


PROJECT_DIR = Path(__file__).parent.parent
DEFAULT_DB_DIR = PROJECT_DIR / ".memory_palace"
DEFAULT_DB = DEFAULT_DB_DIR / "index.sqlite"

# 扫描时跳过的目录/文件
SKIP_PATTERNS = (".git", "__pycache__", ".DS_Store", ".claude")

# wikilink 正则
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# frontmatter 字段 → notes 表字段 映射
FRONTMATTER_FIELD_MAP = {
    "source_type": "type",
    "status": "status",
    "source": "source",
    "created": "created",
}


def get_db_path(db_arg: Optional[str]) -> Path:
    """解析数据库路径"""
    if db_arg:
        return Path(db_arg)
    return DEFAULT_DB


def ensure_db_dir(db_path: Path):
    """确保数据库目录存在"""
    db_path.parent.mkdir(parents=True, exist_ok=True)


def init_db(conn: sqlite3.Connection):
    """初始化数据库表结构"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            type TEXT,
            status TEXT,
            source TEXT,
            created TEXT,
            updated TEXT,
            word_count INTEGER DEFAULT 0,
            body_summary TEXT,
            has_vector INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_note_path TEXT NOT NULL,
            to_title TEXT NOT NULL,
            UNIQUE(from_note_path, to_title)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            UNIQUE(note_id, tag)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_path ON notes(path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_note_path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_note ON tags(note_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
    conn.commit()


def extract_frontmatter(content: str) -> tuple[Optional[dict], str]:
    """从 markdown 内容提取 frontmatter dict 和 note_type"""
    if not content.startswith("---"):
        return None, ""

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, ""

    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, ""

    if not isinstance(fm, dict):
        return None, ""

    # 推断 note_type
    note_type = ""
    if "source_type" in fm:
        note_type = "source"
    elif "atomic_type" in fm:
        note_type = "atomic_note"
    elif "map_type" in fm:
        note_type = "map"
    elif "project_type" in fm:
        note_type = "project"
    elif "day_summary" in fm:
        note_type = "daily_brief"
    elif "week" in fm and "start_date" in fm:
        note_type = "weekly_synthesis"

    return fm, note_type


def extract_title(content: str) -> str:
    """提取 markdown 标题（# Title）"""
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("# ") and len(line) > 2:
            return line[2:].strip()
    return ""


def extract_body(content: str) -> str:
    """提取 frontmatter 后的正文"""
    if not content.startswith("---"):
        return content.strip()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return ""
    return parts[2].strip()


def extract_wikilinks(body: str) -> list[str]:
    """从正文中提取所有 wikilink 的标题"""
    return list(set(WIKILINK_RE.findall(body)))


def extract_tags(fm: dict) -> list[str]:
    """从 frontmatter 提取 tags"""
    tags = fm.get("tags", [])
    if isinstance(tags, list):
        return [str(t) for t in tags if t]
    return []


def generate_summary(body: str, max_len: int = 200) -> str:
    """生成正文摘要（去 markdown 语法）"""
    # 移除 markdown 标题
    text = re.sub(r"^#.*$", "", body, flags=re.MULTILINE)
    # 移除代码块
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # 移除行内代码
    text = re.sub(r"`[^`]+`", "", text)
    # 移除 wikilinks 保留文字
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)
    # 移除其他链接
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 移除多余空白
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit("\n", 1)[0].rsplit(" ", 1)[0] + "..."


def scan_files(root: Path) -> list[Path]:
    """递归扫描所有 .md 文件，跳过指定目录"""
    files = []
    for path in root.rglob("*.md"):
        # 检查路径是否包含跳过目录
        parts = path.parts
        if any(p in SKIP_PATTERNS for p in parts):
            continue
        files.append(path)
    return sorted(files)


def upsert_note(conn: sqlite3.Connection, note_data: dict) -> int:
    """插入或更新 note，返回 note_id"""
    cur = conn.execute("""
        SELECT id FROM notes WHERE path = ?
    """, (note_data["path"],))
    row = cur.fetchone()

    if row:
        note_id = row[0]
        conn.execute("""
            UPDATE notes SET
                title = ?, type = ?, status = ?, source = ?,
                created = ?, updated = ?, word_count = ?, body_summary = ?
            WHERE id = ?
        """, (
            note_data["title"],
            note_data.get("type"),
            note_data.get("status"),
            note_data.get("source"),
            note_data.get("created"),
            note_data.get("updated"),
            note_data.get("word_count", 0),
            note_data.get("body_summary", ""),
            note_id
        ))
    else:
        cur2 = conn.execute("""
            INSERT INTO notes (path, title, type, status, source, created, updated, word_count, body_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_data["path"],
            note_data["title"],
            note_data.get("type"),
            note_data.get("status"),
            note_data.get("source"),
            note_data.get("created"),
            note_data.get("updated"),
            note_data.get("word_count", 0),
            note_data.get("body_summary", "")
        ))
        note_id = cur2.lastrowid

    return note_id


def upsert_link(conn: sqlite3.Connection, note_id: int, from_path: str, to_title: str):
    """插入或忽略 link"""
    conn.execute("""
        INSERT OR IGNORE INTO links (from_note_path, to_title) VALUES (?, ?)
    """, (from_path, to_title))


def upsert_tag(conn: sqlite3.Connection, note_id: int, tag: str):
    """插入或忽略 tag"""
    conn.execute("""
        INSERT OR IGNORE INTO tags (note_id, tag) VALUES (?, ?)
    """, (note_id, tag))


def build_index(db_path: Path, rebuild: bool) -> dict:
    """
    执行索引构建。

    Returns:
        索引报告 dict
    """
    ensure_db_dir(db_path)
    conn = sqlite3.connect(str(db_path))

    if rebuild:
        conn.execute("DROP TABLE IF EXISTS links")
        conn.execute("DROP TABLE IF EXISTS tags")
        conn.execute("DROP TABLE IF EXISTS notes")
        conn.execute("VACUUM")

    init_db(conn)

    files = scan_files(PROJECT_DIR)
    stats = {
        "notes_indexed": 0,
        "links_found": 0,
        "tags_found": 0,
        "errors": 0
    }

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            stats["errors"] += 1
            print(f"[警告] 无法读取文件 {file_path}: {e}", file=sys.stderr)
            continue

        # 解析 frontmatter
        fm, note_type = extract_frontmatter(content)
        title = fm.get("title", "") if fm else ""
        if not title:
            title = extract_title(content)

        body = extract_body(content)
        wikilinks = extract_wikilinks(body)
        tags = extract_tags(fm) if fm else []
        word_count = len(body.split())
        summary = generate_summary(body)

        # 构建 note_data
        note_data = {
            "path": str(file_path),
            "title": title,
            "type": note_type or (fm.get("source_type") if fm else ""),
            "status": fm.get("status") if fm else "",
            "source": fm.get("source") or fm.get("source_url", "") if fm else "",
            "created": str(fm.get("created", "")) if fm else "",
            "updated": str(fm.get("updated", "")) if fm else "",
            "word_count": word_count,
            "body_summary": summary
        }

        # upsert note
        note_id = upsert_note(conn, note_data)

        # upsert links
        for to_title in wikilinks:
            upsert_link(conn, note_id, str(file_path), to_title)
            stats["links_found"] += 1

        # upsert tags
        for tag in tags:
            upsert_tag(conn, note_id, tag)
            stats["tags_found"] += 1

        stats["notes_indexed"] += 1

    conn.commit()
    conn.close()

    stats["files_scanned"] = len(files)
    return stats


def main():
    parser = argparse.ArgumentParser(description="构建 SQLite 元数据索引")
    parser.add_argument("--rebuild", action="store_true", help="全量重建索引")
    parser.add_argument("--db", help=f"数据库路径（默认: {DEFAULT_DB}）")
    args = parser.parse_args()

    db_path = get_db_path(args.db)

    try:
        stats = build_index(db_path, args.rebuild)
        elapsed = 0.0  # 不计时，简化
        result = {
            "success": True,
            "db": str(db_path),
            "stats": stats
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"索引构建失败: {e}"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()