"""
metrics_service.py - 健康指标服务
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

try:
    from config import get_settings
    from vault_metrics import calculate_metrics, get_health_grade
except ImportError:
    get_settings = None
    calculate_metrics = None
    get_health_grade = lambda x: "未知"


def get_metrics() -> dict:
    """获取 Vault 健康指标"""
    if calculate_metrics is None or get_settings is None:
        return {
            "success": False,
            "error": "无法加载 metrics 模块",
            "health_score": 0,
            "health_grade": "未知",
        }

    try:
        settings = get_settings()
        metrics = calculate_metrics(settings.db_path)

        if not metrics.get("success", False):
            return {
                "success": False,
                "error": metrics.get("error", "未知错误"),
                "health_score": 0,
                "health_grade": "未知",
            }

        score = metrics.get("health_score", 0)
        metrics["health_grade"] = get_health_grade(score)
        metrics["success"] = True

        return metrics

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "health_score": 0,
            "health_grade": "未知",
        }