"""Controlled reporting injections; these do not reproduce a runtime Worker failure."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mobiraeon.execution_diagnostics import (
    CheckLog,
    VerificationFailure,
    check_failure_terminal,
    verification_workspace,
)


def test_packaged_main_retains_first_preparation_failure():
    code = """
import json,sys,subprocess
from unittest.mock import patch
import mobiraeon.execution_verification as v
# Trusted isolated Linux-branch reporting injection, never native Windows execution.
v.sys.platform = "linux"
def stopped(command, **kwargs):
    assert command[1:3] == ["-m", "mobiraeon.execution_fixture"]
    return subprocess.CompletedProcess(
        command,17,"PREPARE_STDOUT_SENTINEL","PREPARE_STDERR_SENTINEL"
    )
sys.argv=["execution_verification","--input","input.json","--catalog-input","catalog.json","--image-id","sha256:"+"a"*64]
with patch.object(v.subprocess,"run",side_effect=stopped):
    raise SystemExit(v.main())
"""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=30
    )
    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert report["result"] == "failed" and report["failure_type"] == "AssertionError"
    assert report["active"]["stage"] == "preparation"
    assert not report["terminal_available"] and report["observed_terminal"] is None
    command = report["checks"][-1]
    assert command["exit_code"] == 17
    assert command["stdout"] == "PREPARE_STDOUT_SENTINEL"
    assert command["stderr"] == "PREPARE_STDERR_SENTINEL"
    assert report["package_hashes"]["execution_verification.py"]
    root = Path(report["protected_state"]["directory"])
    try:
        assert root.is_dir() and report["diagnostic_storage"]["available"]
        retained = json.loads(
            Path(report["diagnostic_storage"]["path"]).read_text(encoding="utf-8")
        )
        assert retained["checks"] == report["checks"]
    finally:
        assert root.resolve().parent == Path(__import__("tempfile").gettempdir()).resolve()
        assert root.name.startswith("mobiraeon-execution-check-")
        shutil.rmtree(root)


@pytest.mark.parametrize(
    "changes", [{"outcome": "unknown"}, {"cleanup": "unverified"}, {"artifact_valid": True}]
)
def test_terminal_mismatch_retains_pre_cleanup_record_and_earlier_checks(changes):
    checks = CheckLog("controlled-image")
    checks.append({"case": "earlier", "result": "passed"})
    observed = dict(
        outcome="failed",
        cleanup="verified",
        artifact_valid=False,
        held=False,
        terminal=True,
        completion_state={"Running": False, "ExitCode": 1},
        attachment_exit_code=1,
    )
    observed |= changes
    root = None
    try:
        with pytest.raises(VerificationFailure) as caught:
            with verification_workspace(checks) as root:
                check_failure_terminal(checks, observed, "failed")
        report = caught.value.report
        assert report["result"] == "failed" and report["terminal_available"]
        assert report["observed_terminal"] == observed
        original_cleanup = report["observed_terminal"]["cleanup"]
        observed["cleanup"] = "verified"  # Later cleanup cannot alter retained mismatch.
        assert report["observed_terminal"]["cleanup"] == original_cleanup
        assert report["checks"][0]["case"] == "earlier"
        assert report["active"]["stage"] == "terminal_assertion"
        assert root.exists()
    finally:
        if root is not None:
            shutil.rmtree(root)


def test_original_terminal_predicate_passing_control():
    checks = CheckLog("controlled-image")
    check_failure_terminal(
        checks, dict(outcome="failed", cleanup="verified", artifact_valid=False), "failed"
    )


def test_diagnostic_persistence_failure_does_not_mask_original(monkeypatch):
    import mobiraeon.execution_diagnostics as diagnostics

    checks = CheckLog("controlled-image")

    def unavailable(*args):
        raise OSError("controlled persistence failure")

    monkeypatch.setattr(diagnostics, "durable_new", unavailable)
    root = None
    try:
        with pytest.raises(VerificationFailure) as caught:
            with verification_workspace(checks) as root:
                raise AssertionError("original assertion")
        assert caught.value.report["failure_type"] == "AssertionError"
        assert not caught.value.report["diagnostic_storage"]["available"]
    finally:
        if root is not None:
            shutil.rmtree(root)


@pytest.mark.parametrize("kind", ["timeout", "invalid_json", "wrong_exit"])
def test_command_partial_evidence(kind, monkeypatch, tmp_path):
    checks = CheckLog("controlled-image")

    def stopped(command, **kwargs):
        if kind == "timeout":
            raise subprocess.TimeoutExpired(
                command, 1, output=b"TIMEOUT_OUT", stderr=b"TIMEOUT_ERR"
            )
        return subprocess.CompletedProcess(
            command, 17 if kind == "wrong_exit" else 0, "NOT_JSON_OUT", "SENTINEL_ERR"
        )

    monkeypatch.setattr(subprocess, "run", stopped)
    with pytest.raises((AssertionError, ValueError, subprocess.TimeoutExpired)):
        checks.command(["-m", "controlled"], cwd=tmp_path, env={})
    assert checks[-1]["stdout"] == ("TIMEOUT_OUT" if kind == "timeout" else "NOT_JSON_OUT")
    assert checks[-1]["stderr"] == ("TIMEOUT_ERR" if kind == "timeout" else "SENTINEL_ERR")
    assert checks[-1]["parse_status"] != "parsed"


def test_snapshot_reads_only_bounded_fixture_observations():
    from sqlalchemy import text

    from mobiraeon.forge_verification import fixture
    from mobiraeon.private_state import durable_new

    with fixture() as (app, server):
        capture = app.directory / "diagnostic-capture.json"
        durable_new(
            capture,
            json.dumps(
                {
                    "stdout": "PROGRAM_OUTPUT_SENTINEL",
                    "stderr": "",
                    "channels": {"stdout": "failed", "stderr": "eof"},
                    "truncated": False,
                }
            ).encode(),
        )
        record = dict(
            outcome="failed",
            cleanup="verified",
            artifact_valid=False,
            held=False,
            terminal=True,
            capture_path=str(capture),
            credential="DISALLOWED_FIELD_SENTINEL",
        )
        handoff = {
            "settings": {
                "image_id": "controlled-image",
                "engine_id": "controlled-engine",
                "credential": "DISALLOWED_FIELD_SENTINEL",
            }
        }
        with app.store.transaction() as tx:
            tx.execute(
                text(
                    "INSERT INTO execution_runs(task,attempt,handoff,generation,held,record) "
                    "VALUES(:task,:attempt,:handoff,1,0,:record)"
                ),
                dict(
                    task="task-1",
                    attempt="diagnostic-attempt",
                    handoff=json.dumps(handoff),
                    record=json.dumps(record),
                ),
            )
            tx.execute(
                text("INSERT INTO execution_events(task,record) VALUES(:task,:record)"),
                dict(
                    task="task-1",
                    record=json.dumps(
                        {
                            "event": "sealed",
                            "at": 123,
                            "credential": "DISALLOWED_FIELD_SENTINEL",
                        }
                    ),
                ),
            )
        checks = CheckLog("controlled-image")
        checks.directory = app.directory
        snapshot = checks.snapshot()
        assert snapshot["available"] and snapshot["record"]["outcome"] == "failed"
        assert snapshot["pinned_limits"]["engine_id"] == "controlled-engine"
        assert snapshot["events"][0]["event"] == "sealed"
        assert snapshot["capture"]["channels"]["stdout"] == "failed"
        assert "DISALLOWED_FIELD_SENTINEL" not in json.dumps(snapshot)
        assert "PROGRAM_OUTPUT_SENTINEL" not in json.dumps(snapshot)
        assert not server.routes


def test_unexpected_exit_retains_observed_terminal_before_propagating(monkeypatch, tmp_path):
    checks = CheckLog("controlled-image")
    observed = dict(
        outcome="failed",
        cleanup="unverified",
        artifact_valid=False,
        held=True,
        terminal=False,
        attachment_exit_code=17,
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command,
            17,
            json.dumps({"data": {"records": [observed]}}),
            "NONZERO_TERMINAL_SENTINEL",
        ),
    )
    with pytest.raises(AssertionError):
        checks.command(["-m", "controlled"], cwd=tmp_path, env={}, expect=0)
    report = checks.failure(AssertionError())
    assert report["terminal_available"] and report["observed_terminal"] == observed
    assert report["checks"][-1]["exit_code"] == 17
    assert report["checks"][-1]["parse_status"] == "parsed"
    assert report["checks"][-1]["stderr"] == "NONZERO_TERMINAL_SENTINEL"


@pytest.mark.parametrize(
    "case",
    [
        "uuid",
        "no_uuid",
        "disk_failure",
        "uuid_disk_failure",
        "admission",
        "admission_pass",
        "variant",
        "variant_pass",
    ],
)
def test_later_uuid_and_current_direct_context_through_actual_verifiers(case):
    from mobiraeon.verification_repair_controls import run_case

    observed = run_case(case)
    assert observed["required_behavior"], observed


def test_context_boundary_clears_previous_terminal_and_fixture():
    checks = CheckLog("controlled-image")
    checks.activate(
        "previous",
        "terminal",
        mode="wait",
        directory=Path("previous"),
        terminal={"outcome": "failed", "held": True},
    )
    checks.activate("next", "before_fixture", expected="new case has no prior observations")
    assert checks.terminal is None and checks.directory is None
    assert checks.active["mode"] is None and checks.active["variant"] is None
    assert checks.snapshot()["fixture_directory"] is None


def test_uuid_normalization_never_stringifies_arbitrary_objects():
    from uuid import uuid4

    from mobiraeon.execution_diagnostics import json_observation

    identity = uuid4()
    assert json_observation({"invocation": identity, "nested": [identity]}) == {
        "invocation": str(identity),
        "nested": [str(identity)],
    }

    class Unsupported:
        def __str__(self):
            raise AssertionError("arbitrary stringification is forbidden")

    with pytest.raises(TypeError):
        json_observation({"unsupported": Unsupported()})


@pytest.mark.parametrize(
    "case",
    [
        "preparation",
        "caught",
        "later",
        "cleanup_failure",
        "timeout",
        "malformed",
        "missing_json",
        "unexpected_exit",
        "launch",
        "storage_failure",
        "oversized",
    ],
)
def test_f7_r1_actual_parent_nested_failure_retention(case):
    from mobiraeon.verification_final07_controls import nested_control

    report = nested_control(case)
    assert report["required_behavior"], report
    assert report["child_main_exit"] != 0


def test_f7_r1_optional_command_exit_is_explicit_and_default_stays_strict(
    monkeypatch, tmp_path
):
    import mobiraeon.execution_diagnostics as diagnostics

    def observed(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, '{"outcome":"success"}', "")

    monkeypatch.setattr(diagnostics.subprocess, "run", observed)
    checks = diagnostics.CheckLog("controlled-image")
    result = checks.command(["probe"], cwd=tmp_path, env={}, expect=None)
    assert result == {"outcome": "success"}
    assert checks[-1]["expected_exit_code"] is None and checks[-1]["exit_code"] == 1
    with pytest.raises(AssertionError):
        checks.command(["probe"], cwd=tmp_path, env={})


def test_f7_r1_passing_parent_shape_and_successful_workspace_cleanup(monkeypatch):
    import mobiraeon.execution_diagnostics as diagnostics
    import mobiraeon.execution_repair_verification as nested
    import mobiraeon.execution_verification as parent

    expected = {
        "result": "passed",
        "checks": [{"case": "existing_nested_case", "result": "passed"}],
        "image_id": "controlled-image",
    }
    monkeypatch.setattr(nested, "exercise", lambda *args: expected)
    checks = diagnostics.CheckLog("controlled-image")
    checks.append({"case": "earlier_outer", "result": "passed"})
    with diagnostics.verification_workspace(checks) as outside:
        assert (
            parent.verify_nested_repairs(
                checks, Path("input"), Path("catalog"), "controlled-image"
            )
            is expected
        )
        assert outside.is_dir()
    assert not outside.exists()
    assert len(checks) == 2 and checks[-1]["regressions"] is expected
    assert expected["checks"] == [{"case": "existing_nested_case", "result": "passed"}]


@pytest.mark.parametrize("last", ['{"state":"finished"}\n', "INVALID_JSON\n", "null\n"])
def test_f7_r1_signal_reader_retains_progress_before_thread_parse_failure(last):
    import io
    import queue
    from types import SimpleNamespace

    import mobiraeon.execution_repair_verification as nested

    prefix = '{"data":{"state":"running"}}\n'
    case, notifications = {}, queue.Queue()
    nested._drain_progress(
        SimpleNamespace(stdout=io.StringIO(prefix + last)), case, notifications
    )
    assert case["stdout"] == prefix + last
    assert notifications.get_nowait() == {"data": {"state": "running"}}
    observed = notifications.get_nowait()
    if last.startswith("{"):
        assert case["parse_status"] == "parsed" and observed == {"state": "finished"}
    else:
        assert case["parse_status"] == "invalid_or_nonobject_json"
        assert isinstance(observed, ValueError)


def test_f7_r1_signal_reader_transfers_stream_failure_with_prior_prefix():
    import queue
    from types import SimpleNamespace

    import mobiraeon.execution_repair_verification as nested

    class InterruptedStream:
        def __iter__(self):
            yield '{"data":{"state":"running"}}\n'
            raise OSError("trusted progress-stream failure")

    case, notifications = {}, queue.Queue()
    nested._drain_progress(SimpleNamespace(stdout=InterruptedStream()), case, notifications)
    assert case["stdout"] == '{"data":{"state":"running"}}\n'
    assert case["parse_status"] == "progress_stream_failed"
    assert notifications.get_nowait() == {"data": {"state": "running"}}
    assert isinstance(notifications.get_nowait(), OSError)
