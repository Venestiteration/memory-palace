#!/usr/bin/env python3
"""
runtime_status.py - 运行时状态记录

写入 .memory_palace/runtime_status.json，记录任务执行状态。

用法：
  from runtime_status import JobStatus, update_job_status

  update_job_status("daily", JobStatus.SUCCESS, "步骤 1 失败", exit_code=1)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
STATUS_FILE = PROJECT_DIR / ".memory_palace" / "runtime_status.json"


class JobStatus:
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


def ensure_status_dir():
    """确保状态文件目录存在"""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_status() -> dict:
    """加载现有状态"""
    if not STATUS_FILE.exists():
        return {}
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_status(status: dict):
    """保存状态到文件"""
    ensure_status_dir()
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"警告: 无法写入状态文件: {e}", file=sys.stderr)


def update_job_status(
    job_name: str,
    status: str,
    error_message: Optional[str] = None,
    exit_code: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    steps: Optional[list] = None,
) -> dict:
    """
    更新任务状态。

    Args:
        job_name: 任务名（daily/weekly/sync）
        status: JobStatus 常量
        error_message: 错误信息（失败时）
        exit_code: 退出码
        duration_seconds: 执行时长（秒）
        steps: 步骤列表 [{"name": "...", "status": "...", "error": "..."}]

    Returns:
        更新后的状态字典
    """
    now = datetime.now().isoformat()
    now_date = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")

    # 加载现有状态
    all_status = load_status()

    # 构建新记录
    record = {
        "job": job_name,
        "status": status,
        "date": now_date,
        "time": now_time,
        "started_at": all_status.get(job_name, {}).get("started_at", now),
    }

    if status == JobStatus.SUCCESS:
        record["ended_at"] = now
        if duration_seconds is not None:
            record["duration_seconds"] = duration_seconds

    elif status == JobStatus.FAILURE:
        record["ended_at"] = now
        record["error"] = error_message or "未知错误"
        if exit_code is not None:
            record["exit_code"] = exit_code
        if duration_seconds is not None:
            record["duration_seconds"] = duration_seconds

    elif status == JobStatus.RUNNING:
        record["started_at"] = now

    if steps is not None:
        record["steps"] = steps

    # 更新该任务的状态
    all_status[job_name] = record

    # 只保留最近 10 条历史（用于调试）
    if "history" not in all_status:
        all_status["history"] = []
    all_status["history"].append(record)
    all_status["history"] = all_status["history"][-10:]

    save_status(all_status)
    return record


def get_job_status(job_name: str) -> Optional[dict]:
    """获取指定任务最近状态"""
    status = load_status()
    return status.get(job_name)


def get_all_status() -> dict:
    """获取所有任务状态"""
    return load_status()


def get_diagnostic_info(job_name: str, error_message: str, exit_code: Optional[int] = None) -> str:
    """
    生成失败时的简短诊断信息。

    Returns:
        诊断建议字符串
    """
    diagnostics = []

    # 数据库锁定
    if "database is locked" in error_message:
        diagnostics.append("数据库被占用，尝试关闭其他访问进程后重试")

    # 索引文件问题
    if "index" in error_message.lower():
        if exit_code == 1:
            diagnostics.append("SQLite 索引可能损坏，可使用 --rebuild 重建索引")

    # API key 问题
    if "api_key" in error_message.lower() or "auth" in error_message.lower():
        diagnostics.append("检查 .env 中的 API key 配置")

    # 网络问题
    if "connection" in error_message.lower() or "timeout" in error_message.lower():
        diagnostics.append("网络连接问题，检查网络后重试")

    # 文件权限
    if "permission" in error_message.lower() or "access" in error_message.lower():
        diagnostics.append("检查文件/目录权限")

    if not diagnostics:
        diagnostics.append("查看日志文件获取详细信息")

    return "; ".join(diagnostics)


if __name__ == "__main__":
    # 测试
    print(json.dumps(get_all_status(), indent=2, ensure_ascii=False))