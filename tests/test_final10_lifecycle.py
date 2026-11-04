import json

import pytest

from mobiraeon import signal_verification as signals
from mobiraeon.verification_final10_controls import CASES, run_case


@pytest.mark.parametrize("scenario", CASES)
def test_bounded_progress_policy_and_raw_finalization(scenario):
    result = run_case(scenario)
    assert result["required_behavior"], result
    assert json.loads(json.dumps(result))["required_behavior"]


def test_shared_progress_parser_bounds_line_before_decoding(monkeypatch):
    def unexpected_decode(line):
        raise AssertionError("over-limit input reached the JSON decoder")

    monkeypatch.setattr(signals.json, "loads", unexpected_decode)
    with pytest.raises(ValueError, match="progress line exceeds retained bound"):
        signals.parse_progress_record(" " * (signals.LIMIT + 1))
