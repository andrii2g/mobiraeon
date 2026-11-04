"""Moderate progress-policy controls; trusted observations, no Worker qualification."""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mobiraeon import execution_diagnostics as diagnostics
from mobiraeon import signal_verification as signals

CASES = (
    "depth64",
    "depth65",
    "quoted_chunk_boundaries",
    "parser_exception",
    "read_value_error",
    "decode_exception",
    "parent_depth65",
    "parent_parser_exception",
)
TAIL = "F10_HEALTHY_RAW_STDOUT_TAIL"
FAULT_LINE = '{"parser_fault":true}\n'


class ParserFailure(RuntimeError):
    pass


class DecoderFailure(UnicodeError):
    pass


def _payload(depth):
    # The root object is depth1, so these arrays add depth-1 containers.
    return '{"nested":' + "[" * (depth - 1) + "0" + "]" * (depth - 1) + "}\n"


def _parser(original, calls):
    def parse(line, *args, **kwargs):
        calls.append(line)
        if line == FAULT_LINE:
            raise ParserFailure("fixed nonsecret parser fault")
        return original(line, *args, **kwargs)

    return parse


def _direct(scenario):
    checks = diagnostics.CheckLog("trusted-progress-policy", module=signals.__file__)
    checks.activate("f10_progress_policy", "signal_supervision", variant=scenario)
    case = dict(
        case="f10_progress_policy",
        command=["trusted-owned-child"],
        stdout="",
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
        parse_status="not_attempted",
        exit_code=None,
    )
    checks.append(case)
    body = _payload(64 if scenario == "depth64" else 65)
    if scenario == "quoted_chunk_boundaries":
        prefix = '{"quoted":"'
        # A final backslash in the first read escapes the next chunk's quote.
        # The brackets remain string contents, not container levels.
        body = prefix + "a" * (4095 - len(prefix)) + '\\"' + "[{}]" * 70 + '\\\\"}\n'
    elif scenario == "parser_exception":
        body = FAULT_LINE
    if scenario == "depth65":
        body = body.removesuffix("\n")  # Reject at depth65, before any future newline.
    parts = [body]
    events, calls = [], []

    class Stream(io.StringIO):
        def __init__(self, name):
            super().__init__()
            self.name, self.reads = name, 0
            self.parts = (
                ['{"data":{"state":"running"}}\n', *parts, json.dumps({"tail": TAIL}) + "\n"]
                if name == "stdout"
                else ["F10_STDERR_PREFIX\n"]
            )

        def read(self, size=-1):
            self.reads += 1
            if self.name == "stdout" and scenario == "read_value_error" and self.reads == 2:
                raise ValueError("fixed physical read failure")
            piece = self.parts.pop(0) if self.parts else ""
            if len(piece) > size:
                piece, rest = piece[:size], piece[size:]
                self.parts.insert(0, rest)
            return piece.encode() if scenario == "decode_exception" else piece

        def close(self):
            events.append("close_" + self.name)
            super().close()

    class Process:
        def __init__(self):
            self.stdout, self.stderr = Stream("stdout"), Stream("stderr")

        def poll(self):
            return 1

        def wait(self, timeout=None):
            return 1

        def send_signal(self, value):
            events.append("signal")

        def kill(self):
            events.append("kill")

    class BrokenDecoder:
        def decode(self, *args, **kwargs):
            raise DecoderFailure("fixed physical decoder failure")

    life = signals.SignalLifecycle(checks, case, None)
    with (
        contextlib.redirect_stdout(io.StringIO()),
        patch.object(signals.json, "loads", side_effect=_parser(json.loads, calls)),
    ):
        life.launch(lambda *args, **kwargs: Process(), case["command"])
        life.running(10**12)
        if scenario == "decode_exception":
            life.collector.channels["stdout"]["decoder"] = BrokenDecoder()
        try:
            for _unused in range(len(parts) + 3):
                life.collector.pump()
            case["result"] = "passed"
        except Exception as error:
            life.failure(error)
        line_released = not life.collector.line
        parsing_stopped = not life.collector.parsing
        life.finalize(lambda: events.append("authorized_stop"))
    report = (
        checks.retained_failure()
        if checks.captured_failure
        else {"result": "passed", "checks": list(checks)}
    )
    passing = scenario in {"depth64", "quoted_chunk_boundaries"}
    physical = scenario in {"read_value_error", "decode_exception"}
    expected = {
        "depth65": "ProgressNestingError",
        "parser_exception": "ParserFailure",
        "read_value_error": "ValueError",
        "decode_exception": "DecoderFailure",
    }.get(scenario)
    requirements = {
        "known_exit": case["exit_code"] == 1,
        "stderr_retained": "F10_STDERR_PREFIX" in case["stderr"],
        "independent_finalizers": events[-3:]
        == ["authorized_stop", "close_stdout", "close_stderr"],
        "handles_closed": life.process.stdout.closed and life.process.stderr.closed,
        "line_released": line_released,
        "raw_tail_or_terminal_physical_error": (
            life.collector.channels["stdout"]["status"] == "failed"
            and life.process.stdout.reads == 2
            if physical
            else TAIL in case["stdout"] and case["collection_complete"]
        ),
    }
    if passing:
        requirements["accepted_without_failure"] = (
            report["result"] == "passed" and case["parse_status"] == "parsed"
        )
    else:
        observation = case["failure_observations"][0]
        requirements.update(
            correct_first_error=report["failure_type"] == expected,
            fixed_primary=observation["primary"]
            and report["failure_site"] == observation["failure_site"]
            and report["active"]["stage"] == "signal_supervision",
            correct_failure_boundary=observation["source"]
            == ("collector_read" if scenario == "read_value_error" else "collector_decode")
            if physical
            else observation["source"] == "collector_parse" and "stdout_read_error" not in case,
        )
        if not physical:
            requirements["parsing_stopped"] = parsing_stopped
    if scenario == "depth65":
        requirements["rejected_before_json_decoder_or_newline"] = (
            body not in calls and case["parse_status"] == "progress_nesting_limit_exceeded"
        )
    elif scenario == "parser_exception":
        requirements["parser_status_truthful"] = (
            case["parse_status"] == "progress_parser_failed"
        )
    elif scenario == "quoted_chunk_boundaries":
        requirements["escape_crosses_read_boundary"] = (
            body[4095:4097] == '\\"' and body in calls
        )
    return dict(
        scenario=scenario,
        required_behavior=all(requirements.values()),
        requirements=requirements,
        case=diagnostics.unavailable_observations(case),
        report=report,
        scope="Trusted observations through actual lifecycle; no native Worker claim.",
    )


