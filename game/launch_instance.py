# 启动 game/ 下的丝之歌隔离子实例.
#
# 用法:
#   uv run python game/launch_instance.py          # 后台启动, 立即返回
#   uv run python game/launch_instance.py --wait   # 等游戏退出, 然后打印 BepInEx 日志尾部
#
# 没有装 InstanceTools 时默认拒绝启动, 避免游戏去读写真存档.
# 确认要无隔离启动再加 --allow-unisolated.

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.instance_paths import GAME_EXE_NAME, find_data_directory, get_instance_root
from tools.logutil import get_logger
from tools.tail_log import print_log_tail

log = get_logger("instance")


def launch_instance(target: Path, wait: bool, allow_unisolated: bool, log_tail_lines: int) -> int:
    exe = target / GAME_EXE_NAME
    if not exe.is_file():
        raise FileNotFoundError(
            f"找不到实例: {exe}, 先运行 uv run python game/prepare_instance.py"
        )

    data_directory = find_data_directory(target)
    instance_tools = target / "BepInEx" / "plugins" / "InstanceTools" / "InstanceTools.dll"
    if not instance_tools.is_file():
        if not allow_unisolated:
            raise FileNotFoundError(
                "找不到 InstanceTools.dll, 存档隔离不会生效, 真存档可能被读写. "
                "先跑 just install; 确认要无隔离启动再加 --allow-unisolated."
            )
        log.warning("无 InstanceTools, 存档隔离未启用")

    log.info("存档目录: %s", target / "savedata" / "default")

    steam_dll = data_directory / "Plugins" / "x86_64" / "steam_api64.dll"
    if steam_dll.is_file():
        log.info("Steam 接入: 启用 (steam_api64.dll 在位)")
    else:
        log.info("Steam 接入: 已断开 (steam_api64.dll 被改名)")

    # Unity 的 Player.log 是引擎在托管代码跑起来之前写的.
    # 用引擎自带的 -logFile 指到实例目录; 路径里有空格时由进程参数列表负责引用, 不要自己再加一层引号.
    unity_log = target / "Player.log"
    log.info("启动: %s", exe)
    popen_kwargs = {
        "args": [str(exe), "-logFile", str(unity_log), "-screen-fullscreen", "0"],
        "cwd": str(target),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        # 让游戏在启动脚本退出后还活着, 避免被父进程/作业对象一起收掉.
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    process = subprocess.Popen(**popen_kwargs)

    if not wait:
        log.info("进程号 %s, 引擎日志: %s", process.pid, unity_log)
        log.info("BepInEx 日志: %s", target / "BepInEx" / "LogOutput.log")
        return 0

    log.info("等待游戏退出 ...")
    exit_code = process.wait()
    log.info("游戏已退出 (exit=%s)", exit_code)
    print_log_tail(target / "BepInEx" / "LogOutput.log", log_tail_lines)
    return exit_code or 0


def main() -> int:
    parser = argparse.ArgumentParser(description="启动丝之歌隔离子实例")
    parser.add_argument("--target", default=str(get_instance_root()), help="实例目录")
    parser.add_argument("--wait", action="store_true", help="等游戏退出后打印 BepInEx 日志尾部")
    parser.add_argument("--allow-unisolated", action="store_true", help="允许在没有 InstanceTools 时启动")
    parser.add_argument("--log-tail-lines", type=int, default=40)
    args = parser.parse_args()
    return launch_instance(
        target=Path(args.target),
        wait=args.wait,
        allow_unisolated=args.allow_unisolated,
        log_tail_lines=args.log_tail_lines,
    )


if __name__ == "__main__":
    raise SystemExit(main())
