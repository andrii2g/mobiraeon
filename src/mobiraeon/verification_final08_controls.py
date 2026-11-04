"""Factorized signal-lifecycle required-behavior controls; no execution qualification."""

import contextlib
import hashlib
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

import mobiraeon.execution_diagnostics as diagnostics
import mobiraeon.execution_repair_verification as nested


def signal_control(scenario="stop_raises"):
    import mobiraeon.execution_diagnostics as diagnostics
    import mobiraeon.execution_repair_verification as nested
    import mobiraeon.execution_verification as parent
    from mobiraeon.contracts import Outcome
    from mobiraeon.verification_repair_controls import miniature_fixture, operation

    module_metadata = {
        name: {
            "path": str(Path(module.__file__).resolve()),
            "sha256": hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
        }
        for name, module in [
            ("diagnostics", diagnostics),
            ("nested", nested),
            ("parent", parent),
        ]
    }
    manifest = {"archive_sha256": None}
    OUT_SENTINEL = "INDEPENDENT_F8_INVALID_PROGRESS\n"
    if scenario in {"oversized", "oversized_storage"}:
        OUT_SENTINEL = "F8_OVERSIZED_PREFIX_" + "x" * 280000
    ERR_SENTINEL = "INDEPENDENT_F8_SIGNAL_STDERR_BEFORE_CLEANUP\n"
    record = dict(
        outcome="failed",
        cleanup="verified",
        artifact_valid=False,
        held=False,
        terminal=True,
        capture_complete=False,
        capture_channels={"stdout": "failed", "stderr": "failed"},
        seal="independent-seal",
    )
    observed = {"preparation": [], "stops": [], "stderr_reads": 0}

    class AvailableStdout(io.StringIO):
        def close(self):
            observed["stdout_closed"] = True
            return super().close()

    class AvailableStderr(io.StringIO):
        def close(self):
            observed["stderr_closed"] = True
            return super().close()

        def read(self, *args):
            observed["stderr_reads"] += 1
            return super().read(*args)

    class ObservedProcess:
        def __init__(self, command, **kwargs):
            observed["signal_command"] = command
            self.stdout = AvailableStdout(OUT_SENTINEL)
            self.stderr = AvailableStderr(ERR_SENTINEL)
            self.returncode = None

        def poll(self):
            return self.returncode

        def send_signal(self, signum):
            observed["cleanup_signal"] = str(signum)
            self.returncode = 1

        def wait(self, timeout=None):
            self.returncode = 1
            return self.returncode

        def kill(self):
            self.returncode = -9

    class ObservedExecution:
        def __init__(self, *unused, **kwargs):
            pass

        def invoke(self, *unused, **kwargs):
            return operation(Outcome.FAILURE)

        def load(self, *unused):
            return {}, record.copy()

    def command(argv, **kwargs):
        if argv[1:3] == ["-m", "mobiraeon.execution_fixture"]:
            directory = Path(argv[argv.index("--directory") + 1])
            miniature_fixture(directory, record=record)
            (directory / "independent-partial-marker").write_text("nonsecret control state")
            observed["preparation"].append(str(directory))
            return subprocess.CompletedProcess(argv, 0, '{"prepared":true}', "")
        assert argv[-2:] in (["execution", "stop"], ["execution", "status"]), argv
        directory = Path(argv[argv.index("--config") + 1]).parent
        observed["stops"].append(str(directory))
        if directory.name.startswith("execution_") and scenario == "stop_raises":
            raise OSError("trusted authorized cleanup unavailable")
        if directory.name.startswith("execution_"):
            if scenario == "stop_timeout":
                raise subprocess.TimeoutExpired(argv, 240)
            if scenario == "stop_nonzero":
                return subprocess.CompletedProcess(argv, 7, "{}", "F8_STOP_FAILURE")
            if scenario == "stop_malformed":
                return subprocess.CompletedProcess(argv, 0, "not-json", "")
            if scenario == "snapshot":
                from mobiraeon.configuration import resolve_configuration
                from mobiraeon.persistence import Store

                cfg = resolve_configuration(
                    options={"config": str(directory / "settings.toml")}, environ={}
                )
                store = Store(cfg.database_path)
                with store.engine.begin() as tx:
                    value = record | {"outcome": "stopped"}
                    tx.exec_driver_sql(
                        "UPDATE execution_runs SET record=?", (json.dumps(value),)
                    )
                store.close()
        return subprocess.CompletedProcess(
            argv,
            0,
            json.dumps(
                {
                    "data": {
                        "records": [
                            record
                            | (
                                {"cleanup": "unverified"}
                                if directory.name.startswith("execution_")
                                and scenario == "stop_bad"
                                else {}
                            )
                        ]
                    }
                }
            ),
            "",
        )

    def compose(*unused, **kwargs):
        checks = diagnostics.CheckLog("independent-image")
        checks.append({"case": "earlier_outer_uuid", "operation": asdict(operation())})
        with diagnostics.verification_workspace(checks):
            parent.verify_nested_repairs(
                checks, Path("input"), Path("catalog"), "independent-image"
            )
        raise AssertionError("trusted signal fault must be reached")

    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        patch.object(sys, "platform", "linux"),
        patch.object(parent, "exercise", compose),
        patch.object(nested.subprocess, "run", side_effect=command),
        patch.object(nested.subprocess, "Popen", ObservedProcess),
        patch.object(nested, "ExecutionService", ObservedExecution),
        patch.object(nested, "PrivateState", return_value=SimpleNamespace()),
        patch.object(nested, "proof_for", return_value="trusted-observation"),
        patch.object(
            sys,
            "argv",
            [
                "independent-parent",
                "--input",
                "input",
                "--catalog-input",
                "catalog",
                "--image-id",
                "independent-image",
            ],
        ),
        (
            patch.object(
                diagnostics,
                "durable_new",
                side_effect=OSError("trusted unavailable diagnostic storage"),
            )
            if scenario == "oversized_storage"
            else contextlib.nullcontext()
        ),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        code = parent.main()
    report = json.loads(stdout.getvalue())
    nested_report = report["checks"][-1]["regressions"]
    signal_case = next(
        c for c in nested_report["checks"] if c.get("case", "").startswith("execution_")
    )
    durable = {}
    for name, item in (("parent", report), ("nested", nested_report)):
        path = (
            Path(item["diagnostic_storage"]["path"])
            if item["diagnostic_storage"]["available"]
            else None
        )
        durable[name] = json.loads(path.read_text(encoding="utf-8")) if path else None
    requirements = {
        "actual_parent_nonzero": code != 0 and report["result"] == "failed",
        "primary_progress_parse_failure_retained": report["failure_type"]
        == (
            "ValueError"
            if scenario in {"oversized", "oversized_storage"}
            else "JSONDecodeError"
        ),
        "correct_signal_case_stage": report["active"]["case"] == "execution_SIGINT"
        and report["active"]["stage"] == "signal_supervision",
        "progress_prefix_retained": (
            OUT_SENTINEL[:100] in signal_case["stdout"]
            if scenario in {"oversized", "oversized_storage"}
            else OUT_SENTINEL in signal_case["stdout"]
        ),
        "available_child_stderr_retained": ERR_SENTINEL in signal_case["stderr"],
        "known_final_exit_retained": signal_case["exit_code"] == 1,
        "owned_streams_closed": observed.get("stdout_closed", False)
        and observed.get("stderr_closed", False),
        "independent_finalizers_attempted": all(
            any(a["action"] == n for a in signal_case.get("finalization_actions", []))
            for n in (
                "authorized_stop",
                "collector_cancel",
                "close_stdout",
                "close_stderr",
                "final_poll",
            )
        ),
        "parent_and_nested_durable_match": durable["parent"] == report
        and durable["nested"] == nested_report,
    }
    if scenario in {
        "stop_raises",
        "stop_bad",
        "stop_timeout",
        "stop_nonzero",
        "stop_malformed",
    }:
        requirements["secondary_cleanup_failure_retained"] = any(
            item["stage"]
            in {"authorized_cleanup_failed", "signal_finalization_authorized_stop"}
            for item in report["cleanup_observations"]
        )
    stream_files = {}
    if scenario == "oversized_storage":
        requirements["parent_and_nested_durable_match"] = (
            durable["parent"] is durable["nested"] is None
            and not report["diagnostic_storage"]["available"]
            and not nested_report["diagnostic_storage"]["available"]
        )
        requirements["unavailable_stream_storage_truthful"] = not signal_case[
            "stdout_evidence"
        ]["available"]
        requirements["aggregate_fits_source_wrapper"] = (
            len(stdout.getvalue().encode()) < 2097152
        )
    if scenario == "oversized":
        reference = signal_case["stdout_evidence"]
        text = Path(reference["path"]).read_text(encoding="utf-8")
        requirements["full_bounded_stream_retained"] = (
            len(text) == 262144
            and text.startswith("F8_OVERSIZED_PREFIX_")
            and signal_case["stdout_truncated"]
        )
        requirements["aggregate_fits_source_wrapper"] = (
            len(stdout.getvalue().encode()) < 2097152
        )
        stream_files["stdout"] = {"reference": reference, "text": text}
    if scenario == "snapshot":
        requirements["primary_snapshot_frozen"] = (
            report["pre_cleanup_snapshot"]["record"]["outcome"] == "failed"
        )
        requirements["later_snapshot_separate"] = any(
            x.get("snapshot", {}).get("record", {}).get("outcome") == "stopped"
            for x in report["cleanup_observations"]
        )
    result = {
        "scope": (
            "Portable trusted observations through actual nested/parent main; "
            "no native signal, Docker or historical failure claim."
        ),
        "source_archive_sha256": manifest["archive_sha256"],
        "module_metadata": module_metadata,
        "python": sys.executable,
        "cleanup_fails": scenario == "stop_raises",
        "child_main_exit": code,
        "required_checks": requirements,
        "stream_evidence_payloads": stream_files,
        "observed": observed,
        "signal_case": signal_case,
        "parent_report": report,
        "durable": durable,
        "captured_stderr": stderr.getvalue(),
        "result": "passed" if all(requirements.values()) else "failed_required_retention",
    }
    for root in {
        Path(item["protected_state"]["directory"]) for item in (report, nested_report)
    }:
        assert root.parent.resolve() == Path(tempfile.gettempdir()).resolve()
        assert root.name.startswith("mobiraeon-execution-check-")
        assert not list(root.rglob("*.token")) and not list(root.rglob("credentials"))
        shutil.rmtree(root)
    result["required_behavior"] = all(requirements.values())
    return result


