#!/usr/bin/env python3
"""
vault_metrics.py - Vault 健康评分与质量指标

读取 SQLite，计算知识库健康指标：
- Inbox 积压数
- 孤岛笔记比例
- 标签缺失率
- 过期 seedling 数量
- 输出数量统计

用法:
  python vault_metrics.py
  python vault_metrics.py --json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import get_settings


def calculate_metrics(db_path: Path) -> dict:
    """计算 Vault 健康指标"""
    import sqlite3

    if not db_path.exists():
        return {
            "success": False,
            "error": f"数据库不存在: {db_path}",
            "hint": "先运行: python scripts/build_index.py"
        }

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    metrics = {}

    # 1. Inbox 积压数（source 类型的 inbox 状态）
    cursor.execute("""
        SELECT COUNT(*) FROM notes
        WHERE type = 'source' AND status = 'inbox'
    """)
    metrics["inbox_count"] = cursor.fetchone()[0]

    # 2. Atomic Notes 数量
    cursor.execute("""
        SELECT COUNT(*) FROM notes
        WHERE type = 'atomic_note'
    """)
    metrics["atomic_notes_count"] = cursor.fetchone()[0]

    # 3. MAP 数量
    cursor.execute("""
        SELECT COUNT(*) FROM notes
        WHERE type = 'map'
    """)
    metrics["maps_count"] = cursor.fetchone()[0]

    # 4. 项目数量
    cursor.execute("""
        SELECT COUNT(*) FROM notes
        WHERE type = 'project'
    """)
    metrics["projects_count"] = cursor.fetchone()[0]

    # 5. 孤岛笔记（没有任何 wikilink 指向或来自的笔记）
    cursor.execute("""
        SELECT COUNT(*) FROM notes n
        WHERE n.type = 'atomic_note'
        AND n.id NOT IN (
            SELECT DISTINCT CAST(id AS INTEGER) FROM notes WHERE id IN (
                SELECT CAST(from_note_path AS INTEGER) FROM links
            )
        )
        AND n.id NOT IN (
            SELECT DISTINCT CAST(to_title AS INTEGER) FROM links
        )
    """)
    metrics["orphan_notes"] = cursor.fetchone()[0]

    # 6. 标签缺失的笔记（atomic_note 中没有标签的）
    cursor.execute("""
        SELECT COUNT(*) FROM notes n
        WHERE n.type = 'atomic_note'
        AND n.id NOT IN (SELECT note_id FROM tags)
    """)
    metrics["untagged_notes"] = cursor.fetchone()[0]

    # 7. 过期 seedling（超过 90 天未更新的 seedling）
    cutoff_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT COUNT(*) FROM notes
        WHERE type = 'atomic_note'
        AND status = 'seedling'
        AND updated < ?
    """, (cutoff_date,))
    metrics["stale_seedlings"] = cursor.fetchone()[0]

    # 8. Daily Brief 生成率（本周）
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    week_start_str = week_start.strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT COUNT(*) FROM notes
        WHERE type = 'daily_brief'
        AND created >= ?
    """, (week_start_str,))
    metrics["daily_briefs_this_week"] = cursor.fetchone()[0]

    # 9. Weekly Synthesis 生成率（本月）
    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT COUNT(*) FROM notes
        WHERE type = 'weekly_synthesis'
        AND created >= ?
    """, (month_start,))
    metrics["weekly_syntheses_this_month"] = cursor.fetchone()[0]

    # 10. 笔记总量
    cursor.execute("SELECT COUNT(*) FROM notes")
    metrics["total_notes"] = cursor.fetchone()[0]

    # 11. 有向量的笔记数
    cursor.execute("SELECT COUNT(*) FROM notes WHERE has_vector = 1")
    metrics["vectorized_notes"] = cursor.fetchone()[0]

    # 12. 总链接数
    cursor.execute("SELECT COUNT(*) FROM links")
    metrics["total_links"] = cursor.fetchone()[0]

    # 13. 最近的 Ask Vault 命中（从 08_Outputs 统计）
    output_dir = db_path.parent.parent / "08_Outputs"
    ask_count = 0
    if output_dir.exists():
        for subdir in ["decisions", "reports", "essays"]:
            subdir_path = output_dir / subdir
            if subdir_path.exists():
                ask_count += len(list(subdir_path.glob("*.md")))
    metrics["ask_vault_outputs"] = ask_count

    # 计算健康评分（0-100）
    score = calculate_health_score(metrics)
    metrics["health_score"] = score

    conn.close()

    metrics["success"] = True
    metrics["calculated_at"] = datetime.now().isoformat()

    return metrics


