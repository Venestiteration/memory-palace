"""
jobs.py - 任务状态路由
"""

import sys
from pathlib import Path

# 确保脚本目录在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..services.health_service import get_job_status

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobStatusResponse(BaseModel):
    """任务状态响应"""
    daily: dict
    weekly: dict
    sync: dict


@router.get("/status", response_model=JobStatusResponse)
async def get_jobs_status():
    """
    获取定时任务运行状态。

    返回 daily / weekly / sync 三个任务的最近一次执行状态。
    """
    status = get_job_status()
    return JobStatusResponse(
        daily=status.get("daily", {"status": "unknown"}),
        weekly=status.get("weekly", {"status": "unknown"}),
        sync=status.get("sync", {"status": "unknown"}),
    )