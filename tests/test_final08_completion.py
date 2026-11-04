from pathlib import Path

import pytest

from mobiraeon.verification_completion_controls import budget_control, completion_control

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "case",
    [
        "finished_one",
        "finished_zero",
        "missing",
        "running",
        "unfinished",
        "invalid_exit",
        "attachment_only",
        "capture_only",
        "cleanup_zero",
        "cleanup_one",
        "transport_timeout",
        "launch",
        "nonzero",
        "malformed",
        "engine",
        "ownership",
        "storage",
        "truncation",
        "observed_unavailable",
        "observed_owned_finished",
    ],
)
def test_actual_supervisor_completion_and_conservatism(case):
    state = dict(
        Running=False,
        ExitCode=1,
        StartedAt="2026-11-04T00:00:00Z",
        FinishedAt="2026-11-04T00:00:01Z",
    )
    result = completion_control(
        case,
        ROOT / "examples/execution.json",
        ROOT / "bootstrap/initial-test.json",
        observed=state,
    )
    assert result["required_behavior"], result
    if case == "observed_unavailable":
        assert result["required_failure_predicate"] is False
        assert result["observations"] == []
    if case == "observed_owned_finished":
        assert result["required_failure_predicate"] is True
        assert result["observations"] == ["failed"]


@pytest.mark.parametrize(
    "case",
    [
        "exhausted",
        "under_minimum",
        "info_consumes",
        "late_result",
        "timeout",
        "launch",
        "nonzero",
        "malformed",
        "engine",
        "ownership",
    ],
)
def test_actual_inspection_budget_and_errors(case):
    result = budget_control(case)
    assert result["required_behavior"], result
