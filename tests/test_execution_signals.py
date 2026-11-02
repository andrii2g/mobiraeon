"""Real signals in kill/reap-bounded child processes on Windows and Linux."""

import io
import json
import signal
from contextlib import nullcontext

import pytest
from test_execution import RUN
from test_execution import allocated as allocated
from test_registry import registry as registry

from mobiraeon.contracts import Outcome
from mobiraeon.execution import ExecutionService, summary
from mobiraeon.execution_signal_verification import CASES, run_case
from mobiraeon.scenario import TARGET


@pytest.mark.parametrize("mode,first,second", CASES)
def test_real_signal_delivery_returns_and_restores(mode, first, second):
    result = run_case(mode, first, second)
    assert result["reaped"], result
    if mode == "nested":
        assert result["nested_delivery_observed"], result
        assert result["handler_entries"] == result["handler_returns"] == 2, result
    assert result["result"] == "passed", result
    completion = result["records"][-1]
    # The production handler itself must contain no calls, independent of the
    # scheduling trace and its observing/delegating test wrapper.
    assert completion["handler_call_opcodes"] == [], result


@pytest.mark.parametrize("case", ["close_stdout", "close_stderr", "before_seal"])
def test_capture_close_and_preseal_interruption_remain_fenced(allocated, monkeypatch, case):
    # Retain the independently demonstrated EOF/close and before-seal edges.
    registry, proof, _, reserved = allocated
    monkeypatch.setattr("mobiraeon.execution.actuation_lock", lambda private: nullcontext())

    class CloseFailure(io.BytesIO):
        def close(self):
            super().close()
            raise OSError("trusted close failure")

    class Process:
        def __init__(self, raw):
            self.stdin = io.BytesIO()
            self.stdout = CloseFailure(raw) if case == "close_stdout" else io.BytesIO(raw)
            self.stderr = CloseFailure() if case == "close_stderr" else io.BytesIO()

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    class Worker:
        def __init__(self, settings):
            pass

        def preflight(self):
            return {"trusted_edge_probe": True}

        def create(self, handoff, timeout=None):
            self.handoff = handoff
            return "b" * 64

        def start(self, identity, timeout=None):
            return Process(json.dumps(summary(self.handoff["input"]["content"])).encode())

        def cleanup(self, handoff, record):
            return True

        def inspect(self, handoff, identity=None, timeout=None):
            return {"State": {"StartedAt": "2026-11-02T00:00:00Z", "ExitCode": 0}}

    def hook(phase):
        if case == "before_seal" and phase == "before_seal":
            signal.raise_signal(signal.SIGTERM)
            signal.raise_signal(signal.SIGINT)

    previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    service = ExecutionService(
        registry.store, registry.private, reserved.settings, worker_type=Worker, hook=hook
    )
    result = service.invoke("execution.run", TARGET, RUN, proof=proof)
    _, record = service.load("task-1")
    assert result.outcome != Outcome.SUCCESS and not record["artifact_valid"]
    assert record["cleanup"] == "verified" and not record["held"]
    if case == "before_seal":
        assert record["stop_intent"] and record["outcome"] == "stopped"
    else:
        assert not record["capture_complete"]
        assert record["capture_channels"][case.removeprefix("close_")] == "failed"
    with registry.store.engine.connect() as tx:
        observed = [
            json.loads(r[0])
            for r in tx.exec_driver_sql(
                "SELECT record FROM coordination_facts WHERE stage='observe'"
            )
        ]
    assert not any(r["inputs"]["observation"] == "succeeded" for r in observed)
    assert all(signal.getsignal(s) == h for s, h in previous.items())
