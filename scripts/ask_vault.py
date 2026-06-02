#!/usr/bin/env python3
"""
ask_vault.py - Ask Vault 问答层

接收自然语言问题，通过向量搜索获取相关笔记，调用 LLM 生成回答。

用法:
  python ask_vault.py "SPY相关笔记有哪些？"
  python ask_vault.py "期权希腊字母是什么" --limit 5
  python ask_vault.py "帮我分析最近的交易笔记" --save decisions
  python ask_vault.py "项目进度如何" --save reports

输出:
  默认输出到 stdout（带来源引用）
  --save 参数保存到 08_Outputs/{category}/YYYYMMDD-HHMMSS-{query_slug}.md
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import get_settings
from llm_provider import get_llm_provider


PROJECT_DIR = Path(__file__).parent.parent
DEFAULT_DB = PROJECT_DIR / ".memory_palace" / "index.sqlite"
PROMPT_FILE = Path(__file__).parent / "prompts" / "ask_vault.md"
CLAUDE_FILE = PROJECT_DIR / "CLAUDE.md"
OUTPUT_DIR = PROJECT_DIR / "08_Outputs"

VALID_CATEGORIES = ["decisions", "reports", "essays"]


def load_prompt() -> str:
    """加载 LLM prompt 模板"""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {PROMPT_FILE}")
    return PROMPT_FILE.read_text(encoding="utf-8")


def load_claude_context() -> str:
    """加载 CLAUDE.md 获取用户上下文"""
    if not CLAUDE_FILE.exists():
        return ""
    return CLAUDE_FILE.read_text(encoding="utf-8")


def search_and_fetch_notes(query: str, limit: int = 5) -> list[dict]:
    """
    使用 search_notes.py 的逻辑进行向量搜索，并读取笔记内容。

    Returns:
        list of dict: [{"path": str, "title": str, "content": str, "score": float}, ...]
    """
    from embedding_provider import get_embedding_provider
    import sqlite3
    import numpy as np

    settings = get_settings()
    db_path = settings.db_path
    vector_dir = settings.vector_index_path
    manifest_file = vector_dir / "manifest.json"

    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}。请先运行 build_index.py")

    if not manifest_file.exists():
        raise FileNotFoundError(f"向量索引不存在: {manifest_file}。请先运行 build_vector_index.py")

    # 生成查询向量
    provider = get_embedding_provider()
    query_vector = provider.embed(query)
    query_arr = np.array(query_vector, dtype=np.float32)

    # 加载 manifest 和向量
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    # 连接数据库
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 查询有向量的笔记
    cursor = conn.execute("""
        SELECT id, path, title, body_summary, type, source
        FROM notes
        WHERE has_vector = 1
        ORDER BY updated DESC
        LIMIT 500
    """)
    notes = cursor.fetchall()
    conn.close()

    # 加载向量并计算相似度
    note_scores = []
    for note in notes:
        note_id = str(note["id"])
        vector_path = vector_dir / f"{note_id}.npy"
        if not vector_path.exists():
            continue

        vec = np.load(str(vector_path))
        score = float(np.dot(query_arr, vec) / (np.linalg.norm(query_arr) * np.linalg.norm(vec)))

        note_scores.append({
            "id": note_id,
            "path": note["path"],
            "title": note["title"] or "",
            "body_summary": note["body_summary"] or "",
            "type": note["type"] or "",
            "source": note["source"] or "",
            "score": round(score, 4)
        })

    # 排序取 top K
    note_scores.sort(key=lambda x: x["score"], reverse=True)
    top_notes = note_scores[:limit]

    # 读取笔记内容
    result = []
    for note in top_notes:
        note_path = Path(note["path"])
        if not note_path.exists():
            continue
        try:
            content = note_path.read_text(encoding="utf-8")
        except Exception:
            continue

        result.append({
            "path": str(note_path.relative_to(PROJECT_DIR)),
            "title": note["title"],
            "content": content,
            "score": note["score"],
            "type": note["type"],
            "source": note["source"]
        })

    return result


def build_context(query: str, notes: list[dict], claude_context: str) -> str:
    """构建 LLM 输入上下文"""
    notes_text = []
    for i, note in enumerate(notes, 1):
        # 截取前 2000 字符避免上下文过长
        content = note["content"][:2000]
        notes_text.append(
            f"\n\n## 笔记 {i}: {note['title']}\n"
            f"路径: {note['path']}\n"
            f"相关度: {note['score']}\n"
            f"类型: {note['type']}\n\n"
            f"{content}"
        )

    user_content = f"""## 用户问题
{query}