def calculate_health_score(m: dict) -> int:
    """
    计算健康评分（0-100）。

    评分规则：
    - Inbox 积压：>10 扣分，>50 大幅扣分
    - 孤岛笔记：>20% 扣分
    - 标签缺失：>30% 扣分
    - 过期 seedling：>10 扣分
    """
    score = 100

    # Inbox 积压（最多扣 30 分）
    if m["inbox_count"] > 50:
        score -= 30
    elif m["inbox_count"] > 20:
        score -= 20
    elif m["inbox_count"] > 10:
        score -= 10

    # 孤岛笔记（最多扣 25 分）
    if m["atomic_notes_count"] > 0:
        orphan_ratio = m["orphan_notes"] / m["atomic_notes_count"]
        if orphan_ratio > 0.3:
            score -= 25
        elif orphan_ratio > 0.2:
            score -= 15
        elif orphan_ratio > 0.1:
            score -= 10

    # 标签缺失（最多扣 20 分）
    if m["atomic_notes_count"] > 0:
        untagged_ratio = m["untagged_notes"] / m["atomic_notes_count"]
        if untagged_ratio > 0.5:
            score -= 20
        elif untagged_ratio > 0.3:
            score -= 15
        elif untagged_ratio > 0.1:
            score -= 10

    # 过期 seedling（最多扣 15 分）
    if m["stale_seedlings"] > 20:
        score -= 15
    elif m["stale_seedlings"] > 10:
        score -= 10
    elif m["stale_seedlings"] > 5:
        score -= 5

    # 向量化率低（最多扣 10 分）
    if m["total_notes"] > 0:
        vector_ratio = m["vectorized_notes"] / m["total_notes"]
        if vector_ratio < 0.3:
            score -= 10
        elif vector_ratio < 0.5:
            score -= 5

    return max(0, min(100, score))


def get_health_grade(score: int) -> str:
    """根据评分返回等级"""
    if score >= 90:
        return "优秀"
    elif score >= 70:
        return "良好"
    elif score >= 50:
        return "一般"
    elif score >= 30:
        return "较差"
    else:
        return "危险"


def main():
    parser = argparse.ArgumentParser(description="Vault 健康评分与质量指标")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    settings = get_settings()
    metrics = calculate_metrics(settings.db_path)

    if not metrics["success"]:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 添加等级
    metrics["health_grade"] = get_health_grade(metrics["health_score"])

    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print(f"Vault 健康评分: {metrics['health_score']}/100 ({metrics['health_grade']})")
        print(f"计算时间: {metrics['calculated_at']}")
        print("=" * 50)
        print()
        print("📊 数量统计:")
        print(f"  笔记总量: {metrics['total_notes']}")
        print(f"  Atomic Notes: {metrics['atomic_notes_count']}")
        print(f"  MAPs: {metrics['maps_count']}")
        print(f"  Projects: {metrics['projects_count']}")
        print(f"  向量化: {metrics['vectorized_notes']}")
        print(f"  链接数: {metrics['total_links']}")
        print()
        print("📥 Inbox:")
        print(f"  积压数量: {metrics['inbox_count']}")
        print()
        print("🏝️  孤岛笔记:")
        print(f"  数量: {metrics['orphan_notes']}")
        print()
        print("🏷️  标签:")
        print(f"  缺失标签: {metrics['untagged_notes']}")
        print()
        print("🌱  过期的 seedling:")
        print(f"  数量: {metrics['stale_seedlings']}")
        print()
        print("📝  输出统计:")
        print(f"  Ask Vault 输出: {metrics['ask_vault_outputs']}")
        print(f"  Daily Brief 本周: {metrics['daily_briefs_this_week']}")
        print(f"  Weekly Synthesis 本月: {metrics['weekly_syntheses_this_month']}")

    sys.exit(0)


if __name__ == "__main__":
    main()