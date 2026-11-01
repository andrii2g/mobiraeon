"""Disk-store workflow gates and restart/uncertainty, with trusted isolated fixtures."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Transaction
from test_registry import registry as registry

from mobiraeon.access import CurrentAccessPolicy
from mobiraeon.contracts import Operation, Outcome
from mobiraeon.coordination import Coordinator
from mobiraeon.errors import Reason
from mobiraeon.persistence import Store, TransactionFailure
from mobiraeon.scenario import (
    ASSESSOR_ACTIONS,
    AUTHOR_ACTIONS,
    TARGET,
    FixtureConfiguration,
    ScenarioAccess,
    compose,
    fixture_ref,
    proof_for,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def flow(registry):
    service, admin = registry
    for name, actions in (("author", AUTHOR_ACTIONS), ("assessor", ASSESSOR_ACTIONS)):
        result = service.invoke(
            "access.issue",
            {"kind": "access", "entity_kind": "credential", "identity": name},
            {
                "destination": name + ".token",
                "lifetime_seconds": 3600,
                "grants": [{"action": a.value, "scope": "task:task-1"} for a in sorted(actions)]
                + [{"action": "registry.read", "scope": "*"}],
            },
            proof=admin,
        )
        assert result.outcome == Outcome.SUCCESS
    coordinator = Coordinator(
        service.store,
        service.private,
        access=ScenarioAccess(service.store, service.private),
        configuration_source=FixtureConfiguration(),
    )
    return coordinator, service, admin


def call(flow, action, inputs=None, actor="author", target=TARGET):
    coordinator, service, _ = flow
    return coordinator.invoke(
        action, target, inputs or {}, proof=proof_for(service.private, actor)
    )


def steps(flow, through="accept"):
    scenario = json.loads((ROOT / "examples/coordination.json").read_text())
    requests = [
        ("supply", {"work": scenario["work"]}),
        (
            "allocate",
            {
                "assignment_id": "assignment-1",
                "attempt_id": "attempt-1",
                "configuration": {
                    kind: fixture_ref(kind) for kind in ("agent", "profile", "role", "context")
                },
            },
        ),
        ("dispatch", {"attempt_id": "attempt-1"}),
        (
            "observe",
            {"attempt_id": "attempt-1", "observation": "succeeded", "detail": "simulated"},
        ),
        (
            "submit",
            {
                "attempt_id": "attempt-1",
                "submission_id": "submission-1",
                "artifacts": scenario["artifacts"],
            },
        ),
    ]
    sent = {}
    for version, (action, values) in enumerate(requests):
        inputs = {"operation_id": action + "-1"} | values
        if version:
            inputs["expected_version"] = version
        result = call(flow, "coordination." + action, inputs)
        assert result.outcome == Outcome.SUCCESS, result
        sent[action] = inputs
        if action == through:
            return sent
    submission_digest = result.data.records[0]["fact"]["submission_digest"]
    sent["assess"] = {
        "operation_id": "assess-1",
        "expected_version": 5,
        "submission_id": "submission-1",
        "submission_digest": submission_digest,
        "evidence": scenario["artifacts"],
        "decision": "approve",
        "rationale": "Reviewed exact evidence",
    }
    if through == "before-assess":
        return sent
    assert (
        call(flow, "coordination.assess", sent["assess"], "assessor").outcome == Outcome.SUCCESS
    )
    if through == "assess":
        return sent
    sent["accept"] = {
        "operation_id": "accept-1",
        "expected_version": 6,
        "submission_id": "submission-1",
        "submission_digest": submission_digest,
        "assessment_id": "assess-1",
    }
    assert (
        call(flow, "coordination.accept", sent["accept"], "assessor").outcome == Outcome.SUCCESS
    )
    return sent


def status(flow):
    result = call(flow, "coordination.status")
    assert result.outcome == Outcome.SUCCESS
    return result.data.records[0]


def test_complete_links_history_and_read_after_restart(flow):
    sent = steps(flow)
    current = status(flow)
    assert current["state"] == "accepted" and current["version"] == 7
    assert (
        current["request_state"] == "open" and current["initiative_acceptance"] == "unaccepted"
    )
    assert len(current["history"]) == 7 and len(current["facts"]) == 7
    assert current["facts"]["supply"]["inputs"]["work"] == sent["supply"]["work"]
    assert (
        current["facts"]["allocate"]["snapshot"]["references"]
        == sent["allocate"]["configuration"]
    )
    assert current["facts"]["submit"]["actor"] != current["facts"]["assess"]["actor"]
    assert current["facts"]["accept"]["inputs"]["assessment_id"] == "assess-1"
    coordinator, service, _ = flow
    service.store.close()
    reopened = Store(service.store.path)
    private = service.private
    other = Coordinator(
        reopened,
        private,
        access=ScenarioAccess(reopened, private),
        configuration_source=FixtureConfiguration(),
    )
    try:
        reloaded = other.invoke(
            "coordination.status", TARGET, {}, proof=proof_for(private, "author")
        )
        assert reloaded.data.records[0] == current
    finally:
        reopened.close()
    assert coordinator is not other


@pytest.mark.parametrize(
    "action", ["supply", "allocate", "dispatch", "observe", "submit", "assess", "accept"]
)
def test_exact_duplicates_and_conflicting_reuse(flow, action):
    sent = steps(flow)
    actor = "assessor" if action in {"assess", "accept"} else "author"
    repeated = call(flow, "coordination." + action, sent[action], actor)
    assert repeated.outcome == Outcome.SUCCESS and repeated.data.records[0]["replayed"] is True
    assert len(status(flow)["history"]) == 7
    changed = copy.deepcopy(sent[action])
    if action == "supply":
        changed["work"]["objective"] += " changed"
    else:
        changed["expected_version"] += 1
    assert call(flow, "coordination." + action, changed, actor).reason == Reason.CONFLICT
    assert len(status(flow)["facts"]) == 7


def test_new_ids_cannot_duplicate_dispatch_result_or_acceptance(flow):
    sent = steps(flow)
    for action in ("dispatch", "submit", "accept"):
        inputs = sent[action] | {"operation_id": action + "-again", "expected_version": 7}
        assert (
            call(
                flow,
                "coordination." + action,
                inputs,
                "assessor" if action == "accept" else "author",
            ).outcome
            != Outcome.SUCCESS
        )
    assert status(flow)["version"] == 7


@pytest.mark.parametrize("corruption", ["missing", "stale", "changed", "scope", "self"])
def test_exact_independent_assessment_gate(flow, corruption):
    sent = steps(flow, "before-assess")
    inputs = copy.deepcopy(sent["assess"])
    actor = "assessor"
    if corruption == "missing":
        inputs["evidence"] = inputs["evidence"][:1]
    elif corruption == "stale":
        inputs["submission_digest"] = "stale"
    elif corruption == "changed":
        inputs["evidence"][0]["revision"] = "v2"
    elif corruption == "scope":
        inputs["submission_id"] = "another-submission"
    else:
        # Even giving the author assess permission cannot establish independence.
        service, admin = flow[1:]
        proof = proof_for(service.private, "author")
        grant(service, admin, proof.identifier, AUTHOR_ACTIONS | {Operation.ASSESS})
        actor = "author"
    result = call(flow, "coordination.assess", inputs, actor)
    assert result.outcome != Outcome.SUCCESS
    assert status(flow)["state"] == "submitted"
    assert "accept" not in status(flow)["facts"]


def grant(service, admin, identifier, actions):
    result = service.invoke(
        "access.grants",
        {"kind": "access", "entity_kind": "credential", "identity": identifier},
        {
            "expected_version": 1,
            "grants": [{"action": a.value, "scope": "task:task-1"} for a in sorted(actions)],
        },
        proof=admin,
    )
    assert result.outcome == Outcome.SUCCESS


def test_no_automatic_acceptance_and_accept_gate(flow):
    sent = steps(flow, "before-assess")
    assert status(flow)["state"] == "submitted"
    inputs = {
        "operation_id": "accept-before",
        "expected_version": 5,
        "submission_id": "submission-1",
        "submission_digest": sent["assess"]["submission_digest"],
        "assessment_id": "missing",
    }
    assert call(flow, "coordination.accept", inputs, "assessor").outcome != Outcome.SUCCESS
    rejected = sent["assess"] | {"decision": "reject"}
    assert call(flow, "coordination.assess", rejected, "assessor").outcome == Outcome.SUCCESS
    assert (
        call(
            flow,
            "coordination.accept",
            inputs | {"expected_version": 6, "assessment_id": "assess-1"},
            "assessor",
        ).reason
        == Reason.REVIEW
    )


def test_missing_artifacts_stale_or_nonowner_reports(flow):
    steps(flow, "dispatch")
    inputs = {
        "operation_id": "observe-1",
        "expected_version": 3,
        "attempt_id": "attempt-1",
        "observation": "succeeded",
        "detail": "simulated",
    }
    assert (
        call(flow, "coordination.observe", inputs | {"attempt_id": "old"}).outcome
        != Outcome.SUCCESS
    )
    assert (
        call(flow, "coordination.observe", inputs | {"expected_version": 2}).reason
        == Reason.CONFLICT
    )
    service, admin = flow[1:]
    grant(
        service,
        admin,
        proof_for(service.private, "assessor").identifier,
        ASSESSOR_ACTIONS | {Operation.OBSERVE},
    )
    assert call(flow, "coordination.observe", inputs, "assessor").reason == Reason.REFUSED
    assert call(flow, "coordination.observe", inputs).outcome == Outcome.SUCCESS
    artifacts = json.loads((ROOT / "examples/coordination.json").read_text())["artifacts"]
    assert (
        call(
            flow,
            "coordination.submit",
            {
                "operation_id": "submit-incomplete",
                "expected_version": 4,
                "attempt_id": "attempt-1",
                "submission_id": "submission-1",
                "artifacts": artifacts[:1],
            },
        ).reason
        == Reason.INCOMPLETE
    )


@pytest.mark.parametrize("stop", ["allocation", "reservation", "effect"])
def test_fresh_process_interruption_inspection_never_relaunches(tmp_path, stop):
    directory = tmp_path / "private"
    # Real process exit at the selected durable boundary, then a fresh process read.
    script = """
