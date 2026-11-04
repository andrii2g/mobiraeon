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


def perform(observations):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-image-id")
    parser.add_argument("--uv", default="uv")
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    uv = str(Path(options.uv).resolve()) if Path(options.uv).is_file() else options.uv
    (wheel,) = (root / "dist").glob("mobiraeon-*.whl")
    observations["wheel"] = str(wheel)
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
        assert (
            "mobiraeon/persistence/migrations/versions/0004_execution.py" in archive.namelist()
        )
        assert "mobiraeon/persistence/migrations/versions/0005_forge.py" in archive.namelist()
        for name in ("Dockerfile", "program.py", "guard.py"):
            assert "mobiraeon/fixture_assets/" + name in archive.namelist()
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="mobiraeon-wheel-") as temporary:
        outside = Path(temporary)

        def run(*args, cwd=outside, timeout=60):
            argv = list(map(str, args))
            observations["active_command"] = argv
            try:
                result = subprocess.run(
                    argv,
                    cwd=cwd,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired as error:

                def decode(value):
                    return (
                        value.decode(errors="replace")
                        if isinstance(value, bytes)
                        else value or ""
                    )

                observations["failed_command"] = dict(
                    command=argv,
                    exit_code=None,
                    timed_out=True,
                    stdout=decode(error.stdout)[:2097152],
                    stderr=decode(error.stderr)[:2097152],
                )
                raise
            if result.returncode:
                observations["failed_command"] = dict(
                    command=argv,
                    exit_code=result.returncode,
                    timed_out=False,
                    stdout=result.stdout[:2097152],
                    stderr=result.stderr[:2097152],
                )
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
        observations["active_stage"] = "installed_metadata"
        metadata = json.loads(
            run(
                python,
                "-c",
                """
import json, platform, sqlite3, mobiraeon
from importlib.metadata import version
print(json.dumps({"module": mobiraeon.__file__, "python": platform.python_version(),
    "sqlite": sqlite3.sqlite_version, "dependencies": {
    name: version(name) for name in ("mobiraeon", "SQLAlchemy", "alembic", "httpx2")}}))
""",
            )
        )
        observations["installed"] = metadata
        assert str(root).lower() not in metadata["module"].lower()
        forge = json.loads(run(python, "-m", "mobiraeon.forge_verification"))
        observations["runtime_only_forge"] = forge
        assert forge["result"] == "passed", forge
        # Test-only tools are pinned by the same unchanged lock. Application code
        # remains solely the noneditable wheel, with no source PYTHONPATH.
        test_constraints = run(
            uv, "export", "--locked", "--no-emit-project", "--no-hashes", cwd=root
        )
        (outside / "test-constraints.txt").write_text(test_constraints, encoding="utf-8")
        run(
            uv,
            "pip",
            "install",
            "--python",
            python,
            "--constraint",
            outside / "test-constraints.txt",
            "pytest",
            "httpx2",
            "cryptography",
        )
        from verify_fr_repairs import exercise as repair_exercise

        observations["active_stage"] = "fr_repairs"
        repairs = repair_exercise(python, root, include_tools=False)
        observations["fr_repairs"] = repairs
        assert repairs["result"] == "passed", repairs
        installed_forge_test = outside / "test_forge_installed.py"
        installed_forge_test.write_bytes((root / "tests/test_forge.py").read_bytes())
        installed_forge = run(
            python, "-m", "pytest", "-q", "--tb=short", installed_forge_test, timeout=180
        )
        observations["installed_forge_regressions"] = installed_forge
        reporting_test = outside / "test_execution_reporting_installed.py"
        reporting_test.write_bytes((root / "tests/test_execution_reporting.py").read_bytes())
        reporting = run(python, "-m", "pytest", "-q", "--tb=short", reporting_test)
        observations["installed_execution_reporting"] = reporting
        database = outside / "wheel.sqlite3"
        assert run(console, "--version").strip() == "0.1.0"
        run(python, "-m", "mobiraeon", "--help")
        for command in ("initialize", "initialize", "upgrade", "check"):
            result = json.loads(run(console, "--database", database, command))
            assert result["outcome"] == "success"
            assert result["schema_revision"] == "0005"
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
        assert started["capabilities"]["fixture_execution"] == "supervised_fixture_only"
        assert started["capabilities"]["forge_integration"] == "gitea_manual_task_comment"
        assert (
            started["capabilities"]["coordination_workflows"]
            == "local_simulated_task_acceptance"
        )
        run(console, "--database", database, "check")
        from verify_registry import exercise

        registry = exercise(python, root / "bootstrap/initial-test.json")
        observations["registry"] = registry
        from verify_coordination import exercise as coordination_exercise

        coordination = coordination_exercise(
            python, root / "examples/coordination.json", root / "bootstrap/initial-test.json"
        )
        observations["coordination"] = coordination
        from verify_execution import exercise as execution_exercise

        signal_regressions = json.loads(
            run(python, "-m", "mobiraeon.execution_signal_verification")
        )
        observations["execution_signal_regressions"] = signal_regressions
        assert signal_regressions["result"] == "passed"
        observations["active_stage"] = "fixture_execution"
        execution = execution_exercise(
            python,
            root / "examples/execution.json",
            root / "bootstrap/initial-test.json",
            options.fixture_image_id,
        )
        observations["fixture_execution"] = execution
        observations["active_stage"] = "installed_interruptions"
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
                    "fr_repairs": repairs,
                    "runtime_only_forge": forge,
                    "installed_forge_regressions": installed_forge,
                    "installed_execution_reporting": reporting,
                    "registry": registry,
                    "coordination": coordination,
                    "fixture_execution": execution,
                    "execution_signal_regressions": signal_regressions,
                    "installed_interruptions": interruptions,
                },
                indent=2,
            )
        )


def main():
    observations = {"active_stage": "wheel_preparation"}
    try:
        return perform(observations)
    except Exception as error:
        report = {
            "result": "failed",
            "failure_type": type(error).__name__,
            "completed_observations": observations,
        }
        if hasattr(error, "report"):
            report["failed_check"] = error.report
        # FR-06: failure stdout stays empty; re-raise the original exception.
        print("MOBIRAEON_WHEEL_FAILURE " + json.dumps(report), file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
