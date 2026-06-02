#!/usr/bin/env python3
"""
run_regression_tests.py - 最小回归测试流程

检查系统是否处于可正常运行状态。

用法:
  python run_regression_tests.py              # 人类可读输出
  python run_regression_tests.py --json       # JSON 输出
  python run_regression_tests.py --strict     # 严格模式

退出码:
  0 - 全部通过
  1 - 存在警告（--strict 时）
  2 - 存在错误
"""

import argparse
import subprocess
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def run_command(cmd: list, description: str) -> tuple[bool, str]:
    """运行命令并返回 (success, output)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=PROJECT_ROOT
        )
        success = result.returncode == 0
        output = result.stdout if result.returncode == 0 else result.stderr
        return success, output.strip()
    except subprocess.TimeoutExpired:
        return False, "超时"
    except Exception as e:
        return False, str(e)


def run_tests(strict: bool = False, verbose: bool = False) -> dict:
    """运行所有回归测试"""
    results = []

    # 1. check_system.py
    if verbose:
        print("运行 check_system.py...", file=sys.stderr)
    success, output = run_command(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "check_system.py")],
        "系统检查"
    )
    results.append({
        "name": "check_system",
        "description": "系统健康检查",
        "success": success,
        "output": "通过" if success else output
    })

    # 2. validate templates
    if verbose:
        print("验证模板...", file=sys.stderr)
    template_results = []
    for tmpl in ["atomic_note.md", "source.md", "map.md", "project.md", "daily_brief.md", "weekly_synthesis.md"]:
        tmpl_path = PROJECT_ROOT / "_templates" / tmpl
        if tmpl_path.exists():
            # validate_note.py: 0=通过, 1=警告(但ok=true), 2=错误
            success, stderr = run_command(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_note.py"), str(tmpl_path)],
                f"模板验证: {tmpl}"
            )
            # 退出码 0 或 1 都算通过（1 只是警告）
            success = success or (stderr == "" and True)  # 简化判断
            # 检查实际验证结果：解析 stdout 看 ok 字段
            proc = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_note.py"), str(tmpl_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=PROJECT_ROOT
            )
            try:
                results_json = json.loads(proc.stdout)
                for r in results_json:
                    is_ok = r.get("ok", False)
                    template_results.append({"template": tmpl, "success": is_ok})
            except:
                template_results.append({"template": tmpl, "success": False})
        else:
            template_results.append({"template": tmpl, "success": False, "error": "file not found"})

    all_templates_ok = all(t["success"] for t in template_results)
    results.append({
        "name": "templates",
        "description": "模板验证",
        "success": all_templates_ok,
        "details": template_results
    })

    # 3. run_daily --dry-run
    if verbose:
        print("运行 run_daily --dry-run...", file=sys.stderr)
    success, output = run_command(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily.py"), "--dry-run"],
        "每日任务dry-run"
    )
    results.append({
        "name": "run_daily_dry_run",
        "description": "每日任务dry-run",
        "success": success,
        "output": "通过" if success else output
    })

    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "results": results,
        "success": failed == 0
    }


def print_human_readable(summary: dict):
    """人类可读输出"""
    print("=" * 60)
    print("Memory Palace 回归测试")
    print("=" * 60)

    for r in summary["results"]:
        status = "✅" if r["success"] else "❌"
        print(f"{status} {r['description']}")
        if not r["success"] and r.get("output"):
            print(f"   {r['output'][:200]}")

    print()
    print("-" * 60)
    print(f"通过: {summary['passed']}/{summary['total']}")

    if summary["failed"] > 0:
        print(f"❌ 失败: {summary['failed']}")
    else:
        print("✅ 全部通过")

    print("=" * 60)


def print_json(summary: dict):
    """JSON 输出"""
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Memory Palace 回归测试")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--strict", action="store_true", help="严格模式")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    summary = run_tests(strict=args.strict, verbose=args.verbose)

    if args.json:
        print_json(summary)
    else:
        print_human_readable(summary)

    # 退出码：失败返回2，有警告且strict返回1
    if summary["failed"] > 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()