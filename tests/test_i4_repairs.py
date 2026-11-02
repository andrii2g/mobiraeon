"""I4 review regressions using real SQLite stores; capture faults are trusted doubles."""

import hashlib
import io
import json
import signal
from contextlib import nullcontext
from dataclasses import replace

import pytest
from test_execution import RUN
from test_execution import allocated as allocated
from test_registry import registry as registry

from mobiraeon.access import Access
from mobiraeon.contracts import EntityId, Outcome
from mobiraeon.coordination import Coordinator
from mobiraeon.execution import ExecutionService, summary
from mobiraeon.scenario import TARGET


class BrokenReader(io.BytesIO):
    def read(self, size):
        if self.tell() == len(self.getvalue()):
            raise OSError("trusted read failure")
        return super().read(size)


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
@pytest.mark.parametrize(
    "channel,prefix,cleaned,live",
    [
        ("stdout", True, True, False),
        ("stdout", False, True, False),
        ("stderr", True, True, False),
        ("stderr", True, False, False),
        ("stdout", True, True, True),
        ("ok", True, True, False),
    ],
)
def test_capture_error_never_seals_success(
    allocated, monkeypatch, channel, prefix, cleaned, live
):
    registry, proof, _, reserved = allocated
    monkeypatch.setattr("mobiraeon.execution.actuation_lock", lambda private: nullcontext())
    reserved.settings = reserved.settings | {"execution_seconds": 0.3}

    class Process:
        def __init__(self, raw):
            self.stdin = io.BytesIO()
            self.stdout = (
                BrokenReader(raw if prefix else b"") if channel == "stdout" else io.BytesIO(raw)
            )
            self.stderr = BrokenReader() if channel == "stderr" else io.BytesIO()

        def poll(self):
            return None if live else 0

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    class Worker:
        def __init__(self, settings):
            pass

        def preflight(self):
            return {"trusted_capture_fault": True}

        def create(self, handoff, timeout=None):
            self.handoff = handoff
            return "a" * 64

        def start(self, identity, timeout=None):
            return Process(json.dumps(summary(self.handoff["input"]["content"])).encode())

        def inspect(self, handoff, identity=None, timeout=None):
            return {
                "State": {
                    "StartedAt": "2026-11-02T00:00:00Z",
                    "FinishedAt": "2026-11-02T00:00:01Z",
                    "Running": False,
                    "ExitCode": 0,
                }
            }

        def cleanup(self, handoff, record):
            return cleaned

    service = ExecutionService(
        registry.store, registry.private, reserved.settings, worker_type=Worker
    )
    result = service.invoke("execution.run", TARGET, RUN, proof=proof)
    _, record = service.load("task-1")
    print(json.dumps({"outcome": result.outcome, "record": record}))
    if channel == "ok":
        assert result.outcome == Outcome.SUCCESS and record["artifact_valid"]
        assert record["capture_complete"] is True
        return
    assert result.outcome != Outcome.SUCCESS
    assert not record["artifact_valid"] and record.get("artifact") is None
    assert record["capture_complete"] is False
    assert record["capture_channels"][channel] == "failed"
    assert record["outcome"] == "capture_failed"
    assert record["held"] is (not cleaned)
    with registry.store.engine.connect() as tx:
        facts = [
            json.loads(r[0])
            for r in tx.exec_driver_sql(
                "SELECT record FROM coordination_facts WHERE stage='observe'"
            )
        ]
    assert not any(f["inputs"]["observation"] == "succeeded" for f in facts)
    replay = service.invoke("execution.run", TARGET, RUN, proof=proof)
    assert replay.data.records[0]["artifact_valid"] is False
    assert (
        Coordinator(registry.store, registry.private)
        .invoke(
            "coordination.submit",
            TARGET,
            {
                "operation_id": "forged-submit",
                "expected_version": 4,
                "attempt_id": "attempt-1",
                "submission_id": "submission-1",
                "artifacts": [
                    {
                        "identity": "fixture-summary",
                        "revision": "v1",
                        "sha256": hashlib.sha256(b"fake").hexdigest(),
                        "content": "fake",
                    }
                ],
            },
            proof=proof,
        )
        .outcome
        != Outcome.SUCCESS
    )


def seal(allocated):
    registry, proof, coordinator, execution = allocated
    execution.invoke("execution.run", TARGET, RUN, proof=proof)
    handoff, _ = execution.load("task-1")
    raw = json.dumps(summary(handoff["input"]["content"])).encode()
    path = registry.private.directory / "captured.txt"
    path.write_bytes(raw)
    artifact = {
        "identity": "fixture-summary",
        "revision": "sha256-" + hashlib.sha256(raw).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content": raw.decode(),
    }
    execution.update(
        "task-1",
        1,
        {
            "terminal": True,
            "held": False,
            "cleanup": "verified",
            "outcome": "succeeded",
            "artifact_valid": True,
            "artifact": artifact,
            "artifact_path": str(path),
            "seal": "test-seal",
        },
        "trusted-test-seal",
    )
    assert (
        coordinator.invoke(
            "coordination.observe",
            TARGET,
            {
                "operation_id": "observe-1",
                "expected_version": 3,
                "attempt_id": "attempt-1",
                "observation": "succeeded",
                "detail": "test-seal",
            },
            proof=proof,
        ).outcome
        == Outcome.SUCCESS
    )
    return artifact


class IndependentAccess(Access):
    def caller(self, proof):
        caller = super().caller(proof)
        return (
            replace(caller, actor=EntityId("human", "trusted-independent-assessor"))
            if caller
            else None
        )


