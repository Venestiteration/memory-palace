#!/usr/bin/env python3
"""
generate_weekly_synthesis.py - 生成每周总结

读取过去 7 天新增/更新内容，调用 LLM 生成 Weekly Synthesis。

用法:
  python generate_weekly_synthesis.py                    # 生成本周总结
  python generate_weekly_synthesis.py --dry-run          # 仅输出 JSON，不写文件
  python generate_weekly_synthesis.py --week YYYY-Www   # 指定周（如 2026-W20）

输出:
  07_Weekly_Synthesis/YYYY-Www.md

环境变量:
  MINIMAX_API_KEY 或 ANTHROPIC_API_KEY - MiniMax API key（必填）
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import yaml


SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_DB = PROJECT_DIR / ".memory_palace" / "index.sqlite"
PROMPT_FILE = SCRIPT_DIR / "prompts" / "weekly_synthesis.md"
OUTPUT_DIR = PROJECT_DIR / "07_Weekly_Synthesis"
TEMPLATE_FILE = PROJECT_DIR / "_templates" / "weekly_synthesis.md"
CLAUDE_FILE = PROJECT_DIR / "CLAUDE.md"


def get_api_key() -> str:
    """从环境变量获取 API key（支持 MINIMAX_API_KEY 或 ANTHROPIC_API_KEY）"""
    key = os.environ.get("MINIMAX_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("环境变量 MINIMAX_API_KEY 或 ANTHROPIC_API_KEY 未设置")
    return key


def get_db_path() -> Path:
    """获取数据库路径"""
    db_path = os.environ.get("MEMORY_PALACE_DB")
    if db_path:
        return Path(db_path)
    return DEFAULT_DB


def load_prompt() -> str:
    """加载 LLM prompt 模板"""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {PROMPT_FILE}")
    return PROMPT_FILE.read_text(encoding="utf-8")


def load_template() -> str:
    """加载 weekly_synthesis 模板"""
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"模板文件不存在: {TEMPLATE_FILE}")
    return TEMPLATE_FILE.read_text(encoding="utf-8")


def load_claude_context() -> str:
    """加载 CLAUDE.md 获取用户上下文"""
    if not CLAUDE_FILE.exists():
        return ""
    return CLAUDE_FILE.read_text(encoding="utf-8")


def parse_week_str(week_str: str) -> tuple[datetime, datetime]:
    """
    解析 YYYY-Www 格式的周字符串，返回该周的周一和周日。

    例如: 2026-W20 -> (2026-05-11, 2026-05-17)
    """
    match = re.match(r"(\d{4})-W(\d{2})", week_str)
    if not match:
        raise ValueError(f"无效周格式: {week_str}，应为 YYYY-Www（如 2026-W20）")

    year = int(match.group(1))
    week = int(match.group(2))

    # 计算该周的周一
    # ISO 周从周一开始
    jan4 = datetime(year, 1, 4)
    days_since_jan4 = (week - 1) * 7
    monday = jan4 - timedelta(days=jan4.weekday()) + timedelta(days=days_since_jan4)
    sunday = monday + timedelta(days=6)

    return monday, sunday


def get_week_string(dt: datetime) -> str:
    """获取 YYYY-Www 格式的周字符串"""
    iso_cal = dt.isocalendar()
    return f"{iso_cal[0]}-W{iso_cal[1]:02d}"


def query_week_notes(db_path: Path, since_dt: datetime, until_dt: datetime, limit: int = 100) -> list[dict]:
    """查询指定时间范围内的笔记"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    since_str = since_dt.strftime("%Y-%m-%d %H:%M:%S")
    until_str = until_dt.strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.execute("""
        SELECT id, path, title, body_summary, type, source, created, updated
        FROM notes
        WHERE (created >= ? AND created <= ?)
        OR (updated >= ? AND updated <= ?)
        AND type NOT IN ('daily_brief', 'weekly_synthesis')
        ORDER BY updated DESC
        LIMIT ?
    """, (since_str, until_str, since_str, until_str, limit))

    rows = cursor.fetchall()
    conn.close()

    notes = []
    for row in rows:
        note_path = Path(row["path"])
        if not note_path.exists():
            continue
        try:
            content = note_path.read_text(encoding="utf-8")
        except Exception:
            continue

        notes.append({
            "id": row["id"],
            "path": str(note_path.relative_to(PROJECT_DIR)),
            "title": row["title"] or "",
            "body_summary": row["body_summary"] or "",
            "type": row["type"] or "",
            "source": row["source"] or "",
            "created": row["created"] or "",
            "updated": row["updated"] or "",
            "content": content
        })

    return notes


