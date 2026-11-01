"""Prepare the approved persistent initial test catalog using normal installed CLI operations.

Creates local application administrator access only, never provider credentials.
Private state must be outside the checkout; raw application tokens are never read here.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = args.input.resolve()
    private = args.state_dir.resolve()
    private.parent.mkdir(parents=True, exist_ok=True)
    commands = []
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="mobiraeon-initial-catalog-") as temporary:
        outside = Path(temporary)
        config = outside / "settings.toml"
        config.write_text(f"""[database]
path = {json.dumps(str(private / "catalog.db"))}
[access]
private_dir = {json.dumps(str(private))}
credential_file = {json.dumps(str(private / "credentials/owner.token"))}
[api]
enabled = false
""")
        base = [str(args.python), "-m", "mobiraeon", "--config", str(config)]

        def run(*arguments):
            command = [*base, *map(str, arguments)]
            result = subprocess.run(
                command,
                cwd=outside,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
            commands.append(
                {
                    "command": command,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
            if result.returncode:
                raise RuntimeError(
                    "catalog operation failed; inspect safe output and reconcile before retry"
                )
            return json.loads(result.stdout)

        existed = private.exists()
        if not existed:
            run("provision")
            run("initialize")
            setup = package.parent / "owner-setup.example.json"
            run("--request-file", setup, "setup")
            # A deliberately partial normal preparation establishes real resume evidence.
            partial = json.loads(package.read_text(encoding="utf-8"))
            partial["definitions"] = partial["definitions"][:4]
            partial_path = outside / "partial-input.json"
            partial_path.write_text(json.dumps(partial), encoding="utf-8")
            run("--input-file", partial_path, "prepare")
        first = run("--input-file", package, "prepare")["data"]["records"][0]
        second = run("--input-file", package, "prepare")["data"]["records"][0]
        assert first == second
        controls = []
        for agent in (x for x in first["publications"] if x["kind"] == "agent"):
            request = outside / "read.json"
            request.write_text(
                json.dumps(
                    {
                        "operation": "registry.read",
                        "target": {
                            "kind": "control",
                            "entity_kind": "agent",
                            "identity": agent["identity"],
                        },
                        "inputs": {},
                    }
                )
            )
            record = run("--request-file", request, "registry")["data"]["records"][0]
            assert record["enabled"] is False and record["selected"] == agent["revision"]
            controls.append(record)
        assert len(controls) == 5
        installed = subprocess.check_output(
            [
                str(args.python),
                "-c",
                "import json,platform,sqlite3,mobiraeon; "
                "print(json.dumps({'module':mobiraeon.__file__,'python':platform.python_version(),"
                "'platform':platform.platform(),'sqlite':sqlite3.sqlite_version}))",
            ],
            cwd=outside,
            env=environment,
            text=True,
        )
        report = {
            "source_archive_sha256": args.snapshot,
            "input_sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
            "state_directory": str(private),
            "configuration": "initial_test",
            "external_dependencies": "unprovisioned_unverified",
            "resumed_from_partial_in_this_run": not existed,
            "repeat_identical": True,
            "catalog": first,
            "controls": controls,
            "commands": commands,
            "installed_environment": json.loads(installed),
            "qualification": "not established; "
            "execution/provider calls/enablement not authorized",
        }
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        # Persist only nonsecret settings for later owner use. No raw token is read.
        if not existed:
            from mobiraeon.private_state import durable_new

            durable_new(private / "settings.toml", config.read_bytes())
    print(
        json.dumps(
            {"result": "prepared_disabled", "agents": len(controls), "output": str(args.output)}
        )
    )


if __name__ == "__main__":
    main()