def lifecycle_control(scenario):
    """Factorized faults in actual owned lifecycle; all process/pipe observations synthetic."""
    import itertools

    from mobiraeon.signal_verification import SignalLifecycle

    checks = diagnostics.CheckLog("synthetic-image", module=nested.__file__)
    checks.activate(
        "signal_table",
        "signal_supervision",
        mode="stubborn_child",
        variant="single",
        phase="SIGINT",
        expected="retained primary and independent finalization",
    )
    case = dict(
        case="signal_table",
        command=["trusted-synthetic-child"],
        exit_code=None,
        stdout="",
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
        parse_status="not_attempted",
    )
    if scenario == "normalization":
        case["unsupported"] = object()
    if scenario == "snapshot_error":
        checks.snapshot = lambda: (_ for _ in ()).throw(OSError("trusted snapshot failure"))
    checks.append(case)
    actions = []
    faults = set(scenario.split("+"))

    class Stream(io.StringIO):
        def __init__(self, name, text):
            super().__init__(text)
            self.name = name
            self.reads = 0

        def read(self, size=-1):
            self.reads += 1
            if self.name + "_read" in faults and self.reads > 1:
                raise OSError("trusted read fault")
            return super().read(min(size, 64))

        def close(self):
            actions.append("close_" + self.name)
            super().close()
            if "close_" + self.name in faults:
                raise OSError("trusted close fault")

    class Process:
        def __init__(self, *unused, **kw):
            if "launch" in faults:
                raise OSError("trusted launch fault")
            self.returncode = None
            progress = (
                '{"data":{"state":"running"}}\n'
                if faults
                & {
                    "passing",
                    "semantic",
                    "signal",
                    "wait",
                    "cleanup_stop",
                    "cleanup_drain",
                    "cleanup_close",
                }
                else "F8_PRIMARY_PROGRESS\n"
            )
            if faults & {"stdout_read", "stderr_read"}:
                progress = '{"data":{"state":"waiting"},"text":"F8_PREFIX"}\n'
            if "readiness" in faults:
                progress = ""
            self.stdout = Stream("stdout", progress)
            self.stderr = Stream("stderr", "F8_STDERR_PREFIX")
            if "setup" in faults:

                class Unsupported:
                    def fileno(self):
                        raise OSError("trusted collector setup fault")

                    def close(self):
                        actions.append("close_stderr")

                self.stderr = Unsupported()

        def poll(self):
            actions.append("poll")
            if "poll" in faults:
                raise OSError("trusted poll fault")
            return self.returncode

        def send_signal(self, value):
            actions.append("signal")
            if "signal" in faults:
                raise OSError("trusted signal fault")
            if not faults & {"kill", "reap", "wait"}:
                self.returncode = 1

        def wait(self, timeout=None):
            actions.append("wait")
            if "wait" in faults:
                raise OSError("trusted wait fault")
            if faults & {"kill", "reap"}:
                raise subprocess.TimeoutExpired("trusted", timeout)
            self.returncode = 1
            return 1

        def kill(self):
            actions.append("kill")
            if "kill" in faults:
                raise OSError("trusted kill fault")
            self.returncode = -9

    life = SignalLifecycle(checks, case, None)
    clock = itertools.count(0, 0.3)
    with (
        patch("mobiraeon.signal_verification.time.monotonic", side_effect=lambda: next(clock)),
        patch("mobiraeon.signal_verification.time.sleep"),
        (
            patch(
                "mobiraeon.signal_verification.PipeCollector",
                side_effect=OSError("trusted initialization fault"),
            )
            if scenario == "initialization"
            else contextlib.nullcontext()
        ),
    ):
        try:
            life.launch(Process, case["command"])
            life.running(30 if "readiness" not in faults else -1)
            if "signal" in faults:
                life.process.send_signal(2)
            life.wait(12, "controlled_wait")
            life.collector.finish(14)
            if "semantic" in faults:
                checks.terminal = {"outcome": "failed"}
                raise AssertionError("trusted semantic mismatch")
            case["result"] = "passed"
        except Exception as error:
            life.failure(error)

        def stop():
            actions.append("authorized_stop")
            if faults & {"stop", "cleanup_stop"}:
                raise OSError("trusted stop fault")
            if "cleanup_drain" in faults:
                faults.add("stderr_read")
                life.collector.channels["stderr"]["status"] = "pending"
            if "cleanup_close" in faults:
                faults.add("close_stdout")

        life.finalize(stop)
    report = (
        checks.retained_failure()
        if checks.captured_failure
        else {"result": "passed", "checks": list(checks)}
    )
    actual = [a["action"] for a in case["finalization_actions"]]
    required = (
        report["result"] == "passed" if scenario == "passing" else report["result"] == "failed"
    )
    required &= "authorized_stop" in actual
    if scenario not in {"launch", "initialization"}:
        required &= all(
            n in actual
            for n in ("collector_cancel", "close_stdout", "close_stderr", "final_poll")
        )
    if faults & {"close_stdout", "close_stderr", "stop", "cleanup_stop", "cleanup_close"}:
        required &= case["exit_code"] == 1
    if "poll" in faults:
        required &= any(
            a.get("failure_type") == "OSError" for a in case["finalization_actions"]
        )
    if "stop" in faults and "close_stdout" in faults:
        required &= sum(a["result"] == "failed" for a in case["finalization_actions"]) >= 2
    if scenario in {
        "stdout_read",
        "stderr_read",
        "signal",
        "wait",
        "launch",
        "setup",
        "initialization",
    }:
        required &= report["failure_type"] == "OSError"
    if scenario == "readiness":
        required &= report["failure_type"] == "TimeoutExpired"
    if scenario in {"stdout_read", "stderr_read"}:
        required &= "F8_PREFIX" in case["stdout"] and "F8_STDERR_PREFIX" in case["stderr"]
    if scenario.startswith("cleanup_"):
        required &= report["active"]["stage"].startswith("signal_finalization_")
    if scenario in {"normalization", "snapshot_error"}:
        required &= not report["diagnostic_normalization"]["available"]
    if scenario == "kill":
        required &= (
            case["exit_code"] is None and not case["final_exit_observation"]["available"]
        )
    if scenario not in {"launch", "initialization"}:
        required &= actual[-3:] == ["close_stdout", "close_stderr", "final_poll"]
    return dict(
        required_behavior=bool(required),
        case=diagnostics.unavailable_observations(case),
        report=report,
        observed_actions=actions,
        scope="Portable trusted pipe observations; no real Worker/native signal claim.",
    )


