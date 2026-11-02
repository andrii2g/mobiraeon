"""Reproduce checks on an extracted captured source, without requiring Git.

Pass the original source manifest and an external output location. This is used
for Linux/WSL verification of the exact Windows-captured source archive.
"""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-image-id")
    parser.add_argument("--uv", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(options.manifest.read_text(encoding="utf-8"))

    def verify_source():
        for name, entry in manifest["files"].items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == entry["sha256"], (
                name
            )

    verify_source()
    uv = str(Path(options.uv).resolve())
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    report = {
        "source_archive_sha256": manifest["archive_sha256"],
        "base_revision": manifest["base_revision"],
        "started_utc": datetime.now(UTC).isoformat(),
        "configuration": "Extracted source; temporary SQLite disk databases outside checkout.",
        "checks": [],
    }
    commands = [
        [uv, "sync", "--locked"],
        [uv, "run", "--locked", "pytest"],
        [uv, "run", "--locked", "ruff", "check", "."],
        [uv, "run", "--locked", "ruff", "format", "--check", "."],
        [uv, "build"],
        [uv, "run", "--locked", "python", str(root / "tools/verify_wheel.py"), "--uv", uv],
        [uv, "run", "--locked", "python", str(root / "tools/verify_interruptions.py")],
        [
            uv,
            "run",
            "--locked",
            "python",
            "-c",
            """
import json, platform, sqlite3
from importlib.metadata import distributions
print(json.dumps({"platform": platform.platform(), "python": platform.python_version(),
    "sqlite": sqlite3.sqlite_version,
    "packages": {d.metadata["Name"]: d.version for d in distributions()}}))
""",
        ],
        [uv, "--version"],
    ]
    commands.append(
        [uv, "run", "--locked", "python", str(root / "tools/verify_interruptions.py"), "--api"]
    )
    commands.append(
        [
            uv,
            "run",
            "--locked",
            "python",
            str(root / "tools/verify_coordination.py"),
            "--input",
            str(root / "examples/coordination.json"),
            "--catalog-input",
            str(root / "bootstrap/initial-test.json"),
        ]
    )
    commands.append(
        [
            uv,
            "run",
            "--locked",
            "python",
            str(root / "tools/verify_registry.py"),
            "--input",
            str(root / "bootstrap/initial-test.json"),
        ]
    )
    if options.fixture_image_id:
        for command in commands:
            if any(str(part).endswith("verify_wheel.py") for part in command):
                command.extend(["--fixture-image-id", options.fixture_image_id])
    commands.append(
        [
            uv,
            "run",
            "--locked",
            "python",
            str(root / "tools/verify_execution.py"),
            "--input",
            str(root / "examples/execution.json"),
            "--catalog-input",
            str(root / "bootstrap/initial-test.json"),
            *(["--image-id", options.fixture_image_id] if options.fixture_image_id else []),
        ]
    )
    for command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=1200,
            )
        except (subprocess.TimeoutExpired, OSError) as error:

            def decoded(value):
                return (
                    value.decode(errors="replace") if isinstance(value, bytes) else value or ""
                )

            result = subprocess.CompletedProcess(
                command,
                -1,
                decoded(getattr(error, "stdout", "")),
                decoded(getattr(error, "stderr", ""))
                + "\nEnvironment limitation: "
                + type(error).__name__,
            )
        report["checks"].append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        options.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"command": command[1:], "exit_code": result.returncode}), flush=True)
    verify_source()
    report["source_unchanged_after_checks"] = True
    report["artifacts"] = {
        file.name: hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted((root / "dist").glob("mobiraeon-*"))
    }
    report["finished_utc"] = datetime.now(UTC).isoformat()
    options.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return int(any(check["exit_code"] for check in report["checks"]))


if __name__ == "__main__":
    raise SystemExit(main())