import sys
from pathlib import Path
from mobiraeon.scenario import run_scenario
run_scenario(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), stop_after=sys.argv[4])
"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(directory),
            str(ROOT / "examples/coordination.json"),
            str(ROOT / "bootstrap/initial-test.json"),
            stop,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        [sys.executable, "-m", "mobiraeon.scenario", "status", "--directory", str(directory)],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    current = json.loads(result.stdout)["data"]["records"][0]
    assert current["unresolved"] is (stop != "allocation")
    assert "accept" not in current["facts"]
    assert (directory / "simulated-effect.json").exists() is (stop == "effect")
    store, private, coordinator = compose(directory)
    try:
        inputs = {
            "operation_id": "dispatch-1",
            "expected_version": 2,
            "attempt_id": "attempt-1",
        }
        repeated = coordinator.invoke(
            "coordination.dispatch", TARGET, inputs, proof=proof_for(private, "author")
        )
        assert repeated.outcome == Outcome.SUCCESS
        assert repeated.data.records[0]["replayed"] is (stop != "allocation")
        assert (directory / "simulated-effect.json").exists() is (stop == "effect")
    finally:
        store.close()


def test_unknown_observation_remains_unresolved(flow):
    steps(flow, "dispatch")
    assert (
        call(
            flow,
            "coordination.observe",
            {
                "operation_id": "unknown-1",
                "expected_version": 3,
                "attempt_id": "attempt-1",
                "observation": "unknown",
                "detail": "effect unknown",
            },
        ).outcome
        == Outcome.SUCCESS
    )

    assert status(flow)["unresolved"] is True
    assert (
        call(
            flow,
            "coordination.observe",
            {
                "operation_id": "try-again",
                "expected_version": 4,
                "attempt_id": "attempt-1",
                "observation": "succeeded",
                "detail": "unproved",
            },
        ).outcome
        != Outcome.SUCCESS
    )