def call_llm(system_prompt: str, user_content: str) -> dict:
    """调用 MiniMax API 生成 Weekly Synthesis"""
    import requests

    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "MiniMax-M2.7",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "max_tokens": 2048,
        "temperature": 0.5
    }

    response = requests.post(
        "https://api.minimax.chat/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=120
    )
    response.raise_for_status()
    result = response.json()
    raw_text = result["choices"][0]["message"]["content"].strip()

    # 移除 thinking block
    raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)

    # 尝试移除 markdown code block
    if "```json" in raw_text:
        start = raw_text.find("```json") + 7
        end = raw_text.rfind("```")
        raw_text = raw_text[start:end].strip()
    elif "```" in raw_text:
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])

    # 从响应中提取 JSON 部分
    json_start = raw_text.find("{")
    json_end = raw_text.rfind("}")
    if json_start != -1 and json_end != -1:
        raw_text = raw_text[json_start:json_end + 1]

    return json.loads(raw_text.strip())


def validate_note(file_path: Path) -> tuple[bool, str]:
    """调用 validate_note.py 验证生成的笔记"""
    import subprocess

    validate_script = SCRIPT_DIR / "validate_note.py"
    try:
        result = subprocess.run(
            [sys.executable, str(validate_script), str(file_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)


def render_weekly_synthesis(
    synthesis_data: dict,
    week_str: str,
    start_date: str,
    end_date: str,
    notes_count: int
) -> str:
    """将 LLM 返回的数据渲染为 Weekly Synthesis markdown"""

    # 构建各 section 内容
    insights_lines = []
    for insight in synthesis_data.get("insights", []):
        if insight:
            insights_lines.append(f"- {insight}")

    contradictions_lines = []
    for contr in synthesis_data.get("contradictions", []):
        if isinstance(contr, dict):
            contradictions_lines.append(f"- **{contr.get('description', '')}**\n  {contr.get('implication', '')}")
        elif contr:
            contradictions_lines.append(f"- {contr}")

    gaps_lines = []
    for gap in synthesis_data.get("gaps", []):
        if gap:
            gaps_lines.append(f"- {gap}")

    actions_lines = []
    for action in synthesis_data.get("actions", []):
        if isinstance(action, dict):
            target = action.get("target", "")
            desc = action.get("action", "")
            if target:
                actions_lines.append(f"- {desc} → {target}")
            else:
                actions_lines.append(f"- {desc}")
        elif action:
            actions_lines.append(f"- {action}")

    # 构建 markdown
    lines = [
        "---",
        f"id: weekly-{uuid.uuid4().hex[:8]}",
        f"week: {week_str}",
        f"start_date: {start_date}",
        f"end_date: {end_date}",
        "status: draft",
        "---",
        "",
        f"# Weekly Synthesis - {week_str}",
        "",
        "## INSIGHTS CAPTURED",
    ]

    if insights_lines:
        lines.extend(insights_lines)
    else:
        lines.append("（本周无新增笔记）")

    lines.extend([
        "",
        "## CONTRADICTIONS",
    ])

    if contradictions_lines:
        lines.extend(contradictions_lines)
    else:
        lines.append("（无）")

    lines.extend([
        "",
        "## KNOWLEDGE GAPS",
    ])

    if gaps_lines:
        lines.extend(gaps_lines)
    else:
        lines.append("（无）")

    lines.extend([
        "",
        "## VAULT ACTION",
    ])

    if actions_lines:
        lines.extend(actions_lines)
    else:
        lines.append("（无）")

    return "\n".join(lines)


def generate_weekly_synthesis(
    week_str: str = None,
    dry_run: bool = False,
    db_path: Path = None
) -> dict:
    """生成 Weekly Synthesis 的主逻辑"""

    # 确定周
    if week_str:
        monday, sunday = parse_week_str(week_str)
    else:
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        week_str = get_week_string(today)

    start_date_str = monday.strftime("%Y-%m-%d")
    end_date_str = sunday.strftime("%Y-%m-%d")

    # 计算 7 天前的时间
    since_dt = monday

    # 检查数据库
    db_path = db_path or get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}。请先运行 build_index.py")

    # 查询本周的笔记
    week_notes = query_week_notes(db_path, since_dt, sunday)

    # 加载上下文
    claude_context = load_claude_context()
    prompt_template = load_prompt()

    # 构建 LLM 输入
    notes_text = ""
    if week_notes:
        for note in week_notes[:50]:
            notes_text += f"\n\n---\n\n## 笔记: {note['title']}\n路径: {note['path']}\n创建: {note['created']}\n更新: {note['updated']}\n\n摘要: {note['body_summary']}"
    else:
        notes_text = "\n\n（本周无新增笔记）"

    user_content = f"""## CLAUDE.md 内容

{claude_context}

---

## 本周（{start_date_str} 至 {end_date_str}）的笔记

{notes_text}

---

请根据以上内容生成 Weekly Synthesis，以指定的 JSON 格式输出。"""

    # 调用 LLM
    try:
        synthesis_data = call_llm(prompt_template, user_content)
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败: {e}")

    # --dry-run 模式
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "week": week_str,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "notes_count": len(week_notes),
            "synthesis_data": synthesis_data
        }

    # 渲染 markdown
    markdown_content = render_weekly_synthesis(
        synthesis_data,
        week_str,
        start_date_str,
        end_date_str,
        len(week_notes)
    )

    # 原子写入文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{week_str}.md"

    # 检查是否已存在
    if output_file.exists():
        # 备份旧文件
        backup_file = OUTPUT_DIR / f"{week_str}-backup-{datetime.now().strftime('%H%M%S')}.md"
        output_file.rename(backup_file)

    # 写入临时文件
    tmp_file = OUTPUT_DIR / f".tmp-{week_str}-{uuid.uuid4().hex[:8]}.md"
    tmp_file.write_text(markdown_content, encoding="utf-8")

    # 验证
    valid, err = validate_note(tmp_file)
    if not valid:
        tmp_file.unlink()
        raise ValueError(f"生成的笔记未通过验证: {err}")

    # rename 为正式文件
    tmp_file.rename(output_file)

    return {
        "success": True,
        "week": week_str,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "notes_count": len(week_notes),
        "output_file": str(output_file.relative_to(PROJECT_DIR)),
        "synthesis_data": synthesis_data
    }


def main():
    parser = argparse.ArgumentParser(description="生成每周总结")
    parser.add_argument(
        "--week",
        help="指定周（YYYY-Www），默认为本周"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅输出 JSON，不写文件"
    )
    parser.add_argument(
        "--db",
        help=f"数据库路径（默认: {DEFAULT_DB}）"
    )
    args = parser.parse_args()

    # 检查 API key
    try:
        get_api_key()
    except ValueError as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "hint": "设置环境变量: export MINIMAX_API_KEY=sk-..."
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    # 验证周格式
    week_str = args.week
    if week_str:
        try:
            parse_week_str(week_str)
        except ValueError as e:
            print(json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

    # 获取数据库路径
    db_path = Path(args.db) if args.db else None

    try:
        result = generate_weekly_synthesis(week_str=week_str, dry_run=args.dry_run, db_path=db_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()