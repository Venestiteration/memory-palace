#!/usr/bin/env python3
"""
capture_telegram.py - 处理 Telegram 消息并生成快速捕获笔记

用途：将 Telegram message JSON 文件转换为 Markdown 笔记，存入 00_Inbox/telegram/
使用方式：python capture_telegram.py <message.json>

输入：Telegram message JSON 文件
输出：
  - 00_Inbox/telegram/YYYYMMDD-HHMMSS-telegram-{message_id}.md
  - JSON 处理结果（stdout）
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def parse_telegram_message(json_path: Path) -> dict:
    """
    解析 Telegram message JSON 文件。

    Returns:
        解析后的消息字典
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {str(e)}")
    except Exception as e:
        raise ValueError(f"文件读取失败: {str(e)}")

    if not isinstance(data, dict):
        raise ValueError("JSON 根节点必须是对象")

    return data


def extract_fields(data: dict) -> dict:
    """
    从 Telegram message JSON 中提取必要字段。

    Returns:
        {
            "message_id": str,
            "chat_id": str,
            "text": str,
            "date": str,
            "from": str
        }
    """
    errors = []

    message_id = data.get("message_id")
    if not message_id:
        errors.append("缺少必填字段: message_id")

    chat_id = data.get("chat", {}).get("id")
    if not chat_id:
        errors.append("缺少必填字段: chat.id")

    text = data.get("text")
    if not text:
        errors.append("缺少必填字段: text")

    date = data.get("date")
    if not date:
        errors.append("缺少必填字段: date")

    # from: 优先取 username，其次 first_name
    from_data = data.get("from", {})
    if from_data:
        from_user = from_data.get("username") or from_data.get("first_name", "unknown")
    else:
        from_user = "unknown"

    if errors:
        raise ValueError("; ".join(errors))

    return {
        "message_id": str(message_id),
        "chat_id": str(chat_id),
        "text": text,
        "date": date,
        "from": from_user
    }


def format_date(date_str: str) -> str:
    """
    将 Telegram date 字符串格式化为 YYYY-MM-DD。

    Telegram date 格式: "2026-05-13T14:30:52+08:00" 或 "2026-05-13 14:30:52"
    """
    # 尝试 ISO 格式
    try:
        dt = datetime.fromisoformat(date_str.replace("+", "+").rstrip("Z"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    # 尝试简单格式
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    # 回退：直接提取日期部分
    return date_str[:10] if len(date_str) >= 10 else date_str


def format_datetime(date_str: str) -> str:
    """
    将 Telegram date 字符串格式化为 YYYYMMDD-HHMMSS。
    """
    try:
        dt = datetime.fromisoformat(date_str.replace("+", "+").rstrip("Z"))
        return dt.strftime("%Y%m%d-%H%M%S")
    except ValueError:
        pass

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y%m%d-%H%M%S")
    except ValueError:
        pass

    # 回退：移除非数字字符
    import re
    return re.sub(r'\D', '', date_str[:19])[:15]


def escape_yaml_value(text: str) -> str:
    """对 YAML 值进行转义，处理特殊字符"""
    if not text:
        return '""'
    needs_quoting = any(c in text for c in ':{}[]|>&*!%@`"\'\n') or text.startswith(' ') or text.endswith(' ')
    if needs_quoting:
        return json.dumps(text, ensure_ascii=False)[1:-1]
    return text


def generate_markdown(fields: dict, output_dir: Path) -> Path:
    """
    生成 Markdown 笔记文件。

    Returns:
        生成的笔记文件路径
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{format_datetime(fields['date'])}-telegram-{fields['message_id']}.md"
    filepath = output_dir / filename

    # 处理 title（text 前50字），转义特殊字符
    raw_text = fields["text"]
    safe_title = raw_text[:50] + ("..." if len(raw_text) > 50 else "")

    content_lines = [
        "---",
        f'id: telegram-{fields["message_id"]}',
        f"created: {format_date(fields['date'])}",
        "source_type: telegram",
        f'source_url: ""',
        f"title: |",
        f"  {escape_yaml_value(raw_text[:50])}",
        f'author: {escape_yaml_value(fields["from"])}',
        f'tags: ["telegram", "chat_{fields["chat_id"]}"]',
        "status: inbox",
        "rating: 0",
        "---",
        "",
        "# Quick Capture",
        "",
        "## Raw",
        f"{raw_text}",
        "",
        "## Source",
        f"- Message ID: {fields['message_id']}",
        f"- Chat ID: {fields['chat_id']}",
        f"- Date: {fields['date']}",
        f"- From: {fields['from']}",
        "",
        "## Processing Notes",
        "-",
    ]

    filepath.write_text("\n".join(content_lines), encoding="utf-8")
    return filepath


def main():
    # --help 处理
    if len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)

    # --test 处理：本地模拟一条消息
    if "--test" in sys.argv:
        test_message = {
            "message_id": 99999,
            "date": "2026-05-13T15:00:00+08:00",
            "chat": {"id": -100123456789, "type": "group", "title": "Test Group"},
            "from": {"id": 123456, "is_bot": False, "first_name": "Test", "username": "test_user"},
            "text": "这是一条测试消息，用于验证 capture_telegram.py 的功能"
        }
        test_path = Path("/tmp/test_telegram_message.json")
        test_path.write_text(json.dumps(test_message, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({
            "success": True,
            "message": "测试消息已写入 /tmp/test_telegram_message.json",
            "hint": "运行: python scripts/capture_telegram.py /tmp/test_telegram_message.json"
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    if len(sys.argv) < 2:
        result = {
            "success": False,
            "error": "用法: python capture_telegram.py <message.json>",
            "exit_code": 2
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    json_path = Path(sys.argv[1])

    if not json_path.exists():
        result = {
            "success": False,
            "error": f"文件不存在: {json_path}",
            "exit_code": 2
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    try:
        data = parse_telegram_message(json_path)
        fields = extract_fields(data)
    except ValueError as e:
        result = {
            "success": False,
            "error": str(e),
            "exit_code": 2
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    # 输出目录：00_Inbox/telegram/
    output_dir = Path("00_Inbox/telegram")

    try:
        filepath = generate_markdown(fields, output_dir)
    except Exception as e:
        result = {
            "success": False,
            "error": f"生成笔记失败: {str(e)}",
            "exit_code": 2
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    result = {
        "success": True,
        "file": str(filepath),
        "message_id": fields["message_id"],
        "chat_id": fields["chat_id"],
        "processed_at": datetime.now().isoformat()
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()