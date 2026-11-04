"""Trusted aggregation injections; none claim actual Docker/Worker execution."""

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, root=ROOT):
    spec = importlib.util.spec_from_file_location(
        "controlled_" + name, root / "tools" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "exit_code,body",
    [
        (17, {"result": "failed", "checks": [{"sentinel": "CHILD_PARTIAL"}]}),
        (0, {"result": "failed"}),
        (0, None),
    ],
)
def test_execution_wrapper_never_admits_failed_or_malformed_child(exit_code, body, monkeypatch):
    module = load("verify_execution")
    monkeypatch.setattr(module.sys, "platform", "linux")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda c, **k: subprocess.CompletedProcess(
            c, exit_code, json.dumps(body) if body else "INVALID_JSON", "CHILD_STDERR"
        ),
    )
    with pytest.raises(module.ExecutionVerificationFailure) as caught:
        module.exercise(sys.executable, Path("input"), Path("catalog"), "controlled-image")
    report = caught.value.report
    assert report["result"] == "failed" and report["exit_code"] == exit_code
    assert report["stderr"] == "CHILD_STDERR"
    if body:
        assert report["fixture"] == body
    else:
        assert report["parse_status"] == "invalid_json"


def test_execution_wrapper_timeout_and_cli_propagation(monkeypatch):
    module = load("verify_execution")
    monkeypatch.setattr(module.sys, "platform", "linux")

    def timeout(c, **k):
        raise subprocess.TimeoutExpired(c, 900, output=b"PARTIAL_OUT", stderr=b"PARTIAL_ERR")

    monkeypatch.setattr(module.subprocess, "run", timeout)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_execution",
            "--input",
            "input",
            "--catalog-input",
            "catalog",
            "--image-id",
            "controlled-image",
        ],
    )
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = module.main()
    report = json.loads(output.getvalue())
    assert code != 0
    assert (
        report["timed_out"]
        and report["stdout"] == "PARTIAL_OUT"
        and report["stderr"] == "PARTIAL_ERR"
    )


@pytest.mark.parametrize("kind", ["worker", "assertion"])
def test_wheel_empty_stdout_and_earlier_observations_survive(kind, monkeypatch):
    wheel = load("verify_wheel")
    source = load("verify_execution")
    error = (
        source.ExecutionVerificationFailure(
            {"result": "failed", "checks": [{"sentinel": "EARLIER_CHILD_CHECK"}]}
        )
        if kind == "worker"
        else AssertionError({"result": "failed", "sentinel": "FR06_STYLE"})
    )

    def failed(observations):
        observations["installed"] = {"module": "controlled/site-packages/mobiraeon/__init__.py"}
        observations["runtime_only_forge"] = {
            "result": "passed",
            "sentinel": "EARLIER_WHEEL_CHECK",
        }
        observations["active_stage"] = "fixture_execution"
        raise error

    monkeypatch.setattr(wheel, "perform", failed)
    output = io.StringIO()
    diagnostic = io.StringIO()
    with (
        contextlib.redirect_stdout(output),
        contextlib.redirect_stderr(diagnostic),
        pytest.raises(type(error)) as caught,
    ):
        wheel.main()
    assert caught.value is error and not output.getvalue()
    report = json.loads(diagnostic.getvalue().split("MOBIRAEON_WHEEL_FAILURE ", 1)[1])
    assert (
        report["result"] == "failed"
        and report["completed_observations"]["runtime_only_forge"]["sentinel"]
        == "EARLIER_WHEEL_CHECK"
    )
    if kind == "worker":
        assert report["failed_check"]["checks"][0]["sentinel"] == "EARLIER_CHILD_CHECK"


