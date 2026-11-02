"""Portable contracts and transactions. Real enforcement is verified on Linux Docker."""

import hashlib
import json
import shutil
import sys
from importlib.resources import files
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_registry import registry as registry

from mobiraeon.api import create_api
from mobiraeon.configuration import resolve_configuration
from mobiraeon.contracts import BusinessTarget, Operation, Outcome
from mobiraeon.coordination import Coordinator
from mobiraeon.errors import Reason, SafeError
from mobiraeon.execution import ExecutionService, SupervisedConfiguration
from mobiraeon.execution_schema import decode, reference, validate
from mobiraeon.execution_settings import DEFAULTS, effective, setting
from mobiraeon.persistence import Store
from mobiraeon.scenario import TARGET

ROOT = Path(__file__).resolve().parents[1]
RUN = {
    "operation_id": "launch-1",
    "expected_version": 2,
    "attempt_id": "attempt-1",
    "mode": "success",
}


class AdmissionDouble:
    """Short-transaction mechanics only; no claim of Docker enforcement."""

    cleaned_settings = None

    def __init__(self, settings):
        self.settings = settings

    def preflight(self):
        return {"mechanics_fixture": True}

    def cleanup(self, handoff, record):
        AdmissionDouble.cleaned_settings = self.settings
        return True


class ReservedOnly(ExecutionService):
    effects = 0

    def supervise(self, target, proof, progress):
        self.effects += 1


@pytest.fixture
def allocated(registry):
    service, proof = registry
    coordinator = Coordinator(
        service.store, service.private, configuration_source=SupervisedConfiguration()
    )
    work = json.loads((ROOT / "examples/execution.json").read_bytes())["work"]
    assert (
        coordinator.invoke(
            "coordination.supply",
            TARGET,
            {"operation_id": "supply-1", "work": work},
            proof=proof,
        ).outcome
        == Outcome.SUCCESS
    )
    assert (
        coordinator.invoke(
            "coordination.allocate",
            TARGET,
            {
                "operation_id": "allocate-1",
                "expected_version": 1,
                "assignment_id": "assignment-1",
                "attempt_id": "attempt-1",
                "configuration": {
                    kind: reference(kind) for kind in ("agent", "profile", "role", "context")
                },
            },
            proof=proof,
        ).outcome
        == Outcome.SUCCESS
    )
    settings = DEFAULTS | {
        "data_dir": str(service.private.directory / "output"),
        "image_id": "sha256:" + "0" * 64,
        "docker_executable": "/absent/docker",
        "endpoint": "unix:///var/run/docker.sock",
        "engine_id": "mechanics",
    }
    execution = ReservedOnly(
        service.store, service.private, settings, worker_type=AdmissionDouble
    )
    return service, proof, coordinator, execution


@pytest.mark.parametrize(
    "action,inputs",
    [
        (Operation.EXECUTION_RUN, RUN | {"expected_version": True}),
        (Operation.EXECUTION_RUN, RUN | {"actor": "owner"}),
        (Operation.EXECUTION_RUN, RUN | {"mode": "cpu"}),
        (Operation.EXECUTION_RUN, RUN | {"container_id": "other"}),
        (Operation.EXECUTION_RUN, RUN | {"command": "shell"}),
        (Operation.EXECUTION_STATUS, {}),
        (Operation.EXECUTION_STOP, {"operation_id": "s", "attempt_id": "a", "reason": ""}),
    ],
)
def test_strict_execution_requests(action, inputs):
    with pytest.raises((SafeError, ValueError)):
        validate(action, BusinessTarget(**TARGET), inputs)


