"""Review regressions: real protected stores and deterministic process interleavings."""

import contextlib
import io
import json
import multiprocessing
import threading
from pathlib import Path

import pytest
from sqlalchemy import text

from mobiraeon.access import credential_proof
from mobiraeon.catalog import RegistryService
from mobiraeon.cli import main
from mobiraeon.contracts import Outcome
from mobiraeon.persistence import Store
from mobiraeon.private_state import PrivateState, harden
from mobiraeon.registry_schema import GRANTABLE


def grants():
    return [{"action": x.value, "scope": "*"} for x in sorted(GRANTABLE)]


@pytest.fixture
def installation(tmp_path):
    private = PrivateState(tmp_path / "private", tmp_path / "private/catalog.db")
    private.provision()
    store = Store(private.database, 1)
    store.initialize()
    harden(private.database)
    service = RegistryService(store, private)
    result = service.invoke(
        "access.setup",
        {"kind": "access", "entity_kind": "installation", "identity": "owner"},
        {
            "destination": "owner.token",
            "lifetime_seconds": 3600,
            "allow_self_review": True,
            "grants": grants(),
        },
        proof=service.access.owner_proof(),
    )
    assert result.outcome == Outcome.SUCCESS
    config = tmp_path / "settings.toml"
    config.write_text(
        "[database]\npath = "
        + json.dumps(str(private.database))
        + "\n[access]\nprivate_dir = "
        + json.dumps(str(private.directory))
        + "\ncredential_file = "
        + json.dumps(str(private.credential_path("owner.token")))
        + "\n"
    )
    yield service, config
    store.close()


def cli(config, *arguments):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(["--config", str(config), *map(str, arguments)])
    return code, json.loads(stdout.getvalue()), stderr.getvalue()


def cleanup(config, identifier, name):
    request = config.parent / "cleanup.json"
    request.write_text(
        json.dumps(
            {
                "operation": "access.reconcile",
                "target": {
                    "kind": "access",
                    "entity_kind": "credential",
                    "identity": identifier,
                },
                "inputs": {},
            }
        )
    )
    return cli(config, "--request-file", request, "--credential-name", name, "cleanup")


def paused_registration(directory, database, operation, release, pipe, through_api):
    """Spawn-safe worker. Only nonsecret IDs/outcomes cross the process pipe."""
    private = PrivateState(directory, database)
    store = Store(Path(database), 1)
    service = RegistryService(store, private)
    raw = private.read_credential(private.credential_path("owner.token"))
    proof = credential_proof(raw)
    original = service.access.deliver

    def deliver(inputs):
        delivered = original(inputs)
        pipe.send({"phase": "delivered", "id": delivered.identifier})
        if not release.wait(30):
            raise RuntimeError("bounded regression release timeout")
        return delivered

    service.access.deliver = deliver
    target = {"kind": "access", "entity_kind": "credential", "identity": proof.identifier}
    inputs = {
        "destination": "replacement.token",
        "lifetime_seconds": 3600,
        "grants": grants()
        if operation == "rotate"
        else [{"action": "registry.read", "scope": "*"}],
    }
    if operation == "rotate":
        inputs["expected_version"] = 1
    try:
        if through_api:
            from fastapi.testclient import TestClient

            from mobiraeon.api import create_api

            with TestClient(create_api(service), base_url="https://testserver") as client:
                response = client.post(
                    "/v1/operations",
                    json={
                        "operation": "access." + operation,
                        "target": target,
                        "inputs": inputs,
                    },
                    headers={"Authorization": "Bearer " + raw},
                )
                result = response.json()
                outcome, reason = result["outcome"], result["reason"]
        else:
            result = service.invoke("access." + operation, target, inputs, proof=proof)
            outcome, reason = result.outcome.value, result.reason.value
        pipe.send({"phase": "result", "outcome": outcome, "reason": reason})
    finally:
        store.close()
        pipe.close()


