#!/usr/bin/env python3
"""
capture_provider.py - 统一捕获入口定义

提供 CaptureResult 数据类和辅助函数。
所有 capture 脚本必须通过此模块定义的标准格式输出。
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid
import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.config import get_settings


@dataclass
class CaptureResult:
    """统一捕获结果"""
    id: str                          # 唯一标识
    source_type: str               # manual/web/voice/telegram/readwise
    title: str                     # 标题
    content: str                   # 原始内容
    created: str                   # ISO 格式时间
    tags: list[str] = field(default_factory=list)
    source_url: Optional[str] = None
    author: Optional[str] = None
    rating: int = 0
    metadata: dict = field(default_factory=dict)  # 来源特定的附加数据

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "title": self.title,
            "content": self.content,
            "created": self.created,
            "tags": self.tags,
            "source_url": self.source_url,
            "author": self.author,
            "rating": self.rating,
            "metadata": self.metadata,
        }


def new_capture_id(prefix: str = "capture") -> str:
    """生成新的捕获 ID"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    short_uuid = str(uuid.uuid4())[:4]
    return f"{prefix}-{ts}-{short_uuid}"


def now_iso() -> str:
    """返回当前时间的 ISO 格式字符串"""
    return datetime.now().isoformat()


def get_project_root() -> Path:
    """获取项目根目录"""
    try:
        return get_settings().project_root
    except Exception:
        # 回退：基于脚本位置推断
        return Path(__file__).parent.parent.resolve()


def get_inbox_dir(subdir: str) -> Path:
    """获取 Inbox 子目录路径"""
    root = get_project_root()
    return root / "00_Inbox" / subdir


def ensure_inbox_dir(subdir: str) -> Path:
    """确保 Inbox 子目录存在"""
    inbox_dir = get_inbox_dir(subdir)
    inbox_dir.mkdir(parents=True, exist_ok=True)
    return inbox_dir