@pytest.mark.parametrize("tool", ["verify_platform", "verify_foundation"])
@pytest.mark.parametrize("failed_tool", ["verify_execution.py", "verify_wheel.py"])
def test_actual_aggregate_propagation(
    tmp_path, monkeypatch, tool, failed_tool, nested_report=None
):
    root = tmp_path / "candidate"
    (root / "tools").mkdir(parents=True)
    for name in (tool, "source_integrity"):
        shutil.copyfile(ROOT / "tools" / f"{name}.py", root / "tools" / f"{name}.py")
    (root / "dist").mkdir()
    out = root / "submissions" / "controlled"
    out.mkdir(parents=True)
    files = {
        p.relative_to(root).as_posix(): {
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "bytes": p.stat().st_size,
        }
        for p in (root / "tools").glob("*.py")
    }
    manifest = out / "source-manifest.json"
    manifest.write_text(
        json.dumps(
            dict(
                files=files,
                deleted_paths=[],
                archive_sha256="controlled-aggregation",
                base_revision="controlled",
            )
        )
    )
    monkeypatch.syspath_prepend(str(root / "tools"))
    module = load(tool, root)

    def completed(command, **kwargs):
        failed = any(str(x).endswith(failed_tool) for x in command)
        failed_report = {"result": "failed", "sentinel": "AGGREGATE_CHILD"}
        if nested_report is not None:
            failed_report["fixture"] = nested_report
        return subprocess.CompletedProcess(
            command,
            1 if failed else 0,
            json.dumps(failed_report) if failed else "controlled prerequisite",
            "CONTROLLED_STDERR" if failed else "",
        )

    monkeypatch.setattr(subprocess, "run", completed)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "controlled-uv")
    args = [tool, "--uv", "controlled-uv"]
    if tool == "verify_platform":
        args += ["--manifest", str(manifest), "--output", str(out / "platform.json")]
    else:
        args += ["--increment", "increment-5", "--output-directory", str(out)]
    monkeypatch.setattr(sys, "argv", args)
    assert module.main() != 0
    report = json.loads(
        (
            out / ("platform.json" if tool == "verify_platform" else "verification.json")
        ).read_text()
    )
    child = next(
        c for c in report["checks"] if any(str(x).endswith(failed_tool) for x in c["command"])
    )
    assert (
        child["exit_code"] == 1 and json.loads(child["stdout"])["sentinel"] == "AGGREGATE_CHILD"
    )
    assert child["stderr"] == "CONTROLLED_STDERR" and report["source_unchanged_after_checks"]


@pytest.mark.parametrize("tool", ["verify_platform", "verify_foundation"])
def test_f7_r1_nested_parent_evidence_survives_actual_aggregates(tmp_path, monkeypatch, tool):
    from mobiraeon.verification_final07_controls import nested_control

    nested_result = nested_control("later")
    assert nested_result["required_behavior"]
    parent_report = nested_result["parent_report"]
    test_actual_aggregate_propagation(
        tmp_path, monkeypatch, tool, "verify_execution.py", nested_report=parent_report
    )
    path = (
        tmp_path
        / "candidate/submissions/controlled"
        / ("platform.json" if tool == "verify_platform" else "verification.json")
    )
    aggregate = json.loads(path.read_text())
    child = next(
        c
        for c in aggregate["checks"]
        if any(str(x).endswith("verify_execution.py") for x in c["command"])
    )
    assert child["exit_code"] != 0
    assert json.loads(child["stdout"])["fixture"] == parent_report
    assert parent_report["active"]["phase"] == "stderr"
    assert len(aggregate["checks"]) > 1


@pytest.mark.parametrize("tool", ["verify_platform", "verify_foundation"])
def test_f8_signal_report_survives_actual_aggregates(tmp_path, monkeypatch, tool):
    from mobiraeon.verification_final08_controls import signal_control

    observed = signal_control("stop_raises")
    assert observed["required_behavior"]
    parent_report = observed["parent_report"]
    test_actual_aggregate_propagation(
        tmp_path, monkeypatch, tool, "verify_execution.py", nested_report=parent_report
    )
    aggregate = json.loads(
        (
            tmp_path
            / "candidate/submissions/controlled"
            / ("platform.json" if tool == "verify_platform" else "verification.json")
        ).read_text()
    )
    child = next(
        c
        for c in aggregate["checks"]
        if any(str(x).endswith("verify_execution.py") for x in c["command"])
    )
    assert child["exit_code"] == 1
    assert json.loads(child["stdout"])["fixture"] == parent_report
    assert observed["signal_case"]["exit_code"] == 1