def test_conflicting_input_artifact_revision_cannot_be_submitted(flow):
    import hashlib

    steps(flow, "observe")
    scenario = json.loads((ROOT / "examples/coordination.json").read_text())
    conflicting = dict(scenario["work"]["inputs"][0])
    conflicting["content"] = "Changed content at the original input revision"
    conflicting["sha256"] = hashlib.sha256(conflicting["content"].encode()).hexdigest()
    result = call(
        flow,
        "coordination.submit",
        {
            "operation_id": "submit-conflict",
            "expected_version": 4,
            "attempt_id": "attempt-1",
            "submission_id": "submission-1",
            "artifacts": scenario["artifacts"] + [conflicting],
        },
    )
    assert result.reason == Reason.CONFLICT
    assert status(flow)["state"] == "observed"


@pytest.mark.parametrize("committed", [True, False])
def test_unknown_dispatch_commit_requires_inspection(flow, monkeypatch, committed):
    steps(flow, "allocate")
    original = Transaction.commit
    calls = 0

    def uncertain(tx):
        nonlocal calls
        calls += 1
        if calls == 1:
            if committed:
                original(tx)
            raise RuntimeError("SENSITIVE_COMMIT")
        original(tx)

    with monkeypatch.context() as scoped:
        scoped.setattr(Transaction, "commit", uncertain)
        result = call(
            flow,
            "coordination.dispatch",
            {"operation_id": "dispatch-1", "expected_version": 2, "attempt_id": "attempt-1"},
        )
    assert result.outcome == Outcome.UNCERTAIN
    current = status(flow)
    assert current["unresolved"] is True
    again = call(
        flow,
        "coordination.dispatch",
        {"operation_id": "dispatch-1", "expected_version": 2, "attempt_id": "attempt-1"},
    )
    assert (again.outcome == Outcome.SUCCESS) is committed
    assert (
        call(
            flow,
            "coordination.dispatch",
            {
                "operation_id": "new-dispatch",
                "expected_version": current["version"],
                "attempt_id": "attempt-1",
            },
        ).outcome
        != Outcome.SUCCESS
    )


