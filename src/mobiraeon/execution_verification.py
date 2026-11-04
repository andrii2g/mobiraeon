"""Trusted fixture-only verification, callable from source or a clean installed wheel."""

import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
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
from mobiraeon.execution_diagnostics import (
    CheckLog,
    VerificationFailure,
    check_failure_terminal,
    json_observation,
    verification_workspace,
)
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


def verify_trusted_variant(checks, directory, variant, store, private, execution):
    """The real verifier's fixed-variant assertions, shared with trusted reporting controls."""

    inputs = json.loads((directory / "run.json").read_text())["inputs"]
    mode = inputs["mode"]

    def stage(name, expected, terminal=None):
        checks.activate(
            "trusted_variant",
            name,
            mode=mode,
            variant=variant,
            directory=directory,
            expected=expected,
            terminal=terminal,
        )

    stage("invoke", "the fixed trusted variant produces verified failure")
    result = execution.invoke(
        "execution.run", TARGET, inputs, proof=proof_for(private, "author")
    )
    record = execution.load("task-1")[1]
    stage(
        "terminal_assertion", "failed operation, verified cleanup and invalid artifact", record
    )
    assert (
        result.outcome == Outcome.FAILURE
        and record["cleanup"] == "verified"
        and not record["artifact_valid"]
    ), record
    stage("coordination_observation", "failed observation matches the execution seal", record)
    with store.engine.connect() as tx:
        observed = json.loads(
            tx.exec_driver_sql(
                "SELECT record FROM coordination_facts WHERE stage='observe'"
            ).scalar()
        )
    assert observed["inputs"]["observation"] == "failed"
    assert observed["inputs"]["detail"] == record["seal"]
    stage(
        "capture_assertions",
        "the fixed variant has its required diagnostic observations",
        record,
    )
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
        assert record["runtime_state"]["OOMKilled"] or "MemoryError" in capture["stderr"]
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


def verify_nested_repairs(checks, input_file, catalog_input, image_id):
    """The actual parent integration, also used by trusted no-Docker controls."""
    from mobiraeon.execution_repair_verification import exercise as repair_exercise

    checks.activate(
        "I4-R1-R3_regressions", "nested_verification", expected="nested repair suite passes"
    )
    try:
        repairs = repair_exercise(input_file, catalog_input, image_id)
    except VerificationFailure as error:
        checks.append(
            {"case": "I4-R1-R3_regressions", "result": "failed", "regressions": error.report}
        )
        report = error.report | {
            "checks": json_observation(list(checks)),
            "nested_diagnostic": {
                "module": error.report["module"],
                "protected_state": error.report["protected_state"],
                "diagnostic_storage": error.report["diagnostic_storage"],
            },
            "parent_context": {"module": __file__, "active": checks.active.copy()},
        }
        raise VerificationFailure(report) from None
    checks.append(
        {"case": "I4-R1-R3_regressions", "result": repairs["result"], "regressions": repairs}
    )
    assert repairs["result"] == "passed", repairs
    return repairs


