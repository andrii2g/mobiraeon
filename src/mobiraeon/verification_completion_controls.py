"""Ordinary-import completion controls. Trusted observations; never live qualification."""

import io
import json
import tempfile
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from mobiraeon import execution_fixture
from mobiraeon.configuration import resolve_configuration
from mobiraeon.docker_worker import DockerWorker
from mobiraeon.errors import Reason, SafeError
from mobiraeon.execution import ExecutionService, summary
from mobiraeon.execution_diagnostics import terminal_fields
from mobiraeon.execution_settings import DEFAULTS
from mobiraeon.execution_trace import event
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState, harden
from mobiraeon.scenario import TARGET, proof_for


def completion_control(case, input_file, catalog_input, *, observed=None, observed_error=None):
    state = dict(
        Running=False,
        ExitCode=1,
        StartedAt="2026-11-04T00:00:00Z",
        FinishedAt="2026-11-04T00:00:01Z",
    )
    positive = case in {
        "finished_one",
        "finished_zero",
        "storage",
        "truncation",
        "observed_owned_finished",
    }
    attach = 0 if case == "finished_zero" else 1
    inspections = []

    class Process:
        def __init__(self, content):
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(
                json.dumps(summary(content)).encode() if attach == 0 else b""
            )
            self.stderr = io.BytesIO(b"fixture failure\n" if attach else b"")

        def poll(self):
            return attach

        def wait(self, timeout=None):
            return attach

        def kill(self):
            pass

    class Worker:
        def __init__(self, settings):
            self.inspections = 0

        def preflight(self):
            return {"trusted_control": True}

        def create(self, handoff, timeout=None):
            self.handoff = handoff
            return "a" * 64

        def start(self, identity, timeout=None):
            return Process(self.handoff["input"]["content"])

        def inspect(self, handoff, identity=None, timeout=None):
            self.inspections += 1
            inspections.append(
                dict(
                    stage="startup" if self.inspections == 1 else "completion", timeout=timeout
                )
            )
            if self.inspections == 1:
                return {"State": state | dict(Running=True, FinishedAt="0001-01-01T00:00:00Z")}
            if case == "observed_unavailable" and observed_error is not None:
                assert observed_error["exception_type"] == "SafeError"
                assert observed_error["reason"] == Reason.UNCERTAIN.value
            if case in {
                "transport_timeout",
                "launch",
                "nonzero",
                "engine",
                "ownership",
                "observed_unavailable",
            }:
                raise SafeError(
                    Reason.UNAVAILABLE if case in {"engine", "nonzero"} else Reason.UNCERTAIN
                )
            if case == "malformed":
                raise json.JSONDecodeError("trusted", "", 0)
            if case in {
                "missing",
                "cleanup_zero",
                "cleanup_one",
                "attachment_only",
                "capture_only",
            }:
                return None
            result = state.copy()
            if case == "running":
                result.update(Running=True)
            if case == "unfinished":
                result.update(FinishedAt="0001-01-01T00:00:00Z")
            if case == "invalid_exit":
                result.update(ExitCode=True)
            if case == "finished_zero":
                result.update(ExitCode=0)
            if case == "observed_owned_finished":
                assert (
                    observed
                    and observed["Running"] is False
                    and type(observed["ExitCode"]) is int
                )
                result = observed.copy()
            return {"State": result}

        def cleanup(self, handoff, record):
            self.last_state = {
                "State": state | {"ExitCode": 0 if case == "cleanup_zero" else 1}
            }
            return True

    with tempfile.TemporaryDirectory(prefix="mobiraeon-q2-control-") as temporary:
        outside = Path(temporary)
        harden(outside)
        directory = outside / "private"
        settings = DEFAULTS | dict(
            image_id="sha256:" + "a" * 64,
            engine_id="trusted-engine",
            endpoint="unix:///trusted.sock",
            docker_executable="/trusted/docker",
        )
        with (
            patch.object(execution_fixture, "discover", return_value=settings),
            patch.object(DockerWorker, "preflight", return_value={"trusted_control": True}),
        ):
            execution_fixture.prepare(
                directory, Path(input_file), Path(catalog_input), settings["image_id"]
            )
        config = resolve_configuration(
            options={"config": str(directory / "settings.toml")}, environ={}
        )
        private = PrivateState(config.private_dir, config.database_path)
        store = Store(config.database_path)
        try:
            service = ExecutionService(store, private, config.execution, worker_type=Worker)

            def hook(phase):
                if case == "truncation" and phase == "after_start":
                    for number in range(1000):
                        event(
                            "controlled_verbose_event",
                            number=number,
                            **{str(i): "x" * 2000 for i in range(32)},
                        )
                    for number in range(100):
                        event("controlled_critical_pressure", critical=True, number=number)
                    event("controlled_critical_retained", critical=True)

            service.hook = hook
            inputs = json.loads((directory / "run.json").read_text())["inputs"]
            inputs["mode"] = "success" if attach == 0 else "failure"

            def unavailable(*a, **k):
                raise OSError("trusted diagnostic storage fault")

            storage = (
                patch("mobiraeon.execution_trace.durable_new", side_effect=unavailable)
                if case == "storage"
                else nullcontext()
            )
            with (
                patch(
                    "mobiraeon.execution.actuation_lock",
                    side_effect=lambda unused: nullcontext(),
                ),
                storage,
            ):
                result = service.invoke(
                    "execution.run", TARGET, inputs, proof=proof_for(private, "author")
                )
            handoff, record = service.load("task-1")
            with store.engine.connect() as tx:
                observations = [
                    json.loads(v)["inputs"]["observation"]
                    for v in tx.exec_driver_sql(
                        "SELECT record FROM coordination_facts WHERE stage='observe'"
                    ).scalars()
                ]
            path = Path(handoff["settings"]["data_dir"]) / (handoff["nonce"] + ".boundary.json")
            trace = json.loads(path.read_text()) if path.exists() else None
            expected = (
                "succeeded" if case == "finished_zero" else "failed" if positive else "unknown"
            )
            required = (
                record["outcome"] == expected
                and record["cleanup"] == "verified"
                and not record["held"]
            )
            required &= observations == (
                ["succeeded"] if expected == "succeeded" else ["failed"] if positive else []
            )
            required &= record["artifact_valid"] is (expected == "succeeded")
            if not positive:
                required &= record["completion_state"] is None and record["runtime_state"][
                    "ExitCode"
                ] in (0, 1)
            if case == "storage":
                required &= (
                    trace is None and service.last_boundary_diagnostic["available"] is False
                )
            if case == "truncation":
                required &= (
                    trace["events_truncated"]
                    and len(path.read_bytes()) <= 262144
                    and any(e["kind"] == "run_start" for e in trace["events"])
                    and any(e["fields"].get("fields_truncated") for e in trace["events"])
                    and any(
                        e["kind"] == "controlled_critical_retained" for e in trace["events"]
                    )
                )
            return dict(
                required_behavior=bool(required),
                scope=(
                    "Trusted actual service/SQLite/Coordination boundary replay; "
                    "not live qualification or an old request rerun."
                ),
                case=case,
                required_failure_predicate=record["outcome"] == "failed",
                outcome=result.outcome.value,
                record=terminal_fields(record),
                observations=observations,
                inspections=inspections,
                diagnostic_storage=service.last_boundary_diagnostic,
                boundary_trace=trace,
            )
        finally:
            store.close()