def _parent(scenario):
    import mobiraeon.execution_repair_verification as nested
    import mobiraeon.execution_verification as parent
    from mobiraeon.contracts import Outcome
    from mobiraeon.verification_repair_controls import miniature_fixture, operation

    body = _payload(65) if scenario == "parent_depth65" else FAULT_LINE
    payload = body + "x" * 4200 + TAIL + "\n"
    closed, calls = [], []
    record = dict(
        outcome="failed",
        cleanup="verified",
        artifact_valid=False,
        held=False,
        terminal=True,
        capture_complete=False,
        capture_channels={"stdout": "failed", "stderr": "failed"},
        seal="f10-control-seal",
    )

    class Stream(io.StringIO):
        def __init__(self, name):
            super().__init__(payload if name == "stdout" else "F10_STDERR_PREFIX\n")
            self.name = name

        def close(self):
            closed.append(self.name)
            super().close()

    class Process:
        def __init__(self, *args, **kwargs):
            self.stdout, self.stderr = Stream("stdout"), Stream("stderr")
            self.returncode = None

        def poll(self):
            return self.returncode

        def send_signal(self, value):
            self.returncode = 1

        def wait(self, timeout=None):
            self.returncode = 1
            return 1

        def kill(self):
            self.returncode = -9

    class Execution:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, *args, **kwargs):
            return operation(Outcome.FAILURE)

        def load(self, *args):
            return {}, record.copy()

    def command(argv, **kwargs):
        if argv[1:3] == ["-m", "mobiraeon.execution_fixture"]:
            directory = Path(argv[argv.index("--directory") + 1])
            miniature_fixture(directory, record=record)
            return subprocess.CompletedProcess(argv, 0, '{"prepared":true}', "")
        assert argv[-2:] in (["execution", "stop"], ["execution", "status"]), argv
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"data": {"records": [record]}}), ""
        )

    def compose(*args, **kwargs):
        checks = diagnostics.CheckLog("trusted-progress-policy")
        checks.append({"case": "earlier_outer_uuid", "operation": asdict(operation())})
        with diagnostics.verification_workspace(checks):
            parent.verify_nested_repairs(
                checks, Path("input"), Path("catalog"), "trusted-image"
            )
        raise AssertionError("trusted parser fault must be reached")

    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        patch.object(sys, "platform", "linux"),
        patch.object(parent, "exercise", compose),
        patch.object(nested.subprocess, "run", side_effect=command),
        patch.object(nested.subprocess, "Popen", Process),
        patch.object(nested, "ExecutionService", Execution),
        patch.object(nested, "PrivateState", return_value=SimpleNamespace()),
        patch.object(nested, "proof_for", return_value="trusted-observation"),
        patch.object(signals.json, "loads", side_effect=_parser(json.loads, calls)),
        patch.object(
            sys,
            "argv",
            [
                "trusted-parent",
                "--input",
                "input",
                "--catalog-input",
                "catalog",
                "--image-id",
                "trusted-image",
            ],
        ),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        code = parent.main()
    report = json.loads(stdout.getvalue())
    nested_report = report["checks"][-1]["regressions"]
    case = next(
        c for c in nested_report["checks"] if c.get("case", "").startswith("execution_")
    )
    durable = {
        name: json.loads(Path(value["diagnostic_storage"]["path"]).read_text(encoding="utf-8"))
        for name, value in (("parent", report), ("nested", nested_report))
    }
    expected = "ProgressNestingError" if scenario == "parent_depth65" else "ParserFailure"
    requirements = dict(
        parent_nonzero=code == 1 and report["result"] == "failed",
        first_error_retained=report["failure_type"] == expected,
        context_retained=report["active"]["case"] == "execution_SIGINT"
        and report["active"]["stage"] == "signal_supervision",
        failure_site_retained=report["failure_site"]
        == case["failure_observations"][0]["failure_site"],
        raw_tail_retained=TAIL in case["stdout"],
        stderr_retained="F10_STDERR_PREFIX" in case["stderr"],
        healthy_eof=case["collection_complete"],
        known_exit=case["exit_code"] == 1,
        handles_closed=set(closed) == {"stdout", "stderr"},
        durable_roundtrip=durable["parent"] == report and durable["nested"] == nested_report,
        earlier_capture_cases=len(nested_report["checks"]) >= 3,
    )
    result = dict(
        scenario=scenario,
        required_behavior=all(requirements.values()),
        requirements=requirements,
        case=case,
        parent_report=report,
        scope="Trusted nested exercise and parent main; no native Worker claim.",
    )
    for root in {
        Path(value["protected_state"]["directory"]) for value in (report, nested_report)
    }:
        assert root.parent.resolve() == Path(tempfile.gettempdir()).resolve()
        assert root.name.startswith("mobiraeon-execution-check-")
        assert not list(root.rglob("*.token")) and not list(root.rglob("credentials"))
        shutil.rmtree(root)
    return result


def run_case(scenario):
    if scenario not in CASES:
        raise ValueError("unknown progress policy control")
    return _parent(scenario) if scenario.startswith("parent_") else _direct(scenario)
