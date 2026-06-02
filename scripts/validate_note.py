#!/usr/bin/env python3
"""
validate_note.py - 验证 Markdown 文件的 frontmatter 规范

退出码：
  0 - 验证通过
  1 - 验证失败（格式错误、字段缺失、枚举值非法）
  2 - 文件无法读取或 YAML 解析错误

用法:
  python validate_note.py <file.md> [file2.md ...]
  python validate_note.py --help
"""

import sys
import json
import re
from pathlib import Path
from typing import Any

import yaml


# frontmatter 字段规范定义
FRONTMATTER_SPEC = {
    "source": {
        "required": ["id", "created", "source_type", "title", "status", "tags"],
        "fields": {
            "id": {"type": "string", "enum": None},
            "created": {"type": "string", "enum": None},
            "source_type": {"type": "string", "enum": ["article", "book", "podcast", "video", "tweet", "meeting", "document", "web", "telegram", "manual", "voice", "other"]},
            "source_url": {"type": "string", "enum": None},
            "title": {"type": "string", "enum": None},
            "author": {"type": "string", "enum": None},
            "tags": {"type": "array", "enum": None},
            "status": {"type": "string", "enum": ["inbox", "processing", "archived"]},
            "rating": {"type": "number", "enum": None},
        }
    },
    "atomic_note": {
        "required": ["id", "created", "atomic_type", "title", "status", "tags"],
        "fields": {
            "id": {"type": "string", "enum": None},
            "created": {"type": "string", "enum": None},
            "atomic_type": {"type": "string", "enum": ["concept", "claim", "mental_model", "question", "people", "case", "method", "tool", "resource"]},
            "title": {"type": "string", "enum": None},
            "tags": {"type": "array", "enum": None},
            "source": {"type": "string", "enum": None},
            "status": {"type": "string", "enum": ["seedling", "budding", "evergreen", "draft"]},
        }
    },
    "map": {
        "required": ["id", "created", "map_type", "title", "status", "tags"],
        "fields": {
            "id": {"type": "string", "enum": None},
            "created": {"type": "string", "enum": None},
            "map_type": {"type": "string", "enum": ["topic", "project", "domain", "concept"]},
            "title": {"type": "string", "enum": None},
            "tags": {"type": "array", "enum": None},
            "status": {"type": "string", "enum": ["active", "archived"]},
        }
    },
    "project": {
        "required": ["id", "created", "project_type", "title", "status", "start_date", "tags"],
        "fields": {
            "id": {"type": "string", "enum": None},
            "created": {"type": "string", "enum": None},
            "project_type": {"type": "string", "enum": ["research", "writing", "learning", "investment", "product", "other"]},
            "title": {"type": "string", "enum": None},
            "status": {"type": "string", "enum": ["active", "completed", "archived", "on_hold"]},
            "start_date": {"type": "string", "enum": None},
            "target_date": {"type": "string", "enum": None},
            "tags": {"type": "array", "enum": None},
        }
    },
    "daily_brief": {
        "required": ["id", "date", "day_summary"],
        "fields": {
            "id": {"type": "string", "enum": None},
            "title": {"type": "string", "enum": None},
            "date": {"type": "string", "enum": None},
            "day_summary": {"type": "string", "enum": None},
            "mood": {"type": "string", "enum": None},
            "energy": {"type": "string", "enum": None},
        }
    },
    "weekly_synthesis": {
        "required": ["id", "week", "start_date", "end_date", "status"],
        "fields": {
            "id": {"type": "string", "enum": None},
            "title": {"type": "string", "enum": None},
            "week": {"type": "string", "enum": None},
            "start_date": {"type": "string", "enum": None},
            "end_date": {"type": "string", "enum": None},
            "status": {"type": "string", "enum": ["draft", "published", "archived"]},
        }
    }
}


# 模板占位符替换值
PLACEHOLDER_VALUES = {
    "{{date}}": "2026-01-01",
    "{{source_type}}": "article",
    "{{source_url}}": "https://example.com",
    "{{title}}": "Template Title",
    "{{author}}": "Unknown",
    "{{rating}}": "3",
    "{{atomic_type}}": "concept",
    "{{source}}": "unknown",
    "{{map_type}}": "topic",
    "{{project_type}}": "other",
    "{{target_date}}": "2026-12-31",
    "{{week_number}}": "1",
    "{{start_date}}": "2026-01-01",
    "{{end_date}}": "2026-01-07",
    "{{mood}}": "neutral",
    "{{energy}}": "5",
    "{{theme}}": "General",
}


def get_placeholder_value(key: str) -> str:
    """返回占位符的有效值"""
    placeholder = f"{{{{{key}}}}}"
    return PLACEHOLDER_VALUES.get(placeholder, f"placeholder_{key}")


def _convert_yaml_dates(obj):
    """递归转换 YAML 日期对象为字符串"""
    if isinstance(obj, dict):
        return {k: _convert_yaml_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_yaml_dates(item) for item in obj]
    elif hasattr(obj, 'strftime'):
        return obj.strftime('%Y-%m-%d')
    return obj


