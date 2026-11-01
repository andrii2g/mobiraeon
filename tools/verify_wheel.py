"""Clean, noneditable wheel verification outside the checkout.

Run with `uv run --locked python tools/verify_wheel.py --uv <uv executable>`.
Uses runtime constraints exported from the unchanged project lock.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", default="uv")
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    uv = str(Path(options.uv).resolve()) if Path(options.uv).is_file() else options.uv
    (wheel,) = (root / "dist").glob("mobiraeon-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        assert "mobiraeon/persistence/migrations/env.py" in archive.namelist()
        assert (
            "mobiraeon/persistence/migrations/versions/0001_identity.py" in archive.namelist()
        )
        assert (
            "mobiraeon/persistence/migrations/versions/0002_registry.py" in archive.namelist()
        )
        assert (
            "mobiraeon/persistence/migrations/versions/0003_coordination.py"
            in archive.namelist()
        )
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="mobiraeon-wheel-") as temporary:
        outside = Path(temporary)

        def run(*args, cwd=outside):
            result = subprocess.run(
                list(map(str, args)),
                cwd=cwd,
                env=environment,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode:
                raise RuntimeError(
                    f"wheel verification failed: {result.stdout}\n{result.stderr}"
                )
            return result.stdout

        constraints = run(
            uv, "export", "--locked", "--no-dev", "--no-emit-project", "--no-hashes", cwd=root
        )
        (outside / "constraints.txt").write_text(constraints, encoding="utf-8")
        # Exercise actual packaged migration resources beneath a literal percent path.
        installed = outside / "100%valid" / "venv"
        run(uv, "venv", "--python", sys.executable, installed)
        bin_path = installed / ("Scripts" if os.name == "nt" else "bin")
        python = bin_path / ("python.exe" if os.name == "nt" else "python")
        console = bin_path / ("mobiraeon.exe" if os.name == "nt" else "mobiraeon")
        run(
            uv,
            "pip",
            "install",
            "--python",
            python,
            "--constraint",
            outside / "constraints.txt",
            wheel,
        )
        metadata = json.loads(
            run(
                python,
                "-c",
                """
import json, platform, sqlite3, mobiraeon
from importlib.metadata import version
print(json.dumps({"module": mobiraeon.__file__, "python": platform.python_version(),
    "sqlite": sqlite3.sqlite_version, "dependencies": {
    name: version(name) for name in ("mobiraeon", "SQLAlchemy", "alembic")}}))
""",
            )
        )
        assert str(root).lower() not in metadata["module"].lower()
        database = outside / "wheel.sqlite3"
        assert run(console, "--version").strip() == "0.1.0"
        run(python, "-m", "mobiraeon", "--help")
        for command in ("initialize", "initialize", "upgrade", "check"):
            result = json.loads(run(console, "--database", database, command))
            assert result["outcome"] == "success"
            assert result["schema_revision"] == "0003"
        # The real installed foreground host; a fixture event supplies stop.
        host_output = run(
            python,
            "-c",
            """
import threading
from mobiraeon import cli
stop = threading.Event()
serve = cli.serve
cli.serve = lambda: serve(stop)
threading.Timer(0.5, stop.set).start()
raise SystemExit(cli.main())
""",
            "--database",
            database,
            "start",
        )
        started, stopped = [json.loads(line) for line in host_output.splitlines()]
        assert started["foundation_ready"] is True
        assert started["phase"] == "ready"
        assert stopped["phase"] == "terminal" and stopped["outcome"] == "success"
        assert stopped["foundation_ready"] is False
        assert (
            started["capabilities"]["registry_business_operations"]
            == "authenticated_administration"
        )
        assert started["capabilities"]["agent_execution"] == "unavailable"
        assert started["capabilities"]["forge_integration"] == "unavailable"
        assert (
            started["capabilities"]["coordination_workflows"]
            == "local_simulated_task_acceptance"
        )
        run(console, "--database", database, "check")
        from verify_registry import exercise

        registry = exercise(python, root / "bootstrap/initial-test.json")
        from verify_coordination import exercise as coordination_exercise

        coordination = coordination_exercise(
            python, root / "examples/coordination.json", root / "bootstrap/initial-test.json"
        )
        interruptions = [
            json.loads(
                run(
                    sys.executable,
                    root / "tools/verify_interruptions.py",
                    "--target-python",
                    python,
                    *extra,
                )
            )
            for extra in ((), ("--api",))
        ]
        print(
            json.dumps(
                {
                    "result": "passed",
                    "installed": metadata,
                    "registry": registry,
                    "coordination": coordination,
                    "installed_interruptions": interruptions,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
