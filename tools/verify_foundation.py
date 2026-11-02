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

from source_integrity import verify_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-image-id")
    parser.add_argument("--uv", default="uv")
    parser.add_argument(
        "--increment",
        choices=["increment-1", "increment-2", "increment-3", "increment-4"],
        default="increment-2",
    )
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = (args.output_directory or root / "submissions" / args.increment).resolve()
    if not output.is_relative_to(root / "submissions") or output == root / "submissions":
        parser.error("output directory must be inside submissions")
    uv = str(Path(args.uv).resolve()) if Path(args.uv).is_file() else args.uv
    subprocess.run(
        [
            sys.executable,
            str(root / "tools/capture_submission.py"),
            "--increment",
            args.increment,
            "--output-directory",
            str(output),
        ],
        check=True,
    )
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
    commands.append(
        [
            uv,
            "run",
            "--locked",
            "python",
            str(root / "tools/verify_interruptions.py"),
            "--api",
            "--output",
            str(output / "native-windows-api-interruption.json"),
        ]
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
    if args.fixture_image_id:
        for command in commands:
            if any(str(part).endswith("verify_wheel.py") for part in command):
                command.extend(["--fixture-image-id", args.fixture_image_id])
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
            *(["--image-id", args.fixture_image_id] if args.fixture_image_id else []),
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
        print(json.dumps({"command": command[1:], "exit_code": result.returncode}), flush=True)
        (output / "verification.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    verify_source(root, manifest)
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
