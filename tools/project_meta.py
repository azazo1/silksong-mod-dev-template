# 读 Directory.Build.props 的 Version. 给打包脚本和 scripts/build-version 用.

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


def read_msbuild_property(path: Path, name: str) -> str | None:
    root = ET.parse(path).getroot()
    for group in root.findall("PropertyGroup"):
        node = group.find(name)
        if node is not None and node.text and node.text.strip():
            return node.text.strip()
    return None


def read_package_version(repo_root: Path | None = None) -> str:
    props = (repo_root or ROOT) / "Directory.Build.props"
    version = read_msbuild_property(props, "Version")
    if not version:
        raise RuntimeError(f"{props} 缺少 Version")
    return version


def read_assembly_name(csproj: Path) -> str:
    name = read_msbuild_property(csproj, "AssemblyName")
    if not name:
        name = csproj.stem
    return name


def main() -> int:
    print(read_package_version())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
