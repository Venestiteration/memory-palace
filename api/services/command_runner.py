"""
command_runner.py - 调用现有脚本的封装
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


PROJECT_DIR = Path(__file__).parent.parent.parent.resolve()
SCRIPTS_DIR = PROJECT_DIR / "scripts"


def run_python_script(script_name: str, args: list[str] = []) -> tuple[int, str, str]:
    """
    运行 scripts/ 目录下的 Python 脚本。

    Args:
        script_name: 脚本文件名
        args: 命令行参数列表

    Returns:
        (returncode, stdout, stderr)
    """
    script_path = SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR
    )
    return result.returncode, result.stdout, result.stderr


def run_json_script(script_name: str, args: list[str] = []) -> Optional[dict]:
    """
    运行脚本并解析 JSON 输出。

    Returns:
        解析后的 dict，失败返回 None
    """
    returncode, stdout, stderr = run_python_script(script_name, args)

    if returncode != 0:
        return None

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def check_path_traversal(file_path: str) -> bool:
    """
    检查路径是否在项目目录内。

    Args:
        file_path: 要检查的路径

    Returns:
        True 表示安全，False 表示越界
    """
    try:
        # 解析为绝对路径
        abs_path = (PROJECT_DIR / file_path).resolve()

        # 检查是否在项目目录内
        return str(abs_path).startswith(str(PROJECT_DIR))
    except Exception:
        return False