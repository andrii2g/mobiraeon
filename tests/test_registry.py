from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from mobiraeon.access import credential_proof
from mobiraeon.api import create_api
from mobiraeon.bootstrap import prepare, read_package
from mobiraeon.catalog import RegistryService
from mobiraeon.contracts import Outcome
from mobiraeon.errors import Reason, SafeError
from mobiraeon.persistence import Store, TransactionFailure
from mobiraeon.private_state import PrivateState, harden
from mobiraeon.registry_schema import GRANTABLE


@pytest.fixture
def registry(tmp_path):
    private = PrivateState(tmp_path / "private", tmp_path / "private" / "registry.db")
    private.provision()
    store = Store(private.database, 0.1)
    store.initialize()
    harden(private.database)
    service = RegistryService(store, private)
    target = {"kind": "access", "entity_kind": "installation", "identity": "owner"}
    result = service.invoke(
        "access.setup",
        target,
        {
            "destination": "owner.token",
            "lifetime_seconds": 3600,
            "allow_self_review": True,
            "grants": [{"action": x.value, "scope": "*"} for x in sorted(GRANTABLE)],
        },
        proof=service.access.owner_proof(),
    )
    assert result.outcome == Outcome.SUCCESS, result
    proof = credential_proof(private.read_credential(private.credential_path("owner.token")))
    yield service, proof
    store.close()


def invoke(
    registry,
    operation,
    kind="instruction",
    identity="sample",
    inputs=None,
    target_kind="entity",
    **kw,
):
    service, proof = registry
    return service.invoke(
        operation,
        {"kind": target_kind, "entity_kind": kind, "identity": identity} | kw,
        inputs or {},
        proof=proof,
    )


def document(text_value="Reviewed instructions"):
    import hashlib

    return {
        "text": text_value,
        "source": {
            "uri": "test",
            "revision": "v1",
            "sha256": hashlib.sha256(text_value.encode()).hexdigest(),
        },
    }


def test_exact_review_and_immutable_publication(registry):
    assert (
        invoke(registry, "registry.create", inputs={"document": document()}).outcome
        == Outcome.SUCCESS
    )
    review = invoke(
        registry,
        "registry.review",
        target_kind="draft",
        inputs={
            "expected_version": 1,
            "decision": "approve",
            "rationale": "Reviewed candidate",
        },
    )
    assert review.outcome == Outcome.SUCCESS
    published = invoke(
        registry,
        "registry.publish",
        target_kind="draft",
        inputs={"expected_version": 1, "review_id": review.data.reference},
    )
    assert published.outcome == Outcome.SUCCESS
    changed = invoke(
        registry,
        "registry.edit",
        target_kind="draft",
        inputs={"expected_version": 1, "document": document("Changed instructions")},
    )
    assert changed.data.version == 2
    stale = invoke(
        registry,
        "registry.publish",
        target_kind="draft",
        inputs={"expected_version": 2, "review_id": review.data.reference},
    )
    assert stale.reason == Reason.REVIEW
    read = invoke(
        registry, "registry.read", target_kind="publication", revision=published.data.reference
    )
    assert read.data.records[0]["document"] == document()
    service, _ = registry
    with pytest.raises(TransactionFailure), service.store.transaction() as tx:
        tx.execute(text("UPDATE registry_publications SET document='{}'"))


def test_bootstrap_restart_repeat_and_disabled_controls(registry):
    service, proof = registry
    package = read_package(Path(__file__).parents[1] / "bootstrap/initial-test.json")
    first = prepare(service, package, proof)
    service.store.close()
    service = RegistryService(Store(service.private.database, 0.1), service.private)
    second = prepare(service, package, proof)
    assert first == second
    agents = [x for x in first["publications"] if x["kind"] == "agent"]
    assert len(agents) == 5
    for agent in agents:
        target = {"kind": "control", "entity_kind": "agent", "identity": agent["identity"]}
        read = service.invoke("registry.read", target, {}, proof=proof)
        assert read.data.records[0]["enabled"] is False
        before = read.data.version
        enable = service.invoke(
            "registry.enable", target, {"expected_version": before}, proof=proof
        )
        assert enable.outcome == Outcome.UNAVAILABLE
        read = service.invoke("registry.read", target, {}, proof=proof)
        assert read.data.version == before
        assert (
            service.invoke(
                "registry.disable", target, {"expected_version": before}, proof=proof
            ).outcome
            == Outcome.SUCCESS
        )
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_publications")).scalar() == len(
            first["publications"]
        )
        assert tx.execute(text("SELECT count(*) FROM access_credentials")).scalar() == 1
    service.store.close()


