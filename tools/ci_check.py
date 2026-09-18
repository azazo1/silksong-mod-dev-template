# 不依赖游戏本体的脚本检查. 插件 DLL 由 CI 里的 dotnet build 编.

from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.logutil import get_logger

log = get_logger("ci")

PYTHON_FILES = (
    ROOT / "game" / "prepare_instance.py",
    ROOT / "game" / "launch_instance.py",
    ROOT / "tools" / "bepinex.py",
    ROOT / "tools" / "fsutil.py",
    ROOT / "tools" / "instance_paths.py",
    ROOT / "tools" / "logutil.py",
    ROOT / "tools" / "tail_log.py",
    ROOT / "tools" / "ci_check.py",
)

HELP_COMMANDS = (
    [sys.executable, str(ROOT / "game" / "prepare_instance.py"), "--help"],
    [sys.executable, str(ROOT / "game" / "launch_instance.py"), "--help"],
    [sys.executable, str(ROOT / "tools" / "tail_log.py"), "--help"],
)

REQUIRED_FILES = (
    ROOT / "src" / "ExampleMod" / "ExampleMod.csproj",
    ROOT / "src" / "ExampleMod" / "ExampleModPlugin.cs",
    ROOT / "src" / "ExampleMod" / "Config" / "PluginConfig.cs",
    ROOT / "src" / "ExampleMod" / "Patches" / "GameManagerStartPatch.cs",
    ROOT / "game" / "instance-tools" / "InstanceTools.csproj",
    ROOT / "game" / "instance-tools" / "src" / "InstanceToolsPlugin.cs",
    ROOT / "game" / "instance-tools" / "src" / "RedirectedPaths.cs",
    ROOT / "SilksongMod.sln",
    ROOT / "Plugin.props",
    ROOT / "Directory.Build.props",
    ROOT / "nuget.config",
    ROOT / "src" / "ExampleMod" / "packages.lock.json",
    ROOT / "game" / "instance-tools" / "packages.lock.json",
    ROOT / "justfile",
    ROOT / "SilksongPath.props.example",
)


def check_python_syntax() -> None:
    log.info("检查 Python 语法: %s 个文件", len(PYTHON_FILES))
    for path in PYTHON_FILES:
        if not path.is_file():
            raise FileNotFoundError(f"缺少脚本: {path}")
        py_compile.compile(str(path), doraise=True)
        log.info("语法通过: %s", path.relative_to(ROOT))


def check_help() -> None:
    log.info("检查 CLI --help")
    for command in HELP_COMMANDS:
        log.info("运行: %s", " ".join(command))
        completed = subprocess.run(command, cwd=str(ROOT), check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"命令失败 (exit={completed.returncode}): {command}")


def check_required_files() -> None:
    log.info("检查模板文件")
    for path in REQUIRED_FILES:
        if not path.is_file():
            raise FileNotFoundError(f"缺少模板文件: {path}")
        log.info("在位: %s", path.relative_to(ROOT))


def check_no_powershell() -> None:
    leftovers = [
        path
        for path in ROOT.rglob("*.ps1")
        if ".venv" not in path.parts and path.parts[:1] != (".tmp",)
    ]
    if leftovers:
        raise RuntimeError("还留着 PowerShell 脚本: " + ", ".join(str(path) for path in leftovers))
    log.info("没有遗留的 .ps1")


def main() -> int:
    check_python_syntax()
    check_help()
    check_required_files()
    check_no_powershell()
    log.info("脚本检查通过. 插件编译走 dotnet build.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
