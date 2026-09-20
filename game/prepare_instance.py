# 创建或刷新一份与源安装隔离的丝之歌游戏子实例.
#
# 实例目录: game/Hollow Knight Silksong/ (相对本仓库根目录;
# 路径层级的完整说明见 game/README.md, 这里只讲本脚本做什么)
#   - 共享 (目录联接, 不占额外空间): <exe>_Data 下的 Managed/Resources/StreamingAssets, 以及根目录的 MonoBleedingEdge/D3D12
#   - 独立 (真实副本): 可执行文件, doorstop 文件, BepInEx/, <exe>_Data 下的配置与小数据文件
#   - 隔离存档与日志: 由实例的 InstanceTools 插件在代码层接管, 不需要改游戏文件:
#       Application.persistentDataPath -> <实例目录>/savedata
#       PlayerPrefs                     -> <实例目录>/savedata/instance-prefs.txt
#         (若还没有这份文件, 从 game/instance-prefs.txt 原样复制默认设置)
#       File.Replace                    -> Copy/Delete/Move 等价实现
#     Player.log 由启动脚本用引擎自带的 -logFile 指到 <实例目录>/Player.log.
#   - 隔离 Steam: 默认把实例的 steam_api64.dll 改名为 steam_api64.dll.disabled
#   - BepInEx: 源安装有就复制过来; 没有则下载 BepInExPack_Silksong 只装进实例, 不改源安装
#
# 用法:
#   uv run python game/prepare_instance.py --source '<源安装>'
#   uv run python game/prepare_instance.py --refresh-binaries
#   uv run python game/prepare_instance.py --full-copy
#   uv run python game/prepare_instance.py --keep-steam
#   uv run python game/prepare_instance.py --force

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bepinex import has_bepinex, install_bepinex
from tools.fsutil import (
    copy_directory_contents,
    copy_file_if_needed,
    create_junction,
    ensure_real_directory,
    is_reparse_dir,
    remove_instance_tree,
)
from tools.instance_paths import GAME_EXE_NAME, find_data_directory, get_instance_root
from tools.logutil import get_logger

log = get_logger("instance")

SHARED_ROOT_NAMES = ("MonoBleedingEdge", "D3D12")
SHARED_DATA_NAMES = ("Managed", "Resources", "StreamingAssets")
STEAM_DLL_NAME = "steam_api64.dll"


def resolve_source_directory(path: str | None) -> Path:
    if not path or not path.strip():
        raise ValueError("未指定源安装: 请用 --source 或环境变量 SILKSONG_GAME_DIR.")
    source = Path(path)
    exe = source / GAME_EXE_NAME
    if not exe.is_file():
        raise FileNotFoundError(f"源安装看起来不对, 找不到: {exe}")
    data = find_data_directory(source)
    managed = data / "Managed"
    if not managed.is_dir():
        raise FileNotFoundError(f"源安装看起来不对, 找不到: {managed}")
    return source.resolve()


def set_steam_dll_state(plugins_directory: Path, keep_steam: bool) -> None:
    active = plugins_directory / STEAM_DLL_NAME
    disabled = Path(str(active) + ".disabled")
    if keep_steam:
        if disabled.is_file() and not active.is_file():
            disabled.replace(active)
            log.info("恢复 steam_api64.dll, 实例恢复 Steam 接入")
        return
    if active.is_file():
        active.replace(disabled)
        log.info("禁用 steam_api64.dll (改名成 steam_api64.dll.disabled)")
    else:
        log.info("steam_api64.dll 已处于禁用状态")


def iter_real_files(target: Path, data_name: str):
    skip_roots = {
        target / data_name / "Managed",
        target / data_name / "Resources",
        target / data_name / "StreamingAssets",
        target / "MonoBleedingEdge",
        target / "D3D12",
    }
    for dirpath, dirnames, filenames in os.walk(target, followlinks=False):
        current = Path(dirpath)
        if current in skip_roots or is_reparse_dir(current):
            dirnames[:] = []
            continue
        dirnames[:] = [
            name
            for name in dirnames
            if not is_reparse_dir(current / name) and (current / name) not in skip_roots
        ]
        for name in filenames:
            yield current / name


