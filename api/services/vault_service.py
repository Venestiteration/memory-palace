"""
vault_service.py - Ask Vault 封装
"""

import sys
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from ask_vault import ask_vault as cli_ask_vault


def ask(question: str, limit: int = 5, save_category: str = None) -> dict:
    """
    调用 ask_vault 功能。

    Args:
        question: 问题
        limit: 搜索笔记数量
        save_category: 保存类别（decisions/reports/essays）

    Returns:
        ask_vault 返回的 dict
    """
    return cli_ask_vault(question, limit=limit, save_category=save_category)