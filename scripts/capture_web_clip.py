#!/usr/bin/env python3
"""
capture_web_clip.py - 网页剪藏捕获

接收 url/title/content，写入 00_Inbox/web_clips/。
支持 CLI 和 API 两种调用方式。

用法：
  python capture_web_clip.py <url> <title> <content>
  python capture_web_clip.py --url <url> --title <title> --content <content>
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from capture_provider import (
    CaptureResult,
    new_capture_id,
    now_iso,
    ensure_inbox_dir,
)


def escape_yaml_value(text: str) -> str:
    """对 YAML 值进行转义"""
    if not text:
        return '""'
    needs_quoting = any(c in text for c in ':{}[]|>&*!%@`"\'\n') or text.startswith(' ') or text.endswith(' ')
    if needs_quoting:
        return json.dumps(text, ensure_ascii=False)[1:-1]
    return text


def generate_filename(capture_id: str) -> str:
    """生成文件名：YYYYMMDD-HHMMSS-{id}.md"""
    from datetime import datetime
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{capture_id}.md"


def write_capture(result: CaptureResult, dry_run: bool = False) -> dict:
    """
    将 CaptureResult 写入 Inbox 目录。

    Returns:
        JSON 结果字典
    """
    output_dir = ensure_inbox_dir("web_clips")
    filepath = output_dir / generate_filename(result.id)

    # 构建 frontmatter
    title_display = result.title[:50] + ("..." if len(result.title) > 50 else "")

    content_lines = [
        "---",
        f"id: {result.id}",
        f"created: {result.created}",
        f"source_type: web",
        f"source_url: {escape_yaml_value(result.source_url or '')}",
        f"title: {escape_yaml_value(result.title)}",
        f"tags: {json.dumps(result.tags, ensure_ascii=False)}",
        f"author: {escape_yaml_value(result.author or '')}",
        "status: inbox",
        f"rating: {result.rating}",
        "---",
        "",
        f"# {title_display}",
        "",
        result.content,
        "",
    ]

    content = "\n".join(content_lines)

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "file": str(filepath),
            "content_preview": content[:200],
        }

    # 原子写入：temp → validate → commit
    temp_path = filepath.with_suffix(".tmp")

    try:
        temp_path.write_text(content, encoding="utf-8")

        # 验证
        from scripts.validate_note import validate_file
        validation = validate_file(temp_path)
        if not validation["ok"]:
            temp_path.unlink()
            return {
                "success": False,
                "error": f"验证失败: {validation['errors']}",
                "file": str(filepath),
            }

        # commit
        temp_path.rename(filepath)

        return {
            "success": True,
            "file": str(filepath),
            "id": result.id,
            "title": result.title,
            "url": result.source_url,
            "content_length": len(result.content),
            "processed_at": now_iso(),
        }

    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        return {
            "success": False,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="网页剪藏捕获")
    parser.add_argument("url", nargs="?", help="网页 URL")
    parser.add_argument("title", nargs="?", help="标题")
    parser.add_argument("content", nargs="?", help="内容")
    parser.add_argument("--url", dest="url_arg", help="网页 URL（另一种方式）")
    parser.add_argument("--title", dest="title_arg", help="标题（另一种方式）")
    parser.add_argument("--content", dest="content_arg", help="内容（另一种方式）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--tags", default="", help="逗号分隔的标签")
    parser.add_argument("--author", default="", help="作者")

    args = parser.parse_args()

    # 支持两种参数方式
    url = args.url or args.url_arg
    title = args.title or args.title_arg
    content = args.content or args.content_arg

    if not url:
        print(json.dumps({
            "success": False,
            "error": "用法: python capture_web_clip.py <url> <title> <content>\n       python capture_web_clip.py --url <url> --title <title> --content <content>"
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    if not title:
        title = "Web Clip"
    if not content:
        content = ""

    # 处理标签
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    else:
        tags = ["web_clip"]

    result = CaptureResult(
        id=new_capture_id("web"),
        source_type="web",
        title=title,
        content=content,
        created=now_iso(),
        tags=tags,
        source_url=url,
        author=args.author or None,
    )

    output = write_capture(result, dry_run=args.dry_run)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()