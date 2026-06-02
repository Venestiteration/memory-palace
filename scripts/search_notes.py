#!/usr/bin/env python3
"""
search_notes.py - 语义搜索笔记

使用向量相似度搜索 .memory_palace/index.sqlite 中的笔记。

用法:
  python search_notes.py "我的问题"                    # 基本搜索
  python search_notes.py "期权策略" --limit 5          # 限制结果数
  python search_notes.py "技术分析" --type concept     # 按笔记类型过滤
  python search_notes.py "投资" --project trading      # 按项目过滤
  python search_notes.py "SPY" --json                 # JSON 输出

输出 JSON 格式搜索结果。
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from embedding_provider import get_embedding_provider


PROJECT_DIR = Path(__file__).parent.parent
DEFAULT_DB = PROJECT_DIR / ".memory_palace" / "index.sqlite"
VECTOR_DIR = PROJECT_DIR / ".memory_palace" / "vector_index"
MANIFEST_FILE = VECTOR_DIR / "manifest.json"


def load_manifest() -> dict:
    """加载 manifest.json"""
    if not MANIFEST_FILE.exists():
        return {}
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def load_vector(note_id: str) -> np.ndarray:
    """加载单个 note 的向量"""
    vector_path = VECTOR_DIR / f"{note_id}.npy"
    if not vector_path.exists():
        return None
    return np.load(str(vector_path))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算 cosine similarity"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def search_notes(
    query: str,
    limit: int = 10,
    note_type: str = None,
    project: str = None,
    db_path: Path = None
) -> dict:
    """
    执行语义搜索。

    Returns:
        搜索结果 dict
    """
    db_path = db_path or DEFAULT_DB

    # 获取 Embedding Provider
    try:
        provider = get_embedding_provider()
    except ValueError as e:
        raise RuntimeError(f"Embedding Provider 错误: {e}")

    # 生成查询向量
    query_vector = provider.embed(query)
    query_arr = np.array(query_vector, dtype=np.float32)

    # 连接 SQLite
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 加载 manifest
    manifest = load_manifest()

    # 构建 note_id → vector 缓存
    note_vectors = {}
    for note_id, info in manifest.items():
        vec = load_vector(note_id)
        if vec is not None:
            note_vectors[note_id] = vec

    # 构建 SQL 查询条件
    conditions = ["has_vector = 1"]
    params = []
    if note_type:
        conditions.append("type = ?")
        params.append(note_type)
    if project:
        conditions.append("source LIKE ?")
        params.append(f"%{project}%")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 查询满足条件的 notes
    cursor = conn.execute(f"""
        SELECT id, path, title, body_summary, type, source
        FROM notes
        WHERE {where_clause}
    """, params)
    notes = cursor.fetchall()
    conn.close()

    # 计算相似度
    results = []
    for note in notes:
        note_id = str(note["id"])
        if note_id not in note_vectors:
            continue

        score = cosine_similarity(query_arr, note_vectors[note_id])
        snippet = note["body_summary"] or ""

        results.append({
            "path": note["path"],
            "title": note["title"],
            "score": round(score, 4),
            "snippet": snippet[:150] + "..." if len(snippet) > 150 else snippet,
            "type": note["type"] or "",
            "source": note["source"] or ""
        })

    # 排序并限制结果
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:limit]

    return {
        "query": query,
        "results": results,
        "total": len(results),
        "provider": type(provider).__name__
    }


def main():
    parser = argparse.ArgumentParser(description="语义搜索笔记")
    parser.add_argument("query", nargs="?", help="搜索查询")
    parser.add_argument("--limit", type=int, default=10, help="返回结果数量（默认: 10）")
    parser.add_argument("--type", help="按笔记类型过滤（如: atomic_note, concept）")
    parser.add_argument("--project", help="按项目/来源过滤")
    parser.add_argument("--db", help=f"SQLite 数据库路径（默认: {DEFAULT_DB}）")
    parser.add_argument("--json", action="store_true", help="强制 JSON 输出（默认即为 JSON）")
    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(0)

    db_path = Path(args.db) if args.db else DEFAULT_DB
    if not db_path.exists():
        print(json.dumps({
            "success": False,
            "error": f"数据库不存在: {db_path}。请先运行 build_index.py 和 build_vector_index.py"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not MANIFEST_FILE.exists():
        print(json.dumps({
            "success": False,
            "error": f"向量索引不存在: {MANIFEST_FILE}。请先运行 build_vector_index.py"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        result = search_notes(
            query=args.query,
            limit=args.limit,
            note_type=args.type,
            project=args.project,
            db_path=db_path
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"搜索失败: {e}"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()