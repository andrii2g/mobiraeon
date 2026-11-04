import json

import pytest

from mobiraeon.verification_final08_controls import (
    lifecycle_control,
    real_pipe_control,
    signal_control,
)


@pytest.mark.parametrize(
    "scenario",
    [
        "stop_raises",
        "stop_bad",
        "stop_ok",
        "stop_timeout",
        "stop_nonzero",
        "stop_malformed",
        "snapshot",
        "oversized",
        "oversized_storage",
    ],
)
def test_actual_signal_parent_retains_complete_evidence(scenario):
    result = signal_control(scenario)
    assert result["required_behavior"], result["required_checks"]


@pytest.mark.parametrize(
    "scenario",
    [
        "launch",
        "initialization",
        "setup",
        "stdout_read",
        "stderr_read",
        "readiness",
        "signal",
        "wait",
        "kill",
        "reap",
        "poll",
        "semantic",
        "stop",
        "close_stdout",
        "close_stderr",
        "stop+close_stdout",
        "close_stdout+close_stderr",
        "cleanup_stop",
        "cleanup_drain",
        "cleanup_close",
        "normalization",
        "snapshot_error",
        "passing",
    ],
)
def test_lifecycle_factorized_routes(scenario):
    result = lifecycle_control(scenario)
    assert result["required_behavior"], result
    assert json.loads(json.dumps(result))["required_behavior"]


@pytest.mark.parametrize("kind", ["no_eof", "delayed", "oversized", "multibyte"])
def test_real_bounded_pipes(kind):
    result = real_pipe_control(kind)
    if result.get("result") == "unavailable":
        pytest.skip("actual nonblocking Linux pipe qualification")
    assert result["required_behavior"], result


def test_bounded_aggregate_preserves_uuid_and_correlated_details():
    from mobiraeon.verification_final08_controls import aggregate_control

    result = aggregate_control()
    assert result["required_behavior"], result