def test_supervised_allocation_cannot_use_simulated_claims_before_execution_row(allocated):
    _, proof, coordinator, _ = allocated
    for action, inputs in [
        (
            "coordination.dispatch",
            {"operation_id": "fake-dispatch", "expected_version": 2, "attempt_id": "attempt-1"},
        ),
        (
            "coordination.observe",
            {
                "operation_id": "fake-observe",
                "expected_version": 2,
                "attempt_id": "attempt-1",
                "observation": "succeeded",
                "detail": "claim",
            },
        ),
        (
            "coordination.submit",
            {
                "operation_id": "fake-submit",
                "expected_version": 2,
                "attempt_id": "attempt-1",
                "submission_id": "fake",
                "artifacts": [
                    {
                        "identity": "fixture-summary",
                        "revision": "v1",
                        "content": "fake",
                        "sha256": hashlib.sha256(b"fake").hexdigest(),
                    }
                ],
            },
        ),
    ]:
        assert (
            coordinator.invoke(action, TARGET, inputs, proof=proof).outcome != Outcome.SUCCESS
        )


def test_duplicate_capacity_and_authority_precede_replay(allocated):
    registry, proof, _, execution = allocated
    assert (
        execution.invoke("execution.run", TARGET, RUN, proof=proof).outcome == Outcome.UNCERTAIN
    )
    duplicate = execution.invoke("execution.run", TARGET, RUN, proof=proof)
    assert (
        duplicate.outcome == Outcome.SUCCESS and duplicate.data.records[0]["terminal"] is False
    )
    assert execution.effects == 1
    assert (
        execution.invoke("execution.run", TARGET, RUN | {"mode": "failure"}, proof=proof).reason
        == Reason.CONFLICT
    )
    assert (
        execution.invoke(
            "execution.run", TARGET, RUN | {"operation_id": "other"}, proof=proof
        ).outcome
        != Outcome.SUCCESS
    )
    assert (
        execution.invoke("execution.status", TARGET, {"attempt_id": "attempt-1"}).outcome
        == Outcome.REFUSED
    )
    revoke = registry.invoke(
        "access.grants",
        {"kind": "access", "entity_kind": "credential", "identity": proof.identifier},
        {
            "expected_version": 1,
            "grants": [
                {"action": "access.issue", "scope": "*"},
                {"action": "access.grants", "scope": "*"},
                {"action": "access.revoke", "scope": "*"},
            ],
        },
        proof=proof,
    )
    assert revoke.outcome == Outcome.SUCCESS
    assert (
        execution.invoke("execution.run", TARGET, RUN, proof=proof).outcome == Outcome.REFUSED
    )
    assert (
        execution.invoke(
            "execution.status", TARGET, {"attempt_id": "attempt-1"}, proof=proof
        ).outcome
        == Outcome.REFUSED
    )


def test_stop_pins_cleanup_settings_and_status_is_read_only(allocated, monkeypatch):
    from contextlib import nullcontext

    monkeypatch.setattr("mobiraeon.execution.actuation_lock", lambda private: nullcontext())
    registry, proof, _, execution = allocated
    execution.invoke("execution.run", TARGET, RUN, proof=proof)
    before = registry.store.path.read_bytes()
    read = execution.invoke(
        "execution.status", TARGET, {"attempt_id": "attempt-1"}, proof=proof
    )
    assert read.outcome == Outcome.SUCCESS and registry.store.path.read_bytes() == before
    execution.settings = execution.settings | {"cleanup_seconds": 99}
    stop = {"operation_id": "stop-1", "attempt_id": "attempt-1", "reason": "test"}
    result = execution.invoke("execution.stop", TARGET, stop, proof=proof)
    assert result.data.records[0]["stop_acknowledged"] is True
    assert result.data.records[0]["outcome"] == "unknown"
    assert AdmissionDouble.cleaned_settings["cleanup_seconds"] == DEFAULTS["cleanup_seconds"]
    terminal = execution.load("task-1")[1]
    execution.invoke("execution.stop", TARGET, stop | {"operation_id": "late"}, proof=proof)
    assert execution.load("task-1")[1] == terminal


