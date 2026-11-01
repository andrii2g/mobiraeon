"""Capture the exact combined checkout, excluding generated submission evidence.

No Git mutation. Tracked files and nonignored untracked files are archived verbatim.
The submission directory is excluded to avoid a self-referential manifest/archive.
"""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "submissions" / "increment-1"
    output.mkdir(parents=True, exist_ok=True)

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
    manifest = {}
    with zipfile.ZipFile(
        output / "source.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name in paths:
            if name.startswith("submissions/"):
                continue
            data = (root / name).read_bytes()
            manifest[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    snapshot_hash = hashlib.sha256((output / "source.zip").read_bytes()).hexdigest()
    report = {
        "base_revision": git("rev-parse", "HEAD").decode().strip(),
        "archive_sha256": snapshot_hash,
        "excludes": ["submissions/", "ignored/generated files"],
        "files": manifest,
    }
    (output / "source-manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"archive_sha256": snapshot_hash, "file_count": len(manifest)}))


if __name__ == "__main__":
    main()
