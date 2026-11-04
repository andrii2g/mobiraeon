"""Verify packaged supervised fixture operations outside the checkout."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


class ExecutionVerificationFailure(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(json.dumps(report))


def decoded(value):
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return (value or "")[:2097152]


def exercise(python, input_file, catalog_input, image_id, *, short=False):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    if sys.platform != "linux":
        return {
            "result": "unavailable",
            "reason": "No native Linux Docker Worker; portable execution tests run in pytest",
        }
    if not image_id:
        raise ExecutionVerificationFailure(
            {
                "result": "failed",
                "failure_type": "image_prerequisite",
                "terminal_available": False,
            }
        )
    with tempfile.TemporaryDirectory(prefix="mobiraeon-execution-outside-") as temporary:
        command = [
            str(python),
            "-m",
            "mobiraeon.execution_verification",
            "--input",
            str(input_file),
            "--catalog-input",
            str(catalog_input),
            "--image-id",
            image_id,
            *(["--short"] if short else []),
        ]
        report = {
            "result": "failed",
            "command": command,
            "exit_code": None,
            "timed_out": False,
            "parse_status": "not_attempted",
        }
        try:
            result = subprocess.run(
                command,
                cwd=temporary,
                env=environment,
                capture_output=True,
                text=True,
                timeout=900,
            )
            report |= {
                "exit_code": result.returncode,
                "stdout": decoded(result.stdout),
                "stderr": decoded(result.stderr),
            }
        except (subprocess.TimeoutExpired, OSError) as error:
            report |= {
                "failure_type": type(error).__name__,
                "timed_out": isinstance(error, subprocess.TimeoutExpired),
                "stdout": decoded(getattr(error, "stdout", None)),
                "stderr": decoded(getattr(error, "stderr", None)),
                "terminal_available": False,
            }
            raise ExecutionVerificationFailure(report) from None
        try:
            report["fixture"] = json.loads(result.stdout)
            report["parse_status"] = "parsed"
        except ValueError, TypeError:
            report |= {
                "parse_status": "invalid_json",
                "failure_type": "child_json_invalid",
                "terminal_available": False,
            }
            raise ExecutionVerificationFailure(report) from None
        # A structured failed child is retained even when its process exits nonzero.
        if (
            result.returncode
            or not isinstance(report["fixture"], dict)
            or report["fixture"].get("result") != "passed"
        ):
            report["failure_type"] = (
                "child_nonzero" if result.returncode else "child_report_failed"
            )
            raise ExecutionVerificationFailure(report)
        report["result"] = "passed"
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-python", default=sys.executable)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--catalog-input", type=Path, required=True)
    parser.add_argument("--image-id")
    parser.add_argument("--short", action="store_true")
    args = parser.parse_args()
    try:
        report = exercise(
            args.target_python,
            args.input.resolve(),
            args.catalog_input.resolve(),
            args.image_id,
            short=args.short,
        )
    except ExecutionVerificationFailure as error:
        report = error.report
    print(json.dumps(report, indent=2))
    return int(report["result"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