def extract_frontmatter(content: str) -> tuple:
    """
    从 markdown 内容中提取 frontmatter。

    Returns:
        (frontmatter_dict, note_type, error_message)
    """
    if not content.startswith("---"):
        return None, None, "frontmatter 缺失（未以 --- 开头）"

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, None, "frontmatter 格式错误"

    yaml_content = parts[1]

    # 检查是否包含模板占位符
    has_placeholders = bool(re.search(r'\{\{\w+\}\}', yaml_content))

    try:
        processed_content = yaml_content
        if has_placeholders:
            processed_content = re.sub(r'\{\{(\w+)\}\}', lambda m: get_placeholder_value(m.group(1)), processed_content)

        fm = yaml.safe_load(processed_content)
        if fm is not None:
            fm = _convert_yaml_dates(fm)
    except yaml.YAMLError as e:
        return None, None, f"YAML 解析失败: {str(e)}"

    if not isinstance(fm, dict):
        return None, None, "frontmatter 必须是 YAML 对象"

    # 推断 note_type
    note_type = None
    if "source_type" in fm:
        note_type = "source"
    elif "atomic_type" in fm:
        note_type = "atomic_note"
    elif "map_type" in fm:
        note_type = "map"
    elif "project_type" in fm:
        note_type = "project"
    elif "day_summary" in fm:
        note_type = "daily_brief"
    elif "week" in fm and "start_date" in fm:
        note_type = "weekly_synthesis"

    return fm, note_type, ""


def validate_frontmatter(fm: dict[str, Any], note_type: str) -> tuple:
    """
    验证 frontmatter。

    Returns:
        (errors, warnings) - 错误和警告列表
    """
    errors = []
    warnings = []

    if note_type not in FRONTMATTER_SPEC:
        errors.append(f"未知的 note_type: {note_type}")
        return errors, warnings

    spec = FRONTMATTER_SPEC[note_type]

    # 检查必填字段
    for field in spec["required"]:
        if field not in fm:
            errors.append(f"缺少必填字段: {field}")

    # 验证每个字段
    for field, value in fm.items():
        if field not in spec["fields"]:
            warnings.append(f"未知字段: {field}")
            continue

        field_spec = spec["fields"][field]
        expected_type = field_spec["type"]
        enum_values = field_spec["enum"]

        # 类型检查
        if expected_type == "array":
            if not isinstance(value, list):
                errors.append(f"字段 {field} 必须是数组，实际类型: {type(value).__name__}")
        elif expected_type == "number":
            if not isinstance(value, (int, float)):
                errors.append(f"字段 {field} 必须是数字，实际类型: {type(value).__name__}")
        elif expected_type == "string":
            if not isinstance(value, str):
                errors.append(f"字段 {field} 必须是字符串，实际类型: {type(value).__name__}")

        # 枚举检查
        if enum_values and value not in enum_values:
            errors.append(f"字段 {field} 的值 '{value}' 不在允许的枚举值内: {enum_values}")

    return errors, warnings


def validate_file(file_path: Path) -> dict[str, Any]:
    """
    验证单个文件。

    Returns:
        验证结果字典，包含 file、ok、warnings、errors 字段
    """
    result = {
        "file": str(file_path),
        "ok": False,
        "errors": [],
        "warnings": []
    }

    # 文件不存在
    if not file_path.exists():
        result["errors"].append(f"文件不存在: {file_path}")
        return result

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        result["errors"].append(f"文件读取失败: {str(e)}")
        return result

    fm, note_type, error = extract_frontmatter(content)

    if error:
        result["errors"].append(error)
        return result

    if fm is None:
        result["errors"].append("无法解析 frontmatter")
        return result

    # 检测是否是模板文件（含占位符）
    is_template = "title" in fm and fm.get("title") == "Template Title"

    if note_type:
        errors, warnings = validate_frontmatter(fm, note_type)
        result["errors"].extend(errors)
        result["warnings"].extend(warnings)

        # 模板文件：缺少 id 视为警告而非错误
        if is_template and any("缺少必填字段: id" in e for e in errors):
            result["warnings"].append("模板文件缺少 id 字段（正常，Obsidian 会自动生成）")
            result["errors"] = [e for e in result["errors"] if "缺少必填字段: id" not in e]

        result["ok"] = len(result["errors"]) == 0
    else:
        result["errors"].append("无法推断笔记类型")
        result["ok"] = False

    return result


def main():
    # --help 处理
    if len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)

    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "用法: python validate_note.py <file.md> [file2.md ...]"
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    results = []

    for arg in sys.argv[1:]:
        file_path = Path(arg)
        result = validate_file(file_path)
        results.append(result)

    # 输出 JSON
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # 计算退出码
    # 退出码 0: 全部通过
    # 退出码 1: 存在警告（未知字段等非致命问题）
    # 退出码 2: 存在错误（缺少必填字段、枚举值非法、文件不存在等）

    has_errors = any(r["errors"] for r in results)

    if has_errors:
        sys.exit(2)
    else:
        has_warnings = any(r["warnings"] for r in results)
        sys.exit(1 if has_warnings else 0)


if __name__ == "__main__":
    main()