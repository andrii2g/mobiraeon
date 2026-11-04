"""Bounded diagnostics for trusted fixture verification, never workflow authority."""

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from mobiraeon.private_state import durable_new, harden

TERMINAL_FIELDS = {
    "outcome",
    "cleanup",
    "artifact_valid",
    "held",
    "terminal",
    "phase",
    "completion_state",
    "attachment_exit_code",
    "capture_complete",
    "capture_channels",
    "truncated",
    "runtime_state",
    "generation",
    "container_id",
    "retired",
    "seal",
}
STATE_FIELDS = {
    "Status",
    "Running",
    "Paused",
    "Restarting",
    "OOMKilled",
    "Dead",
    "Pid",
    "ExitCode",
    "StartedAt",
    "FinishedAt",
}
LIMIT_FIELDS = {
    "startup_seconds",
    "execution_seconds",
    "grace_seconds",
    "cleanup_seconds",
    "cpus",
    "memory_bytes",
    "pids",
    "input_bytes",
    "result_bytes",
    "capture_bytes",
    "scratch_bytes",
    "image_id",
    "engine_id",
    "endpoint",
    "docker_executable",
}


def json_observation(value):
    """Normalize the supported non-JSON observation type without object stringification."""

    def supported(item):
        if isinstance(item, UUID):
            return str(item)
        raise TypeError("unsupported diagnostic observation")

    return json.loads(json.dumps(value, default=supported, allow_nan=False))


def unavailable_observations(value):
    """Safe fallback only: an unsupported value is unavailable, never stringified."""
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, float):
        import math

        return value if math.isfinite(value) else {"unavailable_type": "nonfinite_float"}
    if isinstance(value, (list, tuple)):
        return [unavailable_observations(item) for item in value]
    if isinstance(value, dict):
        return {
            key: unavailable_observations(item)
            for key, item in value.items()
            if isinstance(key, str)
        }
    return {"unavailable_type": type(value).__name__}


def bounded(value, maximum=262144):
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return (value or "")[:maximum]


def terminal_fields(record):
    if not isinstance(record, dict):
        return None
    result = {k: record[k] for k in TERMINAL_FIELDS if k in record}
    if not result:
        return None
    for k in ("completion_state", "runtime_state"):
        if isinstance(result.get(k), dict):
            result[k] = {n: v for n, v in result[k].items() if n in STATE_FIELDS}
    return result


def export_stream_evidence(report, outside):
    """Keep aggregate frames small; retain full bounded streams in correlated files."""
    retained = {}

    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for key, item in list(value.items()):
                if (
                    key in {"stdout", "stderr"}
                    and isinstance(item, str)
                    and len(item) > 4096
                    and key + "_evidence" not in value
                ):
                    raw = item.encode("utf-8")
                    digest = hashlib.sha256(raw).hexdigest()
                    if digest not in retained:
                        path = outside / ("stream-" + digest + ".txt")
                        retained[digest] = dict(
                            available=True,
                            path=str(path),
                            sha256=digest,
                            bytes=len(raw),
                            characters=len(item),
                        )
                        try:
                            durable_new(path, raw)
                        except Exception as error:
                            retained[digest].update(
                                available=False, failure_type=type(error).__name__
                            )
                    value[key] = (
                        item[:2000]
                        + "\n[bounded stream evidence retained separately]\n"
                        + item[-2000:]
                    )
                    value[key + "_evidence"] = retained[digest]
                else:
                    visit(item)

    visit(report)
    return report