def test_current_access_last_admin_and_expiry(registry):
    service, proof = registry
    target = {"kind": "access", "entity_kind": "credential", "identity": proof.identifier}
    refused = service.invoke("access.revoke", target, {"expected_version": 1}, proof=proof)
    assert refused.reason == Reason.LAST_ADMIN
    issue = service.invoke(
        "access.issue",
        target,
        {
            "destination": "reader.token",
            "lifetime_seconds": 300,
            "grants": [{"action": "registry.read", "scope": "instruction:*"}],
        },
        proof=proof,
    )
    assert issue.outcome == Outcome.SUCCESS
    reader = credential_proof(
        service.private.read_credential(service.private.credential_path("reader.token"))
    )
    mutation = service.invoke(
        "registry.create",
        {"kind": "entity", "entity_kind": "instruction", "identity": "forbidden"},
        {"document": document()},
        proof=reader,
    )
    assert mutation.outcome == Outcome.REFUSED
    revoke = service.invoke(
        "access.revoke",
        target | {"identity": reader.identifier},
        {"expected_version": 1},
        proof=proof,
    )
    assert revoke.outcome == Outcome.SUCCESS
    assert (
        service.invoke(
            "registry.read",
            {"kind": "entity", "entity_kind": "instruction", "identity": "forbidden"},
            {},
            proof=reader,
        ).reason
        == Reason.AUTHENTICATION
    )


def test_api_transport_and_identity_isolation(registry):
    service, proof = registry
    raw = service.private.read_credential(service.private.credential_path("owner.token"))
    app = create_api(service)
    body = {
        "operation": "registry.create",
        "target": {"kind": "entity", "entity_kind": "instruction", "identity": "api-created"},
        "inputs": {"document": document()},
    }
    with TestClient(
        app, base_url="https://testserver", raise_server_exceptions=False
    ) as client:
        assert client.post("/v1/operations", json=body).status_code == 401
        response = client.post(
            "/v1/operations", json=body, headers={"authorization": "Bearer " + raw}
        )
        assert response.status_code == 200, response.text
        assert raw not in response.text
        assert client.get("/v1/openapi.json").status_code == 401
        assert (
            client.get(
                "/v1/openapi.json", headers={"authorization": "Bearer " + raw}
            ).status_code
            == 200
        )
        assert client.post("/v1/operations", json=body).status_code == 401
        body["actor"] = "owner"
        assert (
            client.post(
                "/v1/operations", json=body, headers={"authorization": "Bearer " + raw}
            ).status_code
            == 422
        )


def test_failed_delivery_no_registration_and_setup_closed(registry):
    service, proof = registry
    target = {"kind": "access", "entity_kind": "credential", "identity": "new"}
    failed = service.invoke(
        "access.issue",
        target,
        {
            "destination": "owner.token",
            "lifetime_seconds": 300,
            "grants": [{"action": "registry.read", "scope": "*"}],
        },
        proof=proof,
    )
    assert failed.reason == Reason.DELIVERY
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM access_credentials")).scalar() == 1
    with pytest.raises(SafeError):
        service.private.provision()


def test_required_audit_rollback_and_attempt_outage(registry, monkeypatch):
    import mobiraeon.catalog as catalog

    service, _ = registry

    def broken(*args, **kwargs):
        raise RuntimeError("synthetic-sensitive-audit")

    monkeypatch.setattr(catalog, "audit", broken)
    result = invoke(registry, "registry.create", inputs={"document": document()})
    assert result.outcome == Outcome.FAILURE
    assert result.data.audit_status == "unavailable"
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_entities")).scalar() == 0
    assert "sensitive" not in str(result)


