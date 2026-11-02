"""Verify packaged supervised fixture operations outside the checkout."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def exercise(python, input_file, catalog_input, image_id, *, short=False):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    if sys.platform != "linux":
        return {
            "result": "unavailable",
            "reason": "No native Linux Docker Worker; portable execution tests run in pytest",
        }
    if not image_id:
        raise RuntimeError("prepared fixture image ID required for Linux verification")
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
        result = subprocess.run(
            command, cwd=temporary, env=environment, capture_output=True, text=True, timeout=900
        )
        report = {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        if result.returncode:
            raise RuntimeError(json.dumps(report))
        report["fixture"] = json.loads(result.stdout)
        assert report["fixture"]["result"] == "passed"
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-python", default=sys.executable)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--catalog-input", type=Path, required=True)
    parser.add_argument("--image-id")
    parser.add_argument("--short", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            exercise(
                args.target_python,
                args.input.resolve(),
                args.catalog_input.resolve(),
                args.image_id,
                short=args.short,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
