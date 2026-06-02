#!/usr/bin/env python3
"""
build_vector_index.py - 构建向量索引

读取 .memory_palace/index.sqlite 中的 notes，对标题+摘要生成 embedding，
保存到 .memory_palace/vector_index/。

用法:
  python build_vector_index.py                  # 增量构建
  python build_vector_index.py --rebuild        # 全量重建
  python build_vector_index.py --db PATH        # 指定 SQLite 路径

输出 JSON 格式报告。
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from embedding_provider import get_embedding_provider


PROJECT_DIR = Path(__file__).parent.parent
DEFAULT_DB = PROJECT_DIR / ".memory_palace" / "index.sqlite"
VECTOR_DIR = PROJECT_DIR / ".memory_palace" / "vector_index"
MANIFEST_FILE = VECTOR_DIR / "manifest.json"


def ensure_vector_dir():
    """确保向量索引目录存在"""
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)


def load_manifest() -> dict:
    """加载 manifest.json"""
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def save_manifest(manifest: dict):
    """保存 manifest.json"""
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_note_text(note: dict) -> str:
    """拼接 note 的文本用于 embedding"""
    parts = []
    if note.get("title"):
        parts.append(note["title"])
    if note.get("body_summary"):
        parts.append(note["body_summary"])
    return "\n".join(parts)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的 cosine similarity"""
    a_arr = np.array(a)
    b_arr = np.array(b)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


def build_vector_index(db_path: Path, rebuild: bool) -> dict:
    """
    执行向量索引构建。

    Returns:
        索引报告 dict
    """
    ensure_vector_dir()

    # 连接 SQLite
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 加载 manifest
    manifest = load_manifest() if not rebuild else {}

    if rebuild:
        # 全量重建：清空向量目录
        for f in VECTOR_DIR.glob("*.npy"):
            f.unlink()
        manifest = {}

    # 获取 Embedding Provider
    try:
        provider = get_embedding_provider()
    except ValueError as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "hint": "请设置 DASHSCOPE_API_KEY 或 ANTHROPIC_API_KEY 环境变量"
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    stats = {
        "vectors_built": 0,
        "vectors_skipped": 0,
        "errors": 0
    }

    # 查询所有 notes
    cursor = conn.execute("""
        SELECT id, path, title, body_summary
        FROM notes
        ORDER BY id
    """)
    notes = cursor.fetchall()

    for note in notes:
        note_id = str(note["id"])
        path = note["path"]

        # 检查是否已存在向量（非 rebuild 时跳过）
        if not rebuild and note_id in manifest:
            stats["vectors_skipped"] += 1
            continue

        # 生成文本
        text = get_note_text({
            "title": note["title"],
            "body_summary": note["body_summary"]
        })
        if not text.strip():
            stats["vectors_skipped"] += 1
            continue

        # 生成 embedding
        try:
            vector = provider.embed(text)
        except Exception as e:
            print(f"[警告] Embedding 失败 {path}: {e}", file=sys.stderr)
            stats["errors"] += 1
            continue

        # 保存向量文件
        vector_path = VECTOR_DIR / f"{note_id}.npy"
        np.save(str(vector_path), np.array(vector, dtype=np.float32))

        # 更新 manifest
        manifest[note_id] = {
            "path": path,
            "title": note["title"],
            "vector_file": f"{note_id}.npy"
        }
        stats["vectors_built"] += 1

        # 标记 has_vector
        conn.execute("UPDATE notes SET has_vector=1 WHERE id=?", (note["id"],))

        # 每 10 条保存一次 manifest
        if stats["vectors_built"] % 10 == 0:
            save_manifest(manifest)

    conn.commit()
    conn.close()

    # 最终保存 manifest
    save_manifest(manifest)

    stats["total_in_db"] = len(notes)
    return stats


def main():
    parser = argparse.ArgumentParser(description="构建向量索引")
    parser.add_argument("--rebuild", action="store_true", help="全量重建向量索引")
    parser.add_argument("--db", help=f"SQLite 数据库路径（默认: {DEFAULT_DB}）")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else DEFAULT_DB
    if not db_path.exists():
        print(json.dumps({
            "success": False,
            "error": f"数据库不存在: {db_path}。请先运行 build_index.py"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        stats = build_vector_index(db_path, args.rebuild)
        result = {
            "success": True,
            "vector_dir": str(VECTOR_DIR),
            "manifest": str(MANIFEST_FILE),
            "stats": stats
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"向量索引构建失败: {e}"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()