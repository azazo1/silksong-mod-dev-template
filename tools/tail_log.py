from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.instance_paths import get_instance_root
from tools.logutil import get_logger

log = get_logger("instance")


def print_log_tail(path: Path, lines: int) -> None:
    if not path.is_file():
        log.info("没有找到 BepInEx 日志: %s", path)
        return
    log.info("BepInEx 日志尾部 (%s):", path)
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in text[-lines:]:
        print(f"  {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description="打印隔离子实例的 BepInEx 日志尾部")
    parser.add_argument("lines", nargs="?", type=int, default=40)
    parser.add_argument(
        "--path",
        default=str(get_instance_root() / "BepInEx" / "LogOutput.log"),
    )
    args = parser.parse_args()
    print_log_tail(Path(args.path), args.lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