def test_transaction_and_history_integrity(flow, monkeypatch):
    coordinator = flow[0]
    original = coordinator._history

    def fail(*args):
        raise RuntimeError("SENSITIVE_HISTORY")

    with monkeypatch.context() as scoped:
        scoped.setattr(coordinator, "_history", fail)
        work = json.loads((ROOT / "examples/coordination.json").read_text())["work"]
        result = call(flow, "coordination.supply", {"operation_id": "supply-1", "work": work})
    assert result.outcome == Outcome.FAILURE and result.data.audit_status == "unavailable"
    assert coordinator._history == original
    with flow[1].store.engine.connect() as tx:
        for table in ("coordination_facts", "coordination_receipts", "coordination_tasks"):
            assert tx.exec_driver_sql("SELECT count(*) FROM " + table).scalar() == 0
    steps(flow)
    with pytest.raises(TransactionFailure), flow[1].store.transaction() as tx:
        tx.execute(text("UPDATE coordination_facts SET record='{}'"))
    assert status(flow)["state"] == "accepted"


def test_current_authority_scopes_revocation_and_forged_claims(flow):
    sent = steps(flow, "supply")
    coordinator, service, admin = flow
    assert coordinator.invoke("coordination.status", TARGET, {}).outcome == Outcome.REFUSED
    wrong = TARGET | {"identity": "another-task"}
    assert call(flow, "coordination.status", target=wrong).outcome == Outcome.REFUSED
    assert (
        call(flow, "coordination.status", {"actor": "scenario-assessor"}).outcome
        == Outcome.INVALID
    )
    assert (
        call(flow, "coordination.supply", sent["supply"] | {"role": "owner"}).outcome
        == Outcome.INVALID
    )
    proof = proof_for(service.private, "author")
    revoked = service.invoke(
        "access.revoke",
        {"kind": "access", "entity_kind": "credential", "identity": proof.identifier},
        {"expected_version": 1},
        proof=admin,
    )
    assert revoked.outcome == Outcome.SUCCESS
    assert call(flow, "coordination.supply", sent["supply"]).outcome == Outcome.REFUSED
    assert call(flow, "coordination.status").outcome == Outcome.REFUSED