@pytest.mark.parametrize("change_at", ["submission", "assessment"])
def test_retained_allowance_survives_settings_edits(allocated, change_at):
    registry, proof, _, _ = allocated
    artifact = seal(allocated)
    coordinator = Coordinator(
        registry.store,
        registry.private,
        content_limits={"result_bytes": 1 if change_at == "submission" else 65536},
    )
    request = {
        "operation_id": "submit-1",
        "expected_version": 4,
        "attempt_id": "attempt-1",
        "submission_id": "submission-1",
        "artifacts": [artifact],
    }
    submitted = coordinator.invoke("coordination.submit", TARGET, request, proof=proof)
    assert submitted.outcome == Outcome.SUCCESS, submitted
    assessor = Coordinator(
        registry.store,
        registry.private,
        access=IndependentAccess(registry.store, registry.private),
        content_limits={"result_bytes": 1},
    )
    assessment = {
        "operation_id": "assess-1",
        "expected_version": 5,
        "submission_id": "submission-1",
        "submission_digest": submitted.data.records[0]["fact"]["submission_digest"],
        "evidence": [artifact],
        "decision": "approve",
        "rationale": "Exact retained evidence",
    }
    assert (
        assessor.invoke("coordination.assess", TARGET, assessment, proof=proof).outcome
        == Outcome.SUCCESS
    )
    assert assessor.invoke("coordination.assess", TARGET, assessment).outcome == Outcome.REFUSED


def test_current_settings_cannot_raise_retained_allowance(allocated):
    registry, proof, _, execution = allocated
    execution.settings = execution.settings | {"result_bytes": 1}
    artifact = seal(allocated)  # Trusted corrupt-seal mechanics; never a real Runner success.
    coordinator = Coordinator(
        registry.store, registry.private, content_limits={"result_bytes": 65536}
    )
    request = {
        "operation_id": "submit-1",
        "expected_version": 4,
        "attempt_id": "attempt-1",
        "submission_id": "submission-1",
        "artifacts": [artifact],
    }
    assert (
        coordinator.invoke("coordination.submit", TARGET, request, proof=proof).outcome
        == Outcome.INVALID
    )


def test_ordinary_cli_uses_pinned_limit_and_keeps_human_independence(allocated, capsys):
    from mobiraeon.cli import main

    registry, _, _, _ = allocated
    artifact = seal(allocated)
    directory = registry.private.directory
    config = directory / "settings.toml"
    config.write_text(
        "[database]\npath="
        + json.dumps(str(registry.store.path))
        + "\n[access]\nprivate_dir="
        + json.dumps(str(directory))
        + "\ncredential_file="
        + json.dumps(str(registry.private.credential_path("owner.token")))
        + "\n[execution]\nresult_bytes=1\n"
    )
    request = directory / "submission.json"
    inputs = {
        "operation_id": "submit-1",
        "expected_version": 4,
        "attempt_id": "attempt-1",
        "submission_id": "submission-1",
        "artifacts": [artifact],
    }
    request.write_text(
        json.dumps({"operation": "coordination.submit", "target": TARGET, "inputs": inputs})
    )
    assert main(["--config", str(config), "--request-file", str(request), "coordination"]) == 0
    submitted = json.loads(capsys.readouterr().out)
    inputs = {
        "operation_id": "assess-1",
        "expected_version": 5,
        "submission_id": "submission-1",
        "submission_digest": submitted["data"]["records"][0]["fact"]["submission_digest"],
        "evidence": [artifact],
        "decision": "approve",
        "rationale": "Same owner must still be refused",
    }
    request.write_text(
        json.dumps({"operation": "coordination.assess", "target": TARGET, "inputs": inputs})
    )
    assert main(["--config", str(config), "--request-file", str(request), "coordination"]) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "review_inapplicable"


def test_foreground_execution_signal_handlers_are_restored(allocated, monkeypatch):
    import mobiraeon.execution as module

    # Handler scope is execution-only and includes exceptional exits.
    context = getattr(module, "execution_signals", None)
    assert context is not None
    before = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    with pytest.raises(RuntimeError), context() as interruption:
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        assert interruption.is_set()
        raise RuntimeError("trusted scope failure")
    assert all(signal.getsignal(s) == h for s, h in before.items())


def test_signal_after_reservation_blocks_create_and_records_stop(allocated, monkeypatch):
    registry, proof, _, reserved = allocated
    monkeypatch.setattr("mobiraeon.execution.actuation_lock", lambda private: nullcontext())
    effects = []

    class Worker:
        def __init__(self, settings):
            pass

        def preflight(self):
            return {"trusted_no_effects_probe": True}

        def create(self, handoff, timeout=None):
            effects.append("create")
            raise AssertionError("interrupted admission must not create")

        def cleanup(self, handoff, record):
            return not record.get("create_intent")

    def interrupt(progress):
        handler = signal.getsignal(signal.SIGTERM)
        assert callable(handler)
        handler(signal.SIGTERM, None)

    before = signal.getsignal(signal.SIGTERM)
    service = ExecutionService(
        registry.store, registry.private, reserved.settings, worker_type=Worker
    )
    result = service.invoke("execution.run", TARGET, RUN, proof=proof, progress=interrupt)
    _, record = service.load("task-1")
    assert result.outcome == Outcome.UNCERTAIN
    assert not effects and record["stop_intent"] and record["cleanup"] == "verified"
    assert record["terminal"] and not record["held"] and not record["artifact_valid"]
    assert signal.getsignal(signal.SIGTERM) == before
