# 定位隔离子实例的存档目录.
#
# 实例的存档目录由实例里的 InstanceTools 插件接管: 它把 Application.persistentDataPath
# 重定向到 <实例目录>/savedata (层级说明见 game/README.md), 游戏的存档就在那里的 default 子目录下.
# 这里不去读 app.info, 也不做任何联接解析 -- 存档就是仓库里的普通文件.

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTANCE_DIR_NAME = "Hollow Knight Silksong"
GAME_EXE_NAME = "Hollow Knight Silksong.exe"


def get_repo_root() -> Path:
    return REPO_ROOT


def get_instance_root(instance_root: str | Path | None = None) -> Path:
    if instance_root:
        return Path(instance_root)
    return REPO_ROOT / "game" / INSTANCE_DIR_NAME


def get_instance_save_directory(instance_root: str | Path | None = None) -> Path:
    root = get_instance_root(instance_root)
    if not root.is_dir():
        raise FileNotFoundError(
            f"找不到隔离子实例: {root}, 先跑 uv run python game/prepare_instance.py"
        )
    return root / "savedata" / "default"


def find_data_directory(game_dir: Path) -> Path:
    matches = [path for path in game_dir.iterdir() if path.is_dir() and path.name.endswith("_Data")]
    if not matches:
        raise FileNotFoundError(f"找不到 *_Data 目录: {game_dir}")
    return matches[0]
