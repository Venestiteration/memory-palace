#!/usr/bin/env python3
"""
install_launchd.py - 安装 launchd 定时任务

生成并安装 macOS launchd plist 文件。

用法:
  python install_launchd.py --dry-run           # 预览将安装的任务
  python install_launchd.py --install           # 安装所有任务
  python install_launchd.py --install daily     # 只安装每日任务
  python install_launchd.py --uninstall         # 卸载所有任务
  python install_launchd.py --uninstall daily   # 只卸载每日任务

安装位置: ~/Library/LaunchAgents/
"""

import argparse
import os
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"

# API key 不写入 plist，从 .env 读取
PLIST_BUNDLE_ID_PREFIX = "com.memorypalace"
PLIST_LABEL_PREFIX = "com.memorypalace"


def get_project_env():
    """获取项目环境变量（不写入 plist）"""
    env = {}
    env_file = PROJECT_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def generate_plist(name: str, script_path: Path, schedule: dict) -> dict:
    """生成 launchd plist 配置"""
    label = f"{PLIST_LABEL_PREFIX}.{name}"

    # ProgramArguments 不包含 shell，API key 通过 EnvironmentVariables 设置
    # 但 launchd 不会继承 .env，所以需要确保 .env 被加载
    plist = {
        "Label": label,
        "ProgramArguments": [sys.executable, str(script_path)],
        "RunAtLoad": schedule.get("RunAtLoad", False) if schedule else True,
        "KeepAlive": {"SuccessfulExit": False} if schedule is None else None,
        "StandardOutPath": str(PROJECT_DIR / "logs" / f"{name}.log"),
        "StandardErrorPath": str(PROJECT_DIR / "logs" / f"{name}.err.log"),
    }

    # 添加定时调度（定时任务）
    if schedule and schedule.get("StartCalendarInterval"):
        plist["StartCalendarInterval"] = schedule["StartCalendarInterval"]

    # 清理 None 值
    plist = {k: v for k, v in plist.items() if v is not None}

    return plist


DAILY_SCHEDULE = {
    "RunAtLoad": True,
    "StartCalendarInterval": {"Hour": 8, "Minute": 0}  # 每天早上 8:00
}

WEEKLY_SCHEDULE = {
    "RunAtLoad": True,
    "StartCalendarInterval": {
        "Weekday": 1,  # 周一
        "Hour": 8,
        "Minute": 30
    }
}

SYNC_SCHEDULE = {
    "RunAtLoad": True,
    "StartCalendarInterval": [
        {"Hour": 7, "Minute": 0},   # 早上 7:00
        {"Hour": 19, "Minute": 0},  # 晚上 7:00
    ]
}


TASKS = {
    "daily": {
        "script": SCRIPT_DIR / "run_daily.py",
        "schedule": DAILY_SCHEDULE,
        "description": "每日例行：index → vector → daily brief（每天 8:00）"
    },
    "weekly": {
        "script": SCRIPT_DIR / "run_weekly.py",
        "schedule": WEEKLY_SCHEDULE,
        "description": "每周例行：index → vector → weekly synthesis（周一 8:30）"
    },
    "sync": {
        "script": SCRIPT_DIR / "run_sync.py",
        "schedule": SYNC_SCHEDULE,
        "description": "同步任务：Readwise + Telegram（每天 7:00, 19:00）"
    },
    "telegram": {
        "script": SCRIPT_DIR / "telegram_bot_service.py",
        "schedule": None,
        "description": "Telegram Bot 实时轮询服务（持续运行，收到消息立即写入 Inbox）"
    }
}


def get_plist_path(name: str) -> Path:
    """获取 plist 文件路径"""
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    return LAUNCH_AGENTS_DIR / f"{PLIST_BUNDLE_ID_PREFIX}.{name}.plist"


def load_plist(name: str) -> dict:
    """加载已安装的 plist"""
    plist_path = get_plist_path(name)
    if not plist_path.exists():
        return {}
    with open(plist_path, "rb") as f:
        return plistlib.load(f)


