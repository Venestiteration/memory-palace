"""
capture.py - 捕获路由

支持文本、网页剪藏、语音转录三种捕获方式。
所有内容写入 00_Inbox/ 对应子目录。
"""

import sys
import json
from pathlib import Path

# 确保脚本目录在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from ..schemas import CaptureTextResponse, CaptureWebClipRequest, CaptureVoiceRequest
from ..security import require_write_token

from capture_provider import (
    CaptureResult,
    new_capture_id,
    now_iso,
    ensure_inbox_dir,
)
import capture_text
import capture_web_clip
import capture_voice

router = APIRouter(prefix="/capture", tags=["capture"])


def _escape_yaml_value(text: str) -> str:
    """对 YAML 值进行转义"""
    if not text:
        return '""'
    import json
    needs_quoting = any(c in text for c in ':{}[]|>&*!%@`"\'\n') or text.startswith(' ') or text.endswith(' ')
    if needs_quoting:
        return json.dumps(text, ensure_ascii=False)[1:-1]
    return text


def _write_capture(result: CaptureResult, dry_run: bool = False) -> dict:
    """将 CaptureResult 写入 Inbox 目录"""
    subdir_map = {
        "manual": "quick_capture",
        "web": "web_clips",
        "voice": "voice",
    }
    subdir = subdir_map.get(result.source_type, "quick_capture")
    output_dir = ensure_inbox_dir(subdir)

    from datetime import datetime
    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{result.id}.md"
    filepath = output_dir / filename

    title_display = result.title[:50] + ("..." if len(result.title) > 50 else "")

    content_lines = [
        "---",
        f"id: {result.id}",
        f"created: {result.created}",
        f"source_type: {result.source_type}",
        f"title: {_escape_yaml_value(result.title)}",
        f"tags: {json.dumps(result.tags, ensure_ascii=False)}",
        "status: inbox",
        f"rating: {result.rating}",
    ]

    if result.source_url:
        content_lines.insert(4, f"source_url: {_escape_yaml_value(result.source_url)}")
    if result.author:
        content_lines.insert(5, f"author: {_escape_yaml_value(result.author)}")

    content_lines.extend([
        "---",
        "",
        f"# {title_display}",
        "",
        result.content,
        "",
    ])

    content = "\n".join(content_lines)

    if dry_run:
        return {"success": True, "dry_run": True, "file": str(filepath)}

    # 原子写入
    temp_path = filepath.with_suffix(".tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")

        from scripts.validate_note import validate_file
        validation = validate_file(temp_path)
        if not validation["ok"]:
            temp_path.unlink()
            return {"success": False, "error": f"验证失败: {validation['errors']}"}

        temp_path.rename(filepath)
        return {"success": True, "file": str(filepath), "id": result.id}

    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        return {"success": False, "error": str(e)}


@router.post("/text", response_model=CaptureTextResponse)
async def capture_text_api(
    body: dict,
    _token: str = Depends(require_write_token)
):
    """
    捕获文本到 Inbox (quick_capture/)。

    请求体:
      content: str (必填)
      title: str (可选，默认 "Quick Capture")
      tags: list[str] (可选)
    """
    content = body.get("content")
    if not content:
        return CaptureTextResponse(success=False, error="content 不能为空")

    title = body.get("title") or "Quick Capture"
    tags = body.get("tags", ["manual"])

    result = CaptureResult(
        id=new_capture_id("manual"),
        source_type="manual",
        title=title,
        content=content,
        created=now_iso(),
        tags=tags if isinstance(tags, list) else ["manual"],
    )

    output = _write_capture(result)
    return CaptureTextResponse(
        success=output["success"],
        file=output.get("file"),
        error=output.get("error"),
    )


@router.post("/web", response_model=CaptureTextResponse)
async def capture_web_api(
    body: CaptureWebClipRequest,
    _token: str = Depends(require_write_token)
):
    """
    捕获网页剪藏到 Inbox (web_clips/)。

    请求体:
      url: str (必填)
      title: str (可选)
      content: str (可选)
      author: str (可选)
      tags: list[str] (可选)
    """
    result = CaptureResult(
        id=new_capture_id("web"),
        source_type="web",
        title=body.title or "Web Clip",
        content=body.content or "",
        created=now_iso(),
        tags=body.tags or ["web_clip"],
        source_url=body.url,
        author=body.author,
    )

    output = _write_capture(result)
    return CaptureTextResponse(
        success=output["success"],
        file=output.get("file"),
        error=output.get("error"),
    )


@router.post("/voice", response_model=CaptureTextResponse)
async def capture_voice_api(
    body: CaptureVoiceRequest,
    _token: str = Depends(require_write_token)
):
    """
    捕获语音转录到 Inbox (voice/)。

    请求体:
      transcript: str (必填)
      title: str (可选)
      tags: list[str] (可选)
    """
    if not body.transcript:
        return CaptureTextResponse(success=False, error="transcript 不能为空")

    result = CaptureResult(
        id=new_capture_id("voice"),
        source_type="voice",
        title=body.title or "Voice Note",
        content=body.transcript,
        created=now_iso(),
        tags=body.tags or ["voice", "transcript"],
    )

    output = _write_capture(result)
    return CaptureTextResponse(
        success=output["success"],
        file=output.get("file"),
        error=output.get("error"),
    )