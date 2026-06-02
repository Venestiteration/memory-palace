#!/usr/bin/env python3
"""
run_sync.py - 同步任务

执行：readwise sync + telegram once

用法:
  python run_sync.py              # 执行全流程
  python run_sync.py --dry-run    # 预览模式（不写文件）
"""

import argparse
import os
import subprocess
import sys
import logging
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
LOG_DIR = PROJECT_DIR / "logs"


def load_env():
    """加载 .env 环境变量"""
    env_file = PROJECT_DIR / ".env"
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value


def setup_logging(name: str, log_file: Path) -> logging.Logger:
    """配置日志"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def run_command(cmd: list, logger: logging.Logger, cwd: Path = None) -> tuple:
    """执行命令并记录日志"""
    cmd_str = " ".join(cmd)
    logger.info(f"执行命令: {cmd_str}")

    result = subprocess.run(cmd, cwd=cwd or PROJECT_DIR, capture_output=True, text=True)

    if result.returncode == 0:
        logger.info(f"成功: {cmd_str}")
        if result.stdout:
            logger.debug(f"输出: {result.stdout[:500]}")
    else:
        logger.error(f"失败: {cmd_str}")
        logger.error(f"退出码: {result.returncode}")
        if result.stdout:
            logger.error(f"stdout: {result.stdout[:500]}")
        if result.stderr:
            logger.error(f"stderr: {result.stderr[:500]}")

    return result.returncode, result.stdout, result.stderr


def run_sync(dry_run: bool = False, logger: logging.Logger = None) -> int:
    """执行同步任务"""
    load_env()

    from runtime_status import JobStatus, update_job_status, get_diagnostic_info

    if logger is None:
        log_file = LOG_DIR / f"run_sync_{datetime.now().strftime('%Y%m%d')}.log"
        logger = setup_logging("run_sync", log_file)

    logger.info("=" * 50)
    logger.info("开始同步任务")
    logger.info("=" * 50)

    start_time = time.time()
    update_job_status("sync", JobStatus.RUNNING)

    steps = []
    has_failure = False
    failure_exit_code = 0

    try:
        if dry_run:
            logger.info("[DRY-RUN 模式] 不会实际写入文件")

        # Step 1: sync_readwise.py
        step_name = "sync_readwise"
        logger.info(f"步骤 1/2: 同步 Readwise 高亮")
        update_job_status("sync", JobStatus.RUNNING, steps=steps)
        cmd = [sys.executable, str(SCRIPT_DIR / "sync_readwise.py")]
        if dry_run:
            cmd.append("--dry-run")
        ret, stdout, stderr = run_command(cmd, logger)
        if ret != 0:
            steps.append({"name": step_name, "status": "failure", "error": (stderr or stdout or "Readwise 同步失败")[:200]})
            logger.warning(f"Readwise 同步失败 (exit code: {ret})，继续执行下一步")
            has_failure = True
            failure_exit_code = ret
        else:
            steps.append({"name": step_name, "status": "success"})

        # Step 2: telegram_bot_service.py --once
        step_name = "telegram_capture"
        logger.info(f"步骤 2/2: 捕获 Telegram 消息")
        update_job_status("sync", JobStatus.RUNNING, steps=steps)
        cmd = [sys.executable, str(SCRIPT_DIR / "telegram_bot_service.py"), "--once"]
        if dry_run:
            cmd.append("--dry-run")
        ret, stdout, stderr = run_command(cmd, logger)
        if ret != 0:
            steps.append({"name": step_name, "status": "failure", "error": (stderr or stdout or "Telegram 捕获失败")[:200]})
            logger.warning(f"Telegram 捕获失败 (exit code: {ret})")
            has_failure = True
            failure_exit_code = ret
        else:
            steps.append({"name": step_name, "status": "success"})

        duration = time.time() - start_time
        if has_failure:
            # sync 任务允许部分失败，只要关键步骤完成了
            update_job_status(
                "sync",
                JobStatus.FAILURE,
                error_message="部分步骤失败",
                exit_code=failure_exit_code,
                duration_seconds=duration,
                steps=steps,
            )
            logger.warning("同步任务完成，但有步骤失败")
        else:
            update_job_status("sync", JobStatus.SUCCESS, duration_seconds=duration, steps=steps)
            logger.info("同步任务完成")

    except Exception as e:
        duration = time.time() - start_time
        error_str = str(e)
        diagnostic = get_diagnostic_info("sync", error_str, failure_exit_code)
        logger.error(f"诊断建议: {diagnostic}")
        update_job_status(
            "sync",
            JobStatus.FAILURE,
            error_message=error_str[:500],
            exit_code=failure_exit_code,
            duration_seconds=duration,
            steps=steps,
        )
        return failure_exit_code if failure_exit_code else 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="同步任务（Readwise + Telegram）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    args = parser.parse_args()

    log_file = LOG_DIR / f"run_sync_{datetime.now().strftime('%Y%m%d')}.log"
    logger = setup_logging("run_sync", log_file)

    ret = run_sync(dry_run=args.dry_run, logger=logger)
    sys.exit(ret)


if __name__ == "__main__":
    main()