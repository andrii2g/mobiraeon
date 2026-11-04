"""Capture the exact combined checkout, excluding generated submission evidence.

No Git mutation. Tracked files and nonignored untracked files are archived verbatim.
The submission directory is excluded to avoid a self-referential manifest/archive.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from source_integrity import source_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--increment",
        choices=["increment-1", "increment-2", "increment-3", "increment-4", "increment-5"],
        default="increment-2",
    )
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = (args.output_directory or root / "submissions" / args.increment).resolve()
    if not output.is_relative_to(root / "submissions") or output == root / "submissions":
        parser.error("output directory must be inside submissions")
    output.mkdir(parents=True, exist_ok=True)
    if (output / "source-manifest.json").exists():
        preserved = output / "archive" / datetime.now(UTC).strftime("capture-%Y%m%dT%H%M%S%fZ")
        preserved.mkdir(parents=True)
        for previous in output.iterdir():
            if previous.is_file() and not previous.name.startswith("starting-"):
                shutil.move(str(previous), str(preserved / previous.name))

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    paths = sorted(
        set(
            git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
            .decode()
            .split("\0")
        )
        - {""}
    )
    tracked = set(git("ls-tree", "-r", "--name-only", "-z", "HEAD").decode().split("\0"))
    tracked.update(git("ls-files", "--cached", "-z").decode().split("\0"))
    paths = sorted(set(paths) | (tracked - {""}))
    manifest, deleted = {}, []
    pending = output / "source.zip.pending"
    try:
        with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in paths:
                if name.startswith("submissions/"):
                    continue
                path = source_path(root, name)
                try:
                    data = path.read_bytes()
                except FileNotFoundError:
                    if name not in tracked or path.is_symlink():
                        raise
                    deleted.append(name)
                    continue
                if path.suffix.lower() in {".pem", ".key", ".token", ".sqlite", ".db"}:
                    raise RuntimeError("private input must not enter source capture")
                if re.search(rb"mbr_[a-f0-9]{32}_[A-Za-z0-9_-]{43}", data) or re.search(
                    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", data
                ):
                    raise RuntimeError("private material must not enter source capture")
                manifest[name] = {
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                }
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        pending.replace(output / "source.zip")
    finally:
        pending.unlink(missing_ok=True)
    snapshot_hash = hashlib.sha256((output / "source.zip").read_bytes()).hexdigest()
    report = {
        "base_revision": git("rev-parse", "HEAD").decode().strip(),
        "archive_sha256": snapshot_hash,
        "excludes": ["submissions/", "ignored/generated files"],
        "files": manifest,
        "deleted_paths": sorted(deleted),
        "captured_git_status": git("status", "--short").decode(),
        "starting_state": (
            json.loads((output / "starting-state.json").read_text(encoding="utf-8-sig"))
            if (output / "starting-state.json").exists()
            else None
        ),
    }
    (output / "source-manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"archive_sha256": snapshot_hash, "file_count": len(manifest)}))


if __name__ == "__main__":
    main()
