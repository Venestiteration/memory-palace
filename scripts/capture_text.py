#!/usr/bin/env python3
"""
capture_text.py - 快速文本捕获

接受文本输入，写入 00_Inbox/quick_capture/。
支持 CLI 和 API 两种调用方式。

用法：
  python capture_text.py "文本内容" [title]
  echo "文本内容" | python capture_text.py --stdin [title]
"""

import sys
import json
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
    output_dir = ensure_inbox_dir("quick_capture")
    filepath = output_dir / generate_filename(result.id)

    # 构建 frontmatter
    title_display = result.title[:50] + ("..." if len(result.title) > 50 else "")

    content_lines = [
        "---",
        f"id: {result.id}",
        f"created: {result.created}",
        f"source_type: manual",
        f"title: {escape_yaml_value(result.title)}",
        f"tags: {json.dumps(result.tags, ensure_ascii=False)}",
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
    # --help
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    # --dry-run
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        sys.argv.remove("--dry-run")

    # --stdin 模式
    if "--stdin" in sys.argv:
        sys.argv.remove("--stdin")
        content = sys.stdin.read().strip()
        title = sys.argv[1] if len(sys.argv) > 1 else "Quick Capture"
    elif len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "用法: python capture_text.py <text> [title] 或 echo <text> | python capture_text.py --stdin [title]"
        }, ensure_ascii=False, indent=2))
        sys.exit(2)
    else:
        content = sys.argv[1]
        title = sys.argv[2] if len(sys.argv) > 2 else "Quick Capture"

    if not content:
        print(json.dumps({
            "success": False,
            "error": "内容不能为空"
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    result = CaptureResult(
        id=new_capture_id("manual"),
        source_type="manual",
        title=title,
        content=content,
        created=now_iso(),
        tags=["manual"],
    )

    output = write_capture(result, dry_run=dry_run)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()