"""Real Docker/public CLI I4-R2/R3 regressions, also runnable against final-03."""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

from mobiraeon.configuration import resolve_configuration
from mobiraeon.contracts import Outcome
from mobiraeon.coordination import Coordinator
from mobiraeon.docker_worker import DockerWorker
from mobiraeon.execution import ExecutionService
from mobiraeon.execution_diagnostics import (
    CheckLog,
    VerificationFailure,
    bounded,
    json_observation,
    terminal_fields,
    verification_workspace,
)
from mobiraeon.execution_verification import AssessorAccess
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState
from mobiraeon.scenario import TARGET, proof_for
from mobiraeon.signal_verification import SignalLifecycle


def _drain_progress(process, case, notifications):
    """Retain bounded progress before parsing; transfer thread errors to the owner."""
    try:
        for line in process.stdout:
            combined = case.get("stdout", "") + line
            case["stdout_truncated"] = (
                case.get("stdout_truncated", False) or len(combined) > 262144
            )
            case["stdout"] = bounded(combined)
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("progress must be a record")
            except ValueError as error:
                case["parse_status"] = "invalid_or_nonobject_json"
                notifications.put(error)
                return
            case["parse_status"] = "parsed"
            notifications.put(event)
    except Exception as error:
        case["parse_status"] = "progress_stream_failed"
        notifications.put(error)