@pytest.mark.parametrize("value", [False, 1, "true"])
def test_transaction_recheck_requires_literal_true(flow, monkeypatch, value):
    work = json.loads((ROOT / "examples/coordination.json").read_text())["work"]
    monkeypatch.setattr(CurrentAccessPolicy, "permits_in_transaction", lambda *a: value)
    assert (
        call(flow, "coordination.supply", {"operation_id": "supply-1", "work": work}).outcome
        == Outcome.REFUSED
    )
    with flow[1].store.engine.connect() as tx:
        assert tx.exec_driver_sql("SELECT count(*) FROM coordination_tasks").scalar() == 0


def test_registry_admin_without_workflow_grants_and_two_tokens_one_human(flow):
    _, service, admin = flow
    ordinary = Coordinator(
        service.store, service.private, configuration_source=FixtureConfiguration()
    )
    author, assessor = (proof_for(service.private, name) for name in ("author", "assessor"))
    assert ordinary.access.caller(author).actor == ordinary.access.caller(assessor).actor
    # Fresh explicit authoring using ordinary identities: tokens cannot establish independence.
    scenario = json.loads((ROOT / "examples/coordination.json").read_text())
    assert (
        ordinary.invoke(
            "coordination.supply",
            TARGET,
            {"operation_id": "supply-1", "work": scenario["work"]},
            proof=author,
        ).outcome
        == Outcome.SUCCESS
    )
    from mobiraeon.registry_schema import ACCESS_ACTIONS, CATALOG_ACTIONS

    result = service.invoke(
        "access.grants",
        {"kind": "access", "entity_kind": "credential", "identity": admin.identifier},
        {
            "expected_version": 1,
            "grants": [
                {"action": a.value, "scope": "*"}
                for a in sorted(ACCESS_ACTIONS | CATALOG_ACTIONS)
            ],
        },
        proof=admin,
    )
    assert result.outcome == Outcome.SUCCESS
    assert (
        ordinary.invoke("coordination.status", TARGET, {}, proof=admin).outcome
        == Outcome.REFUSED
    )


def test_ordinary_allocation_cannot_use_fixture_source_or_http(flow):
    sent = steps(flow, "supply")
    coordinator, service, _ = flow
    refs = {kind: fixture_ref(kind) for kind in ("agent", "profile", "role", "context")}
    inputs = {
        "operation_id": "allocate-1",
        "expected_version": 1,
        "attempt_id": "attempt-1",
        "assignment_id": "assignment-1",
        "configuration": refs,
    }
    ordinary = Coordinator(service.store, service.private, access=coordinator.access)
    assert (
        ordinary.invoke(
            "coordination.allocate", TARGET, inputs, proof=proof_for(service.private, "author")
        ).reason
        == Reason.NOT_FOUND
    )
    assert (
        service.invoke("coordination.supply", TARGET, sent["supply"], proof=flow[2]).outcome
        == Outcome.INVALID
    )
    assert "agent_execution" not in FixtureConfiguration().resolve(refs)
    from fastapi.testclient import TestClient

    from mobiraeon.api import create_api

    raw = service.private.read_credential(service.private.credential_path("owner.token"))
    with TestClient(create_api(service), base_url="https://testserver") as client:
        response = client.post(
            "/v1/operations",
            json={
                "operation": "coordination.supply",
                "target": TARGET,
                "inputs": sent["supply"],
            },
            headers={"Authorization": "Bearer " + raw},
        )
    assert response.status_code == 422
    assert status(flow)["version"] == 1


def test_allocation_conflicting_exact_reference_and_global_single_slot(flow):
    steps(flow, "allocate")
    coordinator, service, admin = flow
    # Give the author a second target scope, without changing its trusted identity.
    proof = proof_for(service.private, "author")
    grants = [{"action": a.value, "scope": "task:*"} for a in sorted(AUTHOR_ACTIONS)]
    grants.append({"action": "registry.read", "scope": "*"})
    result = service.invoke(
        "access.grants",
        {"kind": "access", "entity_kind": "credential", "identity": proof.identifier},
        {"expected_version": 1, "grants": grants},
        proof=admin,
    )
    assert result.outcome == Outcome.SUCCESS
    work = json.loads((ROOT / "examples/coordination.json").read_text())["work"]
    second = TARGET | {"identity": "task-2"}
    assert (
        call(
            flow,
            "coordination.supply",
            {"operation_id": "supply-2", "work": work},
            target=second,
        ).outcome
        == Outcome.SUCCESS
    )
    inputs = {
        "operation_id": "allocate-2",
        "expected_version": 1,
        "assignment_id": "assignment-2",
        "attempt_id": "attempt-2",
        "configuration": {
            kind: fixture_ref(kind) for kind in ("agent", "profile", "role", "context")
        },
    }
    assert call(flow, "coordination.allocate", inputs, target=second).reason == Reason.CONFLICT


