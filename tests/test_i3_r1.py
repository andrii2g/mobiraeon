"""I3-R1: a receipt must establish the original uncertain operation, not just its ID."""

import pytest
from sqlalchemy.engine import Transaction
from test_coordination import call, status, steps
from test_coordination import flow as flow
from test_registry import registry as registry

from mobiraeon.catalog import RegistryService
from mobiraeon.contracts import Outcome
from mobiraeon.coordination import Coordinator
from mobiraeon.errors import Reason
from mobiraeon.persistence import Store
from mobiraeon.scenario import (
    AUTHOR_ACTIONS,
    TARGET,
    FixtureConfiguration,
    ScenarioAccess,
    proof_for,
)


def wildcard_author(flow):
    _, service, admin = flow
    author = proof_for(service.private, "author")
    result = service.invoke(
        "access.grants",
        {"kind": "access", "entity_kind": "credential", "identity": author.identifier},
        {
            "expected_version": 1,
            "grants": [
                {"action": action.value, "scope": "task:*"} for action in sorted(AUTHOR_ACTIONS)
            ]
            + [{"action": "registry.read", "scope": "*"}],
        },
        proof=admin,
    )
    assert result.outcome == Outcome.SUCCESS


DISPATCH = {"operation_id": "uncertain-id", "expected_version": 2, "attempt_id": "attempt-1"}


def unknown_dispatch(flow, monkeypatch, *, committed=False, legacy=False):
    original_commit = Transaction.commit
    original_history = flow[0]._history
    commits = 0

    def commit(tx):
        nonlocal commits
        commits += 1
        if commits == 1:
            if committed:
                original_commit(tx)
            raise RuntimeError("synthetic lost commit acknowledgement")
        original_commit(tx)

    def history(tx, task, invocation, actor, operation, outcome, record):
        # Exercise persisted pre-repair history without changing retained facts.
        if legacy:
            record = {key: value for key, value in record.items() if key != "fingerprint"}
        return original_history(tx, task, invocation, actor, operation, outcome, record)

    with monkeypatch.context() as scoped:
        scoped.setattr(Transaction, "commit", commit)
        scoped.setattr(flow[0], "_history", history)
        result = call(flow, "coordination.dispatch", DISPATCH)
    assert result.outcome == Outcome.UNCERTAIN
    return result


def reopen(flow):
    _, service, admin = flow
    service.store.close()
    store = Store(service.store.path)
    other = Coordinator(
        store,
        service.private,
        access=ScenarioAccess(store, service.private),
        configuration_source=FixtureConfiguration(),
    )
    return other, RegistryService(store, service.private), admin


def collide(flow, monkeypatch, legacy):
    wildcard_author(flow)
    supplied = steps(flow, "allocate")
    unknown_dispatch(flow, monkeypatch, legacy=legacy)
    before = status(flow)
    assert before["unresolved"] and len(before["unresolved_operations"]) == 1
    unrelated = call(
        flow,
        "coordination.supply",
        {"operation_id": "uncertain-id", "work": supplied["supply"]["work"]},
        target=TARGET | {"identity": "task-2"},
    )
    # Independent work may retain its own receipt, but cannot reconcile task-1.
    assert unrelated.outcome == Outcome.SUCCESS


@pytest.mark.parametrize("legacy", [False, True], ids=["new-provenance", "legacy-history"])
@pytest.mark.parametrize("restart", [False, True], ids=["same-process", "reopened-store"])
def test_i3_r1_unrelated_receipt_keeps_original_fence(flow, monkeypatch, legacy, restart):
    collide(flow, monkeypatch, legacy)
    active = reopen(flow) if restart else flow
    try:
        current = status(active)
        assert current["unresolved"] is True
        assert len(current["unresolved_operations"]) == 1
        assert current["version"] == 2 and current["state"] == "allocated"
        refused = call(
            active, "coordination.dispatch", DISPATCH | {"operation_id": "fresh-dispatch"}
        )
        assert refused.outcome != Outcome.SUCCESS
        assert status(active)["version"] == 2
    finally:
        if restart:
            active[1].store.close()


@pytest.mark.parametrize("legacy", [False, True], ids=["new-provenance", "legacy-history"])
def test_i3_r1_fresh_dispatch_refused_after_collision_and_restart(flow, monkeypatch, legacy):
    collide(flow, monkeypatch, legacy)
    active = reopen(flow)
    try:
        refused = call(
            active, "coordination.dispatch", DISPATCH | {"operation_id": "fresh-dispatch"}
        )
        assert refused.outcome != Outcome.SUCCESS
        with active[1].store.engine.connect() as tx:
            assert (
                tx.exec_driver_sql(
                    "SELECT count(*) FROM coordination_facts "
                    "WHERE task='task-1' AND stage='dispatch'"
                ).scalar()
                == 0
            )
    finally:
        active[1].store.close()


@pytest.mark.parametrize("legacy", [False, True], ids=["new-provenance", "legacy-history"])
def test_i3_r1_exact_committed_receipt_reconciles_after_restart(flow, monkeypatch, legacy):
    steps(flow, "allocate")
    unknown_dispatch(flow, monkeypatch, committed=True, legacy=legacy)
    active = reopen(flow)
    try:
        current = status(active)
        assert current["unresolved_operations"] == []
        assert current["state"] == "unresolved" and current["version"] == 3
        repeated = call(active, "coordination.dispatch", DISPATCH)
        assert (
            repeated.outcome == Outcome.SUCCESS and repeated.data.records[0]["replayed"] is True
        )
        conflict = call(active, "coordination.dispatch", DISPATCH | {"expected_version": 3})
        assert conflict.reason == Reason.CONFLICT
        _, service, admin = active
        proof = proof_for(service.private, "author")
        revoked = service.invoke(
            "access.revoke",
            {"kind": "access", "entity_kind": "credential", "identity": proof.identifier},
            {"expected_version": 1},
            proof=admin,
        )
        assert revoked.outcome == Outcome.SUCCESS
        assert call(active, "coordination.dispatch", DISPATCH).outcome == Outcome.REFUSED
        assert call(active, "coordination.status").outcome == Outcome.REFUSED
    finally:
        active[1].store.close()


def test_i3_r1_uncertain_exact_receipt_replay_does_not_create_a_new_fence(flow, monkeypatch):
    steps(flow, "allocate")
    assert call(flow, "coordination.dispatch", DISPATCH).outcome == Outcome.SUCCESS
    unknown_dispatch(flow, monkeypatch)
    active = reopen(flow)
    try:
        assert status(active)["unresolved_operations"] == []
        assert (
            call(active, "coordination.dispatch", DISPATCH).data.records[0]["replayed"] is True
        )
        with active[1].store.engine.connect() as tx:
            assert (
                tx.exec_driver_sql(
                    "SELECT count(*) FROM coordination_facts WHERE stage='dispatch'"
                ).scalar()
                == 1
            )
    finally:
        active[1].store.close()
