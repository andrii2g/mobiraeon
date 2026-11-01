"""Record performed checks for the exact captured developer submission."""

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", default="uv")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "submissions" / "increment-1"
    uv = str(Path(args.uv).resolve()) if Path(args.uv).is_file() else args.uv
    subprocess.run([sys.executable, str(root / "tools/capture_submission.py")], check=True)
    manifest = json.loads((output / "source-manifest.json").read_text(encoding="utf-8"))
    reviewed_manifest = output / "archive/reviewed-49d811ca/source-manifest.json"
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    report = {
        "started_utc": datetime.now(UTC).isoformat(),
        "source_archive_sha256": manifest["archive_sha256"],
        "base_revision": manifest["base_revision"],
        "platform": platform.platform(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "uv": subprocess.check_output([uv, "--version"], text=True).strip(),
        "packages": {d.metadata["Name"]: d.version for d in distributions()},
        "configuration": "Temporary disk databases; no application settings inherited.",
        "checks": [],
        "reviewed_source_archive_sha256": (
            json.loads(reviewed_manifest.read_text(encoding="utf-8"))["archive_sha256"]
            if reviewed_manifest.exists()
            else None
        ),
    }
    commands = [
        [uv, "sync", "--locked"],
        [uv, "run", "--locked", "pytest"],
        [uv, "run", "--locked", "ruff", "check", "."],
        [uv, "run", "--locked", "ruff", "format", "--check", "."],
        [uv, "build"],
        [uv, "run", "--locked", "python", str(root / "tools/verify_wheel.py"), "--uv", uv],
        [
            uv,
            "run",
            "--locked",
            "python",
            str(root / "tools/verify_interruptions.py"),
            "--output",
            str(output / "native-windows-interruption.json"),
        ],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )
        report["checks"].append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        print(json.dumps({"command": command[1:], "exit_code": result.returncode}), flush=True)
        (output / "verification.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    for name, entry in manifest["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == entry["sha256"], name
    report["source_unchanged_after_checks"] = True
    report["artifacts"] = {
        file.name: hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted((root / "dist").iterdir())
        if file.is_file()
    }
    report["finished_utc"] = datetime.now(UTC).isoformat()
    (output / "verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return int(any(check["exit_code"] for check in report["checks"]))


if __name__ == "__main__":
    raise SystemExit(main())
