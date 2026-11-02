"""Trusted completed-observation aggregation controls, not runtime signal failures."""

import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, root=ROOT):
    spec = importlib.util.spec_from_file_location(
        "controlled_" + name, root / "tools" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def signals(result):
    checks = [
        dict(mode=mode, result="passed", timed_out=False, reaped=True)
        for mode in [
            "single",
            "single",
            "nested",
            "nested",
            "nested",
            "nested",
            "spaced_scopes",
            "external",
        ]
    ]
    if result == "failed":
        checks[2].update(result="failed", timed_out=True, handler_entries=2, handler_returns=0)
    return dict(
        result=result,
        checks=checks,
        scope="trusted aggregation injection; not runtime observations",
    )


@contextlib.contextmanager
def observations(pytest_code, signal_result):
    original_spec = importlib.util.spec_from_file_location
    seen = []

    class Loader:
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            module.exercise = lambda **kwargs: signals(signal_result)

    def spec(name, path, *args, **kwargs):
        if Path(path).name == "foundation_signal_verification.py":
            return importlib.machinery.ModuleSpec(name, Loader())
        return original_spec(name, path, *args, **kwargs)

    def completed(command, **kwargs):
        seen.append(list(map(str, command)))
        if "-c" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "module": "controlled-install/100%valid/site-packages/"
                        "mobiraeon/__init__.py"
                    }
                ),
                "",
            )
        if "-m" in command and "pytest" in command:
            xml = Path(command[command.index("--junitxml") + 1])
            failure = '<failure message="controlled pytest failure" />' if pytest_code else ""
            xml.write_text(
                '<testsuites><testsuite><testcase classname="controlled" name="case">'
                + failure
                + "</testcase></testsuite></testsuites>"
            )
            return subprocess.CompletedProcess(
                command, pytest_code, "controlled pytest stdout", "controlled pytest stderr"
            )
        if any(
            str(a).endswith("mobiraeon.exe") or str(a).endswith("/mobiraeon") for a in command
        ):
            raise PastRepairBoundary("wrapper admitted a failed repair aggregate")
        return subprocess.CompletedProcess(command, 0, "controlled setup observation", "")

    with (
        patch("subprocess.run", side_effect=completed),
        patch("importlib.util.spec_from_file_location", side_effect=spec),
    ):
        yield seen


class PastRepairBoundary(Exception):
    pass


def invoke_main(verifier, root):
    stdout = io.StringIO()
    with (
        patch.object(sys, "argv", ["verify_fr_repairs.py", "--candidate-root", str(root)]),
        contextlib.redirect_stdout(stdout),
    ):
        code = verifier.main()
    return code, json.loads(stdout.getvalue())


def emit(case, **data):
    print(
        "FR06_EVIDENCE "
        + json.dumps(
            dict(
                case=case,
                scope="trusted aggregation injection only; "
                "no application signal failure claimed",
                **data,
            )
        )
    )


@pytest.mark.parametrize(
    "pytest_code,signal_result", [(0, "failed"), (1, "passed"), (0, "passed")]
)
def test_fr06_actual_exercise_and_cli(pytest_code, signal_result):
    verifier = load("verify_fr_repairs")
    with observations(pytest_code, signal_result):
        direct = verifier.exercise(sys.executable, ROOT)
        code, result = invoke_main(verifier, ROOT)
    expected = "passed" if pytest_code == 0 and signal_result == "passed" else "failed"
    emit(
        "aggregation",
        pytest_exit=pytest_code,
        probe_result=signal_result,
        actual_cli_exit=code,
        direct=direct,
        report=result,
        tool=verifier.__file__,
    )
    assert direct["result"] == result["result"] == expected
    assert code == int(expected != "passed")
    assert result["exit_code"] == direct["exit_code"] == pytest_code
    assert (
        result["foundation_signals"] == direct["foundation_signals"] == signals(signal_result)
    )
    assert (
        result["stdout"] == "controlled pytest stdout"
        and result["stderr"] == "controlled pytest stderr"
    )
    assert len(result["cases"]) == 1 and result["cases"][0]["result"] == (
        "failed" if pytest_code else "passed"
    )