def real_pipe_control(kind):
    """Actual Linux descriptors: no reader threads and no unrelated process ownership."""
    if sys.platform != "linux":
        return {
            "required_behavior": True,
            "result": "unavailable",
            "scope": "Linux real-pipe check; native Windows Worker not qualified",
        }
    import os
    import time

    from mobiraeon.signal_verification import LIMIT, PipeCollector

    out_r, out_w = os.pipe()
    err_r, err_w = os.pipe()
    writer = None
    process = None
    case = dict(
        stdout="",
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
        parse_status="not_attempted",
    )
    code = (
        "import os,json;os.write(1,(json.dumps("
        "{'data':{'state':'running'},'text':chr(0x20ac)*1700},"
        "ensure_ascii=False)+'\\n').encode())"
    )
    if kind == "oversized":
        code = "import os;os.write(1,b'F8_NO_NEWLINE_'+b'x'*280000)"
    started = time.monotonic()
    try:
        process = subprocess.Popen([sys.executable, "-c", code], stdout=out_w, stderr=err_w)
        process.stdout = os.fdopen(out_r, "rb", buffering=0)
        process.stderr = os.fdopen(err_r, "rb", buffering=0)
        if kind in {"no_eof", "delayed"}:
            delay = "5" if kind == "no_eof" else "0.05"
            writer = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "import os,time,sys;time.sleep(0.05);"
                        "os.write(int(sys.argv[1]),b'F8_DELAYED_STDERR');time.sleep("
                    )
                    + delay
                    + ")",
                    str(err_w),
                ],
                pass_fds=(err_w,),
            )
        os.close(out_w)
        os.close(err_w)
        out_w = err_w = None
        collector = PipeCollector(process, case)
        collector.start()
        while process.poll() is None:
            collector.pump(strict=False)
            assert time.monotonic() - started < 5
            time.sleep(0.005)
        known = process.wait(timeout=1)
        before = time.monotonic()
        collector.finish(before + 2, strict=False)
        duration = time.monotonic() - before
        expected = (
            not case["collection_complete"] and case["collection_cancelled"]
            if kind == "no_eof"
            else case["stdout_truncated"] and len(case["stdout"]) == LIMIT
            if kind == "oversized"
            else case["collection_complete"]
            and case["parse_status"] == "parsed"
            and chr(0x20AC) * 1700 in case["stdout"]
            and chr(0xFFFD) not in case["stdout"]
        )
        if kind in {"no_eof", "delayed"}:
            expected &= "F8_DELAYED_STDERR" in case["stderr"]
        return dict(
            required_behavior=bool(expected and known == 0 and duration < 2.2),
            case=case,
            known_exit=known,
            collection_seconds=duration,
            scope="Actual Linux pipes; owned writer handle; supervisor exit distinct from EOF.",
        )
    finally:
        for child in (writer, process):
            if child is not None:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=2)
        for stream in (getattr(process, "stdout", None), getattr(process, "stderr", None)):
            if stream:
                stream.close()
        for fd in (out_w, err_w):
            if fd is not None:
                os.close(fd)


