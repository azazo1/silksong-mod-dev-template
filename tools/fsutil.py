from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

from tools.logutil import get_logger

log = get_logger("instance")

SKIP_FILE_NAMES = {"LogOutput.log"}
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def is_reparse_dir(path: Path) -> bool:
    try:
        if hasattr(path, "is_junction") and path.is_junction():
            return True
    except OSError:
        return False
    try:
        info = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    return stat.S_ISLNK(info.st_mode)


def read_link_target(path: Path) -> Path | None:
    try:
        return Path(os.readlink(path))
    except OSError:
        return None


def is_link_to(link_path: Path, target_path: Path) -> bool:
    current = read_link_target(link_path)
    if current is None:
        return False
    return os.path.normcase(os.path.abspath(current)) == os.path.normcase(os.path.abspath(target_path))


def remove_link_if_present(path: Path) -> None:
    if path.exists() and is_reparse_dir(path):
        log.info("移除联接: %s", path)
        os.rmdir(path)


def ensure_real_directory(path: Path) -> None:
    if path.exists():
        if is_reparse_dir(path):
            remove_link_if_present(path)
        elif path.is_file():
            raise FileExistsError(f"同名文件挡住了目录, 请先处理: {path}")
    path.mkdir(parents=True, exist_ok=True)


def create_junction(link_path: Path, target_path: Path) -> None:
    if is_link_to(link_path, target_path):
        log.info("联接已在位: %s", link_path.name)
        return

    remove_link_if_present(link_path)
    if link_path.exists():
        raise FileExistsError(f"目标已存在且不是联接, 请先处理: {link_path}")

    link_path.parent.mkdir(parents=True, exist_ok=True)
    import _winapi

    _winapi.CreateJunction(str(target_path), str(link_path))
    log.info("新建联接: %s -> %s", link_path.name, target_path)


def find_junctions(root: Path) -> list[Path]:
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            path = Path(entry.path)
            if entry.is_symlink() or is_reparse_dir(path):
                found.append(path)
                continue
            stack.append(path)
    found.sort(key=lambda item: len(str(item)), reverse=True)
    return found


def remove_instance_tree(path: Path) -> None:
    # 先只删联接本身, 避免递归删除穿透到源安装.
    for link in find_junctions(path):
        log.info("移除联接: %s", link)
        os.rmdir(link)
    shutil.rmtree(path)


def copy_file_if_needed(source: Path, destination: Path, overwrite: bool = False) -> bool:
    if destination.exists() and not overwrite:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def copy_directory_contents(source_dir: Path, dest_dir: Path, overwrite: bool = False) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    kept = 0
    processed = 0
    for dirpath, dirnames, filenames in os.walk(source_dir, followlinks=False):
        relative_dir = Path(dirpath).relative_to(source_dir)
        destination_dir = dest_dir / relative_dir
        destination_dir.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            if name in SKIP_FILE_NAMES:
                continue
            source_file = Path(dirpath) / name
            dest_file = destination_dir / name
            if copy_file_if_needed(source_file, dest_file, overwrite=overwrite):
                copied += 1
            else:
                kept += 1
            processed += 1
            if processed % 500 == 0:
                log.info("复制 %s: 已处理 %s 个文件", source_dir.name, processed)
    log.info("复制 %s: 新增/覆盖 %s 个, 保留已有 %s 个", source_dir.name, copied, kept)