@pytest.mark.parametrize("outcome", ["succeeded", "failed", "unknown"])
def test_sealed_observation_and_submission_provenance(allocated, outcome):
    # Trusted reporting mechanics in a real store; Docker enforcement is separate.
    registry, proof, coordinator, execution = allocated
    execution.invoke("execution.run", TARGET, RUN, proof=proof)
    path = registry.private.directory / "captured.txt"
    raw = b'{"fixture":"captured"}'
    path.write_bytes(raw)
    artifact = {
        "identity": "fixture-summary",
        "revision": "sha256-" + hashlib.sha256(raw).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content": raw.decode(),
    }
    execution.update(
        "task-1",
        1,
        {
            "terminal": True,
            "held": False,
            "cleanup": "verified",
            "outcome": outcome,
            "artifact_valid": outcome == "succeeded",
            "artifact": artifact if outcome == "succeeded" else None,
            "artifact_path": str(path),
            "seal": "trusted-terminal-seal",
        },
        "trusted-test-seal",
    )
    observation = {
        "operation_id": "observe-1",
        "expected_version": 3,
        "attempt_id": "attempt-1",
        "observation": "succeeded" if outcome == "succeeded" else "failed",
        "detail": "trusted-terminal-seal",
    }
    assert (
        coordinator.invoke(
            "coordination.observe", TARGET, observation | {"detail": "forged"}, proof=proof
        ).outcome
        != Outcome.SUCCESS
    )
    if outcome == "succeeded":
        path.write_bytes(b"tampered")
        assert (
            coordinator.invoke("coordination.observe", TARGET, observation, proof=proof).outcome
            != Outcome.SUCCESS
        )
        path.write_bytes(raw)
    observed = coordinator.invoke("coordination.observe", TARGET, observation, proof=proof)
    if outcome == "unknown":
        assert observed.outcome != Outcome.SUCCESS
        return
    assert observed.outcome == Outcome.SUCCESS
    submission = {
        "operation_id": "submit-1",
        "expected_version": 4,
        "attempt_id": "attempt-1",
        "submission_id": "submission-1",
        "artifacts": [artifact],
    }
    if outcome == "succeeded":
        for changed in (
            artifact | {"revision": "forged-revision"},
            artifact | {"content": "forged", "sha256": hashlib.sha256(b"forged").hexdigest()},
        ):
            assert (
                coordinator.invoke(
                    "coordination.submit",
                    TARGET,
                    submission | {"artifacts": [changed]},
                    proof=proof,
                ).outcome
                != Outcome.SUCCESS
            )
    submitted = coordinator.invoke("coordination.submit", TARGET, submission, proof=proof)
    assert (submitted.outcome == Outcome.SUCCESS) is (outcome == "succeeded")


@pytest.mark.parametrize(
    "key,value",
    [
        ("execution_seconds", True),
        ("startup_seconds", float("inf")),
        ("pids", 1.5),
        ("input_bytes", 200000),
        ("capture_bytes", -1),
        ("scratch_bytes", 1),
        ("image_id", "mutable:tag"),
        ("endpoint", "tcp://remote:2375"),
        ("cpus", 0),
        ("memory_bytes", 10**1000),
        ("startup_seconds", 10**1000),
    ],
)
def test_strict_execution_settings(key, value, tmp_path):
    with pytest.raises(SafeError):
        setting(key, value, "file", tmp_path)


def test_default_deadlines_and_normal_precedence(tmp_path):
    path = tmp_path / "app.toml"
    path.write_text('[database]\npath="db"\n[execution]\nexecution_seconds=121\ncpus=0.5\n')
    config = resolve_configuration(
        options={"config": str(path)}, environ={"MOBIRAEON_EXECUTION_EXECUTION_SECONDS": "150"}
    )
    assert (
        config.execution["startup_seconds"] == 100
        and config.execution["execution_seconds"] == 150
    )
    assert config.execution["cpus"] == 0.5
    with pytest.raises(SafeError):
        effective(
            DEFAULTS | {"memory_bytes": 32 * 1024 * 1024, "scratch_bytes": 32 * 1024 * 1024}
        )


