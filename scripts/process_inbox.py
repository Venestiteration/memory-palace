#!/usr/bin/env python3
"""
process_inbox.py - 扫描 00_Inbox/ 并输出待处理清单

用法:
  python process_inbox.py                      # 人类可读表格
  python process_inbox.py --json              # JSON 格式输出
  python process_inbox.py --limit 5           # 最多处理 5 条
  python process_inbox.py --move-archive      # 将建议 archive 的文件移动到 09_Archive/

输出字段:
  file, created, source, type, title, suggested_action, content_length
"""

import argparse
import json
import sys
import re
import shutil
from pathlib import Path
from typing import Optional

import yaml


INBOX_DIR = Path(__file__).parent.parent / "00_Inbox"
ARCHIVE_DIR = Path(__file__).parent.parent / "09_Archive"


def extract_frontmatter(content: str) -> tuple[Optional[dict], Optional[str], str]:
    """从 markdown 内容中提取 frontmatter。"""
    if not content.startswith("---"):
        return None, None, "frontmatter 缺失"

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, None, "frontmatter 格式错误"

    yaml_content = parts[1]
    try:
        fm = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return None, None, f"YAML 解析失败: {e}"

    if not isinstance(fm, dict):
        return None, None, "frontmatter 必须是 YAML 对象"

    # 推断 note_type
    note_type = None
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

    return fm, note_type, ""


def get_body_content(content: str) -> str:
    """提取 frontmatter 之后的正文内容（去空行）"""
    if not content.startswith("---"):
        return content.strip()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return ""

    body = parts[2].strip()
    # 移除 markdown 标题后返回
    body = re.sub(r"^#.*$", "", body, flags=re.MULTILINE)
    return body.strip()


def suggest_action(fm: dict, body: str) -> str:
    """基于启发式规则推断 suggested_action。"""
    # rating >= 4 → archive
    rating = fm.get("rating", 0)
    if isinstance(rating, (int, float)) and rating >= 4:
        return "archive"

    # 内容过短 → needs_manual_review
    if not body or len(body) < 30:
        return "needs_manual_review"

    source_type = fm.get("source_type", "")

    # telegram 消息：短内容不值得升格，保持在 inbox
    if source_type == "telegram" and len(body) < 200:
        return "keep_in_inbox"

    # 内容较长（>= 200 字符）且非 telegram 来源 → promote_to_atomic
    if len(body) >= 200:
        return "promote_to_atomic"

    # 默认保持
    return "keep_in_inbox"


def unique_path(dest_dir: Path, filename: str) -> Path:
    """返回不冲突的目标路径，如有重名则追加 -1, -2 后缀。"""
    dest = dest_dir / filename
    if not dest.exists():
        return dest

    stem, suffix = filename.rsplit(".", 1) if "." in filename else (filename, "")
    counter = 1
    while True:
        new_name = f"{stem}-{counter}.{suffix}" if suffix else f"{stem}-{counter}"
        dest = dest_dir / new_name
        if not dest.exists():
            return dest
        counter += 1


def process_file(file_path: Path) -> Optional[dict]:
    """处理单个 Inbox 文件，返回清单条目或 None（出错时）。"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[警告] 无法读取文件 {file_path}: {e}", file=sys.stderr)
        return None

    fm, note_type, error = extract_frontmatter(content)
    if error or fm is None:
        print(f"[警告] 解析 frontmatter 失败 {file_path}: {error}", file=sys.stderr)
        return None

    body = get_body_content(content)
    action = suggest_action(fm, body)

    # 相对路径展示
    try:
        rel_path = file_path.relative_to(INBOX_DIR.parent)
    except ValueError:
        rel_path = file_path

    return {
        "file": str(rel_path),
        "created": fm.get("created", ""),
        "source": fm.get("source_type", fm.get("source", "")),
        "type": note_type or "unknown",
        "title": fm.get("title", ""),
        "suggested_action": action,
        "content_length": len(body)
    }


def move_to_archive(file_path: Path) -> bool:
    """将文件移动到 09_Archive/，返回是否成功。"""
    try:
        dest_path = unique_path(ARCHIVE_DIR, file_path.name)
        shutil.move(str(file_path), str(dest_path))
        print(f"[归档] {file_path.name} → {dest_path.name}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[错误] 归档失败 {file_path}: {e}", file=sys.stderr)
        return False


def print_table(items: list[dict]):
    """人类可读的表格输出。"""
    if not items:
        print("Inbox 为空。")
        return

    header = "{:<45} {:<12} {:<10} {:<20} {}".format(
        "文件", "创建日期", "来源", "动作", "标题"
    )
    print(header)
    print("-" * 120)

    for item in items:
        filename = item["file"]
        if len(filename) > 44:
            filename = "..." + filename[-41:]

        # 确保 created 是字符串
        created = str(item["created"]) if item["created"] else ""
        source = str(item["source"]) if item["source"] else ""
        action = str(item["suggested_action"]) if item["suggested_action"] else ""
        title = item["title"][:40] if item["title"] else ""

        print("{:<45} {:<12} {:<10} {:<20} {}".format(
            filename, created, source, action, title
        ))

    print()
    print("共 {} 条".format(len(items)))


def main():
    parser = argparse.ArgumentParser(description="扫描 00_Inbox/ 并输出待处理清单")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 条（0=不限制）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--move-archive", action="store_true", help="将建议 archive 的文件移动到 09_Archive/")
    args = parser.parse_args()

    if not INBOX_DIR.exists():
        print(json.dumps({"error": f"Inbox 目录不存在: {INBOX_DIR}"}))
        sys.exit(1)

    # 递归扫描所有 .md 文件
    md_files = sorted(INBOX_DIR.glob("**/*.md"))
    if not md_files:
        if args.json:
            print(json.dumps([], ensure_ascii=False, indent=2))
        else:
            print("Inbox 为空。")
        sys.exit(0)

    # 处理文件
    items = []
    for f in md_files:
        item = process_file(f)
        if item is not None:
            items.append(item)
        if args.limit > 0 and len(items) >= args.limit:
            break

    # 执行归档移动
    if args.move_archive and items:
        archive_items = [item for item in items if item["suggested_action"] == "archive"]
        for item in archive_items:
            # 从相对路径重建绝对路径
            src = INBOX_DIR.parent / item["file"]
            if src.exists():
                move_to_archive(src)
        # 刷新 items（被移动的文件不再展示）
        items = [item for item in items if item["suggested_action"] != "archive"]

    # 输出
    if args.json:
        # datetime.date 无法直接 JSON 序列化，先转字符串
        for item in items:
            if not isinstance(item["created"], str):
                item["created"] = str(item["created"])
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print_table(items)


if __name__ == "__main__":
    main()