def test_lock_timeout_no_handler_effects(registry):
    import sqlite3

    service, _ = registry
    connection = sqlite3.connect(service.private.database)
    connection.execute("BEGIN IMMEDIATE")
    try:
        result = invoke(registry, "registry.create", inputs={"document": document()})
        assert result.outcome == Outcome.UNAVAILABLE
        assert result.data.audit_status == "unavailable"
    finally:
        connection.rollback()
        connection.close()
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_entities")).scalar() == 0


def test_authority_rechecked_inside_transaction(registry, monkeypatch):
    service, proof = registry
    from mobiraeon.access import CurrentAccessPolicy

    original = CurrentAccessPolicy.permits

    def initially_allowed(policy, caller, operation, target):
        granted = original(policy, caller, operation, target)
        if operation.value == "registry.create":
            with service.store.transaction() as tx:
                tx.execute(
                    text("UPDATE access_credentials SET revoked=1 WHERE id=:id"),
                    {"id": proof.identifier},
                )
        return granted

    monkeypatch.setattr(CurrentAccessPolicy, "permits", initially_allowed)
    assert (
        invoke(registry, "registry.create", inputs={"document": document()}).outcome
        == Outcome.REFUSED
    )
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_entities")).scalar() == 0


def test_expiry_recovery_preserves_history_and_owner_checks(registry):
    service, old = registry
    assert (
        invoke(registry, "registry.create", inputs={"document": document()}).outcome
        == Outcome.SUCCESS
    )
    service.access.clock = lambda: 9999999999
    assert invoke(registry, "registry.read").reason == Reason.AUTHENTICATION
    service.access.clock = __import__("time").time
    target = {"kind": "access", "entity_kind": "installation", "identity": "owner"}
    recovery = service.invoke(
        "access.recover",
        target,
        {
            "destination": "recovered.token",
            "lifetime_seconds": 300,
            "grants": [{"action": x.value, "scope": "*"} for x in sorted(GRANTABLE)],
        },
        proof=service.access.owner_proof(),
    )
    assert recovery.outcome == Outcome.SUCCESS
    assert service.access.caller(old) is None
    new = credential_proof(
        service.private.read_credential(service.private.credential_path("recovered.token"))
    )
    assert (
        service.invoke(
            "registry.read",
            {"kind": "entity", "entity_kind": "instruction", "identity": "sample"},
            {},
            proof=new,
        ).outcome
        == Outcome.SUCCESS
    )


