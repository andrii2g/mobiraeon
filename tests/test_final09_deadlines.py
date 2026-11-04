from pathlib import Path

import pytest

import mobiraeon.docker_worker as docker
from mobiraeon.errors import SafeError
from mobiraeon.verification_final09_deadlines import CASES, deadline_control

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("case", CASES)
def test_fixed_completion_cutoff_through_actual_dispatch_and_admission(case):
    observed = deadline_control(
        case, ROOT / "examples/execution.json", ROOT / "bootstrap/initial-test.json"
    )
    assert observed["required_behavior"], observed


def test_nested_completion_scope_cannot_extend_parent_and_always_resets(monkeypatch):
    clock = {"now": 100.0}
    monkeypatch.setattr(docker.time, "monotonic", lambda: clock["now"])
    assert docker._completion_cutoff.get() is None
    with docker.completion_deadline(101.0) as outer_remaining:
        with docker.completion_deadline(102.0) as inner_remaining:
            assert inner_remaining() == 1.0
            clock["now"] = 101.0
            with pytest.raises(SafeError):
                inner_remaining()
        assert docker._completion_cutoff.get() == 101.0
        with pytest.raises(SafeError):
            outer_remaining()
    assert docker._completion_cutoff.get() is None


def test_completion_scope_resets_when_scope_entry_is_already_exhausted(monkeypatch):
    monkeypatch.setattr(docker.time, "monotonic", lambda: 101.0)
    with pytest.raises(SafeError), docker.completion_deadline(101.0):
        pytest.fail("exhausted scope must not enter")
    assert docker._completion_cutoff.get() is None
