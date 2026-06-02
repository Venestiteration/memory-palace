#!/usr/bin/env python3
"""
atomize_note.py - 调用 LLM 将 source/inbox 文件原子化

用法:
  python atomize_note.py <file.md>               # 仅输出 JSON 候选
  python atomize_note.py <file.md> --write       # 写入 02_Atomic_Notes/

环境变量:
  MINIMAX_API_KEY 或 ANTHROPIC_API_KEY - MiniMax API key（必填）

输出字段:
  title, core_claim, evidence, related_topics, suggested_links, counter_argument
"""

import argparse
import json
import os
import re
import sys
import uuid
import subprocess
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "缺少依赖: requests。请运行: pip install requests",
        "exit_code": 2
    }, ensure_ascii=False, indent=2))
    sys.exit(2)


SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = PROJECT_DIR / "_templates"
ATOMIC_TEMPLATE = TEMPLATES_DIR / "atomic_note.md"
PROMPT_FILE = SCRIPT_DIR / "prompts" / "atomize_note.md"
VALIDATE_SCRIPT = SCRIPT_DIR / "validate_note.py"
INBOX_DIR = PROJECT_DIR / "00_Inbox"
SOURCES_DIR = PROJECT_DIR / "01_Sources"
ATOMIC_DIR = PROJECT_DIR / "02_Atomic_Notes"


ATOMIC_TYPE_KEYWORDS = {
    "concept": ["概念", "定义", "本质", "是什么", "定义是"],
    "claim": ["主张", "认为", "观点", "论点", "论断"],
    "mental_model": ["模型", "框架", "思维模型", "心智模型", "范式"],
    "question": ["问题", "为什么", "如何", "怎样", "是不是", "会不会"],
    "people": ["人物", "人物介绍", "创始人", "企业家", "投资者"],
    "case": ["案例", "例子", "实例", "事件", "故事"],
    "method": ["方法", "技巧", "策略", "做法", "流程"],
    "tool": ["工具", "软件", "平台", "系统", "产品"],
    "resource": ["资源", "资料", "来源", "素材", "数据库"],
}


