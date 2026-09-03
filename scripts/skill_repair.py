#!/usr/bin/env python3
"""Verify or restore managed Literary Production Planner Skill files."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Mapping, Optional, Tuple


FORMAT = "literary-production-planner-recovery-baseline"
VERSION = 1
BASELINE_RELATIVE = Path("recovery") / "baseline.zip"
CHECKSUM_RELATIVE = Path("recovery") / "baseline.sha256"
MAX_BASELINE_BYTES = 20 * 1024 * 1024
MAX_CHECKSUM_BYTES = 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_FILE_COUNT = 512
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MANAGED_ROOT_FILES = {
    ".gitattributes",
    ".gitignore",
    "README.md",
    "PORTABILITY.md",
    "SKILL.md",
}
MANAGED_DIRECTORIES = {"agents", "references", "scripts"}


class BaselineError(RuntimeError):
    """The local or supplied recovery baseline cannot be trusted."""


class CollisionError(RuntimeError):
    """A target path is unsafe to replace automatically."""


def default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_existing_directory(value: Path, label: str) -> Path:
    path = value.expanduser().resolve()
    if not path.exists():
        raise RuntimeError("{} does not exist: {}".format(label, path))
    if not path.is_dir():
        raise RuntimeError("{} is not a directory: {}".format(label, path))
    return path


def read_expected_checksum(content: bytes) -> str:
    try:
        decoded = content.decode("ascii")
    except UnicodeDecodeError as error:
        raise BaselineError("baseline.sha256 is not valid ASCII") from error
    match = re.fullmatch(
        r"\s*([0-9a-fA-F]{64})(?:\s+\*?baseline\.zip)?\s*", decoded
    )
    if not match:
        raise BaselineError("baseline.sha256 has an invalid format")
    return match.group(1).lower()


def validate_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError("baseline manifest contains an invalid managed path")
    if "\\" in value:
        raise BaselineError("baseline manifest path uses a backslash: {}".format(value))
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts:
        raise BaselineError("baseline manifest path is not relative: {}".format(value))
    if any(part in ("", ".", "..") for part in path.parts):
        raise BaselineError("baseline manifest path is unsafe: {}".format(value))
    if path.as_posix() != value:
        raise BaselineError("baseline manifest path is not normalized: {}".format(value))
    if path.parts[0] in {".git", "recovery"}:
        raise BaselineError("baseline manifest manages a protected path: {}".format(value))
    if not (
        len(path.parts) == 1 and path.parts[0] in MANAGED_ROOT_FILES
        or len(path.parts) >= 2 and path.parts[0] in MANAGED_DIRECTORIES
    ):
        raise BaselineError("baseline manifest manages an unknown path: {}".format(value))
    return value


def validate_file_metadata(relative: str, metadata: Any) -> Dict[str, Any]:
    if not isinstance(metadata, dict):
        raise BaselineError("manifest metadata is invalid for {}".format(relative))
    digest = metadata.get("sha256")
    size = metadata.get("size")
    mode = metadata.get("mode")
    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest.lower()):
        raise BaselineError("manifest checksum is invalid for {}".format(relative))
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise BaselineError("manifest size is invalid for {}".format(relative))
    if size > MAX_FILE_BYTES:
        raise BaselineError("manifest file is too large: {}".format(relative))
    if mode is not None and (
        isinstance(mode, bool)
        or not isinstance(mode, int)
        or mode < 0
        or mode > 0o7777
    ):
        raise BaselineError("manifest mode is invalid for {}".format(relative))
    return {"sha256": digest.lower(), "size": size, "mode": mode}


def validate_baseline(source_root: Path) -> Dict[str, Any]:
    recovery_directory = source_root / "recovery"
    archive_path = source_root / BASELINE_RELATIVE
    checksum_path = source_root / CHECKSUM_RELATIVE
    if recovery_directory.is_symlink():
        raise BaselineError("recovery must not be a symbolic link")
    if recovery_directory.exists() and not recovery_directory.is_dir():
        raise BaselineError("recovery is not a directory")
    if archive_path.is_symlink() or checksum_path.is_symlink():
        raise BaselineError("recovery anchors must not be symbolic links")
    if not archive_path.is_file() or not checksum_path.is_file():
        raise BaselineError("recovery/baseline.zip or recovery/baseline.sha256 is missing")
    if archive_path.stat().st_size > MAX_BASELINE_BYTES:
        raise BaselineError("recovery baseline is larger than the safety limit")
    if checksum_path.stat().st_size > MAX_CHECKSUM_BYTES:
        raise BaselineError("baseline.sha256 is larger than the safety limit")

    archive_bytes = archive_path.read_bytes()
    checksum_bytes = checksum_path.read_bytes()
    expected_digest = read_expected_checksum(checksum_bytes)
    actual_digest = sha256_bytes(archive_bytes)
    if actual_digest != expected_digest:
        raise BaselineError("baseline.zip does not match baseline.sha256")

    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as error:
        raise BaselineError("baseline.zip is not a valid ZIP archive") from error

    with archive:
        entries = archive.infolist()
        if len(entries) == 0 or len(entries) > MAX_FILE_COUNT + 1:
            raise BaselineError("baseline ZIP has an unsafe number of entries")
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise BaselineError("baseline ZIP contains duplicate entries")
        if "manifest.json" not in names:
            raise BaselineError("baseline ZIP does not contain manifest.json")
        manifest_info = archive.getinfo("manifest.json")
        if manifest_info.file_size > MAX_FILE_BYTES:
            raise BaselineError("baseline manifest exceeds the safety limit")
        try:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
            raise BaselineError("baseline manifest is unreadable") from error

        if not isinstance(manifest, dict):
            raise BaselineError("baseline manifest is not an object")
        if manifest.get("format") != FORMAT or manifest.get("version") != VERSION:
            raise BaselineError("baseline manifest format or version is unsupported")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise BaselineError("baseline manifest has no managed files")
        if len(files) > MAX_FILE_COUNT:
            raise BaselineError("baseline manifest has too many managed files")

        metadata_by_path: Dict[str, Dict[str, Any]] = {}
        for raw_relative, raw_metadata in files.items():
            relative = validate_relative_path(raw_relative)
            metadata_by_path[relative] = validate_file_metadata(relative, raw_metadata)

        expected_names = {"manifest.json"}
        expected_names.update(
            "files/{}".format(relative) for relative in metadata_by_path
        )
        if set(names) != expected_names:
            raise BaselineError("baseline ZIP entries do not match its manifest")

        data_by_path: Dict[str, bytes] = {}
        total_bytes = 0
        for relative in sorted(metadata_by_path):
            archive_name = "files/{}".format(relative)
            info = archive.getinfo(archive_name)
            metadata = metadata_by_path[relative]
            if info.is_dir() or info.file_size != metadata["size"]:
                raise BaselineError("baseline content size mismatch for {}".format(relative))
            total_bytes += info.file_size
            if total_bytes > MAX_BASELINE_BYTES:
                raise BaselineError("baseline content exceeds the safety limit")
            try:
                data = archive.read(archive_name)
            except zipfile.BadZipFile as error:
                raise BaselineError("baseline content is corrupt for {}".format(relative)) from error
            if sha256_bytes(data) != metadata["sha256"]:
                raise BaselineError("baseline content checksum mismatch for {}".format(relative))
            data_by_path[relative] = data

    return {
        "archive_bytes": archive_bytes,
        "checksum_bytes": checksum_bytes,
        "files": metadata_by_path,
        "data": data_by_path,
    }


def target_path_state(
    root: Path, relative: str, expected_size: int, expected_digest: str
) -> Tuple[str, str, Path]:
    candidate = root
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        candidate = candidate / part
        if candidate.is_symlink():
            return "collision", "symbolic link", candidate
        if index < len(parts) - 1:
            if candidate.exists() and not candidate.is_dir():
                return "collision", "parent is not a directory", candidate
        elif candidate.exists():
            if candidate.is_dir():
                return "collision", "path is a directory", candidate
            if not candidate.is_file():
                return "collision", "path is not a regular file", candidate

    if not candidate.exists():
        return "missing", "file is missing", candidate
    if candidate.stat().st_size != expected_size:
        return "modified", "file size differs", candidate
    if sha256_file(candidate) != expected_digest:
        return "modified", "file checksum differs", candidate
    return "healthy", "matches baseline", candidate


def scan_managed_files(target_root: Path, baseline: Mapping[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for relative in sorted(baseline["files"]):
        metadata = baseline["files"][relative]
        state, reason, _ = target_path_state(
            target_root, relative, metadata["size"], metadata["sha256"]
        )
        if state != "healthy":
            findings.append(
                {
                    "kind": "managed",
                    "path": relative,
                    "state": state,
                    "reason": reason,
                }
            )
    return findings


def scan_recovery_anchors(
    target_root: Path, baseline: Mapping[str, Any]
) -> List[Dict[str, str]]:
    anchors = {
        BASELINE_RELATIVE.as_posix(): baseline["archive_bytes"],
        CHECKSUM_RELATIVE.as_posix(): baseline["checksum_bytes"],
    }
    findings: List[Dict[str, str]] = []
    for relative in sorted(anchors):
        content = anchors[relative]
        state, reason, _ = target_path_state(
            target_root, relative, len(content), sha256_bytes(content)
        )
        if state != "healthy":
            findings.append(
                {
                    "kind": "recovery-anchor",
                    "path": relative,
                    "state": state,
                    "reason": reason,
                }
            )
    return findings


def ensure_source_is_healthy(
    source_root: Path, baseline: Mapping[str, Any]
) -> None:
    issues = scan_managed_files(source_root, baseline)
    if issues:
        paths = ", ".join(issue["path"] for issue in issues)
        raise BaselineError(
            "trusted source installation does not match its recovery baseline: {}".format(
                paths
            )
        )


def timestamped_backup_directory(target_root: Path) -> Path:
    recovery_directory = target_root / "recovery"
    if recovery_directory.is_symlink():
        raise CollisionError("recovery is a symbolic link")
    if recovery_directory.exists() and not recovery_directory.is_dir():
        raise CollisionError("recovery is not a directory")
    backup_parent = target_root / "recovery" / "backups"
    if backup_parent.is_symlink():
        raise CollisionError("recovery/backups is a symbolic link")
    if backup_parent.exists() and not backup_parent.is_dir():
        raise CollisionError("recovery/backups is not a directory")
    recovery_directory.mkdir(parents=True, exist_ok=True)
    backup_parent.mkdir(parents=True, exist_ok=True)
    base_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = backup_parent / base_name
    suffix = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = backup_parent / "{}-{:02d}".format(base_name, suffix)
        suffix += 1
    candidate.mkdir()
    return candidate


def write_atomically(destination: Path, content: bytes, mode: Optional[int] = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".skill-repair-", dir=str(destination.parent)
    )
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary_name, mode)
        os.replace(temporary_name, str(destination))
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def backup_existing_files(
    target_root: Path, findings: List[Dict[str, str]], source_root: Path
) -> Path:
    backup_root = timestamped_backup_directory(target_root)
    backed_up: List[str] = []
    for finding in findings:
        if finding["state"] != "modified":
            continue
        source_path = target_root / PurePosixPath(finding["path"])
        destination_path = backup_root / PurePosixPath(finding["path"])
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source_path), str(destination_path), follow_symlinks=False)
        backed_up.append(finding["path"])
    record = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "changed_paths": [finding["path"] for finding in findings],
        "backed_up_paths": backed_up,
    }
    write_atomically(
        backup_root / "repair.json",
        (json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    return backup_root


def ensure_safe_parent(target_root: Path, relative: str) -> Path:
    candidate = target_root
    parts = PurePosixPath(relative).parts
    for part in parts[:-1]:
        candidate = candidate / part
        if candidate.is_symlink():
            raise CollisionError("{} is a symbolic link".format(candidate))
        if candidate.exists() and not candidate.is_dir():
            raise CollisionError("{} is not a directory".format(candidate))
        if not candidate.exists():
            candidate.mkdir()
    return target_root / PurePosixPath(relative)


def repair(
    target_root: Path,
    source_root: Path,
    baseline: Mapping[str, Any],
    dry_run: bool,
) -> Dict[str, Any]:
    findings = scan_managed_files(target_root, baseline)
    if target_root != source_root:
        findings.extend(scan_recovery_anchors(target_root, baseline))
    collisions = [finding for finding in findings if finding["state"] == "collision"]
    if collisions:
        raise CollisionError(
            "automatic repair stopped because one or more target paths are unsafe"
        )
    if not findings:
        return {"status": "healthy", "changed": [], "backup": None}
    if dry_run:
        return {"status": "dry-run", "changed": findings, "backup": None}

    for finding in findings:
        ensure_safe_parent(target_root, finding["path"])
    backup_root = backup_existing_files(target_root, findings, source_root)

    for finding in findings:
        relative = finding["path"]
        destination = ensure_safe_parent(target_root, relative)
        if finding["kind"] == "managed":
            metadata = baseline["files"][relative]
            mode = metadata.get("mode")
            write_atomically(destination, baseline["data"][relative], mode)
        elif relative == BASELINE_RELATIVE.as_posix():
            write_atomically(destination, baseline["archive_bytes"])
        elif relative == CHECKSUM_RELATIVE.as_posix():
            write_atomically(destination, baseline["checksum_bytes"])
        else:
            raise RuntimeError("Unexpected repair path: {}".format(relative))

    remaining = scan_managed_files(target_root, baseline)
    if target_root != source_root:
        remaining.extend(scan_recovery_anchors(target_root, baseline))
    if remaining:
        paths = ", ".join(issue["path"] for issue in remaining)
        raise RuntimeError("post-repair verification failed: {}".format(paths))

    return {
        "status": "repaired",
        "changed": findings,
        "backup": str(backup_root),
        "verified": True,
    }


def verification_result(target_root: Path) -> Dict[str, Any]:
    try:
        baseline = validate_baseline(target_root)
    except BaselineError as error:
        return {
            "status": "baseline invalid",
            "target": str(target_root),
            "error": str(error),
            "issues": [],
        }
    issues = scan_managed_files(target_root, baseline)
    return {
        "status": "healthy" if not issues else "degraded",
        "target": str(target_root),
        "managed_file_count": len(baseline["files"]),
        "issues": issues,
    }


def print_result(result: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    print("Status: {}".format(result["status"]))
    if result.get("target"):
        print("Target: {}".format(result["target"]))
    if result.get("managed_file_count") is not None:
        print("Managed files: {}".format(result["managed_file_count"]))
    if result.get("error"):
        print("Reason: {}".format(result["error"]))
    issues = result.get("issues") or result.get("changed") or []
    for issue in issues:
        print(
            "- [{state}] {path}: {reason}".format(
                state=issue.get("state", "changed"),
                path=issue["path"],
                reason=issue.get("reason", "will be restored"),
            )
        )
    if result.get("backup"):
        print("Backup: {}".format(result["backup"]))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify or repair managed Literary Production Planner Skill files."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    verify_parser = subcommands.add_parser("verify", help="Check the installed Skill.")
    verify_parser.add_argument("--target", type=Path, default=default_root())
    verify_parser.add_argument("--json", action="store_true")

    repair_parser = subcommands.add_parser("repair", help="Restore managed Skill files.")
    repair_parser.add_argument("--target", type=Path, default=default_root())
    repair_parser.add_argument(
        "--source",
        type=Path,
        help="Trusted clean Skill directory used as the recovery source.",
    )
    repair_parser.add_argument("--dry-run", action="store_true")
    repair_parser.add_argument("--json", action="store_true")

    arguments = parser.parse_args()
    try:
        target_root = resolve_existing_directory(arguments.target, "target")
        if arguments.command == "verify":
            result = verification_result(target_root)
            print_result(result, arguments.json)
            return 0 if result["status"] == "healthy" else 1 if result["status"] == "degraded" else 2

        source_root = (
            resolve_existing_directory(arguments.source, "source")
            if arguments.source
            else target_root
        )
        baseline = validate_baseline(source_root)
        if source_root != target_root:
            ensure_source_is_healthy(source_root, baseline)
        result = repair(target_root, source_root, baseline, arguments.dry_run)
        result["target"] = str(target_root)
        result["source"] = str(source_root)
        result["managed_file_count"] = len(baseline["files"])
        print_result(result, arguments.json)
        return 0
    except BaselineError as error:
        result = {"status": "baseline invalid", "error": str(error)}
        print_result(result, getattr(arguments, "json", False))
        return 2
    except CollisionError as error:
        result = {"status": "repair blocked", "error": str(error)}
        print_result(result, getattr(arguments, "json", False))
        return 3
    except (OSError, RuntimeError, ValueError) as error:
        result = {"status": "repair failed", "error": str(error)}
        print_result(result, getattr(arguments, "json", False))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