@pytest.mark.parametrize("operation", ["issue", "rotate"])
@pytest.mark.parametrize("cross_process", [False, True])
def test_cleanup_cannot_remove_pending_registration(installation, operation, cross_process):
    service, config = installation
    private = service.private
    old = credential_proof(private.read_credential(private.credential_path("owner.token")))
    context = multiprocessing.get_context("spawn")
    release = context.Event()
    parent, child = context.Pipe()
    args = (
        str(private.directory),
        str(private.database),
        operation,
        release,
        child,
        cross_process,
    )
    worker = (
        context.Process(target=paused_registration, args=args)
        if cross_process
        else (threading.Thread(target=paused_registration, args=args))
    )
    worker.start()
    try:
        assert parent.poll(20), "delivery did not reach the synchronization point"
        delivered = parent.recv()
        assert delivered["phase"] == "delivered"
        code, result, diagnostic = cleanup(config, delivered["id"], "replacement.token")
        before_file = private.credential_path("replacement.token").exists()
        with service.store.engine.connect() as tx:
            before_old = service.access.authenticate(tx, old) is not None
            before_registered = tx.execute(
                text("SELECT count(*) FROM access_credentials WHERE id=:id"),
                {"id": delivered["id"]},
            ).scalar()
    finally:
        release.set()
        worker.join(30)
    assert not worker.is_alive()
    assert parent.poll(10)
    registered = parent.recv()
    assert registered == {"phase": "result", "outcome": "success", "reason": "ok"}
    after_file = private.credential_path("replacement.token").exists()
    with service.store.engine.connect() as tx:
        after_old = service.access.authenticate(tx, old) is not None
        persisted = tx.execute(
            text("SELECT count(*) FROM access_credentials WHERE id=:id"),
            {"id": delivered["id"]},
        ).scalar()
    assert {
        "cleanup_exit": code,
        "cleanup_outcome": result["outcome"],
        "before_file": before_file,
        "before_old": before_old,
        "before_registered": before_registered,
        "after_file": after_file,
        "after_old": after_old,
        "persisted": persisted,
    } == {
        "cleanup_exit": 1,
        "cleanup_outcome": "unavailable",
        "before_file": True,
        "before_old": True,
        "before_registered": 0,
        "after_file": True,
        "after_old": operation != "rotate",
        "persisted": 1,
    }
    replacement = credential_proof(
        private.read_credential(private.credential_path("replacement.token"))
    )
    with service.store.engine.connect() as tx:
        assert service.access.authenticate(tx, replacement) is not None
    assert "Traceback" not in diagnostic
    parent.close()
    if cross_process:
        child.close()


@pytest.mark.parametrize("registration", ["failed", "revoked"])
def test_cleanup_after_established_registration_outcome(
    installation, monkeypatch, registration
):
    service, config = installation
    private = service.private
    owner = credential_proof(private.read_credential(private.credential_path("owner.token")))
    original = service.access.mutate
    if registration == "failed":

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic-sensitive-registration-failure")

        monkeypatch.setattr(service.access, "mutate", fail)
    result = service.invoke(
        "access.issue",
        {"kind": "access", "entity_kind": "credential", "identity": "new"},
        {
            "destination": "obsolete.token",
            "lifetime_seconds": 300,
            "grants": [{"action": "registry.read", "scope": "*"}],
        },
        proof=owner,
    )
    monkeypatch.setattr(service.access, "mutate", original)
    identifier = result.data.reference
    assert result.outcome == (Outcome.FAILURE if registration == "failed" else Outcome.SUCCESS)
    if registration == "revoked":
        revoked = service.invoke(
            "access.revoke",
            {"kind": "access", "entity_kind": "credential", "identity": identifier},
            {"expected_version": 1},
            proof=owner,
        )
        assert revoked.outcome == Outcome.SUCCESS
    code, report, _ = cleanup(config, identifier, "obsolete.token")
    assert code == 0 and report["outcome"] == "success"
    assert not private.credential_path("obsolete.token").exists()
    with service.store.engine.connect() as tx:
        assert service.access.authenticate(tx, owner) is not None