def prepare_instance(
    source: Path,
    target: Path,
    keep_steam: bool,
    full_copy: bool,
    refresh_binaries: bool,
    force: bool,
    bepinex_version: str | None,
) -> None:
    data_name = find_data_directory(source).name
    log.info("源安装: %s", source)
    log.info("实例目录: %s", target)

    if force and target.exists():
        log.info("按 --force 重建, 先删除已有实例")
        remove_instance_tree(target)

    ensure_real_directory(target)

    for name in SHARED_ROOT_NAMES:
        from_path = source / name
        if not from_path.exists():
            log.info("源安装没有 %s, 跳过", name)
            continue
        to_path = target / name
        if full_copy:
            ensure_real_directory(to_path)
            copy_directory_contents(from_path, to_path, overwrite=refresh_binaries)
        else:
            create_junction(to_path, from_path)

    source_data = source / data_name
    instance_data = target / data_name
    ensure_real_directory(instance_data)

    for name in SHARED_DATA_NAMES:
        from_path = source_data / name
        if not from_path.exists():
            log.info("源安装没有 %s\\%s, 跳过", data_name, name)
            continue
        to_path = instance_data / name
        if full_copy:
            ensure_real_directory(to_path)
            copy_directory_contents(from_path, to_path, overwrite=refresh_binaries)
        else:
            create_junction(to_path, from_path)

    data_file_count = 0
    for file in source_data.iterdir():
        if file.is_file() and copy_file_if_needed(file, instance_data / file.name, overwrite=refresh_binaries):
            data_file_count += 1
    log.info("复制 %s 顶层文件: %s 个", data_name, data_file_count)

    source_plugins = source_data / "Plugins"
    instance_plugins = instance_data / "Plugins"
    if source_plugins.is_dir():
        ensure_real_directory(instance_plugins)
        copy_directory_contents(source_plugins, instance_plugins, overwrite=refresh_binaries)

    set_steam_dll_state(instance_plugins / "x86_64", keep_steam)

    root_copied = 0
    for file in source.iterdir():
        if file.is_file() and copy_file_if_needed(file, target / file.name, overwrite=refresh_binaries):
            root_copied += 1
    log.info("复制根目录文件: %s 个", root_copied)

    source_bepinex = source / "BepInEx"
    if has_bepinex(source):
        log.info("源安装已有 BepInEx, 复制到实例")
        ensure_real_directory(target / "BepInEx")
        copy_directory_contents(source_bepinex, target / "BepInEx", overwrite=refresh_binaries)
        for name in ("winhttp.dll", "doorstop_config.ini", ".doorstop_version"):
            item = source / name
            if item.is_file():
                copy_file_if_needed(item, target / name, overwrite=refresh_binaries)
    else:
        log.info("源安装没有 BepInEx, 将下载装进实例 (不改源安装)")

    if not has_bepinex(target) or (refresh_binaries and not has_bepinex(source)):
        install_bepinex(target, version=bepinex_version, force=refresh_binaries)

    default_prefs = Path(__file__).resolve().parent / "instance-prefs.txt"
    instance_prefs = target / "savedata" / "instance-prefs.txt"
    if copy_file_if_needed(default_prefs, instance_prefs):
        log.info("写入默认设置: %s", instance_prefs)
    else:
        log.info("已有设置文件, 保留: %s", instance_prefs)

    exe = target / GAME_EXE_NAME
    if not exe.is_file():
        raise FileNotFoundError(f"实例不完整, 找不到: {exe}")
    if not has_bepinex(target):
        raise RuntimeError(f"实例没有 BepInEx, 找不到: {target / 'BepInEx' / 'core' / 'BepInEx.dll'}")

    real_files = list(iter_real_files(target, data_name))
    total_bytes = sum(path.stat().st_size for path in real_files)
    steam_enabled = keep_steam or (instance_plugins / "x86_64" / STEAM_DLL_NAME).is_file()
    log.info("实例就绪.")
    log.info("真实占用: %s 个文件, %.1f MB", len(real_files), total_bytes / (1024 * 1024))
    log.info("存档目录 (由实例里的 InstanceTools 接管): %s", target / "savedata" / "default")
    log.info("Steam 接入: %s", "启用" if steam_enabled else "已断开")
    log.info("下一步: just install, 然后 just launch")
    log.info("插件目录: %s", target / "BepInEx" / "plugins")


def main() -> int:
    parser = argparse.ArgumentParser(description="创建或刷新丝之歌隔离子实例")
    parser.add_argument("--source", default=os.environ.get("SILKSONG_GAME_DIR"), help="源安装游戏目录")
    parser.add_argument("--target", default=str(get_instance_root()), help="实例目录")
    parser.add_argument("--keep-steam", action="store_true", help="保留 Steam 接入")
    parser.add_argument("--full-copy", action="store_true", help="连数据目录也完整复制")
    parser.add_argument("--refresh-binaries", action="store_true", help="覆盖刷新可执行文件与 BepInEx 基础文件")
    parser.add_argument("--force", action="store_true", help="删除已有实例后重建")
    parser.add_argument("--bepinex-version", default=None, help="指定 BepInExPack_Silksong 版本, 默认取最新")
    args = parser.parse_args()

    prepare_instance(
        source=resolve_source_directory(args.source),
        target=Path(args.target),
        keep_steam=args.keep_steam,
        full_copy=args.full_copy,
        refresh_binaries=args.refresh_binaries,
        force=args.force,
        bepinex_version=args.bepinex_version,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