def export_aggregate_evidence(report, outside, *, maximum):
    """Bound the frame while retaining correlated local details and nested durable identity."""
    report = export_stream_evidence(report, outside)

    def size(value):
        return len(json.dumps(value, allow_nan=False).encode())

    if size(report) <= maximum:
        return report
    saved = {}

    def retain(value):
        raw = json.dumps(value, allow_nan=False).encode()
        digest = hashlib.sha256(raw).hexdigest()
        if digest not in saved:
            path = outside / ("observation-" + digest + ".json")
            saved[digest] = dict(available=True, path=str(path), sha256=digest, bytes=len(raw))
            try:
                if len(raw) > 4194304:
                    raise ValueError("aggregate detail exceeds private-file allowance")
                durable_new(path, raw)
            except Exception as error:
                saved[digest].update(available=False, failure_type=type(error).__name__)
        return saved[digest]

    def shrink(value, *, root=False):
        if isinstance(value, list):
            for item in value:
                shrink(item)
        elif isinstance(value, dict):
            # A nested emitted report already has its own bound/durable export.
            # Never mutate it and thereby break parent/nested round-trip equality.
            if not root and "diagnostic_storage" in value:
                return
            for key, item in list(value.items()):
                if (
                    key in {"stdout", "stderr", "content", "text"}
                    and isinstance(item, str)
                    and len(item) > 512
                ):
                    if key + "_evidence" not in value:
                        value[key + "_evidence"] = retain(item)
                    value[key] = (
                        item[:128] + "\n[protected correlated evidence]\n" + item[-128:]
                    )
                else:
                    shrink(item)

    shrink(report, root=True)
    if size(report) > maximum:
        for check in report.get("checks", []):
            if size(check) < 2048 or "regressions" in check:
                continue
            evidence = retain(check)
            kept = {
                k: v
                for k, v in check.items()
                if k
                in {
                    "case",
                    "command",
                    "expected_exit_code",
                    "exit_code",
                    "result",
                    "failure_type",
                    "stdout",
                    "stderr",
                    "stdout_evidence",
                    "stderr_evidence",
                    "parse_status",
                    "timed_out",
                    "final_exit_observation",
                }
            }
            if isinstance(check.get("operation"), dict):
                kept["operation"] = {k: v for k, v in check["operation"].items() if k != "data"}
            check.clear()
            check.update(kept, observations_evidence=evidence)
    report["aggregate_frame"] = dict(
        maximum_bytes=maximum,
        compacted=True,
        full_observations_retained=all(v["available"] for v in saved.values()),
    )
    if size(report) > maximum:
        raise ValueError("bounded diagnostic frame remains too large")
    return report


class VerificationFailure(AssertionError):
    def __init__(self, report):
        self.report = report
        super().__init__("fixture verification failed; structured evidence retained")


