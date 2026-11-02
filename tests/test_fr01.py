"""FR-01: transport EOF is not authoritative execution completion."""

import io
import json
from contextlib import nullcontext

import pytest
from test_execution import RUN
from test_execution import allocated as allocated
from test_registry import registry as registry

from mobiraeon.execution import ExecutionService, summary
from mobiraeon.scenario import TARGET


@pytest.mark.parametrize(
    "running,exit_code,attach,missing,clean_exit,cleaned,expected",
    [
        (True, 0, 0, False, 137, True, "uncertain_effects"),
        (True, 0, 0, False, 0, True, "uncertain_effects"),
        (True, 0, 1, True, 0, True, "uncertain_effects"),
        (True, 0, 1, True, 0, False, "uncertain_effects"),
        (False, 0, 1, False, 0, True, "known_failure"),
        (False, 0, 0, False, 0, True, "success"),
        (False, 9, 0, False, 9, True, "known_failure"),
    ],
)
def test_fr01_completion(
    allocated, monkeypatch, running, exit_code, attach, missing, clean_exit, cleaned, expected
):
    registry, proof, _, reserved = allocated
    monkeypatch.setattr("mobiraeon.execution.actuation_lock", lambda private: nullcontext())

    class Process:
        def __init__(self, raw):
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(raw)
            self.stderr = io.BytesIO()

        def poll(self):
            return attach

        def wait(self, timeout=None):
            return attach

        def kill(self):
            pass

    class Worker:
        def __init__(self, settings):
            self.inspections = 0

        def preflight(self):
            return {"trusted_transport_fault": True}

        def create(self, handoff, timeout=None):
            self.handoff = handoff
            return "b" * 64

        def start(self, identity, timeout=None):
            return Process(json.dumps(summary(self.handoff["input"]["content"])).encode())

        def inspect(self, handoff, identity=None, timeout=None):
            self.inspections += 1
            if missing and self.inspections > 1:
                return None
            return {
                "State": {
                    "StartedAt": "2026-11-02T00:00:00Z",
                    "FinishedAt": "0001-01-01T00:00:00Z" if running else "2026-11-02T00:00:01Z",
                    "Running": running,
                    "ExitCode": exit_code,
                }
            }

        def cleanup(self, handoff, record):
            self.last_state = {
                "State": {
                    "Running": False,
                    "ExitCode": clean_exit,
                    "StartedAt": "2026-11-02T00:00:00Z",
                    "FinishedAt": "2026-11-02T00:00:02Z",
                }
            }
            return cleaned

    service = ExecutionService(
        registry.store, registry.private, reserved.settings, worker_type=Worker
    )
    result = service.invoke("execution.run", TARGET, RUN, proof=proof)
    _, state = service.load("task-1")
    assert result.outcome.value == expected, (result, state)
    assert state["held"] is (not cleaned) and state["cleanup"] == (
        "verified" if cleaned else "unverified"
    )
    assert state["artifact_valid"] is (expected == "success")
    with registry.store.engine.connect() as tx:
        observed = [
            json.loads(r[0])
            for r in tx.exec_driver_sql(
                "SELECT record FROM coordination_facts WHERE stage='observe'"
            )
        ]
    assert any(r["inputs"]["observation"] == "succeeded" for r in observed) is (
        expected == "success"
    )
    if running:
        assert state["outcome"] == "unknown" and not observed
    elif expected != "success" and cleaned:
        assert observed[0]["inputs"]["observation"] == "failed"
    if expected == "success":
        assert state["outcome"] == "succeeded"
