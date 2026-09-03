#!/usr/bin/env python3
"""Build a recovery baseline from a reviewed, known-good Skill release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, Tuple


FORMAT = "literary-production-planner-recovery-baseline"
VERSION = 1
BASELINE_RELATIVE = Path("recovery") / "baseline.zip"
CHECKSUM_RELATIVE = Path("recovery") / "baseline.sha256"
EXCLUDED_TOP_LEVEL = {".git", "recovery"}
EXCLUDED_FILE_NAMES = {".DS_Store", "Thumbs.db"}
MANAGED_ROOT_FILES = {
    ".gitattributes",
    ".gitignore",
    "README.md",
    "PORTABILITY.md",
    "SKILL.md",
}
MANAGED_DIRECTORIES = {"agents", "references", "scripts"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_relative(root: Path, file_path: Path) -> str:
    return file_path.relative_to(root).as_posix()


def is_excluded(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    if not parts:
        return True
    if parts[0] in EXCLUDED_TOP_LEVEL:
        return True
    if "__pycache__" in parts:
        return True
    if parts[-1] in EXCLUDED_FILE_NAMES:
        return True
    return parts[-1].endswith((".pyc", ".pyo"))


def is_managed(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    return (
        len(parts) == 1 and parts[0] in MANAGED_ROOT_FILES
    ) or (
        len(parts) >= 2 and parts[0] in MANAGED_DIRECTORIES
    )


def iter_managed_files(root: Path) -> Iterable[Tuple[str, Path]]:
    for file_path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = normalized_relative(root, file_path)
        if is_excluded(relative) or not is_managed(relative):
            continue
        if file_path.is_symlink():
            raise RuntimeError(
                "Refusing to baseline a symbolic link: {}".format(relative)
            )
        if file_path.is_file():
            yield relative, file_path


def write_atomically(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".recovery-", dir=str(destination.parent)
    )
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, str(destination))
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def build(root: Path) -> Tuple[int, Path]:
    root = root.resolve()
    if not (root / "SKILL.md").is_file():
        raise RuntimeError("SKILL.md was not found under {}".format(root))
    recovery_directory = root / "recovery"
    if recovery_directory.is_symlink():
        raise RuntimeError("recovery must not be a symbolic link")
    if recovery_directory.exists() and not recovery_directory.is_dir():
        raise RuntimeError("recovery is not a directory")

    records: Dict[str, Dict[str, object]] = {}
    file_data: Dict[str, bytes] = {}
    for relative, file_path in iter_managed_files(root):
        data = file_path.read_bytes()
        records[relative] = {
            "sha256": sha256_bytes(data),
            "size": len(data),
            "mode": stat.S_IMODE(file_path.stat().st_mode),
        }
        file_data[relative] = data

    if not records:
        raise RuntimeError("No managed files were found.")

    manifest = {
        "format": FORMAT,
        "version": VERSION,
        "files": records,
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    recovery_directory.mkdir(parents=True, exist_ok=True)
    destination = root / BASELINE_RELATIVE
    handle, temporary_name = tempfile.mkstemp(
        prefix=".baseline-", suffix=".zip", dir=str(recovery_directory)
    )
    os.close(handle)
    try:
        with zipfile.ZipFile(
            temporary_name,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            archive.writestr("manifest.json", manifest_bytes)
            for relative in sorted(file_data):
                info = zipfile.ZipInfo("files/{}".format(relative))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (records[relative]["mode"] & 0xFFFF) << 16
                archive.writestr(info, file_data[relative])
        os.replace(temporary_name, str(destination))
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

    checksum_content = "{}  baseline.zip\n".format(
        sha256_bytes(destination.read_bytes())
    ).encode("ascii")
    write_atomically(root / CHECKSUM_RELATIVE, checksum_content)
    return len(records), destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a recovery baseline from a known-good Skill release."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Skill directory to baseline. Defaults to this script's parent Skill directory.",
    )
    arguments = parser.parse_args()
    try:
        file_count, destination = build(arguments.root)
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        print("Baseline build failed: {}".format(error))
        return 1
    print("Created {} from {} managed files.".format(destination, file_count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