def test_versioned_artifact_hash_and_unknown_fields_are_strict(flow):
    work = json.loads((ROOT / "examples/coordination.json").read_text())["work"]
    work["inputs"][0]["content"] = "changed without matching hash"
    assert (
        call(flow, "coordination.supply", {"operation_id": "supply-1", "work": work}).outcome
        == Outcome.INVALID
    )

    assert (
        call(
            flow,
            "coordination.supply",
            {"operation_id": "supply-1", "work": work, "force_enable": True},
        ).outcome
        == Outcome.INVALID
    )


def test_accepted_registry_store_forward_upgrade_preserves_all_records(tmp_path):
    import shutil
    from importlib.resources import files

    legacy = tmp_path / "legacy"
    shutil.copytree(files("mobiraeon.persistence").joinpath("migrations"), legacy)
    (legacy / "versions/0003_coordination.py").unlink()
    store = Store(tmp_path / "accepted-registry.db")
    store.path.touch(mode=0o600)
    try:
        assert store.upgrade(migration_path=legacy, _new=True) == "0002"
        with store.transaction() as tx:
            tx.execute(text("INSERT INTO registry_entities VALUES('role','retained-role')"))
            tx.execute(
                text(
                    "INSERT INTO registry_drafts VALUES"
                    "('role','retained-role',1,'{}','retained-hash','human-1',0)"
                )
            )
            tx.execute(
                text(
                    "INSERT INTO registry_audit(invocation,operation,actor,outcome,reason,"
                    "record,at) VALUES('prior','registry.create','human-1','success',"
                    "'ok','{}',1)"
                )
            )
        with store.engine.connect() as tx:
            before = {
                name: tx.exec_driver_sql("SELECT * FROM " + name).fetchall()
                for name in (
                    "foundation_identity",
                    "registry_entities",
                    "registry_drafts",
                    "registry_audit",
                )
            }
        assert store.upgrade() == "0003"
        with store.engine.connect() as tx:
            for name, rows in before.items():
                assert tx.exec_driver_sql("SELECT * FROM " + name).fetchall() == rows
            assert tx.exec_driver_sql("SELECT count(*) FROM coordination_facts").scalar() == 0
    finally:
        store.close()


@pytest.mark.parametrize("changed", ["submission_digest", "submission_id", "assessment_id"])
def test_acceptance_does_not_transfer_to_other_revision_or_assessment(flow, changed):
    sent = steps(flow, "assess")
    inputs = {
        "operation_id": "accept-1",
        "expected_version": 6,
        "submission_id": "submission-1",
        "submission_digest": sent["assess"]["submission_digest"],
        "assessment_id": "assess-1",
    }
    inputs[changed] = "different-revision"
    assert call(flow, "coordination.accept", inputs, "assessor").outcome != Outcome.SUCCESS
    assert status(flow)["state"] == "assessed"


def test_revoked_assessor_and_replay_withdrawn_grants(flow):
    sent = steps(flow)
    service, admin = flow[1:]
    assessor = proof_for(service.private, "assessor")
    grant(service, admin, assessor.identifier, {Operation.STATUS})
    assert (
        call(flow, "coordination.accept", sent["accept"], "assessor").outcome == Outcome.REFUSED
    )
    assert status(flow)["state"] == "accepted"  # Original evidence is retained.