@pytest.mark.parametrize("missing", ["MemoryLimit", "SwapLimit", "CpuCfsQuota", "PidsLimit"])
def test_unsupported_enforcement_refused_before_reservation(allocated, monkeypatch, missing):
    from mobiraeon.docker_worker import DockerWorker

    registry, proof, _, execution = allocated
    info = {
        "OSType": "linux",
        "CgroupVersion": "2",
        "MemoryLimit": True,
        "SwapLimit": True,
        "CpuCfsPeriod": True,
        "CpuCfsQuota": True,
        "PidsLimit": True,
        missing: False,
    }
    monkeypatch.setattr(DockerWorker, "engine", lambda self: info)
    execution.worker_type = DockerWorker
    result = execution.invoke("execution.run", TARGET, RUN, proof=proof)
    assert result.outcome == Outcome.UNAVAILABLE and execution.effects == 0
    with registry.store.engine.connect() as tx:
        assert tx.exec_driver_sql("SELECT count(*) FROM execution_runs").scalar() == 0
        assert tx.exec_driver_sql("SELECT version FROM coordination_tasks").scalar() == 2


@pytest.mark.parametrize("content", ["é" * 32768, "\x01" * 65536, "a" * 65536])
def test_utf8_full_input_envelope_and_byte_limits(registry, content):
    service, proof = registry
    work = json.loads((ROOT / "examples/execution.json").read_bytes())["work"]
    work["inputs"][0] |= {
        "content": content,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }
    inputs = {"operation_id": "supply-1", "work": work}
    envelope = json.dumps(
        {"operation": "coordination.supply", "target": TARGET, "inputs": inputs}
    ).encode()
    assert decode(envelope)["inputs"] == inputs
    coordinator = Coordinator(
        service.store, service.private, content_limits={"input_bytes": 65536}
    )
    assert (
        coordinator.invoke("coordination.supply", TARGET, inputs, proof=proof).outcome
        == Outcome.SUCCESS
    )
    work["inputs"][0]["content"] += "a"
    work["inputs"][0]["sha256"] = hashlib.sha256(
        work["inputs"][0]["content"].encode()
    ).hexdigest()
    assert (
        coordinator.invoke(
            "coordination.supply", TARGET, inputs | {"operation_id": "over"}, proof=proof
        ).outcome
        == Outcome.INVALID
    )


def test_registry_http_remains_closed_to_execution(allocated):
    registry, _, _, _ = allocated
    raw = registry.private.read_credential(registry.private.credential_path("owner.token"))
    with TestClient(create_api(registry), base_url="https://testserver") as client:
        response = client.post(
            "/v1/operations",
            json={"operation": "execution.run", "target": TARGET, "inputs": RUN},
            headers={"Authorization": "Bearer " + raw},
        )
    assert response.status_code == 422


def test_accepted_coordination_store_upgrade_retains_records(tmp_path):
    legacy = tmp_path / "migrations"
    shutil.copytree(files("mobiraeon.persistence").joinpath("migrations"), legacy)
    (legacy / "versions/0004_execution.py").unlink()
    store = Store(tmp_path / "old.db")
    store.path.touch(mode=0o600)
    assert store.upgrade(migration_path=legacy, _new=True) == "0003"
    with store.transaction() as tx:
        tx.execute(text("INSERT INTO coordination_tasks VALUES('task-1',2,'allocated')"))
        tx.execute(
            text(
                "INSERT INTO coordination_facts VALUES('task-1','supply','operation:old','{}')"
            )
        )
        tx.execute(
            text("INSERT INTO coordination_receipts VALUES('old','task-1','original','{}')")
        )
        tx.execute(
            text(
                "INSERT INTO coordination_history"
                "(task,invocation,actor,operation,outcome,record) "
                "VALUES('task-1','prior','human','coordination.supply','success','{}')"
            )
        )
    names = (
        "foundation_identity",
        "coordination_tasks",
        "coordination_facts",
        "coordination_receipts",
        "coordination_history",
    )
    with store.engine.connect() as tx:
        before = {
            name: tx.exec_driver_sql("SELECT * FROM " + name).fetchall() for name in names
        }
    assert store.upgrade() == "0004"
    with store.engine.connect() as tx:
        assert all(
            tx.exec_driver_sql("SELECT * FROM " + name).fetchall() == records
            for name, records in before.items()
        )
    store.close()


