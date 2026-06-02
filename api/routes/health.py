"""
health.py - 健康检查路由
"""

from fastapi import APIRouter

from ..schemas import HealthResponse
from ..services.health_service import get_health

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    健康检查接口。

    返回系统状态、脚本可用性、索引状态。
    无需认证。
    """
    health = get_health()
    return HealthResponse(
        status=health.get("status", "ok"),
        timestamp=health.get("timestamp", ""),
        version="1.0.0"
    )


@router.get("/detailed")
async def detailed_health_check():
    """
    详细健康检查。

    返回完整的健康状态信息。
    无需认证。
    """
    return get_health()