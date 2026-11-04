"""Trusted completion-deadline controls using ordinary imports, never live qualification."""

import argparse
import io
import json
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

import mobiraeon.docker_worker as docker
import mobiraeon.execution as execution
import mobiraeon.execution_trace as telemetry
from mobiraeon import execution_fixture
from mobiraeon.configuration import resolve_configuration
from mobiraeon.execution_diagnostics import terminal_fields
from mobiraeon.execution_settings import DEFAULTS
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState, harden
from mobiraeon.scenario import TARGET, proof_for

CASES = (
    "failed",
    "success",
    "supervisor_to_inspect",
    "inspect_entry",
    "info_call_entry",
    "container_call_entry",
    "info_call_exit",
    "container_call_exit",
    "before_dispatch",
    "info_transport_return",
    "container_transport_return",
    "info_result",
    "container_result",
    "info_parse",
    "container_parse",
    "engine_identity",
    "container_state",
    "owned_identity_verified",
    "inspect_exit",
    "completion_predicates",
    "custom_worker_return",
    "deadline_equality",
    "telemetry_failure",
)


def deadline_control(case, input_file, catalog_input):
    """Actual service, SQLite, Worker dispatch and admission under controlled scheduling."""
    if case not in CASES:
        raise ValueError("unsupported trusted deadline control")
    positive = case in {"failed", "success", "telemetry_failure"}
    attachment_exit = 0 if case == "success" else 1
    clock = {"now": 100.0, "deadline": None, "paused": False}
    calls = []
    cleanup_scope = []
    original_add, original_loads = telemetry.BoundaryTrace.add, json.loads

    def pause():
        if not clock["paused"]:
            clock["now"] += 0.05
            clock["paused"] = True

    def add(trace, kind, **fields):
        if case == "telemetry_failure" and kind == "inspect_entry":
            raise OSError("trusted telemetry unavailable")
        result = original_add(trace, kind, **fields)
        if kind == "execution_deadline":
            clock["deadline"] = fields["execution_deadline"]
            clock["now"] = clock["deadline"] - 0.01
        operation = fields.get("operation")
        if (
            kind == case
            or case == "info_call_entry"
            and kind == "docker_call_entry"
            and operation == "info"
            or case == "container_call_entry"
            and kind == "docker_call_entry"
            and operation == "container_inspect"
            or case == "info_call_exit"
            and kind == "docker_call_exit"
            or case == "container_call_exit"
            and kind == "docker_call_exit"
            and sum(c["cutoff"] is not None for c in calls) == 2
            or case == "info_result"
            and kind == "docker_call_result"
            and operation == "info"
            or case == "container_result"
            and kind == "docker_call_result"
            and operation == "container_inspect"
        ):
            pause()
        if case == "deadline_equality" and kind == "inspect_entry":
            clock["now"] = clock["deadline"]
            clock["paused"] = True
        return result

    def loads(raw, *args, **kwargs):
        result = original_loads(raw, *args, **kwargs)
        if isinstance(raw, bytes) and (
            case == "info_parse"
            and raw.startswith(b'{"ID":')
            or case == "container_parse"
            and raw.startswith(b'[{"Id":')
        ):
            pause()
        return result

    finished = dict(
        Running=False,
        ExitCode=attachment_exit,
        StartedAt="2026-11-04T00:00:00Z",
        FinishedAt="2026-11-04T00:00:01Z",
        OOMKilled=False,
    )

    class Process:
        def __init__(self, content):
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(
                json.dumps(execution.summary(content)).encode() if attachment_exit == 0 else b""
            )
            self.stderr = io.BytesIO(b"fixture failure\n" if attachment_exit else b"")

        def poll(self):
            return attachment_exit

        def wait(self, timeout=None):
            return attachment_exit

        def kill(self):
            pass

    class Worker(docker.DockerWorker):
        def __init__(self, settings):
            super().__init__(settings)
            self.inspections = 0

        def preflight(self):
            return {"trusted_control": True}

        def create(self, handoff, timeout=None):
            self.handoff = handoff
            return "a" * 64

        def start(self, identity, timeout=None):
            return Process(self.handoff["input"]["content"])

        def inspect(self, handoff, identity=None, timeout=10):
            self.inspections += 1
            if self.inspections == 1:
                return {
                    "State": finished | {"Running": True, "FinishedAt": "0001-01-01T00:00:00Z"}
                }
            if case == "supervisor_to_inspect":
                pause()
            if case == "custom_worker_return":
                pause()
                return {"State": finished}
            return super().inspect(handoff, identity, timeout)

        def _call(self, *command, timeout=10, check=True):
            if case == "before_dispatch":
                pause()
            return super()._call(*command, timeout=timeout, check=check)

        def cleanup(self, handoff, record):
            cleanup_scope.append(docker._completion_cutoff.get())
            self.last_state = {"State": finished}
            return True

    def transport(command, **kwargs):
        operation = "info" if command[2] == "info" else "container_inspect"
        scope = docker._completion_cutoff.get()
        calls.append(
            dict(
                operation=operation,
                timeout=kwargs["timeout"],
                cutoff=scope,
                remaining=None if scope is None else scope - clock["now"],
            )
        )
        if operation == "info":
            data = {"ID": settings["engine_id"]}
            if case == "info_transport_return":
                pause()
        else:
            active_worker = workers[-1]
            data = [
                dict(
                    Id="a" * 64,
                    Name="/" + active_worker.handoff["name"],
                    Image=settings["image_id"],
                    Config={"Labels": {"name.mobiraeon.nonce": active_worker.handoff["nonce"]}},
                    State=finished,
                )
            ]
            if case == "container_transport_return":
                pause()
        return subprocess.CompletedProcess(command, 0, json.dumps(data).encode(), b"")

    with tempfile.TemporaryDirectory(prefix="mobiraeon-final09-deadline-") as temporary:
        outside = Path(temporary)
        harden(outside)
        directory = outside / "private"
        settings = DEFAULTS | dict(
            image_id="sha256:" + "a" * 64,
            engine_id="trusted-engine",
            endpoint="unix:///trusted.sock",
            docker_executable="/trusted/docker",
            startup_seconds=10,
            execution_seconds=2,
            grace_seconds=1,
            cleanup_seconds=5,
        )
        with (
            patch.object(execution_fixture, "discover", return_value=settings),
            patch.object(docker.DockerWorker, "preflight", return_value={}),
        ):
            execution_fixture.prepare(
                directory, Path(input_file), Path(catalog_input), settings["image_id"]
            )
        config = resolve_configuration(
            options={"config": str(directory / "settings.toml")}, environ={}
        )
        private = PrivateState(config.private_dir, config.database_path)
        store = Store(config.database_path)
        workers = []

        def worker_type(values):
            instance = Worker(values)
            workers.append(instance)
            return instance

        try:
            service = execution.ExecutionService(
                store, private, config.execution, worker_type=worker_type
            )
            inputs = json.loads((directory / "run.json").read_text())["inputs"] | {
                "mode": "success" if attachment_exit == 0 else "failure"
            }
            with (
                patch.object(execution.time, "monotonic", side_effect=lambda: clock["now"]),
                patch.object(telemetry.BoundaryTrace, "add", add),
                patch.object(docker.json, "loads", loads),
                patch.object(docker.subprocess, "run", side_effect=transport),
                patch.object(docker.sys, "platform", "linux"),
                patch.object(
                    execution, "actuation_lock", side_effect=lambda unused: nullcontext()
                ),
            ):
                result = service.invoke(
                    "execution.run", TARGET, inputs, proof=proof_for(private, "author")
                )
                handoff, record = service.load("task-1")
                # A failed completion must not leak its expired cutoff into unrelated calls.
                reset_before_call = docker._completion_cutoff.get() is None
                outside_result = docker.DockerWorker(settings).call("info", timeout=0.1)
            with store.engine.connect() as tx:
                observations = [
                    json.loads(v)["inputs"]["observation"]
                    for v in tx.exec_driver_sql(
                        "SELECT record FROM coordination_facts WHERE stage='observe'"
                    ).scalars()
                ]
            path = Path(handoff["settings"]["data_dir"]) / (handoff["nonce"] + ".boundary.json")
            trace = json.loads(path.read_text())
            expected = "succeeded" if case == "success" else "failed" if positive else "unknown"
            expected_observations = [expected] if positive else []
            scoped_calls = [c for c in calls if c["cutoff"] is not None]
            required = (
                record["outcome"] == expected
                and observations == expected_observations
                and record["artifact_valid"] is (case == "success")
                and record["cleanup"] == "verified"
                and record["held"] is False
                and all(
                    c["remaining"] > 0 and 0 < c["timeout"] <= c["remaining"]
                    for c in scoped_calls
                )
                and cleanup_scope == [None]
                and reset_before_call
                and outside_result.returncode == 0
                and calls[-1]["cutoff"] is None
            )
            if not positive:
                required &= record["completion_state"] is None and clock["paused"]
            if case == "telemetry_failure":
                required &= trace["telemetry_failed"]
            return dict(
                required_behavior=bool(required),
                case=case,
                scope=(
                    "Trusted scheduling/transport observations through actual service, "
                    "Worker dispatch and SQLite; no Docker or historical cause claim"
                ),
                python=sys.executable,
                outcome=result.outcome.value,
                record=terminal_fields(record),
                expected_outcome=expected,
                observations=observations,
                calls=calls,
                cleanup_scope_reset=cleanup_scope == [None],
                post_scope_call_succeeded=reset_before_call and outside_result.returncode == 0,
                boundary_trace=trace,
            )
        finally:
            store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--catalog-input", type=Path, required=True)
    parser.add_argument("--case", choices=CASES)
    args = parser.parse_args()
    results = [
        deadline_control(case, args.input, args.catalog_input)
        for case in ((args.case,) if args.case else CASES)
    ]
    passed = all(result["required_behavior"] for result in results)
    print(json.dumps({"result": "passed" if passed else "failed", "checks": results}))
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