def exercise(input_file, catalog_input, image_id, *, long_wait=True):
    if sys.platform != "linux":
        return {
            "result": "unavailable",
            "reason": "Worker requires local Linux Docker; portable tests remain applicable",
        }

    checks = CheckLog(image_id)
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    environment.pop("PYTHONPATH", None)
    with verification_workspace(checks) as outside:

        def command(args, expect=0, timeout=240):
            return checks.command(
                args, cwd=outside, env=environment, expect=expect, timeout=timeout
            )

        counter = 0

        def installation(mode="success", duration=2):
            nonlocal counter
            counter += 1
            directory = outside / ("private-" + str(counter))
            checks.activate(
                "fixture_preparation",
                "preparation",
                mode=mode,
                directory=directory,
                expected="preparation exits zero with valid JSON and protected settings",
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
            checks.activate(
                "fixture_preparation",
                "fixture_configuration",
                mode=mode,
                directory=directory,
                expected="apply the fixed public fixture settings",
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
            checks.activate(
                checks.active.get("case")
                if checks.active.get("case") != "fixture_preparation"
                else "public_cli",
                "cli." + action,
                mode=checks.active.get("mode"),
                variant=checks.active.get("variant"),
                phase=checks.active.get("phase"),
                expected=f"CLI {action} exits {expect} with valid JSON",
                directory=directory,
            )
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

        def context(
            case,
            stage,
            expected,
            *,
            mode="success",
            variant=None,
            phase=None,
            terminal=None,
            fixture=None,
        ):
            checks.activate(
                case,
                stage,
                expected=expected,
                mode=mode,
                variant=variant,
                phase=phase,
                directory=fixture if fixture is not None else directory,
                terminal=terminal,
            )

        # Public helper/CLI success; exact output through independent assessment and acceptance.
        directory = installation()
        context(
            "registry_admin_without_execution_grants",
            "admission",
            "refused.outcome == Outcome.REFUSED",
        )
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
        context("public_success", "run", "successful public execution with a valid artifact")
        result = cli(directory, "run")
        record = result["data"]["records"][0]
        context(
            "public_success",
            "terminal_assertion",
            "successful execution releases its hold",
            terminal=record,
        )
        assert (
            record["outcome"] == "succeeded" and record["artifact_valid"] and not record["held"]
        )
        inspected = cli(directory, "status")["data"]["records"][0]
        context(
            "public_success",
            "status_artifact",
            "status retains the exact artifact",
            terminal=inspected,
        )
        assert inspected["artifact"] == record["artifact"]
        replayed = cli(directory, "run")["data"]["records"][0]
        context(
            "public_success",
            "replay",
            "duplicate public launch is inspection only",
            terminal=replayed,
        )
        assert replayed["replayed"]
        context(
            "accepted_exact_supervised_artifact",
            "coordinator_setup",
            "only exact captured evidence can progress to independent acceptance",
            terminal=record,
        )
        store, private, execution = service(directory)
        try:
            coordinator = Coordinator(store, private, access=AssessorAccess(store, private))
            with store.engine.connect() as tx:
                version = tx.exec_driver_sql("SELECT version FROM coordination_tasks").scalar()
            author = proof_for(private, "author")
            context(
                "accepted_exact_supervised_artifact",
                "submit",
                "submission.outcome == Outcome.SUCCESS",
                terminal=record,
            )
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
            context(
                "accepted_exact_supervised_artifact",
                "self_assessment_refused",
                "author cannot independently assess",
                terminal=record,
            )
            assert (
                coordinator.invoke(
                    "coordination.assess", TARGET, assessment, proof=author
                ).outcome
                != Outcome.SUCCESS
            )
            context(
                "accepted_exact_supervised_artifact",
                "independent_assessment",
                "the independent fixture assessor can assess exact evidence",
                terminal=record,
            )
            assessor = proof_for(private, "assessor")
            assert (
                coordinator.invoke(
                    "coordination.assess", TARGET, assessment, proof=assessor
                ).outcome
                == Outcome.SUCCESS
            )
            context(
                "accepted_exact_supervised_artifact",
                "accept",
                "accepted.outcome == Outcome.SUCCESS",
                terminal=record,
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
            context(
                "accepted_exact_supervised_artifact",
                "status",
                "Task accepted; Request open; Initiative unaccepted",
                terminal=record,
            )
            status = coordinator.invoke(
                "coordination.status", TARGET, {}, proof=author
            ).data.records[0]
            assert (
                status["state"] == "accepted"
                and status["request_state"] == "open"
                and status["initiative_acceptance"] == "unaccepted"
            )
            assert store.engine.connect().close() is None
            context(
                "accepted_exact_supervised_artifact",
                "terminal_stop_readonly",
                "stop does not change the sealed terminal",
                terminal=record,
            )
            terminal = execution.load("task-1")[1]
            checks.cleanup_observation("before_terminal_stop", terminal)
            cli(directory, "stop")
            after_stop = execution.load("task-1")[1]
            checks.cleanup_observation("after_terminal_stop", after_stop)
            context(
                "accepted_exact_supervised_artifact",
                "terminal_stop_readonly",
                "stop does not change the sealed terminal",
                terminal=after_stop,
            )
            assert after_stop == terminal
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
            context(
                "public_failure_mode",
                "run",
                "public mode fails without a valid artifact",
                mode=mode,
            )
            result = cli(directory, "run", expect=1)
            record = result["data"]["records"][0]
            check_failure_terminal(checks, record, expected)
            context(
                "public_failure_mode",
                "coordination_observation",
                "failed observation matches seal",
                mode=mode,
                terminal=record,
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
            context(
                "trusted_variant",
                "service_setup",
                "fixed trusted variant can be inspected",
                variant=variant,
            )

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
                    context(
                        "trusted_variant",
                        "cpu_probe",
                        "nr_throttled is positive",
                        variant=variant,
                        phase=phase,
                        fixture=directory,
                    )
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
                verify_trusted_variant(checks, directory, variant, store, private, execution)
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
            context(
                "injected_effect", "invoke", "injected effect remains uncertain", phase=phase
            )
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
                context(
                    "injected_effect",
                    "injected_phase",
                    "ordered stop or retained delivery uncertainty",
                    phase=phase,
                    fixture=directory,
                )
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
                context(
                    "injected_effect",
                    "result_assertion",
                    "result.outcome == Outcome.UNCERTAIN",
                    phase=phase,
                )
                assert result.outcome == Outcome.UNCERTAIN
                record = execution.load("task-1")[1]
                assert not record["artifact_valid"]
                context(
                    "injected_effect",
                    "replay_and_fence",
                    "replay does not repeat create/start",
                    phase=phase,
                    terminal=record,
                )
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
                checks.cleanup_observation("before_cleanup", record)
                context(
                    "injected_effect",
                    "authorized_cleanup",
                    "cleanup cannot manufacture success",
                    phase=phase,
                    terminal=record,
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
                checks.cleanup_observation("after_cleanup", final)
                context(
                    "injected_effect",
                    "cleanup_assertion",
                    "unknown create holds or verified unknown retirement",
                    phase=phase,
                    terminal=final,
                )
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
        context(
            "revoked_caller_safety_cleanup_without_progression",
            "invoke",
            "revocation allows safety cleanup only",
        )

        def revoke_before_seal(phase):
            if phase == "before_seal":
                context(
                    "revoked_caller_safety_cleanup_without_progression",
                    "revoke",
                    "revoked.outcome == Outcome.SUCCESS",
                    phase=phase,
                )
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
            record = execution.load("task-1")[1]
            context(
                "revoked_caller_safety_cleanup_without_progression",
                "cleanup_and_authority_assertions",
                "verified cleanup without Coordination progression or revoked status access",
                terminal=record,
            )
            assert record["cleanup"] == "verified"
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
            context(
                "broken_worker_binding",
                "invoke",
                "binding loss retains uncertain hold",
                mode="wait",
                variant=failure,
            )

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

            def break_binding(phase, failure=failure):
                if phase == "after_start":
                    context(
                        "broken_worker_binding",
                        "injected_phase",
                        "lost or changed Engine identity stays uncertain",
                        mode="wait",
                        variant=failure,
                        phase=phase,
                    )
                    BrokenBinding.broken = True

            store, private, execution = service(directory, BrokenBinding, break_binding)
            try:
                result = execution.invoke(
                    "execution.run",
                    TARGET,
                    json.loads((directory / "run.json").read_text())["inputs"],
                    proof=proof_for(private, "author"),
                )
                record = (
                    execution.load("task-1")[1] if result.outcome == Outcome.UNCERTAIN else None
                )
                context(
                    "broken_worker_binding",
                    "hold_assertion",
                    "uncertain execution remains held",
                    mode="wait",
                    variant=failure,
                    terminal=record,
                )
                assert result.outcome == Outcome.UNCERTAIN and record["held"]
                before = store.path.read_bytes()
                status_record = cli(directory, "status")["data"]["records"][0]
                context(
                    "broken_worker_binding",
                    "status_readonly",
                    "status cannot mutate retained bytes",
                    mode="wait",
                    variant=failure,
                    terminal=status_record,
                )
                assert store.path.read_bytes() == before
                checks.cleanup_observation("before_cleanup", record)
                stopped = cli(directory, "stop")["data"]["records"][0]
                checks.cleanup_observation("after_cleanup", stopped)
                context(
                    "broken_worker_binding",
                    "cleanup_assertion",
                    "verified cleanup retains unknown outcome",
                    mode="wait",
                    variant=failure,
                    terminal=stopped,
                )
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
        checks.activate(
            "utf8_64k_escaped_end_to_end_acceptance",
            "prepare_input",
            mode="success",
            expected="escaping-heavy 64-KiB UTF-8 input is retained exactly",
        )
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
        context(
            "utf8_64k_escaped_end_to_end_acceptance",
            "preparation",
            "boundary fixture preparation exits zero",
        )
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
        context(
            "utf8_64k_escaped_end_to_end_acceptance",
            "artifact_assertion",
            "valid captured artifact retains 65536 UTF-8 bytes",
            terminal=record,
        )
        assert (
            record["artifact_valid"]
            and json.loads(record["artifact"]["content"])["utf8_bytes"] == 65536
        )
        store, private, execution = service(directory)
        try:
            coordinator = Coordinator(store, private, access=AssessorAccess(store, private))
            author = proof_for(private, "author")
            context(
                "utf8_64k_escaped_end_to_end_acceptance",
                "submit",
                "exact boundary artifact submission succeeds",
                terminal=record,
            )
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
            context(
                "utf8_64k_escaped_end_to_end_acceptance",
                "assess",
                "independent assessment of boundary evidence succeeds",
                terminal=record,
            )
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
            context(
                "utf8_64k_escaped_end_to_end_acceptance",
                "accept",
                "exact assessed boundary artifact can be accepted",
                terminal=record,
            )
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
            case = "abrupt_guard_cleanup" if abrupt else "long_wait_public_stop"
            context(case, "start", "public supervisor emits running readiness", mode="wait")
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
            context(
                case,
                "running_observation",
                "running supervisor is retained until explicit stop or guard",
                mode="wait",
            )
            if abrupt:
                process.kill()
                process.wait(timeout=5)
                record = cli(directory, "status")["data"]["records"][0]
                context(
                    case,
                    "lost_supervisor_assertion",
                    "lost supervisor retains a nonterminal hold",
                    mode="wait",
                    terminal=record,
                )
                assert record["held"] and not record["terminal"]
                store, private, execution = service(directory)
                try:
                    handoff, current = execution.load("task-1")
                    context(
                        case,
                        "lifetime_guard",
                        "fixed lifetime guard stops owned activity",
                        mode="wait",
                        terminal=record,
                    )
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
                    status_record = cli(directory, "status")["data"]["records"][0]
                    context(
                        case,
                        "status_readonly",
                        "lost-supervisor status is read-only",
                        mode="wait",
                        terminal=status_record,
                    )
                    assert store.path.read_bytes() == before
                    checks.cleanup_observation("before_cleanup", record)
                    stopped = cli(directory, "stop")["data"]["records"][0]
                    checks.cleanup_observation("after_cleanup", stopped)
                    context(
                        case,
                        "cleanup_assertion",
                        "verified retirement retains unknown execution",
                        mode="wait",
                        terminal=stopped,
                    )
                    assert stopped["cleanup"] == "verified" and stopped["outcome"] == "unknown"
                finally:
                    store.close()
            else:
                context(
                    case, "long_wait", "supervisor stays alive beyond 30 seconds", mode="wait"
                )
                if long_wait:
                    # A bounded wait exceeding the former 30-second assumption.
                    end = time.monotonic() + 31
                    while time.monotonic() < end:
                        assert process.poll() is None
                        time.sleep(0.25)
                running = cli(directory, "status")["data"]["records"][0]
                context(
                    case,
                    "running_assertion",
                    "public status still observes running",
                    mode="wait",
                    terminal=running,
                )
                assert running["phase"] == "running"
                from concurrent.futures import ThreadPoolExecutor

                context(
                    case,
                    "concurrent_stop",
                    "both authorized stop requests are acknowledged",
                    mode="wait",
                )
                with ThreadPoolExecutor(max_workers=2) as pool:
                    stops = list(
                        pool.map(
                            lambda _, directory=directory: cli(directory, "stop"), range(2)
                        )
                    )
                context(
                    case,
                    "stop_acknowledgements",
                    "both concurrent stops acknowledge intent",
                    mode="wait",
                    terminal=stops[-1]["data"]["records"][0],
                )
                assert all(s["data"]["records"][0]["stop_acknowledged"] for s in stops)
                process.wait(timeout=20)
                cli(directory, "stop")
                stopped = cli(directory, "status")["data"]["records"][0]
                context(
                    case,
                    "cleanup_assertion",
                    "cleanup is verified and artifact invalid",
                    mode="wait",
                    terminal=stopped,
                )
                assert stopped["cleanup"] == "verified" and not stopped["artifact_valid"]
            context(
                case,
                "capture_export",
                "finished supervisor streams can be exported",
                mode="wait",
                terminal=stopped,
            )
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
        verify_nested_repairs(checks, input_file, catalog_input, image_id)
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
    try:
        report = exercise(
            args.input, args.catalog_input, args.image_id, long_wait=not args.short
        )
    except VerificationFailure as error:
        report = error.report
    except Exception as error:
        report = CheckLog(args.image_id).failure(error)
        report["diagnostic_storage"] = {"available": False, "reason": "outside_workspace"}
    print(json.dumps(json_observation(report)))
    return int(report["result"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
