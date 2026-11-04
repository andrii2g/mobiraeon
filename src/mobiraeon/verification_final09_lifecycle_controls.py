"""Trusted F9-R1 failure-order controls; no real signal or Worker qualification."""

import contextlib
import io
import itertools
import subprocess
from unittest.mock import patch

from mobiraeon import execution_diagnostics as diagnostics
from mobiraeon import signal_verification as signals

CASES = (
    "read_then_wait_error",
    "read_then_wait_timeout",
    "read_then_wait_success",
    "parse_then_wait_error",
    "two_normal_read_errors",
    "stdout_value_error",
    "old_then_new_cleanup_read",
    "two_new_cleanup_reads",
    "semantic_then_multiple_cleanup_errors",
    "semantic_reused_error",
    "cleanup_read_is_primary",
    "observer_failure_does_not_skip_other_stream",
    "passing",
)


class FirstReadFailure(OSError):
    pass


class SecondReadFailure(OSError):
    pass


class LaterWaitFailure(OSError):
    pass


class SemanticFailure(AssertionError):
    pass


class StopFailure(OSError):
    pass


class CloseFailure(OSError):
    pass


class ObserverFailure(OSError):
    pass


def run_case(scenario):
    """Exercise actual collection, wait, reporting and independent finalizers."""
    if scenario not in CASES:
        raise ValueError("unknown lifecycle control")
    checks = diagnostics.CheckLog("trusted-image", module=signals.__file__)
    checks.activate(
        "f9_signal_order",
        "signal_supervision",
        mode="stubborn_child",
        variant=scenario,
        phase="SIGINT",
        expected="first observed failure remains primary and later failures stay ordered",
    )
    case = dict(
        case="f9_signal_order",
        command=["trusted-synthetic-child"],
        exit_code=None,
        stdout="",
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
        parse_status="not_attempted",
        timed_out=False,
    )
    checks.append(case)
    events = []
    cleanup = [False]
    reused_error = StopFailure("fixed nonsecret reused finalizer control")
    late_reads = scenario in {
        "old_then_new_cleanup_read",
        "two_new_cleanup_reads",
        "semantic_then_multiple_cleanup_errors",
        "cleanup_read_is_primary",
    }
    normal_both = scenario in {
        "two_normal_read_errors",
        "observer_failure_does_not_skip_other_stream",
    }

    class Stream(io.StringIO):
        def __init__(self, name):
            super().__init__()
            self.name = name
            self.reads = 0
            self.failed = False

        def read(self, size=-1):
            self.reads += 1
            if self.reads == 1:
                return (
                    '{"data":{"state":"running"}}\n'
                    if self.name == "stdout"
                    else "F9_STDERR_PREFIX\n"
                )
            failure = None
            if self.name == "stdout":
                if normal_both:
                    failure = FirstReadFailure
                elif scenario == "stdout_value_error":
                    failure = ValueError
                elif scenario == "parse_then_wait_error" and self.reads == 2:
                    events.append("parse_failure")
                    return "F9_INVALID_AFTER_RUNNING\n"
                elif late_reads:
                    if not cleanup[0]:
                        raise BlockingIOError
                    failure = SecondReadFailure
            else:
                if normal_both:
                    failure = SecondReadFailure
                elif (
                    scenario.startswith("read_then_") or scenario == "old_then_new_cleanup_read"
                ):
                    failure = FirstReadFailure
                elif late_reads:
                    if not cleanup[0]:
                        raise BlockingIOError
                    if scenario != "old_then_new_cleanup_read":
                        failure = FirstReadFailure
            if failure is not None:
                assert not self.failed, "a failed channel was read again"
                self.failed = True
                events.append(self.name + ":" + failure.__name__)
                raise failure("fixed nonsecret stream control")
            return ""

        def close(self):
            events.append("close_" + self.name)
            super().close()
            if scenario == "semantic_reused_error" and self.name == "stdout":
                raise reused_error
            if scenario == "semantic_then_multiple_cleanup_errors" and self.name == "stdout":
                raise CloseFailure("fixed nonsecret close control")

    class Process:
        def __init__(self, *unused, **kwargs):
            self.stdout, self.stderr = Stream("stdout"), Stream("stderr")
            self.returncode = None

        def poll(self):
            return self.returncode

        def send_signal(self, signum):
            events.append("signal")

        def wait(self, timeout=None):
            events.append("wait")
            if self.returncode is not None:
                return self.returncode
            if scenario == "read_then_wait_timeout":
                raise subprocess.TimeoutExpired("trusted-synthetic-child", timeout)
            self.returncode = 1
            if scenario in {"read_then_wait_error", "parse_then_wait_error"}:
                raise LaterWaitFailure("fixed nonsecret wait control")
            return self.returncode

        def kill(self):
            events.append("kill")
            self.returncode = -9

    life = signals.SignalLifecycle(checks, case, None)
    original_capture = checks.capture_failure
    capture_calls = [0]

    def capture(error):
        capture_calls[0] += 1
        if capture_calls[0] == 1:
            raise ObserverFailure("fixed nonsecret observer control")
        return original_capture(error)

    clock = itertools.count(0, 0.1)
    with (
        patch.object(signals.time, "monotonic", side_effect=lambda: next(clock)),
        patch.object(signals.time, "sleep"),
        patch.object(checks, "capture_failure", side_effect=capture)
        if scenario == "observer_failure_does_not_skip_other_stream"
        else contextlib.nullcontext(),
    ):
        try:
            life.launch(Process, case["command"])
            life.running(30)
            if scenario in {
                "two_new_cleanup_reads",
                "semantic_then_multiple_cleanup_errors",
                "semantic_reused_error",
            }:
                raise SemanticFailure("fixed nonsecret semantic mismatch")
            life.wait(12, "signal_wait")
            if scenario != "cleanup_read_is_primary":
                life.collector.finish(14)
            case["result"] = "passed"
        except Exception as error:
            life.failure(error)

        def stop():
            events.append("authorized_stop")
            cleanup[0] = True
            if scenario == "semantic_reused_error":
                checks.active["stage"] = "cli_stop"
                raise reused_error
            if scenario == "semantic_then_multiple_cleanup_errors":
                raise StopFailure("fixed nonsecret stop control")

        life.finalize(stop)
    report = (
        checks.retained_failure()
        if checks.captured_failure
        else {"result": "passed", "checks": list(checks)}
    )
    observations = case["failure_observations"]
    kinds = [r["failure_type"] for r in observations]
    actions = [r["action"] for r in case["finalization_actions"]]
    required = all(
        n in actions
        for n in (
            "authorized_stop",
            "collector_cancel",
            "close_stdout",
            "close_stderr",
            "final_poll",
        )
    )
    required &= case["exit_code"] == (-9 if scenario == "read_then_wait_timeout" else 1)
    required &= "F9_STDERR_PREFIX" in case["stderr"]
    required &= all(r["sequence"] == index + 1 for index, r in enumerate(observations))
    if scenario == "passing":
        required &= report["result"] == "passed" and not observations
    else:
        expected = (
            "JSONDecodeError"
            if scenario == "parse_then_wait_error"
            else "SemanticFailure"
            if scenario
            in {
                "two_new_cleanup_reads",
                "semantic_then_multiple_cleanup_errors",
                "semantic_reused_error",
            }
            else "ValueError"
            if scenario == "stdout_value_error"
            else "SecondReadFailure"
            if scenario == "cleanup_read_is_primary"
            else "FirstReadFailure"
        )
        required &= report["result"] == "failed" and report["failure_type"] == expected
        required &= (
            case["failure_type"] == expected and observations[0]["failure_type"] == expected
        )
        required &= observations[0]["primary"] and sum(r["primary"] for r in observations) == 1
        required &= report["failure_site"] == observations[0]["failure_site"]
        required &= all(r["failure_site"] is not None for r in observations)
        required &= report["active"]["stage"] == (
            "signal_finalization_collector_cancel"
            if scenario == "cleanup_read_is_primary"
            else "signal_supervision"
        )
    if scenario in {"read_then_wait_error", "parse_then_wait_error"}:
        required &= kinds.count("LaterWaitFailure") == 1 and kinds.index("LaterWaitFailure") > 0
        required &= "kill" not in events
    if scenario == "read_then_wait_timeout":
        required &= kinds.count("TimeoutExpired") == 1 and kinds.index("TimeoutExpired") > 0
        required &= "kill" in events
    if normal_both or scenario == "old_then_new_cleanup_read":
        required &= kinds.count("FirstReadFailure") == kinds.count("SecondReadFailure") == 1
        if normal_both:
            required &= [r["channel"] for r in observations[:2]] == ["stdout", "stderr"]
        else:
            required &= observations[kinds.index("SecondReadFailure")]["stage"].startswith(
                "signal_finalization_"
            )
    if scenario in {"two_new_cleanup_reads", "semantic_then_multiple_cleanup_errors"}:
        required &= kinds.count("FirstReadFailure") == kinds.count("SecondReadFailure") == 1
        required &= (
            kinds.index("SemanticFailure")
            < kinds.index("SecondReadFailure")
            < kinds.index("FirstReadFailure")
        )
    if scenario == "semantic_then_multiple_cleanup_errors":
        required &= kinds.count("StopFailure") == kinds.count("CloseFailure") == 1
        required &= (
            kinds.index("StopFailure")
            < kinds.index("SecondReadFailure")
            < kinds.index("CloseFailure")
        )
    if scenario == "semantic_reused_error":
        reused = [r for r in observations if r["failure_type"] == "StopFailure"]
        required &= [r["source"] for r in reused] == ["authorized_stop", "close_stdout"]
        required &= [r["stage"] for r in reused] == [
            "signal_finalization_authorized_stop",
            "signal_finalization_close_stdout",
        ]
        required &= reused[0]["operation_stage"] == "cli_stop"
    if scenario == "observer_failure_does_not_skip_other_stream":
        required &= case["collection_observer_failure_count"] == 1
        required &= case["collection_observer_failures"][0]["failure_type"] == "ObserverFailure"
    if scenario == "stdout_value_error":
        required &= life.collector.channels["stdout"]["status"] == "failed"
        required &= kinds.count("ValueError") == 1 and life.process.stdout.reads == 2
    return dict(
        required_behavior=bool(required),
        scenario=scenario,
        case=diagnostics.unavailable_observations(case),
        report=report,
        event_order=events,
        scope=(
            "Trusted portable observations through actual signal lifecycle; "
            "no real Worker/native signal claim."
        ),
    )