class CheckLog(list):
    def __init__(self, image_id, *, module=None):
        super().__init__()
        self.image_id = image_id
        self.active = {"case": "initialization", "stage": "before_preparation"}
        self.directory = None
        self.terminal = None
        self.cleanup_history = []
        self.module = (
            Path(module)
            if module is not None
            else Path(__file__).with_name("execution_verification.py")
        )
        self.captured_failure = None
        self.failure_cleanup_index = 0

    def capture_failure(self, error):
        """Freeze the first mismatch before a case's authorized finally cleanup."""
        if self.captured_failure is None:
            try:
                self.captured_failure = json_observation(self.failure(error))
            except Exception as diagnostic_error:
                trace, site = error.__traceback__, None
                while trace is not None:
                    site = dict(
                        module=trace.tb_frame.f_code.co_filename,
                        line=trace.tb_lineno,
                        function=trace.tb_frame.f_code.co_name,
                    )
                    trace = trace.tb_next
                self.captured_failure = dict(
                    result="failed",
                    failure_type=type(error).__name__,
                    active=unavailable_observations(self.active),
                    failure_site=site,
                    expected_condition=self.active.get("expected"),
                    terminal_available=self.terminal is not None,
                    observed_terminal=unavailable_observations(self.terminal),
                    checks=unavailable_observations(list(self)),
                    module=str(self.module),
                    pre_cleanup_snapshot=dict(
                        available=False, failure_type=type(diagnostic_error).__name__
                    ),
                    cleanup_observations=unavailable_observations(self.cleanup_history),
                    diagnostic_normalization=dict(
                        available=False, failure_type=type(diagnostic_error).__name__
                    ),
                )
            self.failure_cleanup_index = len(self.cleanup_history)

    def retained_failure(self):
        report = json_observation(self.captured_failure)
        try:
            report["checks"] = json_observation(list(self))
        except Exception as error:
            report["checks"] = unavailable_observations(list(self))
            report["diagnostic_normalization"] = dict(
                available=False, failure_type=type(error).__name__
            )
        report["cleanup_observations"] += json_observation(
            self.cleanup_history[self.failure_cleanup_index :]
        )
        if len(self.cleanup_history) > self.failure_cleanup_index:
            report["cleanup"] = (
                "authorized_cleanup_observations_recorded_protected_state_retained"
            )
        return report

    def raise_if_failed(self):
        if self.captured_failure is not None:
            raise VerificationFailure(self.retained_failure())

    @contextmanager
    def cleanup_stage(self, directory):
        self.cleanup_observation("before_authorized_cleanup", self.terminal)
        active = self.active.copy()
        self.activate(
            active["case"],
            "authorized_cleanup",
            directory=directory,
            mode=active.get("mode"),
            variant=active.get("variant"),
            phase=active.get("phase"),
            expected="owned cleanup is verified",
            terminal=self.terminal,
        )
        try:
            yield
        except Exception as error:
            observation = self.failure(error)
            self.capture_failure(error)
            self.cleanup_history.append(
                {
                    "stage": "authorized_cleanup_failed",
                    "failure_type": type(error).__name__,
                    "failure_site": observation["failure_site"],
                    "directory": str(directory),
                    "snapshot": observation["pre_cleanup_snapshot"],
                }
            )
            raise
        else:
            self.cleanup_observation("after_authorized_cleanup", self.terminal)

    def activate(
        self,
        case,
        stage,
        *,
        mode=None,
        directory=None,
        expected=None,
        variant=None,
        phase=None,
        terminal=None,
    ):
        self.directory = Path(directory) if directory is not None else None
        self.active = dict(
            case=case,
            stage=stage,
            mode=mode,
            expected=expected,
            variant=variant,
            phase=phase,
            directory=str(self.directory) if self.directory is not None else None,
        )
        # A new context never inherits another case's terminal observation.
        self.terminal = terminal_fields(terminal)

    def cleanup_observation(self, stage, record):
        self.cleanup_history.append(
            dict(
                stage=stage,
                terminal=terminal_fields(record),
                directory=self.active.get("directory"),
            )
        )

    def append(self, record):
        super().append(record)
        print(
            json.dumps(
                {
                    "case": record.get("case", "cli"),
                    "exit_code": record.get("exit_code"),
                    "result": record.get("result"),
                }
            ),
            file=sys.stderr,
            flush=True,
        )

    def command(self, args, *, cwd, env, expect=0, timeout=240):
        self.terminal = None
        argv = [sys.executable, *map(str, args)]
        record = dict(
            command=argv,
            expected_exit_code=expect,
            exit_code=None,
            timed_out=False,
            parse_status="not_attempted",
            timeout_seconds=timeout,
            stdout="",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
        )
        try:
            result = subprocess.run(
                argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout
            )
            record |= dict(
                exit_code=result.returncode,
                stdout=bounded(result.stdout),
                stderr=bounded(result.stderr),
                stdout_truncated=len(result.stdout) > 262144,
                stderr_truncated=len(result.stderr) > 262144,
            )
        except subprocess.TimeoutExpired as error:
            record |= dict(
                timed_out=True,
                stdout=bounded(error.stdout),
                stderr=bounded(error.stderr),
                parse_status="timeout",
                stdout_truncated=len(bounded(error.stdout, 262145)) > 262144,
                stderr_truncated=len(bounded(error.stderr, 262145)) > 262144,
            )
            self.append(record)
            raise
        except OSError:
            record["parse_status"] = "process_unavailable"
            self.append(record)
            raise
        self.append(record)
        try:
            parsed = [json.loads(line) for line in result.stdout.splitlines()][-1]
        except ValueError, IndexError:
            record["parse_status"] = "invalid_or_missing_json"
            if expect is not None:
                assert result.returncode == expect
            raise
        record["parse_status"] = "parsed"
        if isinstance(parsed, dict):
            records = (parsed.get("data") or {}).get("records", [])
            if records and isinstance(records[0], dict) and "outcome" in records[0]:
                self.terminal = terminal_fields(records[0])
        if expect is not None:
            assert result.returncode == expect
        return parsed

    def snapshot(self):
        return {
            "fixture_directory": str(self.directory) if self.directory is not None else None,
            **self._snapshot(),
        }

    def _snapshot(self):
        """Read only the active fixture's Run and bounded public observation summaries."""
        from mobiraeon.configuration import resolve_configuration
        from mobiraeon.persistence import Store

        if self.directory is None or not (self.directory / "settings.toml").is_file():
            return {"available": False, "reason": "preparation_incomplete"}
        store = None
        try:
            config = resolve_configuration(
                options={"config": str(self.directory / "settings.toml")}, environ={}
            )
            if not config.database_path.is_file():
                return {"available": False, "reason": "store_unavailable"}
            store = Store(config.database_path)
            with store.engine.connect() as tx:
                row = tx.exec_driver_sql(
                    "SELECT handoff,record FROM execution_runs WHERE task='task-1'"
                ).first()
                events = (
                    tx.exec_driver_sql(
                        "SELECT record FROM execution_events WHERE task='task-1' "
                        "ORDER BY sequence DESC LIMIT 40"
                    )
                    .scalars()
                    .all()
                )
                observations = (
                    tx.exec_driver_sql(
                        "SELECT record FROM coordination_facts WHERE task='task-1' "
                        "AND stage='observe' LIMIT 4"
                    )
                    .scalars()
                    .all()
                )
            result = {
                "available": True,
                "pinned_limits": {},
                "events": [],
                "coordination_observations": [],
                "terminal_available": row is not None,
            }
            if row:
                handoff, record = map(json.loads, row)
                result["record"] = terminal_fields(record)
                result["pinned_limits"] = {
                    k: v for k, v in handoff.get("settings", {}).items() if k in LIMIT_FIELDS
                }
                capture = record.get("capture_path")
                if capture:
                    path = Path(capture).resolve()
                    if path.is_relative_to(self.directory.resolve()) and path.is_file():
                        with path.open("rb") as stream:
                            raw = stream.read(2097153)
                        if len(raw) > 2097152:
                            raise ValueError("capture diagnostic exceeds bound")
                        data = json.loads(raw)
                        result["capture"] = {
                            k: data[k]
                            for k in (
                                "complete",
                                "channels",
                                "truncated",
                                "capture_complete",
                                "capture_channels",
                            )
                            if k in data
                        }
                        result["capture"]["stream_characters"] = {
                            k: len(data[k])
                            for k in ("stdout", "stderr")
                            if isinstance(data.get(k), str)
                        }
            for value in reversed(events):
                event = json.loads(value)
                result["events"].append(
                    {
                        k: event[k]
                        for k in ("event", "at", "generation", "outcome", "cleanup", "phase")
                        if k in event
                    }
                )
            for value in observations:
                inputs = json.loads(value).get("inputs", {})
                result["coordination_observations"].append(
                    {
                        k: bounded(inputs[k], 256)
                        for k in ("observation", "detail")
                        if k in inputs
                    }
                )
            return result
        except Exception as error:
            return {
                "available": False,
                "reason": "snapshot_unavailable",
                "failure_type": type(error).__name__,
            }
        finally:
            if store:
                try:
                    store.close()
                except Exception:
                    pass  # Retained observations must survive diagnostic teardown failure.

    def failure(self, error):
        package = Path(__file__).parent
        site = None
        expected = self.active.get("expected")
        trace = error.__traceback__
        while trace is not None:
            frame, line = trace.tb_frame, trace.tb_lineno
            path = Path(frame.f_code.co_filename)
            if path.is_relative_to(package):
                site = dict(module=str(path), line=line, function=frame.f_code.co_name)
                if isinstance(error, AssertionError):
                    try:
                        source = path.read_text(encoding="utf-8-sig")
                        for node in ast.walk(ast.parse(source)):
                            if (
                                isinstance(node, ast.Assert)
                                and node.lineno <= line <= node.end_lineno
                            ):
                                expected = ast.get_source_segment(source, node.test)[:2048]
                    except OSError, ValueError, SyntaxError:
                        pass
            trace = trace.tb_next
        files = (
            "execution_diagnostics.py",
            "execution_verification.py",
            "execution_repair_verification.py",
            "signal_verification.py",
            "execution_trace.py",
            "execution.py",
            "docker_worker.py",
            "execution_fixture.py",
            "fixture_assets/program.py",
            "fixture_assets/guard.py",
        )
        hashes = {}
        for name in files:
            try:
                hashes[name] = hashlib.sha256((package / name).read_bytes()).hexdigest()
            except OSError:
                hashes[name] = None
        snapshot = self.snapshot()
        engine = snapshot.get("pinned_limits", {}).get("engine_id")
        return {
            "result": "failed",
            "failure_type": type(error).__name__,
            "active": self.active.copy(),
            "failure_site": site,
            "expected_condition": expected,
            "terminal_available": self.terminal is not None,
            "observed_terminal": self.terminal,
            "terminal_unavailability_reason": None
            if self.terminal is not None
            else "no_public_terminal_observed_at_active_stage",
            "checks": list(self),
            "module": str(self.module),
            "python": sys.executable,
            "image_id": self.image_id,
            "engine_attribution": {"available": bool(engine), "engine_id": engine},
            "package_hashes": hashes,
            "pre_cleanup_snapshot": snapshot,
            "cleanup_observations": [
                *self.cleanup_history,
                {"stage": "pre_cleanup", "terminal": self.terminal},
            ],
            "cleanup": "not_attempted_protected_state_retained",
        }


