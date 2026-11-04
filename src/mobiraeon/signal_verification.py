"""Owned, bounded signal-probe lifecycle. No execution or workflow authority."""

import codecs
import json
import os
import signal
import subprocess
import time
from collections import deque

LIMIT = 262144
PROGRESS_NESTING_LIMIT = 64


class ProgressNestingError(ValueError):
    """A progress record exceeds the verifier's supported container depth."""


class _ProgressNesting:
    def __init__(self):
        self.depth = 0
        self.quoted = False
        self.escaped = False

    def feed(self, text):
        for character in text:
            if self.quoted:
                if self.escaped:
                    self.escaped = False
                elif character == "\\":
                    self.escaped = True
                elif character == '"':
                    self.quoted = False
            elif character == '"':
                self.quoted = True
            elif character in "[{":
                self.depth += 1
                if self.depth > PROGRESS_NESTING_LIMIT:
                    raise ProgressNestingError(
                        "progress JSON nesting exceeds 64 containers, including the root"
                    )
            elif character in "]}":
                self.depth = max(0, self.depth - 1)


def parse_progress_record(line):
    """Parse verifier progress with a bounded, quote-aware container policy."""
    if len(line) > LIMIT:
        raise ValueError("progress line exceeds retained bound")
    _ProgressNesting().feed(line)
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("progress must be a record")
    return value


class PipeCollector:
    """One nonblocking consumer per pipe; cancellation never waits for future EOF."""

    def __init__(self, process, case):
        self.process, self.case = process, case
        self.channels = {
            name: dict(
                stream=None,
                fd=None,
                status="pending",
                decoder=codecs.getincrementaldecoder("utf-8")("replace"),
            )
            for name in ("stdout", "stderr")
        }
        self.events = deque(maxlen=16)
        self.error = None
        self.observe_error = None
        self.pending_errors = deque()
        self.line = ""
        self.parsing = True
        self.nesting = _ProgressNesting()

    def failed(self, error, name, phase):
        if self.error is None:
            self.error = error
        self.pending_errors.append((error, name, phase))
        self.notify_errors()

    def notify_errors(self):
        while self.observe_error is not None and self.pending_errors:
            error, name, phase = self.pending_errors[0]
            try:
                self.observe_error(error, name, phase)
            except Exception as diagnostic_error:
                failures = self.case.setdefault("collection_observer_failures", [])
                self.case["collection_observer_failure_count"] = (
                    self.case.get("collection_observer_failure_count", 0) + 1
                )
                if len(failures) < 8:
                    failures.append(
                        dict(
                            channel=name,
                            phase=phase,
                            failure_type=type(diagnostic_error).__name__,
                        )
                    )
                break
            else:
                self.pending_errors.popleft()

    def start(self):
        failure = None
        for name in ("stdout", "stderr"):
            channel = self.channels[name]
            try:
                stream = getattr(self.process, name)
                channel["stream"] = stream
                try:
                    fd = stream.fileno()
                except AttributeError, OSError, ValueError:
                    import io

                    if not isinstance(stream, (io.StringIO, io.BytesIO)):
                        raise
                else:
                    os.set_blocking(fd, False)
                    channel["fd"] = fd
            except Exception as error:
                channel["status"] = "failed"
                self.case[name + "_setup_error"] = type(error).__name__
                self.failed(error, name, "setup")
                if failure is None:
                    failure = error
        if failure is not None:
            raise failure

    def _text(self, name, text):
        previous = self.case[name]
        self.case[name + "_truncated"] |= len(previous) + len(text) > LIMIT
        self.case[name] = (previous + text)[:LIMIT]

    def _progress(self, text):
        # The read chunk is bounded BEFORE assembling/parsing any logical line.
        for piece in text.splitlines(keepends=True):
            if len(self.line) + len(piece) > LIMIT:
                self.case["parse_status"] = "oversized_progress_line"
                raise ValueError("progress line exceeds retained bound")
            self.nesting.feed(piece)
            self.line += piece
            if self.line.endswith(("\n", "\r")):
                self._line()

    def _line(self):
        line, self.line = self.line, ""
        self.nesting = _ProgressNesting()
        value = parse_progress_record(line)
        self.case["parse_status"] = "parsed"
        self.events.append(value)

    def _parse_failed(self, error):
        if isinstance(error, ProgressNestingError):
            self.case["parse_status"] = "progress_nesting_limit_exceeded"
        elif self.case["parse_status"] != "oversized_progress_line":
            self.case["parse_status"] = (
                "invalid_or_nonobject_json"
                if isinstance(error, ValueError)
                else "progress_parser_failed"
            )
        self.parsing = False
        self.line = ""
        self.nesting = None
        self.failed(error, "stdout", "parse")

    def pump(self, *, strict=True):
        for name, channel in self.channels.items():
            if channel["status"] != "pending":
                continue
            try:
                raw = (
                    os.read(channel["fd"], 4096)
                    if channel["fd"] is not None
                    else channel["stream"].read(4096)
                )
            except BlockingIOError:
                continue
            except Exception as error:
                channel["status"] = "failed"
                self.case[name + "_read_error"] = type(error).__name__
                self.failed(error, name, "read")
                continue
            try:
                text = (
                    channel["decoder"].decode(raw, final=not raw)
                    if isinstance(raw, bytes)
                    else raw
                )
            except Exception as error:
                channel["status"] = "failed"
                self.case[name + "_decode_error"] = type(error).__name__
                self.failed(error, name, "decode")
                continue
            if not raw:
                channel["status"] = "eof"
            try:
                self._text(name, text)
            except Exception as error:
                channel["status"] = "failed"
                self.case[name + "_retention_error"] = type(error).__name__
                self.failed(error, name, "retain")
                continue
            if name == "stdout" and self.parsing:
                try:
                    self._progress(text)
                    if not raw and self.line:
                        self._line()
                except Exception as error:
                    self._parse_failed(error)
        self.case["collection_channels"] = {n: c["status"] for n, c in self.channels.items()}
        self.notify_errors()
        if strict and self.error is not None:
            raise self.error

    def finish(self, deadline, *, strict=True):
        while any(c["status"] == "pending" for c in self.channels.values()):
            self.pump(strict=False)
            if time.monotonic() >= deadline:
                break
            if any(c["status"] == "pending" for c in self.channels.values()):
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        self.pump(strict=False)
        self.case["collection_complete"] = bool(self.channels) and all(
            c["status"] == "eof" for c in self.channels.values()
        )
        self.case["collection_cancelled"] = not self.case["collection_complete"]
        if strict:
            if self.error is not None:
                raise self.error
            assert self.case["collection_complete"], (
                "pipe collection did not reach EOF within existing reader allowance"
            )


