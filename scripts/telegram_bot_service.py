#!/usr/bin/env python3
"""
telegram_bot_service.py - Telegram Bot 轮询服务

从 Telegram Bot API 轮询消息，转换为 capture_telegram.py 格式并写入 Inbox。

用法:
  python telegram_bot_service.py              # 持续轮询（默认 5 秒间隔）
  python telegram_bot_service.py --once        # 执行一次后退出
  python telegram_bot_service.py --interval 10 # 10 秒间隔

环境变量:
  TELEGRAM_BOT_TOKEN - Telegram Bot Token（必填）

日志:
  logs/telegram_bot.log
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import get_settings

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TOKEN_FILE = PROJECT_DIR / ".memory_palace" / "telegram_last_update_id"
LOG_FILE = PROJECT_DIR / "logs" / "telegram_bot.log"
INBOX_DIR = PROJECT_DIR / "00_Inbox" / "telegram"
STATE_DIR = PROJECT_DIR / ".memory_palace"

# Telegram API
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# 从 capture_telegram.py 导入的函数
SAMPLE_TELEGRAM_MESSAGE = {
    "message_id": 99999,
    "date": "2026-05-13T15:00:00+08:00",
    "chat": {"id": -100123456789, "type": "group", "title": "Test Group"},
    "from": {"id": 123456, "is_bot": False, "first_name": "Test", "username": "test_user"},
    "text": "这是一条测试消息"
}


def setup_logging() -> logging.Logger:
    """配置日志"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("telegram_bot")
    logger.setLevel(logging.INFO)

    # 文件 handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 格式
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_bot_token() -> str:
    """从环境变量获取 Bot Token"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "环境变量 TELEGRAM_BOT_TOKEN 未设置\n"
            "请设置: export TELEGRAM_BOT_TOKEN='your_bot_token'"
        )
    return token


def load_last_update_id() -> int:
    """加载上次处理的 update_id"""
    if not TOKEN_FILE.exists():
        return 0
    try:
        return int(TOKEN_FILE.read_text().strip())
    except (ValueError, IOError):
        return 0


def save_last_update_id(update_id: int) -> None:
    """保存最后处理的 update_id"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(str(update_id))


def call_telegram_api(token: str, method: str, **params) -> dict:
    """调用 Telegram API"""
    url = TELEGRAM_API.format(token=token, method=method)
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_updates(token: str, offset: int = 0, limit: int = 100) -> list[dict]:
    """获取 Telegram updates"""
    result = call_telegram_api(token, "getUpdates", offset=offset, limit=limit, timeout=30)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result.get('description', 'Unknown error')}")
    return result.get("result", [])


