from __future__ import annotations

import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

from tools.fsutil import copy_directory_contents, copy_file_if_needed
from tools.instance_paths import get_repo_root
from tools.logutil import get_logger

log = get_logger("bepinex")

PACKAGE_NAMESPACE = "silksong_modding"
PACKAGE_NAME = "BepInExPack_Silksong"
PACKAGE_API_URL = (
    f"https://thunderstore.io/api/experimental/package/{PACKAGE_NAMESPACE}/{PACKAGE_NAME}/"
)
USER_AGENT = "silksong-mod-dev-template"
CORE_DLL_RELATIVE = Path("BepInEx") / "core" / "BepInEx.dll"
DOORSTOP_DLL_NAME = "winhttp.dll"


def has_bepinex(game_dir: Path) -> bool:
    return (game_dir / CORE_DLL_RELATIVE).is_file() and (game_dir / DOORSTOP_DLL_NAME).is_file()


def _request(url: str):
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def resolve_pack_release(version: str | None = None) -> tuple[str, str]:
    if version:
        download_url = (
            f"https://thunderstore.io/package/download/{PACKAGE_NAMESPACE}/{PACKAGE_NAME}/{version}/"
        )
        return version, download_url

    log.info("查询 Thunderstore 上的 %s-%s 最新版", PACKAGE_NAMESPACE, PACKAGE_NAME)
    with urllib.request.urlopen(_request(PACKAGE_API_URL)) as response:
        payload = json.loads(response.read().decode("utf-8"))
    latest = payload["latest"]
    resolved = latest["version_number"]
    download_url = latest["download_url"]
    log.info("最新版: %s", resolved)
    return resolved, download_url


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    log.info("下载 %s", url)
    last_percent = -1
    with urllib.request.urlopen(_request(url)) as response, partial.open("wb") as output:
        total = int(response.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            output.write(chunk)
            read += len(chunk)
            if total <= 0:
                continue
            percent = min(100, read * 100 // total)
            if percent >= last_percent + 10 or percent == 100:
                last_percent = percent
                log.info("下载进度 %s%% (%s / %s)", percent, read, total)
    partial.replace(destination)
    log.info("已保存: %s", destination)


def _find_pack_root(extract_dir: Path) -> Path:
    candidates = [extract_dir, *sorted(path for path in extract_dir.rglob("*") if path.is_dir())]
    for path in candidates:
        if (path / CORE_DLL_RELATIVE).is_file() and (path / DOORSTOP_DLL_NAME).is_file():
            return path
    raise FileNotFoundError(f"压缩包里找不到 BepInEx 与 {DOORSTOP_DLL_NAME}: {extract_dir}")


def _copy_pack(pack_root: Path, dest_dir: Path, overwrite: bool) -> None:
    for item in pack_root.iterdir():
        destination = dest_dir / item.name
        if item.is_dir():
            copy_directory_contents(item, destination, overwrite=overwrite)
        elif item.is_file():
            copied = copy_file_if_needed(item, destination, overwrite=overwrite)
            if copied:
                log.info("复制 %s", item.name)


def install_bepinex(
    dest_dir: Path,
    version: str | None = None,
    force: bool = False,
) -> None:
    if has_bepinex(dest_dir) and not force:
        log.info("实例已有 BepInEx, 跳过下载: %s", dest_dir)
        return

    resolved, download_url = resolve_pack_release(version)
    cache_dir = get_repo_root() / ".tmp" / "bepinex"
    zip_path = cache_dir / f"{PACKAGE_NAME}-{resolved}.zip"
    extract_dir = cache_dir / f"extract-{resolved}"

    if not zip_path.is_file():
        _download(download_url, zip_path)
    else:
        log.info("使用缓存的压缩包: %s", zip_path)

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    log.info("解压 %s", zip_path.name)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)

    pack_root = _find_pack_root(extract_dir)
    log.info("BepInEx 包根目录: %s", pack_root)
    dest_dir.mkdir(parents=True, exist_ok=True)
    _copy_pack(pack_root, dest_dir, overwrite=force)

    if not has_bepinex(dest_dir):
        raise RuntimeError(f"安装 BepInEx 之后仍不完整: {dest_dir}")
    log.info("BepInEx %s 已装进实例 (未改源安装)", resolved)
