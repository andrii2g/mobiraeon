import json

import pytest

from mobiraeon.verification_final09_lifecycle_controls import CASES, run_case


@pytest.mark.parametrize("scenario", CASES)
def test_first_error_and_later_independent_finalization(scenario):
    result = run_case(scenario)
    assert result["required_behavior"], result
    assert json.loads(json.dumps(result))["required_behavior"]
