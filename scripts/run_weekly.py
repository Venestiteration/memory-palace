#!/usr/bin/env python3
"""
run_weekly.py - 每周例行任务

执行：index → vector → weekly synthesis

用法:
  python run_weekly.py              # 执行全流程
  python run_weekly.py --dry-run    # 预览模式（不写文件）
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


def run_weekly(dry_run: bool = False, logger: logging.Logger = None) -> int:
    """执行每周例行任务"""
    load_env()

    from runtime_status import JobStatus, update_job_status, get_diagnostic_info

    if logger is None:
        log_file = LOG_DIR / f"run_weekly_{datetime.now().strftime('%Y%m%d')}.log"
        logger = setup_logging("run_weekly", log_file)

    logger.info("=" * 50)
    logger.info("开始每周例行任务")
    logger.info("=" * 50)

    start_time = time.time()
    update_job_status("weekly", JobStatus.RUNNING)

    steps = []
    overall_error = None
    overall_exit_code = 0

    try:
        if dry_run:
            logger.info("[DRY-RUN 模式] 不会实际写入文件")

        # Step 1: build_index.py
        step_name = "build_index"
        logger.info(f"步骤 1/3: 构建 SQLite 元数据索引")
        update_job_status("weekly", JobStatus.RUNNING, steps=steps)
        ret, stdout, stderr = run_command([sys.executable, str(SCRIPT_DIR / "build_index.py")], logger)
        if ret != 0:
            error_msg = stderr or stdout or "build_index 失败"
            steps.append({"name": step_name, "status": "failure", "error": error_msg[:200]})
            logger.error(f"步骤 1 失败，终止执行 (exit code: {ret})")
            overall_error = error_msg
            overall_exit_code = ret
            raise Exception(f"步骤 1 失败: {error_msg[:100]}")
        steps.append({"name": step_name, "status": "success"})

        # Step 2: build_vector_index.py
        step_name = "build_vector_index"
        logger.info(f"步骤 2/3: 构建向量索引")
        update_job_status("weekly", JobStatus.RUNNING, steps=steps)
        ret, stdout, stderr = run_command([sys.executable, str(SCRIPT_DIR / "build_vector_index.py")], logger)
        if ret != 0:
            error_msg = stderr or stdout or "build_vector_index 失败"
            steps.append({"name": step_name, "status": "failure", "error": error_msg[:200]})
            logger.error(f"步骤 2 失败，终止执行 (exit code: {ret})")
            overall_error = error_msg
            overall_exit_code = ret
            raise Exception(f"步骤 2 失败: {error_msg[:100]}")
        steps.append({"name": step_name, "status": "success"})

        # Step 3: generate_weekly_synthesis.py
        step_name = "generate_weekly_synthesis"
        logger.info(f"步骤 3/3: 生成每周总结")
        update_job_status("weekly", JobStatus.RUNNING, steps=steps)
        cmd = [sys.executable, str(SCRIPT_DIR / "generate_weekly_synthesis.py")]
        if dry_run:
            cmd.append("--dry-run")
        ret, stdout, stderr = run_command(cmd, logger)
        if ret != 0:
            error_msg = stderr or stdout or "generate_weekly_synthesis 失败"
            steps.append({"name": step_name, "status": "failure", "error": error_msg[:200]})
            logger.error(f"步骤 3 失败，终止执行 (exit code: {ret})")
            overall_error = error_msg
            overall_exit_code = ret
            raise Exception(f"步骤 3 失败: {error_msg[:100]}")
        steps.append({"name": step_name, "status": "success"})

        duration = time.time() - start_time
        update_job_status("weekly", JobStatus.SUCCESS, duration_seconds=duration, steps=steps)
        logger.info("每周例行任务完成")

    except Exception as e:
        duration = time.time() - start_time
        error_str = str(e)
        diagnostic = get_diagnostic_info("weekly", error_str, overall_exit_code)
        logger.error(f"诊断建议: {diagnostic}")
        update_job_status(
            "weekly",
            JobStatus.FAILURE,
            error_message=error_str[:500],
            exit_code=overall_exit_code,
            duration_seconds=duration,
            steps=steps,
        )
        return overall_exit_code if overall_exit_code else 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="每周例行任务")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    args = parser.parse_args()

    log_file = LOG_DIR / f"run_weekly_{datetime.now().strftime('%Y%m%d')}.log"
    logger = setup_logging("run_weekly", log_file)

    ret = run_weekly(dry_run=args.dry_run, logger=logger)
    sys.exit(ret)


if __name__ == "__main__":
    main()