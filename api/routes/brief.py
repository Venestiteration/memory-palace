"""
brief.py - 简报路由
"""

from fastapi import APIRouter, Depends

from ..schemas import BriefResponse, GenerateBriefRequest
from ..security import require_read_token, require_write_token
from ..services.command_runner import run_python_script
import json

router = APIRouter(prefix="/brief", tags=["brief"])


@router.get("/daily", response_model=BriefResponse)
async def get_daily_brief(
    date: str = None,
    _token: str = Depends(require_read_token)
):
    """
    获取每日简报内容（dry-run）。
    """
    args = ["daily", "--dry-run"]
    if date:
        args.extend(["--date", date])

    returncode, stdout, stderr = run_python_script("mp.py", ["brief"] + args)

    try:
        data = json.loads(stdout)
        return BriefResponse(
            success=data.get("success", False),
            date=data.get("date"),
            content=data.get("brief_data", {}).get("pattern", ""),
            dry_run=True
        )
    except Exception:
        return BriefResponse(
            success=False,
            error="解析简报失败"
        )


@router.post("/daily/generate", response_model=BriefResponse)
async def generate_daily_brief(
    body: GenerateBriefRequest,
    _token: str = Depends(require_write_token)
):
    """
    生成每日简报。
    """
    args = ["daily"]
    if body.date:
        args.extend(["--date", body.date])

    returncode, stdout, stderr = run_python_script(
        "generate_daily_brief.py",
        [a for a in args if a != "daily"]
    )

    try:
        data = json.loads(stdout)
        return BriefResponse(
            success=data.get("success", False),
            date=data.get("date"),
            content=data.get("content", ""),
            error=data.get("error")
        )
    except Exception:
        return BriefResponse(
            success=False,
            error="生成简报失败"
        )


@router.get("/weekly", response_model=BriefResponse)
async def get_weekly_brief(
    week: str = None,
    _token: str = Depends(require_read_token)
):
    """
    获取每周简报内容（dry-run）。
    """
    args = ["weekly", "--dry-run"]
    if week:
        args.extend(["--week", week])

    returncode, stdout, stderr = run_python_script("mp.py", ["brief"] + args)

    try:
        data = json.loads(stdout)
        return BriefResponse(
            success=data.get("success", False),
            week=data.get("week"),
            content=data.get("brief_data", {}).get("summary", ""),
            dry_run=True
        )
    except Exception:
        return BriefResponse(
            success=False,
            error="解析简报失败"
        )


@router.post("/weekly/generate", response_model=BriefResponse)
async def generate_weekly_brief(
    body: GenerateBriefRequest,
    _token: str = Depends(require_write_token)
):
    """
    生成每周简报。
    """
    args = []
    if body.week:
        args.extend(["--week", body.week])

    returncode, stdout, stderr = run_python_script(
        "generate_weekly_synthesis.py",
        args
    )

    try:
        data = json.loads(stdout)
        return BriefResponse(
            success=data.get("success", False),
            week=data.get("week"),
            content=data.get("content", ""),
            error=data.get("error")
        )
    except Exception:
        return BriefResponse(
            success=False,
            error="生成简报失败"
        )