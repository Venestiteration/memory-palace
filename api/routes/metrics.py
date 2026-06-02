"""
metrics.py - Vault 健康指标路由
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..services.metrics_service import get_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricsResponse(BaseModel):
    success: bool
    health_score: int
    health_grade: str
    inbox_count: int
    orphan_notes: int
    untagged_notes: int
    stale_seedlings: int
    atomic_notes_count: int
    total_notes: int
    vectorized_notes: int
    total_links: int
    calculated_at: str
    error: Optional[str] = None


@router.get("", response_model=MetricsResponse)
async def get_vault_metrics():
    """
    获取 Vault 健康指标。

    返回知识库的健康评分和各维度指标。
    无需认证。
    """
    metrics = get_metrics()
    return MetricsResponse(**metrics)