@pytest.mark.parametrize("committed", [True, False])
def test_acceptance_commit_uncertainty_never_applies_acceptance_twice(
    flow, monkeypatch, committed
):
    sent = steps(flow, "assess")
    inputs = {
        "operation_id": "accept-1",
        "expected_version": 6,
        "submission_id": "submission-1",
        "submission_digest": sent["assess"]["submission_digest"],
        "assessment_id": "assess-1",
    }
    original = Transaction.commit
    calls = 0

    def uncertain(tx):
        nonlocal calls
        calls += 1
        if calls == 1:
            if committed:
                original(tx)
            raise RuntimeError("SENSITIVE_ACCEPT_ACK")
        original(tx)

    with monkeypatch.context() as scoped:
        scoped.setattr(Transaction, "commit", uncertain)
        assert (
            call(flow, "coordination.accept", inputs, "assessor").outcome == Outcome.UNCERTAIN
        )
    assert (status(flow)["state"] == "accepted") is committed
    assert status(flow)["unresolved"] is (not committed)
    repeated = call(flow, "coordination.accept", inputs, "assessor")
    assert (repeated.outcome == Outcome.SUCCESS) is committed
    if committed:
        assert repeated.data.records[0]["replayed"] is True
    with flow[1].store.engine.connect() as tx:
        assert tx.exec_driver_sql(
            "SELECT count(*) FROM coordination_facts WHERE stage='accept'"
        ).scalar() == int(committed)


def test_registry_read_scope_and_current_allocation_grant_are_required(flow):
    steps(flow, "supply")
    service, admin = flow[1:]
    proof = proof_for(service.private, "author")
    grant(service, admin, proof.identifier, AUTHOR_ACTIONS)
    inputs = {
        "operation_id": "allocate-1",
        "expected_version": 1,
        "assignment_id": "assignment-1",
        "attempt_id": "attempt-1",
        "configuration": {
            kind: fixture_ref(kind) for kind in ("agent", "profile", "role", "context")
        },
    }
    assert call(flow, "coordination.allocate", inputs).reason == Reason.REFUSED


def test_two_ordinary_tokens_cannot_assess_their_own_submission(flow):
    coordinator, service, _ = flow
    ordinary = Coordinator(
        service.store, service.private, configuration_source=FixtureConfiguration()
    )
    original_access = coordinator.access
    coordinator.access = ordinary.access
    try:
        sent = steps(flow, "before-assess")
        assert (
            call(flow, "coordination.assess", sent["assess"], "assessor").reason
            == Reason.REVIEW
        )
    finally:
        coordinator.access = original_access


def test_complete_real_catalog_is_unavailable_for_ordinary_allocation(tmp_path):
    from mobiraeon.scenario import setup

    directory = tmp_path / "private"
    prepared = setup(directory, ROOT / "bootstrap/initial-test.json")
    assert prepared["catalog"]
    store, private, fixture = compose(directory)
    try:
        ordinary = Coordinator(store, private, access=fixture.access)
        with store.engine.connect() as tx:
            agent = (
                tx.exec_driver_sql(
                    "SELECT * FROM registry_publications WHERE kind='agent' LIMIT 1"
                )
                .mappings()
                .one()
            )
            profile_ref = json.loads(agent["document"])["profileRef"]
            profile = tx.execute(
                text("SELECT document FROM registry_publications WHERE id=:id"),
                {"id": profile_ref["revision"]},
            ).scalar()
        profile = json.loads(profile)
        work = json.loads((ROOT / "examples/coordination.json").read_text())["work"]
        work["role"] = profile["roleRef"]
        proof = proof_for(private, "author")
        assert (
            ordinary.invoke(
                "coordination.supply",
                TARGET,
                {"operation_id": "supply-1", "work": work},
                proof=proof,
            ).outcome
            == Outcome.SUCCESS
        )
        result = ordinary.invoke(
            "coordination.allocate",
            TARGET,
            {
                "operation_id": "allocate-1",
                "expected_version": 1,
                "assignment_id": "assignment-1",
                "attempt_id": "attempt-1",
                "configuration": {
                    "agent": {
                        "kind": "agent",
                        "identity": agent["identity"],
                        "revision": agent["id"],
                    },
                    "profile": profile_ref,
                    "role": profile["roleRef"],
                    "context": profile["contextPolicyRef"],
                },
            },
            proof=proof,
        )
        assert result.outcome == Outcome.UNAVAILABLE
        with store.engine.connect() as tx:
            assert (
                tx.exec_driver_sql(
                    "SELECT count(*) FROM registry_controls WHERE enabled=1"
                ).scalar()
                == 0
            )
    finally:
        store.close()
