"""
security.py - API 安全模块
"""

import os
import secrets
from fastapi import HTTPException, Header
from typing import Optional

# API Token 从环境变量读取，不硬编码
def get_api_token() -> Optional[str]:
    """获取配置的 API token"""
    return os.environ.get("MEMORY_PALACE_API_TOKEN")


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    """Accept the standard ``Bearer <token>`` form and raw tokens for CLI use."""
    if not authorization:
        return None
    scheme, separator, value = authorization.partition(" ")
    if separator and scheme.lower() == "bearer":
        return value.strip() or None
    return authorization.strip() or None


def verify_token(x_token: Optional[str] = Header(None, alias="Authorization")) -> str:
    """
    验证 API token。

    Args:
        x_token: Authorization header 中的 token

    Returns:
        验证通过的 token

    Raises:
        HTTPException: token 无效或缺失
    """
    configured_token = get_api_token()

    # 如果没有配置 token，允许访问（开发模式）
    # 生产环境应设置 MEMORY_PALACE_API_TOKEN
    if not configured_token:
        return "dev-mode"

    token = _extract_token(x_token)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="缺少 Authorization header"
        )

    if not secrets.compare_digest(token, configured_token):
        raise HTTPException(
            status_code=401,
            detail="无效的 token"
        )

    return token


def require_write_token(x_token: Optional[str] = Header(None, alias="Authorization")) -> str:
    """
    写操作需要验证 token。

    Raises:
        HTTPException: token 无效
    """
    return verify_token(x_token)


def require_read_token(x_token: Optional[str] = Header(None, alias="Authorization")) -> str:
    """
    读操作需要验证 token（如果配置了的话）。
    读操作在无 token 配置时允许匿名访问。
    """
    configured_token = get_api_token()

    # 没有配置 token 则允许读
    if not configured_token:
        return "dev-mode"

    # 有配置则必须验证
    token = _extract_token(x_token)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="缺少 Authorization header"
        )

    if not secrets.compare_digest(token, configured_token):
        raise HTTPException(
            status_code=401,
            detail="无效的 token"
        )

    return token
