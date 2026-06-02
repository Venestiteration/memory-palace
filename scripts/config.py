#!/usr/bin/env python3
"""
config.py - Memory Palace 配置管理

统一加载项目根目录和环境变量。
所有脚本应从此模块获取项目路径和配置。

用法：
  from scripts.config import get_settings

  settings = get_settings()
  print(settings.project_root)
  print(settings.minimax_api_key)
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# 项目根目录（memory_palace/）
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


@dataclass
class Settings:
    """Memory Palace 配置"""
    project_root: Path
    minimax_api_key: Optional[str]
    dashscope_api_key: Optional[str]
    readwise_token: Optional[str]
    db_path: Path
    vector_index_path: Path


def get_settings() -> Settings:
    """
    获取项目配置。

    从环境变量读取 API keys，从固定位置读取数据库路径。

    Returns:
        Settings 对象
    """
    # API Keys
    minimax_api_key = os.environ.get("MINIMAX_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    dashscope_api_key = os.environ.get("DASHSCOPE_API_KEY")
    readwise_token = os.environ.get("READWISE_TOKEN")

    # 数据库路径
    db_path = PROJECT_ROOT / ".memory_palace" / "index.sqlite"
    vector_index_path = PROJECT_ROOT / ".memory_palace" / "vector_index"

    return Settings(
        project_root=PROJECT_ROOT,
        minimax_api_key=minimax_api_key,
        dashscope_api_key=dashscope_api_key,
        readwise_token=readwise_token,
        db_path=db_path,
        vector_index_path=vector_index_path,
    )


def load_env_file(env_path: Optional[Path] = None) -> None:
    """
    加载 .env 文件到环境变量。

    优先使用系统环境变量，已存在的环境变量不会被覆盖。

    Args:
        env_path: .env 文件路径，默认为项目根目录的 .env
    """
    if env_path is None:
        env_path = PROJECT_ROOT / ".env"

    if not env_path.exists():
        return

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue
            # 跳过没有 = 的行
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # 只设置不存在的环境变量
            if key not in os.environ:
                os.environ[key] = value


# 自动加载 .env 文件（如果存在）
load_env_file()


if __name__ == "__main__":
    settings = get_settings()
    print(f"project_root: {settings.project_root}")
    print(f"minimax_api_key: {'*' * 8 if settings.minimax_api_key else 'not set'}")
    print(f"dashscope_api_key: {'*' * 8 if settings.dashscope_api_key else 'not set'}")
    print(f"readwise_token: {'*' * 8 if settings.readwise_token else 'not set'}")
    print(f"db_path: {settings.db_path}")
    print(f"vector_index_path: {settings.vector_index_path}")
