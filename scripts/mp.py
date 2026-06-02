#!/usr/bin/env python3
"""
mp.py - Memory Palace 统一 CLI

用法:
  python mp.py <command> [options]

子命令:
  validate    验证笔记 frontmatter
  capture     捕获 Telegram 消息
  sync        同步 Readwise 高亮
  inbox       扫描 Inbox
  atomize     LLM 原子化笔记
  index       构建 SQLite 元数据索引
  vector      构建向量索引
  search      语义搜索
  brief       生成简报
  ask         Ask Vault 问答
  bot         Telegram Bot 轮询服务
  scheduler   调度任务（daily/weekly/sync）
  launchd     安装 launchd 定时任务

示例:
  python mp.py validate _templates/atomic_note.md
  python mp.py inbox --json
  python mp.py search "SPY" --limit 3
  python mp.py brief daily --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent


def run_script(script_name: str, args: list[str], pass_through: bool = False) -> int:
    """
    运行脚本并返回退出码。

    Args:
        script_name: 脚本文件名（如 validate_note.py）
        args: 传递给脚本的参数列表
        pass_through: 是否透传参数（True = 脚本自行处理输出；False = 捕获输出）

    Returns:
        脚本退出码
    """
    script_path = SCRIPT_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args

    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    return result.returncode


def cmd_validate(args: argparse.Namespace) -> int:
    """validate 子命令"""
    script_args = args.files if hasattr(args, 'files') else []
    if args.recursive:
        script_args = ["--recursive"] + script_args
    return run_script("validate_note.py", script_args)


def cmd_capture(args: argparse.Namespace) -> int:
    """capture 子命令"""
    sub_commands = {
        "text": ("capture_text.py", []),
        "web": ("capture_web_clip.py", []),
        "voice": ("capture_voice.py", []),
        "telegram": ("capture_telegram.py", []),
    }

    if args.subcommand not in sub_commands:
        print(f"Error: capture 子命令必须是: {', '.join(sub_commands.keys())}", file=sys.stderr)
        return 1

    script_name, script_args = sub_commands[args.subcommand]

    # 通用参数
    if getattr(args, 'dry_run', False):
        script_args.append("--dry-run")

    # Telegram 特有参数
    if args.subcommand == "telegram":
        if getattr(args, 'test', False):
            script_args.append("--test")
        if getattr(args, 'input', None):
            script_args.append(args.input)

    # 文本/语音 特有参数
    if args.subcommand in ("text", "voice") and getattr(args, 'content', None):
        script_args.append(args.content)
        if getattr(args, 'title', None):
            script_args.append(args.title)

    # Web clip 特有参数
    if args.subcommand == "web" and getattr(args, 'url', None):
        script_args.extend([args.url, args.title or "Web Clip", args.content or ""])

    return run_script(script_name, script_args)


def cmd_sync(args: argparse.Namespace) -> int:
    """sync 子命令"""
    script_args = []
    if args.since:
        script_args.extend(["--since", args.since])
    if args.dry_run:
        script_args.append("--dry-run")
    return run_script("sync_readwise.py", script_args)


def cmd_inbox(args: argparse.Namespace) -> int:
    """inbox 子命令"""
    script_args = []
    if args.json:
        script_args.append("--json")
    if args.limit:
        script_args.extend(["--limit", str(args.limit)])
    if args.move_archive:
        script_args.append("--move-archive")
    return run_script("process_inbox.py", script_args)


def cmd_atomize(args: argparse.Namespace) -> int:
    """atomize 子命令"""
    script_args = []
    if args.write:
        script_args.append("--write")
    if args.file:
        script_args.append(args.file)
    return run_script("atomize_note.py", script_args)


def cmd_index(args: argparse.Namespace) -> int:
    """index 子命令"""
    script_args = []
    if args.rebuild:
        script_args.append("--rebuild")
    if args.db:
        script_args.extend(["--db", args.db])
    return run_script("build_index.py", script_args)


def cmd_vector(args: argparse.Namespace) -> int:
    """vector 子命令"""
    script_args = []
    if args.rebuild:
        script_args.append("--rebuild")
    if args.db:
        script_args.extend(["--db", args.db])
    return run_script("build_vector_index.py", script_args)


def cmd_search(args: argparse.Namespace) -> int:
    """search 子命令"""
    script_args = [args.query] if args.query else []
    if args.limit:
        script_args.extend(["--limit", str(args.limit)])
    if args.type:
        script_args.extend(["--type", args.type])
    if args.project:
        script_args.extend(["--project", args.project])
    if args.json:
        script_args.append("--json")
    return run_script("search_notes.py", script_args)


def cmd_brief(args: argparse.Namespace) -> int:
    """brief 子命令"""
    script_args = []
    if args.type == "daily":
        script_args = []
        if args.date:
            script_args.extend(["--date", args.date])
        if args.dry_run:
            script_args.append("--dry-run")
        if args.db:
            script_args.extend(["--db", args.db])
        return run_script("generate_daily_brief.py", script_args)
    elif args.type == "weekly":
        script_args = []
        if args.week:
            script_args.extend(["--week", args.week])
        if args.dry_run:
            script_args.append("--dry-run")
        if args.db:
            script_args.extend(["--db", args.db])
        return run_script("generate_weekly_synthesis.py", script_args)
    else:
        print("Error: brief must be 'daily' or 'weekly'", file=sys.stderr)
        return 1


def cmd_ask(args: argparse.Namespace) -> int:
    """ask 子命令"""
    script_args = [args.question] if args.question else []
    if args.limit:
        script_args.extend(["--limit", str(args.limit)])
    if args.save:
        script_args.extend(["--save", args.save])
    if args.json:
        script_args.append("--json")
    return run_script("ask_vault.py", script_args)


def cmd_bot(args: argparse.Namespace) -> int:
    """bot 子命令"""
    script_args = []
    if args.once:
        script_args.append("--once")
    if args.interval:
        script_args.extend(["--interval", str(args.interval)])
    if args.dry_run:
        script_args.append("--dry-run")
    return run_script("telegram_bot_service.py", script_args)


def cmd_scheduler(args: argparse.Namespace) -> int:
    """scheduler 子命令"""
    script_map = {
        "daily": "run_daily.py",
        "weekly": "run_weekly.py",
        "sync": "run_sync.py"
    }
    script_name = script_map.get(args.type)
    if not script_name:
        print(f"Error: type must be daily, weekly, or sync", file=sys.stderr)
        return 1

    script_args = []
    if args.dry_run:
        script_args.append("--dry-run")
    return run_script(script_name, script_args)


def cmd_launchd(args: argparse.Namespace) -> int:
    """launchd 子命令"""
    script_args = []
    if args.install:
        script_args.append("--install")
        if args.install != "all":
            script_args.append(args.install)
    elif args.uninstall:
        script_args.append("--uninstall")
        if args.uninstall != "all":
            script_args.append(args.uninstall)
    elif args.list:
        script_args.append("--list")

    if args.dry_run:
        script_args.append("--dry-run")

    return run_script("install_launchd.py", script_args)


def main():
    parser = argparse.ArgumentParser(
        description="Memory Palace - 本地个人知识操作系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python mp.py validate _templates/atomic_note.md
  python mp.py inbox --json
  python mp.py search "SPY" --limit 3
  python mp.py brief daily --dry-run
  python mp.py brief weekly --dry-run
  python mp.py ask "SPY相关笔记有哪些？"
  python mp.py ask "期权策略" --limit 5 --save decisions
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # === validate ===
    p_validate = subparsers.add_parser("validate", help="验证笔记 frontmatter")
    p_validate.add_argument("files", nargs="*", help="要验证的文件")
    p_validate.add_argument("-r", "--recursive", action="store_true", help="递归验证")
    p_validate.set_defaults(func=cmd_validate)

    # === capture ===
    p_capture = subparsers.add_parser("capture", help="捕获内容")
    capture_sub = p_capture.add_subparsers(dest="subcommand", help="捕获类型")

    p_capture_text = capture_sub.add_parser("text", help="快速文本捕获")
    p_capture_text.add_argument("content", nargs="?", help="文本内容")
    p_capture_text.add_argument("title", nargs="?", help="标题")
    p_capture_text.add_argument("--dry-run", action="store_true", help="预览模式")
    p_capture_text.set_defaults(func=cmd_capture)

    p_capture_web = capture_sub.add_parser("web", help="网页剪藏")
    p_capture_web.add_argument("url", nargs="?", help="网页 URL")
    p_capture_web.add_argument("title", nargs="?", help="标题")
    p_capture_web.add_argument("content", nargs="?", help="内容")
    p_capture_web.add_argument("--dry-run", action="store_true", help="预览模式")
    p_capture_web.set_defaults(func=cmd_capture)

    p_capture_voice = capture_sub.add_parser("voice", help="语音转录捕获")
    p_capture_voice.add_argument("content", nargs="?", help="转录文本")
    p_capture_voice.add_argument("title", nargs="?", help="标题")
    p_capture_voice.add_argument("--dry-run", action="store_true", help="预览模式")
    p_capture_voice.set_defaults(func=cmd_capture)

    p_capture_tg = capture_sub.add_parser("telegram", help="Telegram 消息捕获")
    p_capture_tg.add_argument("input", nargs="?", help="Telegram message JSON 文件")
    p_capture_tg.add_argument("--test", action="store_true", help="测试模式")
    p_capture_tg.set_defaults(func=cmd_capture)

    p_capture.set_defaults(func=cmd_capture)

    # === sync ===
    p_sync = subparsers.add_parser("sync", help="同步 Readwise 高亮")
    p_sync.add_argument("--since", help="只同步指定日期后的（YYYY-MM-DD）")
    p_sync.add_argument("--dry-run", action="store_true", help="不写文件，只预览")
    p_sync.set_defaults(func=cmd_sync)

    # === inbox ===
    p_inbox = subparsers.add_parser("inbox", help="扫描 Inbox")
    p_inbox.add_argument("--json", action="store_true", help="JSON 格式输出")
    p_inbox.add_argument("--limit", type=int, help="限制结果数")
    p_inbox.add_argument("--move-archive", action="store_true", help="移动到 Archive")
    p_inbox.set_defaults(func=cmd_inbox)

    # === atomize ===
    p_atomize = subparsers.add_parser("atomize", help="LLM 原子化笔记")
    p_atomize.add_argument("file", nargs="?", help="要原子化的文件")
    p_atomize.add_argument("--write", action="store_true", help="写入原子笔记")
    p_atomize.set_defaults(func=cmd_atomize)

    # === index ===
    p_index = subparsers.add_parser("index", help="构建 SQLite 元数据索引")
    p_index.add_argument("--rebuild", action="store_true", help="全量重建")
    p_index.add_argument("--db", help="数据库路径")
    p_index.set_defaults(func=cmd_index)

    # === vector ===
    p_vector = subparsers.add_parser("vector", help="构建向量索引")
    p_vector.add_argument("--rebuild", action="store_true", help="全量重建")
    p_vector.add_argument("--db", help="数据库路径")
    p_vector.set_defaults(func=cmd_vector)

    # === search ===
    p_search = subparsers.add_parser("search", help="语义搜索")
    p_search.add_argument("query", nargs="?", help="搜索查询")
    p_search.add_argument("--limit", type=int, help="限制结果数")
    p_search.add_argument("--type", help="按笔记类型过滤")
    p_search.add_argument("--project", help="按项目过滤")
    p_search.add_argument("--json", action="store_true", help="JSON 输出")
    p_search.set_defaults(func=cmd_search)

    # === brief ===
    p_brief = subparsers.add_parser("brief", help="生成简报")
    p_brief.add_argument("type", choices=["daily", "weekly"], help="简报类型")
    p_brief.add_argument("--date", help="指定日期（YYYY-MM-DD）")
    p_brief.add_argument("--week", help="指定周（YYYY-Www）")
    p_brief.add_argument("--dry-run", action="store_true", help="不写文件，只预览")
    p_brief.add_argument("--db", help="数据库路径")
    p_brief.set_defaults(func=cmd_brief)

    # === ask ===
    p_ask = subparsers.add_parser("ask", help="Ask Vault 问答")
    p_ask.add_argument("question", nargs="?", help="要询问的问题")
    p_ask.add_argument("--limit", type=int, help="搜索的笔记数量")
    p_ask.add_argument("--save", choices=["decisions", "reports", "essays"], help="保存到 Output 目录")
    p_ask.add_argument("--json", action="store_true", help="JSON 输出")
    p_ask.set_defaults(func=cmd_ask)

    # === bot ===
    p_bot = subparsers.add_parser("bot", help="Telegram Bot 轮询服务")
    p_bot.add_argument("--once", action="store_true", help="执行一次后退出")
    p_bot.add_argument("--interval", type=int, help="轮询间隔秒数")
    p_bot.add_argument("--dry-run", action="store_true", help="不写入文件，只打印")
    p_bot.set_defaults(func=cmd_bot)

    # === scheduler ===
    p_scheduler = subparsers.add_parser("scheduler", help="调度任务")
    p_scheduler.add_argument("type", choices=["daily", "weekly", "sync"], help="任务类型")
    p_scheduler.add_argument("--dry-run", action="store_true", help="预览模式")
    p_scheduler.set_defaults(func=cmd_scheduler)

    # === launchd ===
    p_launchd = subparsers.add_parser("launchd", help="安装 launchd 定时任务")
    p_launchd.add_argument("--install", nargs="?", const="all", help="安装任务")
    p_launchd.add_argument("--uninstall", nargs="?", const="all", help="卸载任务")
    p_launchd.add_argument("--list", action="store_true", help="列出任务状态")
    p_launchd.add_argument("--dry-run", action="store_true", help="预览模式")
    p_launchd.set_defaults(func=cmd_launchd)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())