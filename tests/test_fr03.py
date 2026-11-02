"""FR-03: native nested delivery must return from both actual handlers."""

import importlib.util
import signal
from pathlib import Path

import pytest

from mobiraeon import cli

spec = importlib.util.spec_from_file_location(
    "foundation_probe", Path(__file__).parents[1] / "tools/foundation_signal_verification.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
CASES, run_case = probe.CASES, probe.run_case


@pytest.mark.parametrize("mode,first,second", CASES)
def test_fr03_native_nested_signals(mode, first, second):
    result = run_case(mode, first, second)
    assert result["reaped"] and result["result"] == "passed", result
    if mode == "nested":
        assert result["nested_delivery_observed"]
        assert result["handler_entries"] == result["handler_returns"] == 2


def test_fr03_exception_restoration():
    class Stop:
        def wait(self, timeout):
            raise RuntimeError("trusted wait failure")

    previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    if hasattr(signal, "SIGBREAK"):
        previous[signal.SIGBREAK] = signal.getsignal(signal.SIGBREAK)
    with pytest.raises(RuntimeError):
        cli.serve(Stop())
    assert all(signal.getsignal(s) == handler for s, handler in previous.items())
