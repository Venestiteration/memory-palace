#!/usr/bin/env python3
"""
generate_daily_brief.py - 生成每日简报

读取过去 24 小时新增/更新内容，调用 LLM 生成 Daily Brief。

用法:
  python generate_daily_brief.py                    # 生成今日简报
  python generate_daily_brief.py --dry-run          # 仅输出 JSON，不写文件
  python generate_daily_brief.py --date YYYY-MM-DD  # 指定日期

输出:
  06_Daily_Briefs/YYYY-MM-DD.md

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
PROMPT_FILE = SCRIPT_DIR / "prompts" / "daily_brief.md"
OUTPUT_DIR = PROJECT_DIR / "06_Daily_Briefs"
TEMPLATE_FILE = PROJECT_DIR / "_templates" / "daily_brief.md"
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
    """加载 daily_brief 模板"""
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"模板文件不存在: {TEMPLATE_FILE}")
    return TEMPLATE_FILE.read_text(encoding="utf-8")


def load_claude_context() -> str:
    """加载 CLAUDE.md 获取用户上下文"""
    if not CLAUDE_FILE.exists():
        return ""
    return CLAUDE_FILE.read_text(encoding="utf-8")


def query_recent_notes(db_path: Path, since_dt: datetime, limit: int = 50) -> list[dict]:
    """查询指定时间后的笔记"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    since_str = since_dt.strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.execute("""
        SELECT id, path, title, body_summary, type, source, created, updated
        FROM notes
        WHERE (created >= ? OR updated >= ?)
        AND type NOT IN ('daily_brief', 'weekly_synthesis')
        ORDER BY updated DESC
        LIMIT ?
    """, (since_str, since_str, limit))

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
    """调用 MiniMax API 生成 Daily Brief"""
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


def render_daily_brief(
    brief_data: dict,
    date_str: str,
    notes_count: int
) -> str:
    """将 LLM 返回的数据渲染为 Daily Brief markdown"""

    # 构建连接列表
    connections_lines = []
    for conn in brief_data.get("connections", []):
        if conn.get("new_note") and conn.get("existing_note"):
            connections_lines.append(
                f"- **{conn['new_note']}** → **{conn['existing_note']}**\n  {conn.get('reason', '')}"
            )

    # 构建隐含模式
    pattern = brief_data.get("pattern", "")

    # 构建今日思考
    reflection = brief_data.get("reflection", "")

    # 构建 markdown
    lines = [
        "---",
        f"id: daily-{uuid.uuid4().hex[:8]}",
        f"date: {date_str}",
        'day_summary: ""',
        'mood: ""',
        'energy: ""',
        "---",
        "",
        f"# Daily Brief - {date_str}",
        "",
        "## 新旧连接",
    ]

    if connections_lines:
        lines.extend(connections_lines)
    else:
        lines.append("（过去 24 小时无新增笔记）")

    lines.extend([
        "",
        "## 隐含模式",
        pattern or "（无）",
        "",
        "## 今日思考",
        reflection or "（无）",
    ])

    return "\n".join(lines)


def generate_daily_brief(
    date_str: str,
    dry_run: bool = False,
    db_path: Path = None
) -> dict:
    """生成 Daily Brief 的主逻辑"""

    # 解析日期
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"无效日期格式: {date_str}，应为 YYYY-MM-DD")

    # 计算 24 小时前的时间
    since_dt = target_date - timedelta(hours=24)

    # 检查数据库
    db_path = db_path or get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}。请先运行 build_index.py")

    # 查询最近的笔记
    recent_notes = query_recent_notes(db_path, since_dt)

    # 加载上下文
    claude_context = load_claude_context()
    prompt_template = load_prompt()

    # 构建 LLM 输入
    notes_text = ""
    if recent_notes:
        for note in recent_notes[:20]:
            notes_text += f"\n\n---\n\n## 笔记: {note['title']}\n路径: {note['path']}\n创建: {note['created']}\n更新: {note['updated']}\n\n摘要: {note['body_summary']}"
    else:
        notes_text = "\n\n（过去 24 小时无新增笔记）"

    user_content = f"""## CLAUDE.md 内容

{claude_context}

---

## 最近 24 小时的笔记

{notes_text}

---

请根据以上内容生成 Daily Brief，以指定的 JSON 格式输出。"""

    # 调用 LLM
    try:
        brief_data = call_llm(prompt_template, user_content)
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败: {e}")

    # --dry-run 模式
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "date": date_str,
            "notes_count": len(recent_notes),
            "brief_data": brief_data
        }

    # 渲染 markdown
    markdown_content = render_daily_brief(brief_data, date_str, len(recent_notes))

    # 原子写入文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{date_str}.md"

    # 检查是否已存在
    if output_file.exists():
        # 备份旧文件
        backup_file = OUTPUT_DIR / f"{date_str}-backup-{datetime.now().strftime('%H%M%S')}.md"
        output_file.rename(backup_file)

    # 写入临时文件
    tmp_file = OUTPUT_DIR / f".tmp-{date_str}-{uuid.uuid4().hex[:8]}.md"
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
        "date": date_str,
        "notes_count": len(recent_notes),
        "output_file": str(output_file.relative_to(PROJECT_DIR)),
        "brief_data": brief_data
    }


def main():
    parser = argparse.ArgumentParser(description="生成每日简报")
    parser.add_argument(
        "--date",
        help="指定日期（YYYY-MM-DD），默认为今天"
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

    # 确定日期
    date_str = args.date
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 验证日期格式
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(json.dumps({
            "success": False,
            "error": f"无效日期格式: {date_str}，应为 YYYY-MM-DD"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 获取数据库路径
    db_path = Path(args.db) if args.db else None

    try:
        result = generate_daily_brief(date_str, dry_run=args.dry_run, db_path=db_path)
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