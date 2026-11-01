"""Exercise explicit scenario inputs in fresh processes, including installed wheels."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def exercise(python, scenario_input, catalog_input):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    checks = []
    with tempfile.TemporaryDirectory(prefix="mobiraeon-coordination-") as temporary:
        outside = Path(temporary)
        directory = outside / "private"
        base = [str(python), "-m", "mobiraeon.scenario"]

        def run(*args):
            command = base + list(map(str, args))
            result = subprocess.run(
                command,
                cwd=outside,
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
            )
            checks.append(
                {
                    "command": command,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout)

        produced = run(
            "run",
            "--directory",
            directory,
            "--input",
            scenario_input,
            "--catalog-input",
            catalog_input,
        )
        reloaded = run("status", "--directory", directory)
        assert reloaded["outcome"] == "success"
        status = reloaded["data"]["records"][0]
        assert status == produced["status"]
        assert status["version"] == 7 and status["state"] == "accepted"
        assert status["request_state"] == "open"
        assert status["initiative_acceptance"] == "unaccepted"
        assert status["unresolved"] is False
        assert len(status["facts"]) == 7
        assert len(status["history"]) == 7
        assert len(produced["actual_agents"]) == 5
        assert all(agent["enabled"] == 0 for agent in produced["actual_agents"])
        # Ordinary CLI read uses established authentication, not scenario identity injection.
        config = outside / "settings.toml"
        config.write_text(
            "[database]\npath="
            + json.dumps(str(directory / "scenario.db"))
            + "\n[access]\nprivate_dir="
            + json.dumps(str(directory))
            + "\ncredential_file="
            + json.dumps(str(directory / "credentials/assessor.token"))
            + "\n",
            encoding="utf-8",
        )
        request = outside / "status.json"
        request.write_text(
            json.dumps(
                {
                    "operation": "coordination.status",
                    "target": {"kind": "entity", "entity_kind": "task", "identity": "task-1"},
                    "inputs": {},
                }
            )
        )
        command = [
            str(python),
            "-m",
            "mobiraeon",
            "--config",
            str(config),
            "--request-file",
            str(request),
            "coordination",
        ]
        result = subprocess.run(
            command, cwd=outside, env=environment, capture_output=True, text=True, timeout=30
        )
        checks.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        assert result.returncode == 0, result.stderr
        ordinary_status = json.loads(result.stdout)["data"]["records"][0]
        assert {k: v for k, v in ordinary_status.items() if k != "current_authority"} == {
            k: v for k, v in status.items() if k != "current_authority"
        }
        assert (
            ordinary_status["current_authority"]["actor"]
            != status["current_authority"]["actor"]
        )
        return {
            "result": "passed",
            "input_sha256": produced["input_sha256"],
            "catalog_input_sha256": produced["catalog_input_sha256"],
            "checks": checks,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-python", default=sys.executable)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--catalog-input", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            exercise(args.target_python, args.input.resolve(), args.catalog_input.resolve()),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