@pytest.fixture
def candidate(tmp_path):
    root = tmp_path / "candidate"
    (root / "tools").mkdir(parents=True)
    for directory in ["tests", "examples", "bootstrap"]:
        shutil.copytree(
            ROOT / directory, root / directory, ignore=shutil.ignore_patterns("__pycache__")
        )
    for name in [
        "verify_fr_repairs",
        "verify_wheel",
        "verify_platform",
        "foundation_signal_verification",
        "source_integrity",
    ]:
        shutil.copyfile(ROOT / "tools" / (name + ".py"), root / "tools" / (name + ".py"))
    (root / "dist").mkdir()
    with zipfile.ZipFile(root / "dist/mobiraeon-controlled.whl", "w") as z:
        for name in [
            "env.py",
            *[
                "versions/000" + str(n) + "_" + suffix + ".py"
                for n, suffix in [
                    (1, "identity"),
                    (2, "registry"),
                    (3, "coordination"),
                    (4, "execution"),
                ]
            ],
        ]:
            z.writestr("mobiraeon/persistence/migrations/" + name, b"controlled fixture only")
        for name in ["Dockerfile", "program.py", "guard.py"]:
            z.writestr("mobiraeon/fixture_assets/" + name, b"controlled fixture only")
    return root


def test_fr06_actual_wheel_boundary(candidate, monkeypatch):
    verifier = load("verify_fr_repairs", candidate)
    wheel = load("verify_wheel", candidate)
    monkeypatch.setitem(sys.modules, "verify_fr_repairs", verifier)
    output = io.StringIO()
    error = None
    with (
        observations(0, "failed") as commands,
        patch.object(sys, "argv", ["verify_wheel.py", "--uv", "controlled-uv"]),
        contextlib.redirect_stdout(output),
    ):
        try:
            wheel.main()
        except (AssertionError, PastRepairBoundary) as caught:
            error = caught
    report = error.args[0] if isinstance(error, AssertionError) else None
    emit(
        "wheel_boundary",
        tool=wheel.__file__,
        tool_sha256=hashlib.sha256(Path(wheel.__file__).read_bytes()).hexdigest(),
        exception=type(error).__name__,
        captured_failure=report,
        wrapper_stdout=output.getvalue(),
        commands=commands,
    )
    assert isinstance(error, AssertionError), type(error).__name__
    assert report["result"] == "failed" and report["exit_code"] == 0
    assert report["foundation_signals"] == signals("failed")
    assert not output.getvalue(), "a successful wheel report must not escape"


def test_fr06_actual_platform_failure_propagation(candidate, monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(candidate / "tools"))
    platform = load("verify_platform", candidate)
    verifier = load("verify_fr_repairs", candidate)
    files = {}
    for p in (candidate / "tools").glob("*.py"):
        data = p.read_bytes()
        files[p.relative_to(candidate).as_posix()] = dict(
            sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)
        )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            dict(
                files=files,
                deleted_paths=[],
                archive_sha256="controlled-aggregation-fixture",
                base_revision="controlled-fixture",
            )
        )
    )
    report_file = tmp_path / "platform.json"

    def completed(command, **kwargs):
        if any(str(a).endswith("verify_fr_repairs.py") for a in command):
            with observations(0, "failed"):
                code, report = invoke_main(verifier, candidate)
            return subprocess.CompletedProcess(
                command, code, json.dumps(report), "controlled wrapper check"
            )
        return subprocess.CompletedProcess(
            command, 0, "controlled prerequisite observation", ""
        )

    output = io.StringIO()
    with (
        patch("subprocess.run", side_effect=completed),
        patch.object(
            sys,
            "argv",
            [
                "verify_platform.py",
                "--manifest",
                str(manifest),
                "--output",
                str(report_file),
                "--uv",
                "controlled-uv",
            ],
        ),
        contextlib.redirect_stdout(output),
    ):
        code = platform.main()
    report = json.loads(report_file.read_text())
    failed = next(
        c
        for c in report["checks"]
        if any(str(a).endswith("verify_fr_repairs.py") for a in c["command"])
    )
    emit("platform_boundary", actual_cli_exit=code, report=report, tool=platform.__file__)
    assert code != 0 and failed["exit_code"] != 0
    child = json.loads(failed["stdout"])
    assert child["exit_code"] == 0 and child["result"] == "failed"
    assert child["foundation_signals"] == signals("failed")
    assert report["source_unchanged_after_checks"]
    assert any(str(a).endswith("verify_execution.py") for a in report["checks"][-1]["command"])