def test_f8_oversized_signal_actual_source_wrapper_and_wheel_frame(monkeypatch):
    from mobiraeon.verification_final08_controls import signal_control

    observed = signal_control("oversized")
    assert observed["required_behavior"]
    parent_report = observed["parent_report"]
    source, wheel = load("verify_execution"), load("verify_wheel")
    body = json.dumps(parent_report)
    assert len(body.encode()) < 2097152
    with monkeypatch.context() as patch:
        patch.setattr(sys, "platform", "linux")
        patch.setattr(
            source.subprocess,
            "run",
            lambda *a, **kw: subprocess.CompletedProcess(a, 1, body, ""),
        )
        with pytest.raises(source.ExecutionVerificationFailure) as caught:
            source.exercise(sys.executable, "input", "catalog", "trusted-image")
    assert caught.value.report["fixture"] == parent_report
    assert caught.value.report["parse_status"] == "parsed"
    error = caught.value

    def failed(observations):
        observations["earlier"] = {"result": "passed"}
        raise error

    monkeypatch.setattr(wheel, "perform", failed)
    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
        pytest.raises(source.ExecutionVerificationFailure),
    ):
        wheel.main()
    assert stdout.getvalue() == ""
    frame = json.loads(stderr.getvalue().split("MOBIRAEON_WHEEL_FAILURE ", 1)[1])
    assert frame["failed_check"]["fixture"] == parent_report
    assert frame["completed_observations"]["earlier"]["result"] == "passed"


@pytest.mark.parametrize("api", [False, True])
@pytest.mark.parametrize(
    "case",
    [
        "positive",
        "nonzero_pass",
        "nonzero_failed",
        "zero_failed",
        "malformed",
        "array",
        "string",
        "null",
        "missing",
        "unsupported",
        "checks_junk",
        "checks_empty",
        "checks_bad_entry",
        "timeout",
        "launch",
    ],
)
def test_f7_a1_actual_native_controller_wrapper(case, api):
    from mobiraeon.verification_final07_controls import interruption_control

    report = interruption_control(ROOT / "tools/verify_interruptions.py", case, api)
    assert report["required_behavior"], report


@pytest.mark.parametrize("tool", ["verify_platform", "verify_foundation"])
def test_f7_a1_failed_native_wrapper_remains_failed_in_actual_aggregate(
    tmp_path, monkeypatch, tool
):
    test_actual_aggregate_propagation(tmp_path, monkeypatch, tool, "verify_interruptions.py")


def test_f7_r1_real_nested_report_survives_source_and_wheel_boundaries(monkeypatch):
    from mobiraeon.verification_final07_controls import nested_control

    controlled = nested_control("caught")
    assert controlled["required_behavior"]
    fixture_report = controlled["parent_report"]
    source = load("verify_execution")
    monkeypatch.setattr(source.sys, "platform", "linux")
    actual_run = subprocess.run

    def child(command, **kwargs):
        if "mobiraeon.execution_verification" not in command:
            return actual_run(command, **kwargs)
        return subprocess.CompletedProcess(
            command, 1, json.dumps(fixture_report), "NESTED_CHILD_STDERR"
        )

    monkeypatch.setattr(source.subprocess, "run", child)
    with pytest.raises(source.ExecutionVerificationFailure) as caught:
        source.exercise(sys.executable, Path("input"), Path("catalog"), "controlled-image")
    retained = caught.value.report
    assert retained["fixture"] == fixture_report and retained["exit_code"] == 1
    wheel = load("verify_wheel")

    def installed(observations):
        observations["earlier_installed"] = {"result": "passed"}
        raise caught.value

    monkeypatch.setattr(wheel, "perform", installed)
    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
        pytest.raises(source.ExecutionVerificationFailure),
    ):
        wheel.main()
    assert stdout.getvalue() == ""
    report = json.loads(stderr.getvalue().split("MOBIRAEON_WHEEL_FAILURE ", 1)[1])
    assert report["failed_check"] == retained
    assert report["completed_observations"]["earlier_installed"]["result"] == "passed"