def budget_control(case):
    import hashlib
    import subprocess
    from types import SimpleNamespace

    settings = dict(
        docker_executable="/trusted/docker",
        endpoint="unix:///trusted.sock",
        engine_id="engine",
        image_id="sha256:fixture",
    )
    handoff = dict(name="owned-name", nonce="owned-nonce", settings=settings)
    identity = "a" * 64
    container = dict(
        Id=identity,
        Name="/owned-name",
        Image="sha256:fixture",
        Config=dict(Labels={"name.mobiraeon.nonce": "owned-nonce"}),
        State=dict(
            Running=False,
            ExitCode=1,
            StartedAt="2026-11-04T00:00:00Z",
            FinishedAt="2026-11-04T00:00:01Z",
        ),
    )
    budget = 0 if case == "exhausted" else 0.02
    clock = SimpleNamespace(value=100.0)
    calls = []

    def run(command, **kwargs):
        op = "info" if command[2] == "info" else "inspect"
        calls.append(
            dict(operation=op, timeout=kwargs["timeout"], remaining=100 + budget - clock.value)
        )
        if op == "info":
            if case == "info_consumes":
                clock.value += 0.03
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"ID": "other" if case == "engine" else "engine"}).encode(),
                b"",
            )
        if case == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if case == "launch":
            raise OSError("trusted launch fault")
        if case == "nonzero":
            return subprocess.CompletedProcess(command, 7, b"", b"trusted failure")
        if case == "malformed":
            return subprocess.CompletedProcess(command, 0, b"not-json", b"")
        if case == "ownership":
            container["Config"]["Labels"]["name.mobiraeon.nonce"] = "different"
        if case == "late_result":
            clock.value += 0.03
        return subprocess.CompletedProcess(command, 0, json.dumps([container]).encode(), b"")

    with (
        patch("mobiraeon.docker_worker.sys.platform", "linux"),
        patch("mobiraeon.docker_worker.time.monotonic", side_effect=lambda: clock.value),
        patch("mobiraeon.docker_worker.subprocess.run", side_effect=run),
    ):
        try:
            result = DockerWorker(settings).inspect(handoff, identity, timeout=budget)
            error = None
        except Exception as exc:
            result = None
            error = dict(
                type=type(exc).__name__,
                reason=getattr(getattr(exc, "reason", None), "value", None),
            )
    required = (
        (not calls and error is not None)
        if case == "exhausted"
        else all(c["timeout"] <= c["remaining"] + 1e-9 and c["remaining"] > 0 for c in calls)
    )
    required &= bool(result) if case == "under_minimum" else error is not None
    if case in {"info_consumes", "engine"}:
        required &= len(calls) == 1
    return dict(
        required_behavior=bool(required),
        case=case,
        calls=calls,
        error=error,
        positive_state=result["State"] if result else None,
        module_sha256=hashlib.sha256(
            Path(
                __import__("mobiraeon.docker_worker", fromlist=["DockerWorker"]).__file__
            ).read_bytes()
        ).hexdigest(),
        scope="Controlled Worker budget/identity predicates; not live qualification",
    )