class SignalLifecycle:
    def __init__(self, checks, case, directory):
        self.checks, self.case, self.directory = checks, case, directory
        self.process = None
        self.collector = None
        self.actions = case.setdefault("finalization_actions", [])
        self.observed_errors = []
        self.case["failure_observations"] = []
        self.case["final_exit_observation"] = {"available": False, "reason": "not_observed"}

    def launch(self, factory, argv, **kwargs):
        # Allocate collection state before Popen; no owned process exists if this fails.
        self.collector = PipeCollector(None, self.case)
        self.collector.observe_error = self.collection_failure
        self.process = factory(argv, **kwargs)
        self.collector.process = self.process
        self.collector.start()

    def exit_observation(self, value, stage):
        observation = {"available": value is not None, "value": value, "stage": stage}
        self.case["last_exit_status_observation"] = observation
        if value is not None or not self.case["final_exit_observation"]["available"]:
            self.case["final_exit_observation"] = observation
        if value is not None:
            self.case["exit_code"] = value

    def poll(self, stage):
        value = self.process.poll()
        self.exit_observation(value, stage)
        return value

    def running(self, deadline):
        while True:
            self.collector.pump()
            while self.collector.events:
                event = self.collector.events.popleft()
                if event.get("data") and event["data"].get("state") == "running":
                    return
            if self.poll("readiness") is not None:
                raise RuntimeError("supervisor exited before running progress")
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(self.case["command"], 30)
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))

    def wait(self, deadline, stage, *, strict=True):
        while True:
            if self.collector is not None:
                self.collector.pump(strict=strict)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(self.case["command"], 0)
            try:
                value = self.process.wait(timeout=min(0.05, remaining))
            except subprocess.TimeoutExpired:
                continue
            self.exit_observation(value, stage)
            return value

    def failure(self, error):
        self.record_failure(error, "supervision")

    def collection_failure(self, error, channel, phase):
        self.record_failure(error, "collector_" + phase, channel=channel)

    def record_failure(self, error, source, *, channel=None, operation_stage=None):
        if any(
            observed is error
            and (source == "supervision" or (source, channel) == (origin, stream))
            for observed, origin, stream in self.observed_errors
        ):
            return
        if "failure_type" not in self.case:
            self.case["pre_cleanup_exit_code"] = self.case.get("exit_code")
            self.case["streams_before_cleanup"] = {
                n: {"characters": len(self.case[n]), "truncated": self.case[n + "_truncated"]}
                for n in ("stdout", "stderr")
            }
            self.case.update(
                failure_type=type(error).__name__,
                timed_out=isinstance(error, subprocess.TimeoutExpired),
            )
        self.case["result"] = "failed"
        primary = self.checks.captured_failure is None
        self.checks.capture_failure(error)
        self.observed_errors.append((error, source, channel))
        try:
            observation = self.checks.failure(error)
        except Exception as diagnostic_error:
            observation = {
                "failure_site": None,
                "pre_cleanup_snapshot": {
                    "available": False,
                    "failure_type": type(diagnostic_error).__name__,
                },
            }
        entry = dict(
            sequence=len(self.case["failure_observations"]) + 1,
            stage=self.checks.active.get("stage"),
            source=source,
            channel=channel,
            failure_type=type(error).__name__,
            failure_site=observation["failure_site"],
            primary=primary,
        )
        if operation_stage is not None:
            entry["operation_stage"] = operation_stage
        self.case["failure_observations"].append(entry)
        self.checks.cleanup_history.append(
            entry | {"snapshot": observation["pre_cleanup_snapshot"]}
        )

    def action(self, name, function):
        record = {"action": name, "stage": "signal_finalization_" + name, "attempted": True}
        self.actions.append(record)
        context = self.checks.active | {"stage": record["stage"]}
        self.checks.active = context.copy()
        try:
            function()
            record["result"] = "passed"
            if name == "authorized_stop":
                self.checks.cleanup_history.append(
                    {
                        "stage": "signal_finalization_authorized_stop_observed",
                        "snapshot": self.checks.snapshot(),
                    }
                )
        except Exception as error:
            record.update(result="failed", failure_type=type(error).__name__)
            operation_stage = self.checks.active.get("stage")
            self.checks.active = context
            self.record_failure(error, name, operation_stage=operation_stage)

    def finalize(self, stop):
        started = time.monotonic()
        grace_end, reap_end = started + 12, started + 17
        original_active = self.checks.active.copy()
        if self.process is not None:
            self.action("poll_before_stop", lambda: self.poll("before_finalization"))

            def signal_owned():
                if self.case.get("exit_code") is None:
                    self.process.send_signal(signal.SIGINT)

            self.action("signal_owned", signal_owned)

            def reap():
                if self.case.get("exit_code") is None:
                    self.wait(grace_end, "finalization_wait", strict=False)

            self.action("wait_owned", reap)
            self.action("poll_before_kill", lambda: self.poll("before_forced_termination"))

            def kill_owned():
                if self.case.get("exit_code") is None:
                    self.process.kill()

            self.action("kill_owned_if_needed", kill_owned)

            def forced_reap():
                if self.case.get("exit_code") is None:
                    self.wait(reap_end, "finalization_reap", strict=False)

            self.action("reap_owned_if_needed", forced_reap)
        self.action("authorized_stop", stop)
        if self.collector is not None and self.process is not None:

            def cancel():
                self.collector.finish(time.monotonic() + 2, strict=False)
                assert self.case["collection_complete"], "bounded collection incomplete"

            self.action("collector_cancel", cancel)
        if self.process is not None:
            for name in ("stdout", "stderr"):
                self.action(
                    "close_" + name, lambda name=name: getattr(self.process, name).close()
                )
            self.action("final_poll", lambda: self.poll("after_stream_close"))
        else:
            self.case["final_exit_observation"] = {
                "available": False,
                "reason": "process_not_launched",
            }
        self.case["finalization_seconds"] = time.monotonic() - started
        self.checks.active = original_active