def aggregate_control():
    from uuid import uuid4

    identity = uuid4()
    checks = diagnostics.CheckLog("trusted-image", module=nested.__file__)
    for number in range(40):
        checks.append(
            dict(
                case=f"earlier-{number}",
                stdout="F8_AGGREGATE_PREFIX" + "x" * 3000,
                stderr="",
                operation={"invocation_id": identity, "data": {"content": "y" * 3000}},
            )
        )
    try:
        with diagnostics.verification_workspace(checks):
            raise AssertionError("trusted later mismatch")
    except diagnostics.VerificationFailure as error:
        report = error.report
    root = Path(report["protected_state"]["directory"])
    durable = json.loads(Path(report["diagnostic_storage"]["path"]).read_text(encoding="utf-8"))
    required = (
        report["failure_type"] == "AssertionError"
        and report["checks"][0]["operation"]["invocation_id"] == str(identity)
        and report["aggregate_frame"]["compacted"]
        and len(json.dumps(report).encode()) < 131072
        and durable == report
        and all("F8_AGGREGATE_PREFIX" in c["stdout"] for c in report["checks"])
    )
    details = {
        str(p): json.loads(p.read_text(encoding="utf-8"))
        for p in root.glob("observation-*.json")
    }
    required &= bool(details)
    assert (
        root.name.startswith("mobiraeon-execution-check-")
        and root.parent.resolve() == Path(tempfile.gettempdir()).resolve()
    )
    shutil.rmtree(root)
    return dict(
        required_behavior=bool(required),
        report=report,
        durable=durable,
        protected_detail_payloads=details,
        scope=(
            "Synthetic shared export:UUID, bounded frame and correlated details; "
            "export precedes authorized deletion."
        ),
    )
