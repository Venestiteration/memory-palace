#!/usr/bin/env python3
"""
check_system.py - 系统健康检查

检查 memory_palace 项目是否处于可运行状态。

用法:
  python check_system.py                    # 人类可读输出
  python check_system.py --json             # JSON 输出
  python check_system.py --strict           # 严格模式（警告也返回非0）
  python check_system.py --verbose          # 详细输出

退出码:
  0 - 全部通过
  1 - 存在警告（--strict 时）
  2 - 存在错误

禁止:
  - 不修改笔记
  - 不重建索引
  - 不读取或打印 .env 中的真实 key
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class CheckResult:
    """检查结果"""

    def __init__(self):
        self.checks = []
        self.errors = []
        self.warnings = []

    def add_ok(self, name: str, message: str = ""):
        self.checks.append({"name": name, "status": "ok", "message": message})

    def add_warning(self, name: str, message: str):
        self.checks.append({"name": name, "status": "warning", "message": message})
        self.warnings.append(f"{name}: {message}")

    def add_error(self, name: str, message: str):
        self.checks.append({"name": name, "status": "error", "message": message})
        self.errors.append(f"{name}: {message}")

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def exit_code(self, strict: bool = False) -> int:
        if self.has_errors():
            return 2
        if strict and self.has_warnings():
            return 1
        return 0


def run_help_check(script_path: Path, name: str, result: CheckResult):
    """检查脚本 --help 是否可运行"""
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT
        )
        if proc.returncode == 0 and len(proc.stdout) > 0:
            result.add_ok(name, f"--help 运行正常")
        else:
            result.add_error(name, f"--help 失败，退出码: {proc.returncode}")
    except subprocess.TimeoutExpired:
        result.add_error(name, "--help 超时")
    except Exception as e:
        result.add_error(name, f"--help 异常: {str(e)}")


def check_key_files(result: CheckResult):
    """检查关键文件是否存在"""
    key_files = {
        "CLAUDE.md": PROJECT_ROOT / "CLAUDE.md",
        ".env.example": PROJECT_ROOT / ".env.example",
        "requirements.txt": PROJECT_ROOT / "requirements.txt",
        "scripts/mp.py": PROJECT_ROOT / "scripts" / "mp.py",
        "scripts/config.py": PROJECT_ROOT / "scripts" / "config.py",
    }

    for name, path in key_files.items():
        if path.exists():
            result.add_ok(name, f"存在: {path}")
        else:
            result.add_error(name, f"缺失: {path}")


def check_scripts_help(result: CheckResult):
    """检查核心脚本 --help"""
    scripts = [
        ("scripts/mp.py", "mp.py"),
        ("scripts/validate_note.py", "validate_note.py"),
        ("scripts/build_index.py", "build_index.py"),
        ("scripts/build_vector_index.py", "build_vector_index.py"),
        ("scripts/search_notes.py", "search_notes.py"),
        ("scripts/atomize_note.py", "atomize_note.py"),
        ("scripts/process_inbox.py", "process_inbox.py"),
    ]

    for script_path, name in scripts:
        full_path = PROJECT_ROOT / script_path
        if full_path.exists():
            run_help_check(full_path, name, result)
        else:
            result.add_error(name, f"脚本不存在: {script_path}")


def check_templates(result: CheckResult):
    """检查模板是否能通过验证"""
    template_dir = PROJECT_ROOT / "_templates"
    templates = [
        "source.md",
        "atomic_note.md",
        "map.md",
        "project.md",
        "daily_brief.md",
        "weekly_synthesis.md",
    ]

    validate_script = PROJECT_ROOT / "scripts" / "validate_note.py"
    if not validate_script.exists():
        result.add_error("templates", "validate_note.py 不存在")
        return

    for tmpl in templates:
        tmpl_path = template_dir / tmpl
        if not tmpl_path.exists():
            result.add_warning(f"template/{tmpl}", "模板文件不存在")
            continue

        try:
            proc = subprocess.run(
                [sys.executable, str(validate_script), str(tmpl_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=PROJECT_ROOT
            )
            # validate_note.py: 0=通过, 1=警告, 2=错误
            if proc.returncode == 0:
                result.add_ok(f"template/{tmpl}", "验证通过")
            elif proc.returncode == 1:
                # 解析警告信息
                try:
                    output = json.loads(proc.stdout)
                    warns = []
                    for r in output:
                        warns.extend(r.get("warnings", []))
                    result.add_warning(f"template/{tmpl}", f"警告: {'; '.join(warns)}")
                except:
                    result.add_warning(f"template/{tmpl}", f"验证有警告，退出码: 1")
            else:
                result.add_error(f"template/{tmpl}", f"验证失败，退出码: {proc.returncode}")
        except Exception as e:
            result.add_error(f"template/{tmpl}", f"验证异常: {str(e)}")


def check_sqlite_index(result: CheckResult):
    """检查 SQLite 索引是否存在"""
    db_path = PROJECT_ROOT / ".memory_palace" / "index.sqlite"

    if db_path.exists():
        size = db_path.stat().st_size
        result.add_ok("sqlite_index", f"存在 ({size} bytes)")
    else:
        result.add_warning("sqlite_index", "不存在（需要运行 build_index.py）")


def check_vector_index(result: CheckResult):
    """检查向量索引是否存在"""
    manifest_path = PROJECT_ROOT / ".memory_palace" / "vector_index" / "manifest.json"

    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            count = len(manifest)
            result.add_ok("vector_index", f"存在 ({count} vectors)")
        except Exception as e:
            result.add_warning("vector_index", f"manifest.json 解析失败: {str(e)}")
    else:
        vector_dir = PROJECT_ROOT / ".memory_palace" / "vector_index"
        if vector_dir.exists():
            result.add_warning("vector_index", "manifest.json 不存在（需要运行 build_vector_index.py）")
        else:
            result.add_warning("vector_index", "向量索引目录不存在")


def check_environment(result: CheckResult):
    """检查环境变量配置（不读取真实 key）"""
    # 检查 .env 是否存在
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        result.add_ok(".env", "存在")

        # 检查关键变量是否已配置（不读取值）
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        has_minimax = "MINIMAX_API_KEY" in content
        has_dashscope = "DASHSCOPE_API_KEY" in content

        if has_minimax:
            result.add_ok("MINIMAX_API_KEY", "已配置（不显示值）")
        else:
            result.add_warning("MINIMAX_API_KEY", "未配置")

        if has_dashscope:
            result.add_ok("DASHSCOPE_API_KEY", "已配置（不显示值）")
        else:
            result.add_warning("DASHSCOPE_API_KEY", "未配置")
    else:
        result.add_warning(".env", ".env 文件不存在")


def check_directory_structure(result: CheckResult):
    """检查目录结构"""
    required_dirs = [
        "00_Inbox",
        "01_Sources",
        "02_Atomic_Notes",
        "03_Maps",
        "04_Cards",
        "05_Projects",
        "06_Daily_Briefs",
        "07_Weekly_Synthesis",
        "08_Outputs",
        "09_Archive",
        "scripts",
        "logs",
        "_templates",
    ]

    all_exist = True
    missing = []
    for d in required_dirs:
        if not (PROJECT_ROOT / d).exists():
            missing.append(d)
            all_exist = False

    if all_exist:
        result.add_ok("directory_structure", "所有目录存在")
    else:
        result.add_error("directory_structure", f"缺失目录: {', '.join(missing)}")


def check_launchd_service(result: CheckResult):
    """检查 launchd 服务配置"""
    plist_path = PROJECT_ROOT / ".memory_palace" / "com.memorypalace.daily.plist"

    if plist_path.exists():
        result.add_ok("launchd_service", "plist 存在")
    else:
        result.add_warning("launchd_service", "尚未安装（可运行 install_launchd.py）")


def run_system_check(strict: bool = False, verbose: bool = False) -> CheckResult:
    """运行所有检查"""
    result = CheckResult()

    if verbose:
        print("开始系统检查...", file=sys.stderr)

    check_key_files(result)
    check_scripts_help(result)
    check_templates(result)
    check_sqlite_index(result)
    check_vector_index(result)
    check_environment(result)
    check_directory_structure(result)
    check_launchd_service(result)

    return result


def print_human_readable(result: CheckResult):
    """人类可读输出"""
    print("=" * 60)
    print("Memory Palace 系统检查")
    print("=" * 60)

    for check in result.checks:
        status_icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}[check["status"]]
        print(f"{status_icon} {check['name']}")
        if check["message"]:
            print(f"   {check['message']}")

    print()
    print("-" * 60)

    if result.has_errors():
        print(f"❌ 错误: {len(result.errors)} 个")
        for e in result.errors:
            print(f"   - {e}")
        print()

    if result.has_warnings():
        print(f"⚠️ 警告: {len(result.warnings)} 个")
        for w in result.warnings:
            print(f"   - {w}")
        print()

    if not result.has_errors() and not result.has_warnings():
        print("✅ 所有检查通过")

    print("=" * 60)


def print_json(result: CheckResult):
    """JSON 输出"""
    output = {
        "success": not result.has_errors(),
        "warnings": result.warnings,
        "errors": result.errors,
        "checks": result.checks,
        "summary": {
            "total": len(result.checks),
            "ok": sum(1 for c in result.checks if c["status"] == "ok"),
            "warnings": len(result.warnings),
            "errors": len(result.errors),
        }
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="检查 memory_palace 系统状态",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python check_system.py                # 人类可读输出
  python check_system.py --json         # JSON 输出
  python check_system.py --strict      # 严格模式（警告也返回非0）
  python check_system.py --verbose     # 详细输出
        """
    )
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--strict", action="store_true", help="严格模式（警告也返回非0）")
    parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    result = run_system_check(strict=args.strict, verbose=args.verbose)

    if args.json:
        print_json(result)
    else:
        print_human_readable(result)

    sys.exit(result.exit_code(strict=args.strict))


if __name__ == "__main__":
    main()