@pytest.mark.skipif(sys.platform == "linux", reason="native Windows unavailable contract")
def test_native_worker_absence_is_explicit_unavailable(allocated):
    registry, proof, _, execution = allocated
    real = ExecutionService(registry.store, registry.private, execution.settings)
    assert real.invoke("execution.run", TARGET, RUN, proof=proof).outcome == Outcome.UNAVAILABLE


@pytest.mark.parametrize("committed", [False, True])
def test_unknown_reservation_commit_never_launches_or_blindly_replays(
    allocated, monkeypatch, committed
):
    from sqlalchemy.engine import Transaction

    registry, proof, _, execution = allocated
    original = Transaction.commit
    calls = 0

    def commit(tx):
        nonlocal calls
        calls += 1
        if calls == 1:
            if committed:
                original(tx)
            raise RuntimeError("injected acknowledgement loss")
        original(tx)

    with monkeypatch.context() as scoped:
        scoped.setattr(Transaction, "commit", commit)
        result = execution.invoke("execution.run", TARGET, RUN, proof=proof)
    assert result.outcome == Outcome.UNCERTAIN and execution.effects == 0
    reopened = Store(registry.store.path)
    try:
        other = ReservedOnly(
            reopened, registry.private, execution.settings, worker_type=AdmissionDouble
        )
        repeated = other.invoke("execution.run", TARGET, RUN, proof=proof)
        assert (repeated.outcome == Outcome.SUCCESS) is committed
        assert other.effects == 0
        assert (
            other.invoke(
                "execution.run", TARGET, RUN | {"operation_id": "new"}, proof=proof
            ).outcome
            != Outcome.SUCCESS
        )
    finally:
        reopened.close()


def test_reservation_history_failure_rolls_back_dispatch_and_worker_slot(
    allocated, monkeypatch
):
    registry, proof, _, execution = allocated

    def failed(*args):
        raise RuntimeError("injected history failure")

    monkeypatch.setattr(execution, "event", failed)
    assert (
        execution.invoke("execution.run", TARGET, RUN, proof=proof).outcome == Outcome.FAILURE
    )
    assert execution.effects == 0
    with registry.store.engine.connect() as tx:
        assert tx.exec_driver_sql("SELECT count(*) FROM execution_runs").scalar() == 0
        assert tx.exec_driver_sql("SELECT version FROM coordination_tasks").scalar() == 2


def test_stale_supervisor_cannot_publish_after_stop_or_terminal(allocated, monkeypatch):
    from contextlib import nullcontext

    from mobiraeon.persistence import TransactionFailure

    monkeypatch.setattr("mobiraeon.execution.actuation_lock", lambda private: nullcontext())
    _, proof, _, execution = allocated
    execution.invoke("execution.run", TARGET, RUN, proof=proof)
    execution.invoke(
        "execution.stop",
        TARGET,
        {"operation_id": "stop-1", "attempt_id": "attempt-1", "reason": "stop"},
        proof=proof,
    )
    with pytest.raises(TransactionFailure):
        execution.update("task-1", 1, {"phase": "running"}, "stale")
    with pytest.raises(TransactionFailure):
        execution.update("task-1", 2, {"outcome": "succeeded"}, "overwrite")
    assert execution.load("task-1")[1]["outcome"] == "unknown"


def test_cli_request_action_mismatch_is_invalid(allocated, capsys):
    from mobiraeon.cli import main

    registry, _, _, execution = allocated
    directory = registry.private.directory
    config = directory / "settings.toml"
    config.write_text(
        "[database]\npath="
        + json.dumps(str(registry.store.path))
        + "\n[access]\nprivate_dir="
        + json.dumps(str(directory))
        + "\ncredential_file="
        + json.dumps(str(registry.private.credential_path("owner.token")))
        + "\n"
    )
    request = directory / "request.json"
    request.write_text(
        json.dumps({"operation": "execution.run", "target": TARGET, "inputs": RUN})
    )
    assert (
        main(["--config", str(config), "--request-file", str(request), "execution", "status"])
        == 2
    )
    assert json.loads(capsys.readouterr().out)["outcome"] == "invalid_input"
    assert execution.effects == 0
