"""
health_service.py - 健康检查服务
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent.resolve()
SCRIPTS_DIR = PROJECT_DIR / "scripts"
STATUS_FILE = PROJECT_DIR / ".memory_palace" / "runtime_status.json"


def check_scripts() -> dict:
    """检查核心脚本是否可用"""
    scripts = [
        "validate_note.py",
        "build_index.py",
        "build_vector_index.py",
        "search_notes.py",
        "process_inbox.py",
        "ask_vault.py",
    ]

    results = {}
    for script in scripts:
        script_path = SCRIPTS_DIR / script
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=PROJECT_DIR
            )
            results[script] = "ok" if result.returncode == 0 else "error"
        except Exception:
            results[script] = "timeout"

    return results


def check_indexes() -> dict:
    """检查索引是否存在"""
    db_path = PROJECT_DIR / ".memory_palace" / "index.sqlite"
    vector_manifest = PROJECT_DIR / ".memory_palace" / "vector_index" / "manifest.json"

    return {
        "sqlite_index": db_path.exists(),
        "vector_index": vector_manifest.exists(),
    }


def get_job_status() -> dict:
    """获取定时任务运行状态"""
    import json

    if not STATUS_FILE.exists():
        return {
            "daily": {"status": "unknown", "date": "", "time": ""},
            "weekly": {"status": "unknown", "date": "", "time": ""},
            "sync": {"status": "unknown", "date": "", "time": ""},
        }

    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            status = json.load(f)

        result = {}
        for job in ["daily", "weekly", "sync"]:
            if job in status:
                record = status[job]
                result[job] = {
                    "status": record.get("status", "unknown"),
                    "date": record.get("date", ""),
                    "time": record.get("time", ""),
                    "error": record.get("error"),
                    "duration_seconds": record.get("duration_seconds"),
                    "steps": record.get("steps", []),
                }
            else:
                result[job] = {"status": "unknown", "date": "", "time": ""}

        return result
    except (json.JSONDecodeError, IOError):
        return {
            "daily": {"status": "error", "date": "", "time": ""},
            "weekly": {"status": "error", "date": "", "time": ""},
            "sync": {"status": "error", "date": "", "time": ""},
        }


def get_health() -> dict:
    """获取完整的健康状态"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "scripts": check_scripts(),
        "indexes": check_indexes(),
        "jobs": get_job_status(),
    }