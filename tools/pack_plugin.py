# 把模组 dll 打成可解压进 BepInEx/plugins 的 zip.
# 包内是 <AssemblyName>/<AssemblyName>.dll, 不含 InstanceTools.

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.logutil import get_logger
from tools.project_meta import read_assembly_name, read_package_version

log = get_logger("pack")

DEFAULT_CSPROJ = ROOT / "src" / "ExampleMod" / "ExampleMod.csproj"


def strip_version_prefix(value: str) -> str:
    text = value.strip()
    if len(text) > 1 and text[0] in "vV" and text[1].isdigit():
        return text[1:]
    return text


def git_build_version() -> str:
    if os.name == "nt":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "build-version.ps1"),
        ]
    else:
        command = ["bash", str(ROOT / "scripts" / "build-version.sh")]
    completed = subprocess.run(command, cwd=str(ROOT), check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "读取 git 构建版本失败: "
            + (completed.stderr.strip() or completed.stdout.strip() or f"exit={completed.returncode}")
        )
    version = strip_version_prefix(completed.stdout.strip())
    if not version:
        raise RuntimeError("build-version 脚本没有输出版本号")
    return version


def resolve_version(git_version: bool) -> str:
    env = os.environ.get("PROJECT_BUILD_VERSION", "").strip()
    if env:
        return strip_version_prefix(env)
    if git_version:
        return git_build_version()
    return read_package_version(ROOT)


def build_solution() -> None:
    log.info("编译 Release")
    completed = subprocess.run(
        ["dotnet", "build", str(ROOT / "SilksongMod.sln"), "-c", "Release"],
        cwd=str(ROOT),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"dotnet build 失败 (exit={completed.returncode})")


def pack(csproj: Path, version: str, configuration: str) -> Path:
    assembly = read_assembly_name(csproj)
    dll = csproj.parent / "bin" / configuration / f"{assembly}.dll"
    pdb = dll.with_suffix(".pdb")
    if not dll.is_file():
        raise FileNotFoundError(f"找不到编译产物: {dll}")

    dist_dir = ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{assembly}-{version}.zip"
    archive = dist_dir / archive_name
    if archive.exists():
        archive.unlink()

    plugin_dir = f"{assembly}/"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(dll, f"{plugin_dir}{dll.name}")
        log.info("加入 %s", dll.name)
        if pdb.is_file():
            zf.write(pdb, f"{plugin_dir}{pdb.name}")
            log.info("加入 %s", pdb.name)

    names = zipfile.ZipFile(archive).namelist()
    expected = f"{plugin_dir}{assembly}.dll"
    if expected not in names:
        raise RuntimeError(f"zip 里缺少 {expected}: {names}")

    log.info("产物: %s", archive)
    log.info("解压到游戏的 BepInEx/plugins 即可")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description="打包模组为 BepInEx/plugins 目录 zip")
    parser.add_argument("--project", default=str(DEFAULT_CSPROJ), help="模组 csproj")
    parser.add_argument("--configuration", default="Release")
    parser.add_argument("--build", action="store_true", help="打包前 dotnet build -c Release")
    parser.add_argument("--git-version", action="store_true", help="文件名用 git 构建版本, 而不是 Directory.Build.props")
    args = parser.parse_args()

    csproj = Path(args.project)
    if not csproj.is_absolute():
        csproj = (ROOT / csproj).resolve()
    if not csproj.is_file():
        raise FileNotFoundError(f"找不到工程: {csproj}")

    if args.build:
        build_solution()

    version = resolve_version(git_version=args.git_version)
    log.info("打包版本: %s", version)
    pack(csproj, version, args.configuration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
