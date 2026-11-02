"""Trusted fixture-only verification, callable from source or a clean installed wheel."""

import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict
from pathlib import Path

from mobiraeon.access import Access
from mobiraeon.configuration import resolve_configuration
from mobiraeon.contracts import CallerContext, EntityId, Outcome
from mobiraeon.coordination import Coordinator
from mobiraeon.docker_worker import DockerWorker
from mobiraeon.errors import Reason, SafeError
from mobiraeon.execution import ExecutionService
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState
from mobiraeon.scenario import TARGET, proof_for


class AssessorAccess(Access):
    def caller(self, proof):
        ordinary = super().caller(proof)
        if ordinary and proof == proof_for(self.private, "assessor"):
            return CallerContext(
                EntityId("human", "supervised-fixture-assessor"), "trusted-fixture"
            )
        return ordinary


def exercise(input_file, catalog_input, image_id, *, long_wait=True):
    if sys.platform != "linux":
        return {
            "result": "unavailable",
            "reason": "Worker requires local Linux Docker; portable tests remain applicable",
        }

    class CheckLog(list):
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

    checks = CheckLog()
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="mobiraeon-execution-check-") as temporary:
        outside = Path(temporary)

        def command(args, expect=0, timeout=240):
            result = subprocess.run(
                [sys.executable, *map(str, args)],
                cwd=outside,
                env=environment,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            checks.append(
                {
                    "command": [sys.executable, *map(str, args)],
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
            assert result.returncode == expect, result.stdout + result.stderr
            return [json.loads(line) for line in result.stdout.splitlines()][-1]

        counter = 0

        def installation(mode="success", duration=2):
            nonlocal counter
            counter += 1
            directory = outside / ("private-" + str(counter))
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
            config = directory / "settings.toml"
            text = config.read_text()
            for key, value in {
                "startup_seconds": 10,
                "execution_seconds": duration,
                "grace_seconds": 1,
                "cleanup_seconds": 5,
                "cpus": 0.25,
                "memory_bytes": 64 * 1024 * 1024,
                "scratch_bytes": 8 * 1024 * 1024,
                "pids": 16,
                "capture_bytes": 8192,
                "result_bytes": 4096,
            }.items():
                import re

                text = re.sub(r"(?m)^" + key + r"=.*$", key + "=" + str(value), text)
            config.write_text(text)
            run = json.loads((directory / "run.json").read_text())
            run["inputs"]["mode"] = mode
            (directory / "run.json").write_text(json.dumps(run))
            return directory

        def cli(directory, action, expect=0):
            return command(
                [
                    "-m",
                    "mobiraeon",
                    "--config",
                    directory / "settings.toml",
                    "--request-file",
                    directory / (action + ".json"),
                    "execution",
                    action,
                ],
                expect=expect,
            )

        def service(directory, worker_type=DockerWorker, hook=None):
            config = resolve_configuration(
                options={"config": str(directory / "settings.toml")}, environ={}
            )
            private = PrivateState(config.private_dir, config.database_path)
            store = Store(config.database_path)
            return (
                store,
                private,
                ExecutionService(
                    store, private, config.execution, worker_type=worker_type, hook=hook
                ),
            )

        # Public helper/CLI success; exact output through independent assessment and acceptance.
        directory = installation()
        admin_store, admin_private, admission = service(directory)
        try:
            refused = admission.invoke(
                "execution.run",
                TARGET,
                json.loads((directory / "run.json").read_text())["inputs"],
                proof=proof_for(admin_private, "admin"),
            )
            assert refused.outcome == Outcome.REFUSED
            checks.append(
                {
                    "case": "registry_admin_without_execution_grants",
                    "result": "passed",
                    "operation": asdict(refused),
                }
            )
        finally:
            admin_store.close()
        result = cli(directory, "run")
        record = result["data"]["records"][0]
        assert (
            record["outcome"] == "succeeded" and record["artifact_valid"] and not record["held"]
        )
        assert cli(directory, "status")["data"]["records"][0]["artifact"] == record["artifact"]
        assert cli(directory, "run")["data"]["records"][0]["replayed"]
        store, private, execution = service(directory)
        try:
            coordinator = Coordinator(store, private, access=AssessorAccess(store, private))
            with store.engine.connect() as tx:
                version = tx.exec_driver_sql("SELECT version FROM coordination_tasks").scalar()
            author = proof_for(private, "author")
            submission = coordinator.invoke(
                "coordination.submit",
                TARGET,
                {
                    "operation_id": "submission-1",
                    "expected_version": version,
                    "attempt_id": "attempt-1",
                    "submission_id": "submission-1",
                    "artifacts": [record["artifact"]],
                },
                proof=author,
            )
            assert submission.outcome == Outcome.SUCCESS, submission
            digest = submission.data.records[0]["fact"]["submission_digest"]
            assessment = {
                "operation_id": "assessment-1",
                "expected_version": version + 1,
                "submission_id": "submission-1",
                "submission_digest": digest,
                "evidence": [record["artifact"]],
                "decision": "approve",
                "rationale": "Trusted independent fixture assessment of captured content",
            }
            assert (
                coordinator.invoke(
                    "coordination.assess", TARGET, assessment, proof=author
                ).outcome
                != Outcome.SUCCESS
            )
            assessor = proof_for(private, "assessor")
            assert (
                coordinator.invoke(
                    "coordination.assess", TARGET, assessment, proof=assessor
                ).outcome
                == Outcome.SUCCESS
            )
            accepted = coordinator.invoke(
                "coordination.accept",
                TARGET,
                {
                    "operation_id": "accept-1",
                    "expected_version": version + 2,
                    "submission_id": "submission-1",
                    "submission_digest": digest,
                    "assessment_id": "assessment-1",
                },
                proof=assessor,
            )
            assert accepted.outcome == Outcome.SUCCESS
            status = coordinator.invoke(
                "coordination.status", TARGET, {}, proof=author
            ).data.records[0]
            assert (
                status["state"] == "accepted"
                and status["request_state"] == "open"
                and status["initiative_acceptance"] == "unaccepted"
            )
            assert store.engine.connect().close() is None
            terminal = execution.load("task-1")[1]
            cli(directory, "stop")
            assert execution.load("task-1")[1] == terminal
            checks.append(
                {
                    "case": "accepted_exact_supervised_artifact",
                    "result": "passed",
                    "status": status,
                }
            )
        finally:
            store.close()
        # Public failure modes, output caps and deadlines on real containers.
        for mode, expected in (
            ("failure", "failed"),
            ("wait", "timeout"),
            ("excess_output", "output_limit"),
            ("stubborn_child", "timeout"),
        ):
            directory = installation(mode)
            result = cli(directory, "run", expect=1)
            record = result["data"]["records"][0]
            assert (
                record["outcome"] == expected
                and record["cleanup"] == "verified"
                and not record["artifact_valid"]
            )
            store, _, execution = service(directory)
            try:
                with store.engine.connect() as tx:
                    observed = json.loads(
                        tx.exec_driver_sql(
                            "SELECT record FROM coordination_facts WHERE stage='observe'"
                        ).scalar()
                    )
                assert observed["inputs"]["observation"] == "failed"
                assert observed["inputs"]["detail"] == record["seal"]
                checks.append({"case": "sealed_failure_observed_" + mode, "result": "passed"})
            finally:
                store.close()
        # Trusted fixed variants. Public mode validation continues to exclude these.
        for variant in (
            "invalid",
            "partial",
            "controls",
            "memory",
            "pids",
            "scratch",
            "scratch_shm",
            "cpu",
            "startup_failure",
        ):
            directory = installation()

            class ProbeWorker(DockerWorker):
                def call(self, *args, test_variant=variant, **kwargs):
                    if args and args[0] == "create" and test_variant == "startup_failure":
                        values = list(args)
                        index = values.index(
                            "type=bind,source=/dev/null,target=/dev/null,readonly"
                        )
                        del values[index - 1 : index + 1]
                        return super().call(*values, **kwargs)
                    return super().call(*args, **kwargs)

                def preflight(self, test_variant=variant):
                    return super().preflight() | {"trusted_test_variant": test_variant}

                def create(self, handoff, timeout=None, test_variant=variant):
                    return super().create(handoff | {"mode": test_variant}, timeout=timeout)

            def cpu_probe(phase, variant=variant, directory=directory):
                if phase == "after_start" and variant == "cpu":
                    time.sleep(0.6)
                    probe_store, _, probe = service(directory)
                    try:
                        handoff, current = probe.load("task-1")
                        worker = DockerWorker(handoff["settings"])
                        observed = worker.call(
                            "exec",
                            current["container_id"],
                            "python",
                            "-c",
                            "print(open('/sys/fs/cgroup/cpu.stat').read())",
                        ).stdout.decode()
                        assert (
                            int(
                                next(
                                    line.split()[1]
                                    for line in observed.splitlines()
                                    if line.startswith("nr_throttled")
                                )
                            )
                            > 0
                        )
                        checks.append(
                            {
                                "case": "cpu_throttling_observed",
                                "result": "passed",
                                "cpu_stat": observed,
                            }
                        )
                    finally:
                        probe_store.close()

            store, private, execution = service(directory, ProbeWorker, cpu_probe)
            try:
                inputs = json.loads((directory / "run.json").read_text())["inputs"]
                result = execution.invoke(
                    "execution.run", TARGET, inputs, proof=proof_for(private, "author")
                )
                record = execution.load("task-1")[1]
                assert (
                    result.outcome == Outcome.FAILURE
                    and record["cleanup"] == "verified"
                    and not record["artifact_valid"]
                ), record
                with store.engine.connect() as tx:
                    observed = json.loads(
                        tx.exec_driver_sql(
                            "SELECT record FROM coordination_facts WHERE stage='observe'"
                        ).scalar()
                    )
                assert observed["inputs"]["observation"] == "failed"
                assert observed["inputs"]["detail"] == record["seal"]
                capture = json.loads(Path(record["capture_path"]).read_text())
                if variant == "controls":
                    controls = json.loads(capture["stdout"])
                    assert not any(
                        "TOKEN" in key or "SECRET" in key or "DOCKER" in key
                        for key in controls["environment"]
                    )
                    assert (
                        controls["uid"] == 65532
                        and controls["network_blocked"]
                        and controls["socket_absent"]
                    )
                    assert controls["write_refused"] == {"/forbidden": True, "/etc/hosts": True}
                    assert controls["cgroup"]["memory.swap.max"] == "0"
                    assert int(controls["cgroup"]["memory.max"]) == 64 * 1024 * 1024
                    assert controls["cgroup"]["pids.max"] == "16"
                    assert controls["cgroup"]["cpu.max"].split()[0] == "25000"
                if variant == "memory":
                    assert (
                        record["runtime_state"]["OOMKilled"]
                        or "MemoryError" in capture["stderr"]
                    )
                if variant == "pids":
                    assert "Resource temporarily unavailable" in capture["stderr"]
                if variant == "startup_failure":
                    assert record["outcome"] == "startup_failed"
                if variant in {"scratch", "scratch_shm"}:
                    assert "No space left on device" in capture["stderr"], (record, capture)
                checks.append(
                    {
                        "case": "trusted_" + variant,
                        "result": "passed",
                        "record": record,
                        "capture": capture,
                    }
                )
            finally:
                store.close()
        # Real Docker effects with injected acknowledgement loss and ordered stop windows.
        for phase in (
            "before_create",
            "after_create",
            "after_start",
            "before_seal",
            "before_start_authorization",
            "before_start_delivery",
        ):
            directory = installation()
            trace = {"starts": 0, "creates": 0}

            class TracedWorker(DockerWorker):
                def create(self, handoff, timeout=None, trace=trace):
                    trace["creates"] += 1
                    return super().create(handoff, timeout=timeout)

                def start(self, identity, timeout=10, trace=trace):
                    trace["starts"] += 1
                    return super().start(identity, timeout=timeout)

            def fault(at, phase=phase, directory=directory):
                if at != phase:
                    return
                if phase in {"before_start_authorization", "before_start_delivery"}:
                    stop_store, stop_private, stopper = service(directory)
                    try:
                        stopped = stopper.invoke(
                            "execution.stop",
                            TARGET,
                            {
                                "operation_id": "ordered-stop",
                                "attempt_id": "attempt-1",
                                "reason": "ordered fault test",
                            },
                            proof=proof_for(stop_private, "author"),
                        )
                        assert (
                            stopped.outcome == Outcome.SUCCESS
                            and stopped.data.records[0]["stop_acknowledged"]
                        )
                    finally:
                        stop_store.close()
                else:
                    raise SafeError(Reason.UNCERTAIN)

            store, private, execution = service(directory, TracedWorker, fault)
            try:
                inputs = json.loads((directory / "run.json").read_text())["inputs"]
                result = execution.invoke(
                    "execution.run", TARGET, inputs, proof=proof_for(private, "author")
                )
                assert result.outcome == Outcome.UNCERTAIN
                record = execution.load("task-1")[1]
                assert not record["artifact_valid"]
                previous = dict(trace)
                repeated = execution.invoke(
                    "execution.run", TARGET, inputs, proof=proof_for(private, "author")
                )
                assert (
                    repeated.outcome in {Outcome.SUCCESS, Outcome.UNCERTAIN}
                    and trace == previous
                )
                if phase == "before_start_authorization":
                    assert trace["starts"] == 0 and not record.get("start_authorized")
                if phase == "before_start_delivery":
                    assert (
                        trace["starts"] == 1
                        and record["start_authorized"]
                        and record["stop_intent"]
                    )
                if not record.get("terminal"):
                    execution.hook = lambda at: None
                    execution.invoke(
                        "execution.stop",
                        TARGET,
                        {
                            "operation_id": "finish-stop",
                            "attempt_id": "attempt-1",
                            "reason": "finish cleanup",
                        },
                        proof=proof_for(private, "author"),
                    )
                final = execution.load("task-1")[1]
                assert not final["artifact_valid"]
                if phase in {"before_create", "after_create"}:
                    assert final["held"]  # unknown create quiescence cannot be force-cleared
                else:
                    assert final["cleanup"] == "verified" and final["outcome"] == "unknown"
                checks.append(
                    {
                        "case": "injected_" + phase,
                        "result": "passed",
                        "effect_counts": trace,
                        "record": final,
                    }
                )
            finally:
                store.close()
        # Revocation permits confined evidence/cleanup but cannot advance Coordination.
        directory = installation()

        def revoke_before_seal(phase):
            if phase == "before_seal":
                from mobiraeon.catalog import RegistryService

                rev_store, rev_private, _ = service(directory)
                try:
                    author = proof_for(rev_private, "author")
                    revoked = RegistryService(rev_store, rev_private).invoke(
                        "access.revoke",
                        {
                            "kind": "access",
                            "entity_kind": "credential",
                            "identity": author.identifier,
                        },
                        {"expected_version": 2},
                        proof=proof_for(rev_private, "admin"),
                    )
                    assert revoked.outcome == Outcome.SUCCESS
                finally:
                    rev_store.close()

        store, private, execution = service(directory, hook=revoke_before_seal)
        try:
            result = execution.invoke(
                "execution.run",
                TARGET,
                json.loads((directory / "run.json").read_text())["inputs"],
                proof=proof_for(private, "author"),
            )
            assert execution.load("task-1")[1]["cleanup"] == "verified"
            with store.engine.connect() as tx:
                assert (
                    tx.exec_driver_sql(
                        "SELECT count(*) FROM coordination_facts WHERE stage='observe'"
                    ).scalar()
                    == 0
                )
            assert (
                execution.invoke(
                    "execution.status",
                    TARGET,
                    {"attempt_id": "attempt-1"},
                    proof=proof_for(private, "author"),
                ).outcome
                == Outcome.REFUSED
            )
            checks.append(
                {
                    "case": "revoked_caller_safety_cleanup_without_progression",
                    "result": "passed",
                    "operation": asdict(result),
                }
            )
        finally:
            store.close()
        # Actual inaccessible endpoint and injected Engine-ID change retain holds.
        for failure in ("unreachable_connection", "changed_engine_id"):
            directory = installation("wait")

            class BrokenBinding(DockerWorker):
                broken = False

                def engine(self, timeout=10, failure=failure):
                    if BrokenBinding.broken:
                        if failure == "unreachable_connection":
                            other = DockerWorker(
                                self.settings
                                | {"endpoint": "unix:///nonexistent-mobiraeon-fixture.sock"}
                            )
                            return other.engine(timeout)
                        other = DockerWorker(self.settings | {"engine_id": "changed-engine"})
                        return other.engine(timeout)
                    return super().engine(timeout)

            def break_binding(phase):
                if phase == "after_start":
                    BrokenBinding.broken = True

            store, private, execution = service(directory, BrokenBinding, break_binding)
            try:
                result = execution.invoke(
                    "execution.run",
                    TARGET,
                    json.loads((directory / "run.json").read_text())["inputs"],
                    proof=proof_for(private, "author"),
                )
                assert (
                    result.outcome == Outcome.UNCERTAIN and execution.load("task-1")[1]["held"]
                )
                before = store.path.read_bytes()
                cli(directory, "status")
                assert store.path.read_bytes() == before
                stopped = cli(directory, "stop")["data"]["records"][0]
                assert stopped["cleanup"] == "verified" and stopped["outcome"] == "unknown"
                checks.append(
                    {
                        "case": failure,
                        "result": "passed",
                        "before_cleanup": asdict(result),
                        "after_cleanup": stopped,
                    }
                )
            finally:
                store.close()
        # Escaping-heavy 64-KiB input through public preparation, actual capture and acceptance.
        boundary = json.loads(input_file.read_bytes())
        content = "\x01" * 65536
        boundary["work"]["inputs"][0] |= {
            "content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }
        boundary_file = outside / "boundary.json"
        boundary_file.write_text(json.dumps(boundary), encoding="utf-8")
        counter += 1
        directory = outside / ("private-" + str(counter))
        command(
            [
                "-m",
                "mobiraeon.execution_fixture",
                "prepare",
                "--directory",
                directory,
                "--input",
                boundary_file,
                "--catalog-input",
                catalog_input,
                "--image-id",
                image_id,
            ]
        )
        result = cli(directory, "run")
        record = result["data"]["records"][0]
        assert (
            record["artifact_valid"]
            and json.loads(record["artifact"]["content"])["utf8_bytes"] == 65536
        )
        store, private, execution = service(directory)
        try:
            coordinator = Coordinator(store, private, access=AssessorAccess(store, private))
            author = proof_for(private, "author")
            submitted = coordinator.invoke(
                "coordination.submit",
                TARGET,
                {
                    "operation_id": "boundary-submit",
                    "expected_version": 4,
                    "attempt_id": "attempt-1",
                    "submission_id": "boundary-submission",
                    "artifacts": [record["artifact"]],
                },
                proof=author,
            )
            assert submitted.outcome == Outcome.SUCCESS
            digest = submitted.data.records[0]["fact"]["submission_digest"]
            assessor = proof_for(private, "assessor")
            assessed = coordinator.invoke(
                "coordination.assess",
                TARGET,
                {
                    "operation_id": "boundary-assess",
                    "expected_version": 5,
                    "submission_id": "boundary-submission",
                    "submission_digest": digest,
                    "evidence": [record["artifact"]],
                    "decision": "approve",
                    "rationale": "Exact byte-boundary artifact assessed",
                },
                proof=assessor,
            )
            assert assessed.outcome == Outcome.SUCCESS
            assert (
                coordinator.invoke(
                    "coordination.accept",
                    TARGET,
                    {
                        "operation_id": "boundary-accept",
                        "expected_version": 6,
                        "submission_id": "boundary-submission",
                        "submission_digest": digest,
                        "assessment_id": "boundary-assess",
                    },
                    proof=assessor,
                ).outcome
                == Outcome.SUCCESS
            )
            checks.append(
                {
                    "case": "utf8_64k_escaped_end_to_end_acceptance",
                    "result": "passed",
                    "artifact": record["artifact"],
                }
            )
        finally:
            store.close()
        # Public concurrency, >30-second lifetime, and the guard after SIGKILL.
        for abrupt in (False, True):
            directory = installation("wait", duration=40 if not abrupt and long_wait else 2)
            args = [
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
                args,
                cwd=outside,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            lines = []
            notifications = queue.Queue()

            def drain(process=process, lines=lines, notifications=notifications):
                for line in process.stdout:
                    lines.append(line)
                    notifications.put(json.loads(line))

            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                event = notifications.get(timeout=max(0.1, deadline - time.monotonic()))
                if event.get("data") and event["data"]["state"] == "running":
                    break
            else:
                raise AssertionError("fixture did not start")
            if abrupt:
                process.kill()
                process.wait(timeout=5)
                record = cli(directory, "status")["data"]["records"][0]
                assert record["held"] and not record["terminal"]
                store, private, execution = service(directory)
                try:
                    handoff, current = execution.load("task-1")
                    deadline = time.monotonic() + 22
                    worker = DockerWorker(handoff["settings"])
                    while time.monotonic() < deadline:
                        observed = worker.inspect(handoff, current["container_id"])
                        if not observed["State"]["Running"]:
                            break
                        time.sleep(0.2)
                    else:
                        raise AssertionError("fixture lifetime guard did not stop activity")
                    before = store.path.read_bytes()
                    cli(directory, "status")
                    assert store.path.read_bytes() == before
                    stopped = cli(directory, "stop")["data"]["records"][0]
                    assert stopped["cleanup"] == "verified" and stopped["outcome"] == "unknown"
                finally:
                    store.close()
            else:
                if long_wait:
                    # A bounded wait exceeding the former 30-second assumption.
                    end = time.monotonic() + 31
                    while time.monotonic() < end:
                        assert process.poll() is None
                        time.sleep(0.25)
                assert cli(directory, "status")["data"]["records"][0]["phase"] == "running"
                from concurrent.futures import ThreadPoolExecutor

                with ThreadPoolExecutor(max_workers=2) as pool:
                    stops = list(
                        pool.map(
                            lambda _, directory=directory: cli(directory, "stop"), range(2)
                        )
                    )
                assert all(s["data"]["records"][0]["stop_acknowledged"] for s in stops)
                process.wait(timeout=20)
                cli(directory, "stop")
                stopped = cli(directory, "status")["data"]["records"][0]
                assert stopped["cleanup"] == "verified" and not stopped["artifact_valid"]
            reader.join(timeout=2)
            errors = process.stderr.read()
            process.stdout.close()
            process.stderr.close()
            checks.append(
                {
                    "case": "abrupt_guard_cleanup" if abrupt else "long_wait_public_stop",
                    "command": args,
                    "exit_code": process.returncode,
                    "stdout": "".join(lines),
                    "stderr": errors,
                    "result": "passed",
                }
            )
        from mobiraeon.execution_repair_verification import exercise as repair_exercise

        repairs = repair_exercise(input_file, catalog_input, image_id)
        checks.append(
            {
                "case": "I4-R1-R3_regressions",
                "result": repairs["result"],
                "regressions": repairs,
            }
        )
        assert repairs["result"] == "passed", repairs
        return {
            "result": "passed",
            "checks": checks,
            "image_id": image_id,
            "input_sha256": hashlib.sha256(input_file.read_bytes()).hexdigest(),
            "catalog_input_sha256": hashlib.sha256(catalog_input.read_bytes()).hexdigest(),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--catalog-input", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--short", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            exercise(args.input, args.catalog_input, args.image_id, long_wait=not args.short),
            default=str,
        )
    )


if __name__ == "__main__":
    main()
