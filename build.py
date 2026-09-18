# 编译插件.
#
# 两个产物:
#   ExampleMod.dll     -- 模组本体, 源码在 src/, 把名字改成你的模组即可
#   InstanceTools.dll  -- 隔离子实例的工具插件, 源码在 game/instance-tools/, 不属于 mod 本体
#
# 本机没有装 .NET SDK 也能编: 直接调用 Visual Studio 自带的 Roslyn csc.exe,
# 引用游戏目录中的程序集与 BepInEx 自带的 Harmony.
#
# 用法:
#   uv run python build.py
#   uv run python build.py --install
#   uv run python build.py --install --game-dir '<游戏目录>'

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

from tools.instance_paths import GAME_EXE_NAME, REPO_ROOT, get_instance_root
from tools.logutil import get_logger

log = get_logger("silksong-mod")

PROJECTS = (
    {"name": "ExampleMod", "source_dir": REPO_ROOT / "src"},
    {"name": "InstanceTools", "source_dir": REPO_ROOT / "game" / "instance-tools" / "src"},
)

VSWHERE = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
FRAMEWORK_CSC = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
VS_SEARCH_ROOTS = (
    Path(r"C:\Program Files\Microsoft Visual Studio"),
    Path(r"C:\Program Files (x86)\Microsoft Visual Studio"),
)


def resolve_relative(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (REPO_ROOT / candidate).resolve()


def resolve_game_dir(explicit: str | None) -> Path:
    if explicit:
        return resolve_relative(explicit)

    props_path = REPO_ROOT / "SilksongPath.props"
    if props_path.is_file():
        match = re.search(r"<GameDir>\s*([^<]+?)\s*</GameDir>", props_path.read_text(encoding="utf-8"))
        if match:
            return resolve_relative(match.group(1).strip())

    instance = get_instance_root()
    if (instance / GAME_EXE_NAME).is_file():
        return instance

    raise FileNotFoundError("找不到游戏目录: 请用 --game-dir 指定, 或先准备 SilksongPath.props / 隔离子实例.")


def resolve_compiler(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)

    if VSWHERE.is_file():
        completed = subprocess.run(
            [
                str(VSWHERE),
                "-latest",
                "-products",
                "*",
                "-find",
                r"**\Roslyn\csc.exe",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if lines:
            return Path(lines[0])

    log.info("vswhere 没找到 Roslyn csc, 改为扫描 Visual Studio 安装目录")
    found: list[Path] = []
    for root in VS_SEARCH_ROOTS:
        if not root.is_dir():
            continue
        found.extend(path for path in root.rglob("csc.exe") if "Roslyn" in str(path))
    if found:
        return sorted(found, key=lambda item: str(item), reverse=True)[0]

    if FRAMEWORK_CSC.is_file():
        return FRAMEWORK_CSC

    raise FileNotFoundError("找不到 csc.exe: 需要 Visual Studio (Roslyn) 或 .NET Framework 自带的编译器.")


def build(game_dir: Path, install: bool, compiler: Path) -> None:
    managed_dir = game_dir / "Hollow Knight Silksong_Data" / "Managed"
    bepinex_core_dir = game_dir / "BepInEx" / "core"
    if not managed_dir.is_dir():
        raise FileNotFoundError(f"游戏目录看起来不对, 找不到: {managed_dir}")
    if not bepinex_core_dir.is_dir():
        raise FileNotFoundError(
            f"游戏目录没有 BepInEx, 找不到: {bepinex_core_dir}. 先跑 just instance 让它下载并装进实例."
        )

    log.info("游戏目录: %s", game_dir)
    log.info("编译器: %s", compiler)

    references = [
        managed_dir / "netstandard.dll",
        bepinex_core_dir / "BepInEx.dll",
        bepinex_core_dir / "0Harmony.dll",
        managed_dir / "Assembly-CSharp.dll",
        managed_dir / "UnityEngine.dll",
        managed_dir / "UnityEngine.CoreModule.dll",
    ]
    # 常见但本模板暂不引用的程序集, 按需加进 references:
    #   UnityEngine.IMGUIModule.dll
    #   UnityEngine.InputLegacyModule.dll
    #   UnityEngine.Physics2DModule.dll
    #   UnityEngine.UIModule.dll
    #   UnityEngine.UI.dll
    #   UnityEngine.TextRenderingModule.dll
    #   Unity.TextMeshPro.dll
    #   Newtonsoft.Json.dll
    #   TeamCherry.Localization.dll

    for reference in references:
        if not reference.is_file():
            raise FileNotFoundError(f"缺少引用程序集: {reference}")

    output_dir = REPO_ROOT / "bin"
    output_dir.mkdir(parents=True, exist_ok=True)

    for project in PROJECTS:
        sources = sorted(project["source_dir"].rglob("*.cs"))
        if not sources:
            raise FileNotFoundError(f"没有找到源文件: {project['source_dir']}")

        output_dll = output_dir / f"{project['name']}.dll"
        arguments = [
            str(compiler),
            "/nologo",
            "/target:library",
            "/langversion:7.3",
            "/optimize+",
            "/deterministic+",
            f"/out:{output_dll}",
        ]
        arguments.extend(f"/r:{reference}" for reference in references)
        arguments.extend(str(path) for path in sources)

        log.info("编译 %s: %s 个源文件 ...", project["name"], len(sources))
        completed = subprocess.run(arguments, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"csc 编译失败 ({project['name']}, exit={completed.returncode})")
        log.info("产物: %s", output_dll)

        if install:
            plugin_dir = game_dir / "BepInEx" / "plugins" / project["name"]
            plugin_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(output_dll, plugin_dir / f"{project['name']}.dll")
            log.info("已安装插件: %s", plugin_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="编译丝之歌模组插件")
    parser.add_argument("--game-dir", default=None, help="游戏目录, 含 exe 与 *_Data 的那一层")
    parser.add_argument("--install", action="store_true", help="编译后复制到 BepInEx/plugins")
    parser.add_argument("--compiler", default=None, help="csc.exe 路径")
    args = parser.parse_args()
    build(
        game_dir=resolve_game_dir(args.game_dir),
        install=args.install,
        compiler=resolve_compiler(args.compiler),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