@pytest.mark.parametrize(
    "content",
    [
        b'{"synthetic-sensitive-json":',
        b"\xff\xfesynthetic-sensitive-encoding",
        b"[]",
        b'{"stage":"initial_test","provenance":{},"definitions":[{}]}',
    ],
)
def test_invalid_package_is_safe_before_preparation(installation, content):
    service, config = installation
    path = config.parent / "input.json"
    path.write_bytes(content)
    code, result, diagnostic = cli(config, "--input-file", path, "prepare")
    assert (code, result["outcome"], result["reason"]) == (2, "invalid_input", "invalid_input")
    assert "synthetic-sensitive" not in diagnostic
    assert "Traceback" not in diagnostic
    with service.store.engine.connect() as tx:
        for table in ("registry_entities", "registry_publications", "registry_controls"):
            assert tx.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0


def test_missing_package_is_invalid_input(installation):
    _, config = installation
    code, result, diagnostic = cli(
        config, "--input-file", config.parent / "synthetic-sensitive-missing", "prepare"
    )
    assert (code, result["outcome"]) == (2, "invalid_input")
    assert "synthetic-sensitive" not in diagnostic


def test_commit_ack_uncertainty_during_preparation_is_preserved(installation, monkeypatch):
    from sqlalchemy.engine import Transaction

    service, config = installation
    path = config.parent / "valid.json"
    package = {
        "stage": "initial_test",
        "provenance": {},
        "definitions": [{"kind": "instruction", "identity": "possible-effect", "document": {}}],
    }
    path.write_text(json.dumps(package))
    original = Transaction.commit

    def committed_then_failed(transaction):
        original(transaction)
        raise RuntimeError("synthetic-sensitive-acknowledgement")

    monkeypatch.setattr(Transaction, "commit", committed_then_failed)
    code, result, diagnostic = cli(config, "--input-file", path, "prepare")
    assert (code, result["outcome"]) == (1, "uncertain_effects")
    assert "synthetic-sensitive" not in diagnostic and "Traceback" not in diagnostic
    monkeypatch.setattr(Transaction, "commit", original)
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_entities")).scalar() == 1


def test_later_structural_error_is_rejected_before_first_mutation(installation):
    import hashlib

    service, config = installation
    path = config.parent / "later-invalid.json"
    text_value = "complete first instruction"
    path.write_text(
        json.dumps(
            {
                "stage": "initial_test",
                "provenance": {},
                "definitions": [
                    {
                        "kind": "instruction",
                        "identity": "first",
                        "document": {
                            "text": text_value,
                            "source": {
                                "uri": "test",
                                "revision": "v1",
                                "sha256": hashlib.sha256(text_value.encode()).hexdigest(),
                            },
                        },
                    },
                    {},
                ],
            }
        )
    )
    code, result, _ = cli(config, "--input-file", path, "prepare")
    assert (code, result["outcome"]) == (2, "invalid_input")
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_entities")).scalar() == 0


def test_process_exit_releases_lifecycle_for_reconciled_cleanup(installation):
    service, config = installation
    private = service.private
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    release = context.Event()
    process = context.Process(
        target=paused_registration,
        args=(str(private.directory), str(private.database), "rotate", release, child, False),
    )
    process.start()
    try:
        assert parent.poll(20)
        delivered = parent.recv()
        code, result, _ = cleanup(config, delivered["id"], "replacement.token")
        assert (code, result["outcome"]) == (1, "unavailable")
    finally:
        process.terminate()
        process.join(20)
        parent.close()
        child.close()
    code, result, _ = cleanup(config, delivered["id"], "replacement.token")
    assert (code, result["outcome"]) == (0, "success")
    owner = credential_proof(private.read_credential(private.credential_path("owner.token")))
    with service.store.engine.connect() as tx:
        assert service.access.authenticate(tx, owner) is not None
        assert tx.execute(text("SELECT count(*) FROM access_credentials")).scalar() == 1