def check_failure_terminal(checks, record, expected):
    """The original public failure-mode predicate; capture BEFORE asserting it."""
    checks.active |= {
        "case": "public_failure_mode",
        "stage": "terminal_assertion",
        "expected": {"outcome": expected, "cleanup": "verified", "artifact_valid": False},
    }
    checks.terminal = terminal_fields(record)
    assert (
        record["outcome"] == expected
        and record["cleanup"] == "verified"
        and not record["artifact_valid"]
    )


@contextmanager
def verification_workspace(checks):
    outside = Path(tempfile.mkdtemp(prefix="mobiraeon-execution-check-"))
    harden(outside)
    try:
        yield outside
        checks.raise_if_failed()
    except Exception as error:
        report = json_observation(
            checks.retained_failure()
            if checks.captured_failure is not None
            else error.report
            if isinstance(error, VerificationFailure)
            else checks.failure(error)
        )
        report["protected_state"] = {"directory": str(outside), "retained": True}
        try:
            maximum = (
                131072 if checks.module.name == "execution_repair_verification.py" else 524288
            )
            report = export_aggregate_evidence(report, outside, maximum=maximum)
            path = outside / "verification-failure.json"
            # The state may be the only evidence of an uncertain Run: never remove it.
            report["diagnostic_storage"] = {"available": True, "path": str(path)}
            durable_new(path, (json.dumps(report) + "\n").encode())
        except Exception as diagnostic_error:
            report["diagnostic_storage"] = {
                "available": False,
                "failure_type": type(diagnostic_error).__name__,
            }
        raise VerificationFailure(report) from None
    else:
        assert outside.resolve().parent == Path(tempfile.gettempdir()).resolve()
        assert outside.name.startswith("mobiraeon-execution-check-")
        shutil.rmtree(outside)
