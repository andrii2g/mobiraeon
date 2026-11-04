"""Source or installed runtime-only forge verification with exact source attribution."""

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from source_integrity import verify_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-gitea",
        action="store_true",
        help="Require isolated actual Gitea 28.2.0 Linux Docker qualification",
    )
    parser.add_argument(
        "--target-python",
        type=Path,
        default=Path(sys.executable),
        help="Clean installed interpreter; default current interpreter",
    )
    parser.add_argument("--docker-executable", default="docker")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--manifest", type=Path, help="Original frozen source manifest; verify before and after"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(args.manifest.read_text()) if args.manifest else None
    if manifest:
        verify_source(root, manifest)
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    report = {
        "started_utc": datetime.now(UTC).isoformat(),
        "source_archive_sha256": manifest["archive_sha256"] if manifest else None,
        "qualification": "real-gitea" if args.real_gitea else "loopback",
    }
    code = (
        "from mobiraeon.forge_gitea_verification import exercise; "
        f"print(json.dumps(exercise({args.docker_executable!r})))"
        if args.real_gitea
        else "from mobiraeon.forge_verification import exercise; print(json.dumps(exercise()))"
    )
    import tempfile

    with tempfile.TemporaryDirectory(prefix="mobiraeon-forge-driver-") as outside:
        try:
            command = [str(args.target_python.absolute()), "-c", "import json; " + code]
            result = subprocess.run(
                command,
                cwd=outside,
                env=environment,
                capture_output=True,
                text=True,
                timeout=240,
            )
            report |= {"command": command, "exit_code": result.returncode}
            if result.returncode == 0:
                report["report"] = json.loads(result.stdout)
                report["result"] = report["report"]["result"]
            else:
                report |= {
                    "result": "failed",
                    "limitation": "Target verification process failed",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            report |= {"result": "failed", "failure_type": type(error).__name__}
    if manifest:
        verify_source(root, manifest)
        report["source_unchanged_before_and_after"] = True
    report["finished_utc"] = datetime.now(UTC).isoformat()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return int(report["result"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
