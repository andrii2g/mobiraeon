"""Timing evidence remains bounded and cannot override a failed signal deadline."""

import json
import subprocess

from mobiraeon import execution_signal_verification as probe


def test_completed_signal_child_still_fails_when_initial_communicate_times_out(monkeypatch):
    records = [
        {"timing": "before_execution_import", "monotonic_ns": 10},
        {"timing": "after_execution_import", "monotonic_ns": 20},
        *[
            {"event": event, "depth": 1, "signal": "SIGTERM"}
            for _ in range(5)
            for event in ("enter", "return")
        ],
        {
            "completed": True,
            "pending": True,
            "restored": True,
            "nested_scheduled": False,
            "handler_call_opcodes": [],
            "timing": "semantic_completion",
            "monotonic_ns": 30,
        },
    ]
    stdout = "".join(json.dumps(record) + "\n" for record in records)
    observed = {"timeouts": [], "killed": 0}

    class Process:
        returncode = None

        def __init__(self, command, **kwargs):
            self.command = command
            assert kwargs["stdout"] == kwargs["stderr"] == subprocess.PIPE
            assert kwargs["text"] is True

        def communicate(self, *, timeout):
            observed["timeouts"].append(timeout)
            if len(observed["timeouts"]) == 1:
                raise subprocess.TimeoutExpired(self.command, timeout, stdout, "")
            self.returncode = -9
            return stdout, ""

        def kill(self):
            observed["killed"] += 1

        def poll(self):
            return self.returncode

    monkeypatch.setattr(probe.subprocess, "Popen", Process)
    observed_ns = iter(range(100, 1000, 10))
    monkeypatch.setattr(probe.time, "monotonic_ns", lambda: next(observed_ns))
    result = probe.run_case("spaced", "SIGTERM", "SIGINT")

    assert observed == {"timeouts": [4, 3], "killed": 1}
    assert result["result"] == "failed" and result["timed_out"]
    assert result["exit_code"] == -9 and result["reaped"]
    assert result["handler_entries"] == result["handler_returns"] == 5
    assert result["records"][-1]["completed"]
    assert result["timing"]["deadline_seconds"] == 4
    assert result["timing"]["post_kill_seconds"] == 3
    parent = result["timing"]["parent"]
    assert result["timing"]["communicate_reference_deadline_ns"] == (
        parent["communicate_started_ns"] + 4_000_000_000
    )
    assert list(parent) == [
        "popen_started_ns",
        "popen_returned_ns",
        "communicate_started_ns",
        "communicate_timed_out_ns",
        "kill_started_ns",
        "kill_returned_ns",
        "reap_communicate_started_ns",
        "reap_communicate_returned_ns",
    ]
    assert list(parent.values()) == sorted(parent.values())
    assert result["timing"]["child"] == {
        "before_execution_import": 10,
        "after_execution_import": 20,
        "semantic_completion": 30,
    }


def test_real_signal_timing_anchors_preserve_final_completion_record():
    result = probe.run_case("single", "SIGTERM", "SIGINT")
    assert result["result"] == "passed", result
    assert result["reaped"] and not result["timed_out"], result
    assert result["records"][-1]["completed"], result
    assert result["records"][-1]["handler_call_opcodes"] == [], result
    timing = result["timing"]
    assert timing["clock"] == "monotonic_ns"
    assert timing["deadline_seconds"] == 4 and timing["post_kill_seconds"] == 3
    child = timing["child"]
    assert list(child) == [
        "before_execution_import",
        "after_execution_import",
        "semantic_completion",
    ]
    assert all(type(value) is int for value in child.values())
    assert list(child.values()) == sorted(child.values())
    parent = timing["parent"]
    assert list(parent) == [
        "popen_started_ns",
        "popen_returned_ns",
        "communicate_started_ns",
        "communicate_returned_ns",
    ]
    assert all(type(value) is int for value in parent.values())
    assert list(parent.values()) == sorted(parent.values())
    # Two import markers are additive; completion remains the final record and
    # the one-signal observation still has exactly one entry and one return.
    assert len(result["records"]) == 6
    assert result["handler_entries"] == result["handler_returns"] == 1