def test_failed_registration_retains_delivery_for_reconciliation(registry, monkeypatch):
    service, proof = registry
    original = service.access.mutate

    def broken(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("synthetic-sensitive-registration")

    monkeypatch.setattr(service.access, "mutate", broken)
    result = service.invoke(
        "access.issue",
        {"kind": "access", "entity_kind": "credential", "identity": "new"},
        {
            "destination": "pending.token",
            "lifetime_seconds": 300,
            "grants": [{"action": "registry.read", "scope": "*"}],
        },
        proof=proof,
    )
    assert result.outcome == Outcome.FAILURE
    assert result.data.state == "delivery_saved_registration_requires_reconciliation"
    assert service.private.credential_path("pending.token").is_file()
    observed = service.invoke(
        "access.reconcile",
        {"kind": "access", "entity_kind": "credential", "identity": result.data.reference},
        {},
        proof=proof,
    )
    assert observed.data.state == "not_registered"


def test_bootstrap_partial_resume_and_conflict(registry):
    import copy

    service, proof = registry
    package = read_package(Path(__file__).parents[1] / "bootstrap/initial-test.json")
    partial = copy.deepcopy(package)
    partial["definitions"] = partial["definitions"][:4]
    first = prepare(service, partial, proof)
    all_records = prepare(service, package, proof)
    assert all_records["publications"][:4] == first["publications"]
    package["definitions"][0]["document"] = document("conflict")
    with pytest.raises(SafeError) as error:
        prepare(service, package, proof)
    assert error.value.reason == Reason.CONFLICT


def test_override_reduction_and_forbidden_fields(registry):
    service, proof = registry
    package = read_package(Path(__file__).parents[1] / "bootstrap/initial-test.json")
    records = prepare(service, package, proof)["publications"]
    profile = next(x for x in records if x["kind"] == "profile")
    doc = {"profileRef": profile, "overrides": {"tokens": 100}}
    assert (
        invoke(registry, "registry.create", "agent", "lower", {"document": doc}).outcome
        == Outcome.SUCCESS
    )
    assert (
        invoke(
            registry, "registry.validate", "agent", "lower", {"expected_version": 1}, "draft"
        ).outcome
        == Outcome.SUCCESS
    )
    doc["overrides"] = {"model": "other"}
    assert (
        invoke(registry, "registry.create", "agent", "forbidden", {"document": doc}).outcome
        == Outcome.INVALID
    )
    doc["overrides"] = {"tokens": 10000000}
    assert (
        invoke(registry, "registry.create", "agent", "higher", {"document": doc}).outcome
        == Outcome.SUCCESS
    )
    assert (
        invoke(
            registry, "registry.validate", "agent", "higher", {"expected_version": 1}, "draft"
        ).outcome
        != Outcome.SUCCESS
    )


def test_ambiguous_commit_reconciles_persisted_mutation_and_audit(registry, monkeypatch):
    from sqlalchemy.engine import Transaction

    service, proof = registry
    original = Transaction.commit

    def committed_then_lost_ack(transaction):
        original(transaction)
        raise RuntimeError("synthetic-sensitive-commit-ack")

    monkeypatch.setattr(Transaction, "commit", committed_then_lost_ack)
    result = invoke(registry, "registry.create", inputs={"document": document()})
    assert result.outcome == Outcome.UNCERTAIN
    monkeypatch.setattr(Transaction, "commit", original)
    observed = service.invoke(
        "registry.reconcile",
        {"kind": "audit", "entity_kind": "audit", "identity": str(result.invocation_id)},
        {},
        proof=proof,
    )
    assert any(x["outcome"] == "success" for x in observed.data.records)
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_entities")).scalar() == 1
    assert "sensitive" not in str(result)


def test_parallel_callers_cannot_inherit_authority(registry):
    from concurrent.futures import ThreadPoolExecutor

    service, proof = registry
    # Isolate authority from the separate 100ms lock-timeout regression. Use the
    # application's configured default when requiring every authorized write.
    service.store.timeout = 5.0
    issue = service.invoke(
        "access.issue",
        {"kind": "access", "entity_kind": "credential", "identity": "reader"},
        {
            "destination": "parallel.token",
            "lifetime_seconds": 300,
            "grants": [{"action": "registry.read", "scope": "*"}],
        },
        proof=proof,
    )
    assert issue.outcome == Outcome.SUCCESS
    reader = credential_proof(
        service.private.read_credential(service.private.credential_path("parallel.token"))
    )

    def create(index):
        return service.invoke(
            "registry.create",
            {
                "kind": "entity",
                "entity_kind": "instruction",
                "identity": "parallel-" + str(index),
            },
            {"document": document()},
            proof=proof if index % 2 == 0 else reader,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(create, range(8)))
    assert all(x.outcome == Outcome.REFUSED for x in results[1::2])
    assert all(x.outcome == Outcome.SUCCESS for x in results[::2])
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_entities")).scalar() == 4


def test_api_unhandled_failure_is_safe(registry, monkeypatch):
    service, _ = registry
    raw = service.private.read_credential(service.private.credential_path("owner.token"))

    def broken(*args, **kwargs):
        raise RuntimeError("synthetic-sensitive-api-error")

    monkeypatch.setattr(service, "invoke", broken)
    with TestClient(
        create_api(service), base_url="https://testserver", raise_server_exceptions=False
    ) as client:
        response = client.post(
            "/v1/operations",
            headers={"authorization": "Bearer " + raw},
            json={"operation": "registry.read", "target": {}, "inputs": {}},
        )
    assert response.status_code == 500
    assert response.json()["outcome"] == "uncertain_effects"
    assert "sensitive" not in response.text and "Traceback" not in response.text


def test_private_resources_fail_closed_on_replacement(registry):
    import os

    service, _ = registry
    marker = service.private.directory / "installation.json"
    saved = marker.read_bytes()
    marker.unlink()
    # A hard-linked marker is deliberately refused on both supported platforms.
    original = service.private.directory / "replacement.json"
    original.write_bytes(saved)
    harden(original)
    os.link(original, marker)
    with pytest.raises(SafeError):
        service.access.owner_proof()


def test_real_increment_one_upgrade_preserves_identity(tmp_path):
    import shutil

    from mobiraeon import persistence

    source = Path(persistence.__file__).parent / "migrations"
    legacy = tmp_path / "legacy-migrations"
    shutil.copytree(source, legacy)
    (legacy / "versions/0002_registry.py").unlink()
    (legacy / "versions/0003_coordination.py").unlink()
    (legacy / "versions/0004_execution.py").unlink()
    store = Store(tmp_path / "legacy.db", 0.1)
    store.path.touch(mode=0o600)
    assert store.upgrade(migration_path=legacy, _new=True) == "0001"
    with store.engine.connect() as tx:
        before = tx.execute(text("SELECT * FROM foundation_identity")).fetchall()
    with pytest.raises(SafeError):
        store.check()
    assert store.upgrade() == "0004"
    with store.engine.connect() as tx:
        assert tx.execute(text("SELECT * FROM foundation_identity")).fetchall() == before
        assert tx.execute(text("SELECT count(*) FROM access_installation")).scalar() == 0
    store.close()


def test_host_configuration_strict_precedence_and_relative_paths(tmp_path):
    from mobiraeon.configuration import resolve_configuration

    path = tmp_path / "settings.toml"
    path.write_text(
        '[database]\npath="store.db"\n[access]\nprivate_dir="private"\n[api]\nenabled=false\nport=8444\n'
    )
    config = resolve_configuration(
        options={"config": str(path)}, environ={"MOBIRAEON_API_PORT": "8445"}, cwd=tmp_path
    )
    assert config.api["port"] == 8445 and config.api["enabled"] is False
    assert config.private_dir == tmp_path / "private"
    path.write_text('[database]\npath="store.db"\n[api]\nenabled="false"\n')
    with pytest.raises(SafeError):
        resolve_configuration(
            options={"config": str(path)}, environ={"MOBIRAEON_API_ENABLED": "false"}
        )


def test_rotation_and_protected_cleanup(registry, tmp_path):
    import json
    from types import SimpleNamespace

    from mobiraeon.administration import administer
    from mobiraeon.configuration import Configuration

    service, proof = registry
    rotated = service.invoke(
        "access.rotate",
        {"kind": "access", "entity_kind": "credential", "identity": proof.identifier},
        {
            "expected_version": 1,
            "destination": "rotated.token",
            "lifetime_seconds": 300,
            "grants": [{"action": x.value, "scope": "*"} for x in sorted(GRANTABLE)],
        },
        proof=proof,
    )
    assert rotated.outcome == Outcome.SUCCESS
    assert service.access.caller(proof) is None
    request = tmp_path / "cleanup.json"
    request.write_text(
        json.dumps(
            {
                "operation": "access.reconcile",
                "target": {
                    "kind": "access",
                    "entity_kind": "credential",
                    "identity": proof.identifier,
                },
                "inputs": {},
            }
        )
    )
    application = SimpleNamespace(
        store=service.store,
        configuration=Configuration(
            service.private.database, private_dir=service.private.directory
        ),
    )
    result = administer(
        application,
        {"command": "cleanup", "request_file": str(request), "credential_name": "owner.token"},
    )
    assert result.outcome == Outcome.SUCCESS
    assert not service.private.credential_path("owner.token").exists()
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM access_credentials")).scalar() == 2


@pytest.mark.parametrize(
    "overrides", [{"tokens": True}, {"tokens": 0}, {"retries": -1}, {"unknown": 1}]
)
def test_override_types_and_bounds(registry, overrides):
    result = invoke(
        registry, "registry.create", "agent", "invalid", {"document": {"overrides": overrides}}
    )
    assert result.outcome == Outcome.INVALID


def test_http_cancellation_does_not_claim_rollback(registry, monkeypatch):
    import asyncio
    import json
    import threading

    service, _ = registry
    raw = service.private.read_credential(service.private.credential_path("owner.token"))
    entered, release = threading.Event(), threading.Event()
    original = service._catalog

    def delayed(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr(service, "_catalog", delayed)
    app = create_api(service)
    body = json.dumps(
        {
            "operation": "registry.create",
            "target": {
                "kind": "entity",
                "entity_kind": "instruction",
                "identity": "cancelled-http",
            },
            "inputs": {"document": document()},
        }
    ).encode()
    sent = []

    async def scenario():
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": "POST",
            "path": "/v1/operations",
            "raw_path": b"/v1/operations",
            "query_string": b"",
            "scheme": "https",
            "server": ("localhost", 443),
            "client": ("localhost", 1234),
            "headers": [(b"authorization", ("Bearer " + raw).encode())],
        }
        task = asyncio.create_task(app(scope, receive, send))
        for _ in range(200):
            if entered.is_set():
                break
            await asyncio.sleep(0.01)
        assert entered.is_set() and app.state.active == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not sent
        release.set()
        for _ in range(200):
            if app.state.active == 0:
                break
            await asyncio.sleep(0.01)
        assert app.state.active == 0

    try:
        asyncio.run(scenario())
    finally:
        release.set()
    with service.store.engine.connect() as tx:
        assert tx.execute(text("SELECT count(*) FROM registry_entities")).scalar() == 1


def test_drain_deadline_reports_uncertainty_boundary(registry, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    import mobiraeon.api as api

    service, _ = registry
    monkeypatch.setattr(
        api.ssl, "SSLContext", lambda *args: SimpleNamespace(load_cert_chain=lambda *args: None)
    )

    class IncompleteDrain:
        def __init__(self, config):
            self.config, self.started = config, False

        async def serve(self):
            self.started = True
            self.config.app.state.active = 1
            await asyncio.sleep(0.05)

    monkeypatch.setattr(api, "Server", IncompleteDrain)
    settings = {
        "allow_remote": False,
        "host": "127.0.0.1",
        "port": 8443,
        "cert_file": "unused",
        "key_file": "unused",
        "startup_timeout_seconds": 1,
        "drain_timeout_seconds": 0.1,
    }
    ready = []
    with pytest.raises(SafeError) as error:
        api.host(service, SimpleNamespace(api=settings), lambda: ready.append(True))
    assert error.value.reason == Reason.DRAIN
    assert ready == [True]


def test_api_enablement_boundary_and_usable_disablement(registry):
    service, proof = registry
    prepare(
        service, read_package(Path(__file__).parents[1] / "bootstrap/initial-test.json"), proof
    )
    owner = service.private.read_credential(service.private.credential_path("owner.token"))
    target = {"kind": "control", "entity_kind": "agent", "identity": "orchestrator-01"}
    service.invoke(
        "access.issue",
        {"kind": "access", "entity_kind": "credential", "identity": "reader"},
        {
            "destination": "limited.token",
            "lifetime_seconds": 300,
            "grants": [{"action": "registry.read", "scope": "*"}],
        },
        proof=proof,
    )
    reader = service.private.read_credential(service.private.credential_path("limited.token"))
    with TestClient(create_api(service), base_url="https://testserver") as client:

        def call(operation, token, inputs):
            return client.post(
                "/v1/operations",
                headers={"authorization": "Bearer " + token},
                json={"operation": operation, "target": target, "inputs": inputs},
            )

        before = call("registry.read", owner, {}).json()["data"]
        assert (
            call("registry.enable", reader, {"expected_version": before["version"]}).status_code
            == 403
        )
        assert (
            call("registry.enable", owner, {"expected_version": before["version"]}).status_code
            == 503
        )
        assert call("registry.read", owner, {}).json()["data"] == before
        disabled = call("registry.disable", owner, {"expected_version": before["version"]})
        assert disabled.status_code == 200
        assert disabled.json()["data"]["version"] == before["version"] + 1
        assert disabled.json()["data"]["records"][0]["enabled"] is False