def format_date(date_val) -> str:
    """将 Telegram date 转换为 YYYY-MM-DD（支持 Unix 时间戳）"""
    if isinstance(date_val, int):
        dt = datetime.fromtimestamp(date_val)
        return dt.strftime("%Y-%m-%d")

    if not isinstance(date_val, str):
        date_val = str(date_val)

    try:
        dt = datetime.fromisoformat(date_val.replace("+", "+").rstrip("Z"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    try:
        dt = datetime.strptime(date_val, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    return date_val[:10] if len(date_val) >= 10 else date_val


def format_datetime(date_val) -> str:
    """
    将 Telegram date 转换为 YYYYMMDD-HHMMSS
    支持：ISO 字符串、Unix 时间戳（int）
    """
    # 处理 Unix 时间戳
    if isinstance(date_val, int):
        dt = datetime.fromtimestamp(date_val)
        return dt.strftime("%Y%m%d-%H%M%S")

    if not isinstance(date_val, str):
        date_val = str(date_val)

    try:
        dt = datetime.fromisoformat(date_val.replace("+", "+").rstrip("Z"))
        return dt.strftime("%Y%m%d-%H%M%S")
    except ValueError:
        pass
    try:
        dt = datetime.strptime(date_val, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y%m%d-%H%M%S")
    except ValueError:
        pass
    return re.sub(r"\D", "", date_val[:19])[:15]


def escape_yaml_value(text: str) -> str:
    """对 YAML 值进行转义，处理特殊字符"""
    if not text:
        return '""'
    needs_quoting = any(c in text for c in ':{}[]|>&*!%@`"\'\n') or text.startswith(' ') or text.endswith(' ')
    if needs_quoting:
        return json.dumps(text, ensure_ascii=False)[1:-1]
    return text


def write_message_to_inbox(message: dict, logger: logging.Logger) -> Optional[Path]:
    """
    将 Telegram message 写入 Inbox。

    复用 capture_telegram.py 的逻辑。
    """
    # 提取字段
    message_id = message.get("message_id")
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text")
    date = message.get("date")

    if not all([message_id, chat_id, text, date]):
        logger.warning(f"消息缺少必填字段，跳过: {message.get('message_id', 'unknown')}")
        return None

    from_data = message.get("from", {})
    from_user = from_data.get("username") or from_data.get("first_name", "unknown")

    fields = {
        "message_id": str(message_id),
        "chat_id": str(chat_id),
        "text": text,
        "date": date,
        "date_formatted": format_datetime(date),
        "date_readable": format_date(date),
        "from": from_user
    }

    # 生成 filename
    filename = f"{fields['date_formatted']}-telegram-{fields['message_id']}.md"
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    filepath = INBOX_DIR / filename

    # 如果文件已存在（message_id 重复），跳过
    if filepath.exists():
        logger.debug(f"文件已存在，跳过: {filepath.name}")
        return filepath

    # 生成 Markdown
    raw_text = fields["text"]
    safe_title = raw_text[:50] + ("..." if len(raw_text) > 50 else "")

    content_lines = [
        "---",
        f'id: telegram-{fields["message_id"]}',
        f"created: {fields['date_readable']}",
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
        f"- Date: {fields['date_formatted']}",
        f"- From: {fields['from']}",
        "",
        "## Processing Notes",
        "-",
    ]

    # 原子写入：先写 temp，再 rename
    temp_path = INBOX_DIR / f".tmp-{uuid.uuid4().hex[:8]}-{filename}"
    temp_path.write_text("\n".join(content_lines), encoding="utf-8")

    # 验证 frontmatter
    valid, err = validate_note(temp_path)
    if not valid:
        temp_path.unlink()
        logger.error(f"验证失败，删除临时文件: {temp_path.name}, error: {err}")
        return None

    # rename 为正式文件
    temp_path.rename(filepath)
    logger.info(f"写入笔记: {filepath.relative_to(PROJECT_DIR)}")

    return filepath


def validate_note(file_path: Path) -> tuple[bool, str]:
    """调用 validate_note.py 验证生成的笔记"""
    validate_script = SCRIPT_DIR / "validate_note.py"
    try:
        import subprocess
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


def process_updates(token: str, logger: logging.Logger, dry_run: bool = False) -> int:
    """
    处理一次轮询。

    Returns:
        处理的 message 数量
    """
    last_update_id = load_last_update_id()
    offset = last_update_id + 1  # 从 last_update_id + 1 开始，获取新消息

    try:
        updates = fetch_updates(token, offset=offset)
    except Exception as e:
        logger.error(f"获取 updates 失败: {e}")
        return 0

    if not updates:
        return 0

    processed = 0
    for update in updates:
        update_id = update.get("update_id", 0)
        message = update.get("message", {})

        if not message or not message.get("text"):
            # 更新 last_update_id 但不处理
            if update_id > last_update_id:
                last_update_id = update_id
            continue

        if not dry_run:
            filepath = write_message_to_inbox(message, logger)
            if filepath:
                processed += 1

        # 更新 last_update_id
        if update_id > last_update_id:
            last_update_id = update_id

    # 保存 last_update_id
    if last_update_id > 0:
        save_last_update_id(last_update_id)

    return processed


def main():
    parser = argparse.ArgumentParser(
        description="Telegram Bot 轮询服务 - 从 Telegram 获取消息并写入 Inbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python telegram_bot_service.py              # 持续轮询（5秒间隔）
  python telegram_bot_service.py --once       # 执行一次后退出
  python telegram_bot_service.py --interval 10 # 10秒间隔

日志文件: logs/telegram_bot.log
        """
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="执行一次后退出"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="轮询间隔秒数（默认: 5）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="不写入文件，只打印会处理的消息"
    )

    args = parser.parse_args()

    # 检查 token
    try:
        token = get_bot_token()
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)

    # 隐藏 token（不打印）
    token_preview = token[:10] + "..." if len(token) > 10 else "***"
    print(f"Bot Token: {token_preview}")

    # 设置日志
    logger = setup_logging()
    logger.info(f"Telegram Bot 服务启动 (interval={args.interval}s, once={args.once})")

    try:
        if args.once:
            # 单次执行
            processed = process_updates(token, logger, dry_run=args.dry_run)
            logger.info(f"处理完成: {processed} 条消息")
            print(f"处理完成: {processed} 条消息")
        else:
            # 持续轮询
            logger.info("进入持续轮询模式，按 Ctrl+C 停止")
            print("进入持续轮询模式，按 Ctrl+C 停止")
            while True:
                processed = process_updates(token, logger, dry_run=args.dry_run)
                if processed > 0:
                    logger.info(f"处理了 {processed} 条消息")
                time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("服务停止")
        print("\n服务停止")
        sys.exit(0)
    except Exception as e:
        logger.error(f"服务异常: {e}")
        print(f"服务异常: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()