def install_task(name: str, dry_run: bool = False) -> bool:
    """安装单个任务"""
    if name not in TASKS:
        print(f"错误: 未知任务 '{name}'")
        return False

    task = TASKS[name]
    script_path = task["script"]

    if not script_path.exists():
        print(f"错误: 脚本不存在 {script_path}")
        return False

    plist = generate_plist(name, script_path, task["schedule"])
    plist_path = get_plist_path(name)

    if dry_run:
        print(f"[DRY-RUN] 将安装: {plist_path}")
        print(f"  Label: {plist['Label']}")
        print(f"  ProgramArguments: {plist['ProgramArguments']}")
        if "StartCalendarInterval" in plist:
            print(f"  StartCalendarInterval: {plist['StartCalendarInterval']}")
        print(f"  StandardOutPath: {plist.get('StandardOutPath', 'N/A')}")
        return True

    # 写入 plist
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)

    print(f"已安装: {plist_path}")

    # 加载任务
    try:
        subprocess.run(["launchctl", "load", str(plist_path)], check=True)
        print(f"已加载: {name}")
    except subprocess.CalledProcessError as e:
        print(f"加载失败: {e}")

    return True


def uninstall_task(name: str, dry_run: bool = False) -> bool:
    """卸载单个任务"""
    plist_path = get_plist_path(name)

    if not plist_path.exists():
        print(f"任务未安装: {name}")
        return True

    if dry_run:
        print(f"[DRY-RUN] 将卸载: {plist_path}")
        return True

    # 卸载前先停止
    label = f"{PLIST_LABEL_PREFIX}.{name}"
    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)

    # 删除 plist
    plist_path.unlink()
    print(f"已卸载: {plist_path}")

    return True


def list_tasks():
    """列出所有任务状态"""
    print(f"安装目录: {LAUNCH_AGENTS_DIR}")
    print()

    for name, task in TASKS.items():
        plist_path = get_plist_path(name)
        installed = plist_path.exists()

        # 检查脚本是否存在
        script_exists = task["script"].exists()

        status = "已安装" if installed else "未安装"
        script_status = "✓" if script_exists else "✗"

        print(f"{name.upper()}")
        print(f"  状态: {status}")
        print(f"  脚本: {task['script']} {script_status}")
        print(f"  描述: {task['description']}")

        if installed:
            try:
                plist_data = load_plist(name)
                print(f"  Label: {plist_data.get('Label', 'N/A')}")
                if "StartCalendarInterval" in plist_data:
                    print(f"  Schedule: {plist_data['StartCalendarInterval']}")
            except Exception:
                pass

        print()


def main():
    parser = argparse.ArgumentParser(
        description="安装/卸载 launchd 定时任务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python install_launchd.py --dry-run          # 预览所有任务
  python install_launchd.py --install          # 安装所有任务
  python install_launchd.py --install daily    # 只安装每日任务
  python install_launchd.py --uninstall        # 卸载所有任务

定时任务:
  - daily:  每天 08:00 执行 index → vector → daily brief
  - weekly: 每周一 08:30 执行 index → vector → weekly synthesis
  - sync:   每天 07:00, 19:00 执行 Readwise + Telegram 同步
        """
    )
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际操作")
    parser.add_argument("--install", nargs="?", const="all", help="安装任务（默认全部）")
    parser.add_argument("--uninstall", nargs="?", const="all", help="卸载任务（默认全部）")
    parser.add_argument("--list", action="store_true", help="列出所有任务状态")

    args = parser.parse_args()

    # 创建日志目录
    (PROJECT_DIR / "logs").mkdir(parents=True, exist_ok=True)

    # 如果指定了 --env 参数，确保环境变量加载
    if args.install or args.uninstall:
        env = get_project_env()
        print(f"注意: API key 不会写入 plist，请确保 .env 文件已配置")

    # 列出任务
    if args.list:
        list_tasks()
        return 0

    # 安装任务
    if args.install:
        targets = TASKS.keys() if args.install == "all" else [args.install]

        for name in targets:
            if name not in TASKS:
                print(f"错误: 未知任务 '{name}'，可用: {', '.join(TASKS.keys())}")
                return 1
            if not install_task(name, dry_run=args.dry_run):
                return 1
        return 0

    # 卸载任务
    if args.uninstall:
        targets = TASKS.keys() if args.uninstall == "all" else [args.uninstall]

        for name in targets:
            if not uninstall_task(name, dry_run=args.dry_run):
                return 1
        return 0

    # 默认显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())