---

## CLAUDE.md 用户上下文

{claude_context}

---

## 相关笔记

{"".join(notes_text)}

---

请根据以上内容回答用户问题。回答必须包含引用来源（笔记路径）。"""

    return user_content


def save_to_output(query: str, answer: str, category: str) -> Path:
    """保存回答到 08_Outputs/{category}/"""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"无效类别: {category}，可选: {VALID_CATEGORIES}")

    output_category_dir = OUTPUT_DIR / category
    output_category_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    query_slug = query[:30].replace(" ", "-").replace("/", "-").replace("\\", "-")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{query_slug}.md"

    # 构建 Markdown
    content = [
        "---",
        f"id: vault-{uuid.uuid4().hex[:8]}",
        f"query: {query}",
        f"category: {category}",
        f"created: {datetime.now().isoformat()}",
        "---",
        "",
        f"# Ask Vault: {query}",
        "",
        answer
    ]

    output_path = output_category_dir / filename
    output_path.write_text("\n".join(content), encoding="utf-8")

    return output_path


def ask_vault(query: str, limit: int = 5, save_category: str = None) -> dict:
    """Ask Vault 主逻辑"""
    # 获取 LLM Provider
    try:
        llm = get_llm_provider()
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "hint": "设置环境变量: export MINIMAX_API_KEY=sk-..."
        }

    # 加载 prompt 和用户上下文
    prompt_template = load_prompt()
    claude_context = load_claude_context()

    # 搜索并获取笔记
    try:
        notes = search_and_fetch_notes(query, limit=limit)
    except Exception as e:
        return {
            "success": False,
            "error": f"搜索失败: {e}"
        }

    if not notes:
        return {
            "success": True,
            "query": query,
            "answer": "未找到相关笔记。请确保已运行 build_index.py 和 build_vector_index.py。",
            "references": [],
            "saved": None
        }

    # 构建上下文并调用 LLM
    user_content = build_context(query, notes, claude_context)

    try:
        answer = llm.chat(prompt_template, user_content)
    except Exception as e:
        return {
            "success": False,
            "error": f"LLM 调用失败: {e}"
        }

    # 提取引用路径
    references = [{"path": n["path"], "title": n["title"], "score": n["score"]} for n in notes]

    result = {
        "success": True,
        "query": query,
        "answer": answer,
        "references": references,
        "notes_count": len(notes),
        "saved": None
    }

    # 保存到文件（如果指定）
    if save_category:
        try:
            output_path = save_to_output(query, answer, save_category)
            result["saved"] = str(output_path.relative_to(PROJECT_DIR))
        except Exception as e:
            result["save_error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Ask Vault - 通过向量搜索和 LLM 回答关于笔记库的问题",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ask_vault.py "SPY相关笔记有哪些？"
  python ask_vault.py "期权希腊字母是什么" --limit 5
  python ask_vault.py "帮我分析最近的交易" --save decisions

输出:
  默认输出到 stdout（带来源引用）
  --save 参数保存到 08_Outputs/{decisions,reports,essays}/YYYYMMDD-HHMMSS-*.md
        """
    )
    parser.add_argument("query", nargs="?", help="要询问的问题")
    parser.add_argument("--limit", type=int, default=5, help="搜索的笔记数量（默认: 5）")
    parser.add_argument(
        "--save",
        choices=VALID_CATEGORIES,
        help=f"保存回答到 08_Outputs/{{decisions,reports,essays}}/"
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")

    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(0)

    result = ask_vault(args.query, limit=args.limit, save_category=args.save)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if not result["success"]:
            print(f"错误: {result['error']}", file=sys.stderr)
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"问题: {result['query']}")
        print(f"{'='*60}\n")
        print(result["answer"])
        print(f"\n{'='*60}")
        print(f"引用来源 ({result['notes_count']} 条):")
        for ref in result["references"]:
            print(f"  - [{ref['path']}] {ref['title']} (相关度: {ref['score']})")

        if result.get("saved"):
            print(f"\n已保存到: {result['saved']}")
        if result.get("save_error"):
            print(f"保存失败: {result['save_error']}", file=sys.stderr)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()