def get_api_key() -> str:
    """从环境变量获取 API key（支持 MINIMAX_API_KEY 或 ANTHROPIC_API_KEY）"""
    key = os.environ.get("MINIMAX_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("环境变量 MINIMAX_API_KEY 或 ANTHROPIC_API_KEY 未设置")
    return key


def infer_atomic_type(title: str, content: str) -> str:
    """根据标题和内容推断 atomic_type"""
    combined = title + content
    scores = {}
    for atype, keywords in ATOMIC_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        scores[atype] = score
    if max(scores.values()) == 0:
        return "concept"
    return max(scores, key=scores.get)


def load_template() -> str:
    """加载 atomic_note 模板"""
    if not ATOMIC_TEMPLATE.exists():
        raise FileNotFoundError(f"模板文件不存在: {ATOMIC_TEMPLATE}")
    return ATOMIC_TEMPLATE.read_text(encoding="utf-8")


def load_prompt() -> str:
    """加载 LLM prompt 模板"""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {PROMPT_FILE}")
    return PROMPT_FILE.read_text(encoding="utf-8")


MINIMAX_API_URL = "https://api.minimax.chat/v1/chat/completions"


def call_llm(source_content: str, system_prompt: str) -> dict:
    """
    调用 MiniMax API 生成候选原子笔记。

    Returns:
        {"candidates": [...]}
    """
    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "MiniMax-M2.7",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""请分析以下 source 文件，提取原子笔记候选：

---

{source_content}

---

请以指定的 JSON 格式输出候选原子笔记。输出仅包含 JSON，不要有其他内容。"""}
        ],
        "max_tokens": 2048,
        "temperature": 0.3
    }
    response = requests.post(MINIMAX_API_URL, headers=headers, json=data, timeout=120)
    response.raise_for_status()
    result = response.json()
    raw_text = result["choices"][0]["message"]["content"].strip()

    # 移除 thinking block（MiniMax 使用 thinks 格式）
    raw_text = re.sub(r"<think>.*?", "", raw_text, flags=re.DOTALL)

    # 尝试移除 markdown code block
    if "```json" in raw_text:
        start = raw_text.find("```json") + 7
        end = raw_text.rfind("```")
        raw_text = raw_text[start:end].strip()
    elif "```" in raw_text:
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # 从响应中提取 JSON 部分（防止模型在 JSON 外添加说明文字）
    json_start = raw_text.find("{")
    json_end = raw_text.rfind("}")
    if json_start != -1 and json_end != -1:
        raw_text = raw_text[json_start:json_end + 1]

    return json.loads(raw_text.strip())


def render_atomic_note(template: str, candidate: dict, source_path: Path, created_date: str) -> str:
    """
    将候选笔记渲染为 atomic_note.md 格式。

    Returns:
        渲染后的 markdown 字符串
    """
    atomic_type = infer_atomic_type(candidate["title"], candidate["core_claim"])
    note_id = f"atomic-{uuid.uuid4().hex[:8]}"

    # 构建联想链接
    links = candidate.get("suggested_links", [])

    # 替换 frontmatter 字段
    content = template
    note_id = f"atomic-{uuid.uuid4().hex[:8]}"
    content = content.replace("{{date}}", created_date)
    content = content.replace("{{atomic_type}}", atomic_type)
    # 只替换 frontmatter 中的 source 行（精确匹配 "source: {{source}}"）
    content = content.replace("source: {{source}}", f"source: {source_path}")
    # tags
    tags = candidate.get("related_topics", [])
    tags_str = json.dumps(tags, ensure_ascii=False)
    content = content.replace("tags: []", f"tags: {tags_str}")
    # id 和 title（必填字段，模板中没有）
    content = content.replace("---\n", f"---\nid: {note_id}\ntitle: {candidate['title']}\n", 1)

    # 替换标题
    content = content.replace("{{title}}", candidate["title"])

    # 替换正文
    content = content.replace("{{content}}", candidate["core_claim"])

    # 来源依据 - 替换正文部分的 {{source}} 为 evidence
    evidence = candidate.get("evidence", "—")
    content = content.replace("## 来源依据\n{{source}}", f"## 来源依据\n{evidence}")

    # 联想 - LLM 返回的 suggested_links 已经是 [[title]] 格式
    link_lines = []
    for link in links:
        # 确保是 [[title]] 格式（LLM 已包含双括号）
        if link.startswith("[[") and link.endswith("]]"):
            link_lines.append(f"- 联想到：{link}")
        else:
            link_lines.append(f"- 联想到：[[{link}]]")
    link_section = "\n".join(link_lines) if link_lines else "-"
    content = content.replace("- 联想到：[[]]", link_section)

    # 反例/质疑
    counter = candidate.get("counter_argument", "—")
    content = content.replace("## 反例/质疑\n-\n", f"## 反例/质疑\n{counter}\n")

    return content


def validate_note(file_path: Path) -> tuple[bool, str]:
    """
    调用 validate_note.py 验证生成的笔记。

    Returns:
        (is_valid, error_message)
    """
    try:
        result = subprocess.run(
            [sys.executable, str(VALIDATE_SCRIPT), str(file_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)


def write_atomic_note(candidate: dict, source_path: Path, created_date: str) -> tuple[Path, str]:
    """
    将单个候选笔记写入 02_Atomic_Notes/。

    Returns:
        (written_path, atomic_type)

    Raises:
        Exception - 写入失败时
    """
    template = load_template()
    atomic_type = infer_atomic_type(candidate["title"], candidate["core_claim"])

    output_dir = ATOMIC_DIR / atomic_type
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    title_slug = candidate["title"][:20]
    title_slug = "".join(c if c.isalnum() or c in " -_" else "_" for c in title_slug)
    filename = f"{created_date.replace('-', '')}-{title_slug}.md"
    dest_path = output_dir / filename

    # 防覆盖：已存在则跳过
    if dest_path.exists():
        raise FileExistsError(f"目标文件已存在: {dest_path}")

    # 原子写：先写 temp，写入完成后再 rename
    content = render_atomic_note(template, candidate, source_path, created_date)
    dir_fd = None
    tmp_fd = None
    try:
        # 在目标目录创建临时文件
        dir_fd = os.open(str(output_dir), os.O_RDONLY)
        tmp_fd = os.open(
            str(output_dir / f".tmp-{filename}"),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644
        )
        os.write(tmp_fd, content.encode("utf-8"))
        os.fsync(tmp_fd)
        os.close(tmp_fd)
        tmp_fd = None

        # validate 临时文件
        tmp_path = output_dir / f".tmp-{filename}"
        valid, err = validate_note(tmp_path)
        if not valid:
            os.unlink(tmp_path)
            raise ValueError(f"生成的笔记未通过验证: {err}")

        # rename 为正式文件
        os.rename(str(tmp_path), str(dest_path))
    finally:
        if tmp_fd is not None:
            os.close(tmp_fd)
        if dir_fd is not None:
            os.close(dir_fd)

    return dest_path, atomic_type


def main():
    parser = argparse.ArgumentParser(description="调用 LLM 将 source 文件原子化")
    parser.add_argument("file", help="source/inbox Markdown 文件路径")
    parser.add_argument("--write", action="store_true", help="写入 02_Atomic_Notes/")
    args = parser.parse_args()

    # 检查 API key
    try:
        api_key = get_api_key()
    except ValueError as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "hint": "设置环境变量: export MINIMAX_API_KEY=sk-..."
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    # 解析文件路径
    source_path = Path(args.file)
    if not source_path.exists():
        source_path = INBOX_DIR / args.file
        if not source_path.exists():
            print(json.dumps({
                "success": False,
                "error": f"文件不存在: {args.file}"
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

    # 读取原文
    try:
        source_content = source_path.read_text(encoding="utf-8")
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"文件读取失败: {e}"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 提取 frontmatter 中的 created 日期
    created_date = ""
    try:
        import yaml
        if source_content.startswith("---"):
            parts = source_content.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1])
                created_date = str(fm.get("created", "")) if fm else ""
    except Exception:
        pass

    # 调用 LLM
    try:
        system_prompt = load_prompt()
        result = call_llm(source_content, system_prompt)
    except requests.RequestException as e:
        print(json.dumps({
            "success": False,
            "error": f"API 请求失败: {e}",
            "candidates": []
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"LLM 调用失败: {e}",
            "candidates": []
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    candidates = result.get("candidates", [])
    if not candidates:
        print(json.dumps({
            "success": False,
            "error": "LLM 未返回任何候选笔记",
            "candidates": []
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # --write 模式
    written = []
    errors = []

    if args.write:
        for candidate in candidates:
            try:
                dest_path, atomic_type = write_atomic_note(
                    candidate, source_path,
                    created_date or "2026-05-13"
                )
                written.append({
                    "file": str(dest_path.relative_to(PROJECT_DIR)),
                    "atomic_type": atomic_type,
                    "title": candidate["title"]
                })
            except FileExistsError:
                errors.append(f"跳过（文件已存在）: {candidate['title']}")
            except Exception as e:
                errors.append(f"写入失败 {candidate['title']}: {e}")

    # 输出
    output = {
        "success": True,
        "source": str(source_path),
        "candidates_count": len(candidates),
        "candidates": candidates,
    }
    if args.write:
        output["written"] = written
        output["errors"] = errors

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