def exercise(input_file, catalog_input, image_id):
    if sys.platform != "linux":
        return {"result": "unavailable", "reason": "Real execution requires Linux Docker"}
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    checks = CheckLog(image_id, module=__file__)
    modes = {}
    with verification_workspace(checks) as outside:

        def command(args, expect=0):
            return checks.command(
                args, cwd=outside, env=environment, expect=expect, timeout=240
            )

        def context(case, stage, directory, *, expected, variant=None, phase=None):
            if checks.active.get("case") == case and checks.directory == directory:
                variant = checks.active.get("variant") if variant is None else variant
                phase = checks.active.get("phase") if phase is None else phase
            checks.activate(
                case,
                stage,
                directory=directory,
                mode=modes.get(directory),
                variant=variant,
                phase=phase,
                expected=expected,
            )

        def edit(directory, **values):
            config = directory / "settings.toml"
            text = config.read_text()
            for key, value in values.items():
                text = re.sub(r"(?m)^" + key + r"=.*$", key + "=" + json.dumps(value), text)
            config.write_text(text)

        def prepare(
            name, mode="success", result_bytes=4096, *, case=None, variant=None, phase=None
        ):
            directory = outside / name
            modes[directory] = mode
            case = case or name
            context(
                case,
                "preparation",
                directory,
                expected="fixture preparation exits zero",
                variant=variant,
                phase=phase,
            )
            command(
                [
                    "-m",
                    "mobiraeon.execution_fixture",
                    "prepare",
                    "--directory",
                    directory,
                    "--input",
                    input_file,
                    "--catalog-input",
                    catalog_input,
                    "--image-id",
                    image_id,
                ]
            )
            context(
                case,
                "fixture_configuration",
                directory,
                expected="prepared fixture settings and mode are valid",
            )
            edit(
                directory,
                startup_seconds=10,
                execution_seconds=30,
                grace_seconds=1,
                cleanup_seconds=5,
                result_bytes=result_bytes,
            )
            path = directory / "run.json"
            request = json.loads(path.read_text())
            request["inputs"]["mode"] = mode
            path.write_text(json.dumps(request))
            return directory

        def cli(directory, action, expect=0, family="execution"):
            active = checks.active.copy()
            context(
                active["case"],
                active["stage"] if active["stage"] == "authorized_cleanup" else "cli_" + action,
                directory,
                expected={"cli_exit": expect},
                variant=active.get("variant"),
                phase=active.get("phase"),
            )
            return command(
                [
                    "-m",
                    "mobiraeon",
                    "--config",
                    directory / "settings.toml",
                    "--request-file",
                    directory / (action + ".json"),
                    family,
                    *([action] if family == "execution" else []),
                ],
                expect,
            )

        def objects(directory):
            config = resolve_configuration(
                options={"config": str(directory / "settings.toml")}, environ={}
            )
            store = Store(config.database_path)
            private = PrivateState(config.private_dir, config.database_path)
            return config, store, private, ExecutionService(store, private, config.execution)

        # Real fixed program and cleanup, with trusted host-side stream fault injection.
        for channel in ("stdout", "stderr"):
            directory = prepare(
                "capture-" + channel,
                case="capture_" + channel + "_read_failure",
                variant="capture_read_failure",
                phase=channel,
            )
            case = {"case": "capture_" + channel + "_read_failure"}
            checks.append(case)

            class ReadFailure:
                def __init__(self, stream):
                    self.stream = stream

                def read(self, size):
                    data = self.stream.read(size)
                    if data:
                        return data
                    raise OSError("trusted capture error instead of EOF")

                def close(self):
                    self.stream.close()

                @property
                def closed(self):
                    return self.stream.closed

            class LossyWorker(DockerWorker):
                def start(self, identity, timeout=10, channel=channel):
                    process = super().start(identity, timeout)
                    setattr(process, channel, ReadFailure(getattr(process, channel)))
                    return process

            context(
                case["case"],
                "service_setup",
                directory,
                variant="capture_read_failure",
                phase=channel,
                expected="prepared fixture service can be inspected",
            )
            config, store, private, execution = objects(directory)
            context(
                case["case"],
                "capture_assertions",
                directory,
                variant="capture_read_failure",
                phase=channel,
                expected="capture failure cannot yield successful output or observation",
            )
            try:
                execution = ExecutionService(
                    store, private, config.execution, worker_type=LossyWorker
                )
                result = execution.invoke(
                    "execution.run",
                    TARGET,
                    json.loads((directory / "run.json").read_text())["inputs"],
                    proof=proof_for(private, "author"),
                )
                _, record = execution.load("task-1")
                case |= {"operation": asdict(result), "persisted": record}
                checks.terminal = terminal_fields(record)
                assert result.outcome != Outcome.SUCCESS and not record["artifact_valid"], case
                assert record["capture_complete"] is False, case
                assert record["capture_channels"][channel] == "failed", case
                with store.engine.connect() as tx:
                    observed = [
                        json.loads(r[0])
                        for r in tx.exec_driver_sql(
                            "SELECT record FROM coordination_facts WHERE stage='observe'"
                        )
                    ]
                assert not any(r["inputs"]["observation"] == "succeeded" for r in observed)
                assert record["cleanup"] == "verified" and not record["held"], case
                case["result"] = "passed"
            except Exception as error:
                checks.capture_failure(error)
                case |= {"result": "failed", "failure_type": type(error).__name__}
            finally:
                try:
                    with checks.cleanup_stage(directory):
                        case["authorized_final_cleanup"] = cli(directory, "stop")
                        assert (
                            case["authorized_final_cleanup"]["data"]["records"][0]["cleanup"]
                            == "verified"
                        )
                finally:
                    store.close()
            checks.raise_if_failed()

        for signum, repeated in (
            (s, repeated) for s in (signal.SIGINT, signal.SIGTERM) for repeated in (False, True)
        ):
            name = "execution_" + signum.name + ("_repeated" if repeated else "")
            directory = prepare(
                name,
                "stubborn_child",
                case=name,
                variant="repeated" if repeated else "single",
                phase=signum.name,
            )
            argv = [
                sys.executable,
                "-m",
                "mobiraeon",
                "--config",
                str(directory / "settings.toml"),
                "--request-file",
                str(directory / "run.json"),
                "execution",
                "run",
            ]
            context(
                name,
                "signal_supervision",
                directory,
                variant="repeated" if repeated else "single",
                phase=signum.name,
                expected="signal stops the owned Run with verified cleanup",
            )
            case = {
                "case": name,
                "command": argv,
                "expected_exit_code": 1,
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "timed_out": False,
                "parse_status": "not_attempted",
                "timeout_seconds": 30,
                "stdout_truncated": False,
                "stderr_truncated": False,
            }
            checks.append(case)
            lifecycle = SignalLifecycle(checks, case, directory)
            try:
                lifecycle.launch(
                    subprocess.Popen,
                    argv,
                    cwd=outside,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                process = lifecycle.process
                lifecycle.running(time.monotonic() + 30)
                time.sleep(0.3)  # Allow the fixed stubborn descendant to start.
                started = time.monotonic()
                sent = []
                for number in range(5 if repeated else 1):
                    actual_signal = (
                        signum
                        if number % 2 == 0
                        else (signal.SIGTERM if signum == signal.SIGINT else signal.SIGINT)
                    )
                    assert process.poll() is None
                    process.send_signal(actual_signal)
                    sent.append(actual_signal.name)
                    if repeated:
                        time.sleep(0.05)
                lifecycle.wait(time.monotonic() + 12, "signal_wait")
                lifecycle.collector.finish(time.monotonic() + 2)
                # Original endpoint: supervision start through process/reader observation,
                # before status and authorized cleanup. Later finalization is separate.
                case |= {
                    "signal": signum.name,
                    "signals_sent": sent,
                    "scheduling": "untraced, 50 ms spaced" if repeated else "single signal",
                    "elapsed_seconds": time.monotonic() - started,
                    "stderr_observation_stage": "before_assertions",
                }
                assert case["parse_status"] == "parsed"
                status = cli(directory, "status")["data"]["records"][0]
                case["persisted_after_signal"] = status
                context(
                    name,
                    "signal_terminal_assertions",
                    directory,
                    variant="repeated" if repeated else "single",
                    phase=signum.name,
                    expected="stop intent, terminal failure and verified cleanup",
                )
                checks.terminal = terminal_fields(status)
                assert status["stop_intent"] and status["cleanup"] == "verified", case
                assert (
                    status["terminal"] and not status["held"] and not status["artifact_valid"]
                ), case
                assert status["outcome"] in {"stopped", "unknown"}, case
                assert process.returncode == 1 and case["elapsed_seconds"] < 9, case
                worker = DockerWorker(status["handoff"]["settings"])
                assert worker.inspect(status["handoff"], status.get("container_id")) is None
                case["result"] = "passed"
            except Exception as error:
                lifecycle.failure(error)
            finally:

                def authorized_stop(case=case, directory=directory):
                    case["authorized_final_cleanup"] = cli(directory, "stop")
                    assert (
                        case["authorized_final_cleanup"]["data"]["records"][0]["cleanup"]
                        == "verified"
                    )

                lifecycle.finalize(authorized_stop)
            checks.raise_if_failed()

        case = {"case": "pinned_submission_assessment_and_future_run"}
        checks.append(case)
        try:
            directory = prepare(
                "pinned", case=case["case"], variant="pinned_allowance", phase="initial"
            )
            record = cli(directory, "run")["data"]["records"][0]
            context(
                case["case"],
                "artifact_assertion",
                directory,
                expected="retained artifact is valid",
            )
            assert record["artifact_valid"]
            edit(directory, result_bytes=1)
            submission = {
                "operation_id": "submit-1",
                "expected_version": 4,
                "attempt_id": "attempt-1",
                "submission_id": "submission-1",
                "artifacts": [record["artifact"]],
            }
            (directory / "submit.json").write_text(
                json.dumps(
                    {"operation": "coordination.submit", "target": TARGET, "inputs": submission}
                )
            )
            submitted = cli(directory, "submit", expect=None, family="coordination")
            case["submission_with_new_limit"] = submitted
            context(
                case["case"],
                "submission_assertion",
                directory,
                expected="submission uses the admitted result allowance",
            )
            assert submitted["outcome"] == Outcome.SUCCESS, submitted
            edit(
                directory,
                result_bytes=2,
                credential_file=str(directory / "credentials" / "assessor.token"),
            )
            assessment = {
                "operation_id": "assess-1",
                "expected_version": 5,
                "submission_id": "submission-1",
                "submission_digest": submitted["data"]["records"][0]["fact"][
                    "submission_digest"
                ],
                "evidence": [record["artifact"]],
                "decision": "approve",
                "rationale": "Exact retained output",
            }
            (directory / "assess.json").write_text(
                json.dumps(
                    {"operation": "coordination.assess", "target": TARGET, "inputs": assessment}
                )
            )
            ordinary = cli(directory, "assess", expect=1, family="coordination")
            case["ordinary_assessment"] = ordinary
            context(
                case["case"],
                "ordinary_assessment_assertion",
                directory,
                expected="ordinary author cannot assess the retained submission",
            )
            assert ordinary["reason"] == "review_inapplicable", ordinary
            config, store, private, execution = objects(directory)
            try:
                assessed = Coordinator(
                    store,
                    private,
                    access=AssessorAccess(store, private),
                    content_limits=config.execution,
                ).invoke(
                    "coordination.assess",
                    TARGET,
                    assessment,
                    proof=proof_for(private, "assessor"),
                )
                context(
                    case["case"],
                    "assessment_assertion",
                    directory,
                    expected="exact retained submission can be assessed",
                )
                case["assessment_operation"] = asdict(assessed)
                assert assessed.outcome == Outcome.SUCCESS, assessed
                handoff, _ = execution.load("task-1")
                assert handoff["settings"]["result_bytes"] == 4096
                case["retained_allowance"] = 4096
                case["assessment_current_allowance"] = config.execution["result_bytes"]
            finally:
                store.close()
            future = prepare(
                "future",
                result_bytes=1,
                case=case["case"],
                variant="pinned_allowance",
                phase="future",
            )
            future_record = cli(future, "run", expect=1)["data"]["records"][0]
            future_status = cli(future, "status")["data"]["records"][0]
            context(
                case["case"],
                "future_run_assertions",
                future,
                expected="future Run uses new limits and cannot produce an artifact",
            )
            assert future_status["handoff"]["settings"]["result_bytes"] == 1
            assert (
                not future_record["artifact_valid"] and future_record["cleanup"] == "verified"
            )
            case |= {"future_run": future_status, "result": "passed"}
        except Exception as error:
            checks.capture_failure(error)
            case |= {"result": "failed", "failure_type": type(error).__name__}
            if checks.directory is not None and (checks.directory / "settings.toml").is_file():
                with checks.cleanup_stage(checks.directory):
                    cli(checks.directory, "stop")
    return {
        "result": "failed" if any(c.get("result") == "failed" for c in checks) else "passed",
        "checks": checks,
        "image_id": image_id,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--catalog-input", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    args = parser.parse_args()
    try:
        result = exercise(args.input.resolve(), args.catalog_input.resolve(), args.image_id)
    except VerificationFailure as error:
        result = error.report
    print(json.dumps(json_observation(result), indent=2))
    return int(result["result"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
