#!/usr/bin/env python3
"""
sync_readwise.py - 从 Readwise 同步高亮到知识库

用途：拉取 Readwise highlights，按来源聚合后写入 01_Sources/
使用方式：
  python sync_readwise.py                       # 同步所有
  python sync_readwise.py --since 2026-05-01    # 只同步指定日期后的
  python sync_readwise.py --dry-run             # 不写文件，只预览

环境变量：
  READWISE_TOKEN - Readwise API token（必填）
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, date
from typing import Optional

try:
    import requests
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "缺少依赖: requests。请运行: pip install requests",
        "exit_code": 2
    }, ensure_ascii=False, indent=2))
    sys.exit(2)


READWISE_API = "https://readwise.io/api/v2"
SOURCE_TYPE_MAP = {
    "article": "01_Sources/articles",
    "book": "01_Sources/books",
    "twitter": "01_Sources/tweets",
}


def get_readwise_token() -> str:
    """从环境变量获取 token"""
    token = os.environ.get("READWISE_TOKEN")
    if not token:
        raise ValueError("环境变量 READWISE_TOKEN 未设置")
    return token


def fetch_highlights(token: str, since: Optional[str] = None) -> list:
    """
    从 Readwise API 拉取所有 highlights（处理分页）。

    Args:
        token: Readwise API token
        since: 可选，ISO 格式日期字符串

    Returns:
        highlights 列表
    """
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }

    params = {}
    if since:
        params["updated_after"] = since

    all_highlights = []
    next_page = None

    while True:
        url = f"{READWISE_API}/highlights"
        if next_page:
            url = next_page

        response = requests.get(url, headers=headers, params=params if not next_page else {})
        response.raise_for_status()
        data = response.json()

        all_highlights.extend(data.get("results", []))

        next_page = data.get("next")
        if not next_page:
            break

        params = {}  # next_page URL 已包含所有参数

    return all_highlights


def aggregate_by_source(highlights: list) -> dict:
    """
    按 source_id 聚合 highlights。

    Returns:
        {
            source_id: {
                "id": source_id,
                "type": source_type,
                "title": title,
                "author": author,
                "source_url": source_url,
                "category": category,
                "highlights": [...]
            }
        }
    """
    sources = {}

    for hl in highlights:
        source = hl.get("book_id") or hl.get("article_id") or hl.get("tweet_id")
        if not source:
            continue

        if source not in sources:
            sources[source] = {
                "id": source,
                "type": hl.get("source_type", "article"),
                "title": hl.get("book_title") or hl.get("article_title") or hl.get("tweet_text", "")[:50],
                "author": hl.get("author") or "Unknown",
                "source_url": hl.get("source_url") or "",
                "category": hl.get("category") or "misc",
                "highlights": []
            }

        sources[source]["highlights"].append({
            "text": hl.get("text", ""),
            "location": hl.get("location"),
            "note": hl.get("note"),
            "highlighted_at": hl.get("highlighted_at"),
        })

    return sources


def generate_markdown(source: dict, output_dir: Path) -> Path:
    """
    为单个 source 生成 Markdown 文件。

    Returns:
        生成的笔记文件路径
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"readwise-{source['id']}.md"
    filepath = output_dir / filename

    highlights = source["highlights"]
    first_date = highlights[0].get("highlighted_at", "")[:10] if highlights else ""

    # 构建 Highlights 部分
    highlights_md = []
    for hl in highlights:
        text = hl.get("text", "").strip()
        if not text:
            continue

        location = hl.get("location")
        location_str = f" Location: {location}" if location else ""

        highlights_md.append(f"> {text}{location_str}")

    highlights_body = "\n---\n".join(highlights_md) if highlights_md else "-（无高亮）"

    content = f"""---
id: readwise-{source['id']}
created: {first_date}
source_type: {source['type']}
source_url: {source['source_url']}
title: {source['title']}
author: {source['author']}
tags: ["readwise", "imported"]
status: inbox
rating: 0
---

# {source['title']}

## Metadata
- Source: {source['source_url'] or "N/A"}
- Author: {source['author']}
- Category: {source['category']}
- Total Highlights: {len(highlights)}
- Imported: {datetime.now().strftime('%Y-%m-%d')}

## Highlights
{highlights_body}

## Candidate Atomic Notes
- （供 Layer 3 加工时参考）
"""

    filepath.write_text(content, encoding="utf-8")
    return filepath


def sync_sources(sources: dict, dry_run: bool = False) -> dict:
    """
    同步所有 sources 到文件系统。

    Returns:
        同步结果统计
    """
    stats = {
        "total": len(sources),
        "skipped": 0,
        "created": 0,
        "errors": []
    }

    for source_id, source in sources.items():
        source_type = source.get("type", "article").lower()

        if source_type == "twitter":
            source_type = "tweet"

        output_dir = Path(SOURCE_TYPE_MAP.get(source_type, "01_Sources/articles"))

        filename = f"readwise-{source_id}.md"
        filepath = output_dir / filename

        # 幂等性：已存在则跳过
        if filepath.exists():
            stats["skipped"] += 1
            continue

        if dry_run:
            stats["created"] += 1
            continue

        try:
            generate_markdown(source, output_dir)
            stats["created"] += 1
        except Exception as e:
            stats["errors"].append(f"source {source_id}: {str(e)}")

    return stats


def main():
    # --help 处理
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    dry_run = "--dry-run" in sys.argv
    since = None

    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--since" and i + 2 < len(sys.argv):
            since = sys.argv[i + 2]

    # 获取 token
    try:
        token = get_readwise_token()
    except ValueError as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "hint": "设置环境变量: export READWISE_TOKEN=your_token",
            "exit_code": 2
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    # 拉取 highlights
    try:
        highlights = fetch_highlights(token, since)
    except requests.RequestException as e:
        print(json.dumps({
            "success": False,
            "error": f"网络请求失败: {str(e)}",
            "exit_code": 1
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not highlights:
        print(json.dumps({
            "success": True,
            "message": "没有新的 highlights",
            "stats": {"total": 0, "skipped": 0, "created": 0}
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 聚合
    sources = aggregate_by_source(highlights)

    # 同步
    stats = sync_sources(sources, dry_run)

    result = {
        "success": True,
        "message": "同步完成" if not dry_run else "dry-run 模式",
        "stats": stats,
        "sources": [
            {"id": s["id"], "type": s["type"], "title": s["title"], "highlights_count": len(s["highlights"])}
            for s in sources.values()
        ]
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if stats["errors"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()