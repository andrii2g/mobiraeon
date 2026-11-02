"""Real Docker/public CLI I4-R2/R3 regressions, also runnable against final-03."""

import argparse
import json
import os
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path

from mobiraeon.configuration import resolve_configuration
from mobiraeon.contracts import Outcome
from mobiraeon.coordination import Coordinator
from mobiraeon.docker_worker import DockerWorker
from mobiraeon.execution import ExecutionService
from mobiraeon.execution_verification import AssessorAccess
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState
from mobiraeon.scenario import TARGET, proof_for


def exercise(input_file, catalog_input, image_id):
    if sys.platform != "linux":
        return {"result": "unavailable", "reason": "Real execution requires Linux Docker"}
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    checks = []
    with tempfile.TemporaryDirectory(prefix="mobiraeon-i4-repairs-") as temporary:
        outside = Path(temporary)

        def command(args, expect=0):
            argv = [sys.executable, *map(str, args)]
            result = subprocess.run(
                argv, cwd=outside, env=environment, capture_output=True, text=True, timeout=240
            )
            checks.append(
                {
                    "command": argv,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
            if expect is not None:
                assert result.returncode == expect, checks[-1]
            return json.loads(result.stdout.splitlines()[-1])

        def edit(directory, **values):
            config = directory / "settings.toml"
            text = config.read_text()
            for key, value in values.items():
                text = re.sub(r"(?m)^" + key + r"=.*$", key + "=" + json.dumps(value), text)
            config.write_text(text)

        def prepare(name, mode="success", result_bytes=4096):
            directory = outside / name
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
            directory = prepare("capture-" + channel)
            case = {"case": "capture_" + channel + "_read_failure"}

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

            config, store, private, execution = objects(directory)
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
            except Exception:
                case |= {"result": "failed", "error": traceback.format_exc()}
            finally:
                case["authorized_final_cleanup"] = cli(directory, "stop")
                assert (
                    case["authorized_final_cleanup"]["data"]["records"][0]["cleanup"]
                    == "verified"
                )
                store.close()
                checks.append(case)

        for signum, repeated in (
            (s, repeated) for s in (signal.SIGINT, signal.SIGTERM) for repeated in (False, True)
        ):
            name = "execution_" + signum.name + ("_repeated" if repeated else "")
            directory = prepare(name, "stubborn_child")
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
            process = subprocess.Popen(
                argv,
                cwd=outside,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            lines, notifications = [], queue.Queue()

            def drain(process=process, lines=lines, notifications=notifications):
                for line in process.stdout:
                    lines.append(line)
                    notifications.put(json.loads(line))

            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            case = {"case": name, "command": argv}
            try:
                end = time.monotonic() + 30
                while True:
                    event = notifications.get(timeout=max(0.1, end - time.monotonic()))
                    if event.get("data") and event["data"]["state"] == "running":
                        break
                    assert time.monotonic() < end
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
                process.wait(timeout=12)  # grace + cleanup + bounded CLI/store overhead
                reader.join(timeout=2)
                case |= {
                    "signal": signum.name,
                    "signals_sent": sent,
                    "scheduling": "untraced, 50 ms spaced" if repeated else "single signal",
                    "elapsed_seconds": time.monotonic() - started,
                    "exit_code": process.returncode,
                    "stdout": "".join(lines),
                    "stderr": process.stderr.read(),
                }
                status = cli(directory, "status")["data"]["records"][0]
                case["persisted_after_signal"] = status
                assert status["stop_intent"] and status["cleanup"] == "verified", case
                assert (
                    status["terminal"] and not status["held"] and not status["artifact_valid"]
                ), case
                assert status["outcome"] in {"stopped", "unknown"}, case
                assert process.returncode == 1 and case["elapsed_seconds"] < 9, case
                worker = DockerWorker(status["handoff"]["settings"])
                assert worker.inspect(status["handoff"], status.get("container_id")) is None
                case["result"] = "passed"
            except Exception:
                case |= {"result": "failed", "error": traceback.format_exc()}
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    try:
                        process.wait(timeout=12)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                reader.join(timeout=2)
                # The unchanged baseline's SIGTERM leaves work active; clean it with authority.
                case["authorized_final_cleanup"] = cli(directory, "stop")
                assert (
                    case["authorized_final_cleanup"]["data"]["records"][0]["cleanup"]
                    == "verified"
                )
                process.stdout.close()
                process.stderr.close()
                checks.append(case)

        case = {"case": "pinned_submission_assessment_and_future_run"}
        try:
            directory = prepare("pinned")
            record = cli(directory, "run")["data"]["records"][0]
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
                assert assessed.outcome == Outcome.SUCCESS, assessed
                handoff, _ = execution.load("task-1")
                assert handoff["settings"]["result_bytes"] == 4096
                case["retained_allowance"] = 4096
                case["assessment_current_allowance"] = config.execution["result_bytes"]
            finally:
                store.close()
            future = prepare("future", result_bytes=1)
            future_record = cli(future, "run", expect=1)["data"]["records"][0]
            future_status = cli(future, "status")["data"]["records"][0]
            assert future_status["handoff"]["settings"]["result_bytes"] == 1
            assert (
                not future_record["artifact_valid"] and future_record["cleanup"] == "verified"
            )
            case |= {"future_run": future_status, "result": "passed"}
        except Exception:
            case |= {"result": "failed", "error": traceback.format_exc()}
        checks.append(case)
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
    result = exercise(args.input.resolve(), args.catalog_input.resolve(), args.image_id)
    print(json.dumps(result, default=str, indent=2))
    return int(result["result"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
