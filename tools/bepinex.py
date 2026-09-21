from __future__ import annotations

import json
import re
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
CONFIG_RELATIVE = Path("BepInEx") / "config" / "BepInEx.cfg"

_SECTION_RE = re.compile(r"^\[(.+)]\s*$")
_KEY_RE = re.compile(r"^(\s*)([^=#;]+?)(\s*=\s*)(\S+)(.*)$")


def has_bepinex(game_dir: Path) -> bool:
    return (game_dir / CORE_DLL_RELATIVE).is_file() and (game_dir / DOORSTOP_DLL_NAME).is_file()


def _set_ini_value(text: str, section: str, key: str, value: str) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    ended_with_newline = text.endswith("\n")
    lines = text.splitlines()
    section_header = f"[{section}]"

    starts: list[int] = []
    headers: list[str] = []
    for index, line in enumerate(lines):
        match = _SECTION_RE.match(line.strip())
        if match:
            starts.append(index)
            headers.append(f"[{match.group(1)}]")

    section_index = next(
        (index for index, header in enumerate(headers) if header == section_header),
        None,
    )
    if section_index is None:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.extend([section_header, f"{key} = {value}"])
    else:
        start = starts[section_index]
        end = starts[section_index + 1] if section_index + 1 < len(starts) else len(lines)
        key_line: int | None = None
        for index in range(start + 1, end):
            stripped = lines[index].strip()
            if not stripped or stripped.startswith("#") or stripped.startswith(";"):
                continue
            match = _KEY_RE.match(lines[index])
            if match and match.group(2).strip() == key:
                key_line = index
                break
        if key_line is not None:
            current = _KEY_RE.match(lines[key_line])
            if current is None:
                lines[key_line] = f"{key} = {value}"
            elif current.group(4).lower() == value.lower():
                return text
            else:
                # 只换等号后面的值, 缩进, 空格和行尾注释原样留下.
                lines[key_line] = (
                    f"{current.group(1)}{current.group(2)}{current.group(3)}"
                    f"{value}{current.group(5)}"
                )
        else:
            insert_at = end
            while insert_at > start + 1 and lines[insert_at - 1].strip() == "":
                insert_at -= 1
            lines.insert(insert_at, f"{key} = {value}")

    result = newline.join(lines)
    if ended_with_newline or not text:
        result += newline
    return result


def enable_console_logging(game_dir: Path) -> None:
    # 只改 [Logging.Console] Enabled, 不动其它段.
    config_path = game_dir / CONFIG_RELATIVE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.is_file():
        config_path.write_text("[Logging.Console]\nEnabled = true\n", encoding="utf-8")
        log.info("已写入 BepInEx 控制台开关: %s", config_path)
        return

    original = config_path.read_text(encoding="utf-8-sig")
    updated = _set_ini_value(original, "Logging.Console", "Enabled", "true")
    if updated == original:
        log.info("BepInEx 控制台已启用: %s", config_path)
        return

    config_path.write_text(updated, encoding="utf-8")
    log.info("已启用 BepInEx 控制台: %s", config_path)


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
