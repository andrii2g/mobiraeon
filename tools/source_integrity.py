"""Validate captured present source and declared tracked deletions without mutation."""

import hashlib
from pathlib import PurePosixPath


def source_path(root, name):
    if (
        not isinstance(name, str)
        or not name
        or "\\" in name
        or ":" in name
        or "\x00" in name
        or name != PurePosixPath(name).as_posix()
        or PurePosixPath(name).is_absolute()
        or any(part in {".", "..", ".git"} for part in PurePosixPath(name).parts)
    ):
        raise ValueError("unsafe source path")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("source path escapes root")
    return path


def verify_source(root, manifest):
    deleted = manifest.get("deleted_paths", [])
    if (
        not isinstance(deleted, list)
        or any(not isinstance(n, str) for n in deleted)
        or deleted != sorted(set(deleted))
    ):
        raise ValueError("invalid deleted_paths")
    for name in deleted:
        path = source_path(root, name)
        if name in manifest["files"] or path.exists() or path.is_symlink():
            raise ValueError("declared deletion is present")
    for name, entry in manifest["files"].items():
        data = source_path(root, name).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["bytes"]:
            raise ValueError("captured source differs")
