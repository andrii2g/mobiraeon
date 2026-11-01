from sqlalchemy import text

from mobiraeon.application import Application
from mobiraeon.configuration import Configuration
from mobiraeon.contracts import (
    CallerContext,
    EntityId,
    Operation,
    Outcome,
    Owner,
    RevisionRef,
)
from mobiraeon.errors import Reason, SafeError
from mobiraeon.operations import Binding, OperationBoundary

CALLER = CallerContext(EntityId("human", "verified-fixture"), "test-adapter")
TARGET = RevisionRef(EntityId("agent", "fixture-agent"), "immutable-r1")


class Policy:
    enabled = True
    revoked = False

    def permits(self, caller, operation, target):
        return not self.revoked and (operation == Operation.REGISTRY_READ or self.enabled)


def boundary(store, handler, *, caller=CALLER, policy=None, transactional=True):
    return OperationBoundary(
        {Operation.REGISTRY_USE: Binding(Owner.REGISTRY, handler, transactional, True)},
        policy or Policy(),
        caller,
        store,
    )


def count(store):
    with store.engine.connect() as connection:
        return connection.exec_driver_sql("SELECT count(*) FROM registry_fixture").scalar()


def test_two_logical_owners_commit_or_rollback_together(store):
    with store.transaction() as tx:
        tx.execute(text("CREATE TABLE registry_fixture (value TEXT)"))
        tx.execute(text("CREATE TABLE coordination_fixture (value TEXT)"))

    class RegistryFixture:
        def write(self, tx):
            tx.execute(text("INSERT INTO registry_fixture VALUES ('r')"))

    class CoordinationFixture:
        def write(self, tx):
            tx.execute(text("INSERT INTO coordination_fixture VALUES ('c')"))

    def combined(tx, target):
        RegistryFixture().write(tx)
        CoordinationFixture().write(tx)

    result = boundary(store, combined).invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.SUCCESS
    assert result.actor == CALLER.actor
    assert result.target == TARGET
    assert count(store) == 1
    assert not hasattr(result, "acceptance")

    def failed(tx, target):
        combined(tx, target)
        raise RuntimeError("SENSITIVE_BODY_ERROR")

    result = boundary(store, failed).invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.FAILURE
    assert result.reason == Reason.ROLLED_BACK
    assert count(store) == 1
    with store.engine.connect() as connection:
        assert (
            connection.exec_driver_sql("SELECT count(*) FROM coordination_fixture").scalar()
            == 1
        )


def test_validation_missing_grant_and_unavailable_never_call_handler(store):
    calls = []
    policy = Policy()
    path = boundary(store, lambda *args: calls.append(args), policy=policy)
    for kwargs in ({"inputs": {"claimed_role": "admin"}}, {"target": "untrusted"}, {}):
        assert path.invoke(Operation.REGISTRY_USE, **kwargs).outcome == Outcome.INVALID
    invalid = path.invoke("SENSITIVE_UNKNOWN_OPERATION")
    assert invalid.operation is None
    assert invalid.outcome == Outcome.INVALID
    policy.enabled = False
    assert path.invoke(Operation.REGISTRY_USE, target=TARGET).outcome == Outcome.REFUSED
    missing = boundary(store, lambda *args: calls.append(args), caller=None)
    result = missing.invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.REFUSED and result.actor is None
    unavailable = boundary(store, None)
    assert (
        unavailable.invoke(Operation.REGISTRY_USE, target=TARGET).outcome == Outcome.UNAVAILABLE
    )
    assert calls == []


def test_missing_trusted_policy_context_is_refused(store):
    calls = []
    path = OperationBoundary(
        {Operation.CHECK: Binding(Owner.FOUNDATION, lambda *args: calls.append(args))},
        None,
        CALLER,
        store,
    )
    assert path.invoke(Operation.CHECK).outcome == Outcome.REFUSED
    assert not calls


def test_policy_dependency_failure_stays_attributable_without_execution(store):
    class FailedPolicy:
        def permits(self, *args):
            raise SafeError(Reason.INTERNAL)

    result = OperationBoundary({}, FailedPolicy(), CALLER, store).invoke(Operation.CHECK)
    assert result.outcome == Outcome.UNAVAILABLE
    assert result.actor == CALLER.actor
    assert result.operation == Operation.CHECK
    assert result.invocation_id


def test_exact_history_stays_retrievable_but_current_use_is_refused(store):
    snapshots = {TARGET: ("exact-profile-r1",)}
    calls = []
    policy = Policy()
    bindings = {
        Operation.REGISTRY_READ: Binding(
            Owner.REGISTRY, lambda tx, target: calls.append(snapshots[target]), False, True
        ),
        Operation.REGISTRY_USE: Binding(
            Owner.REGISTRY, lambda *args: calls.append("used"), False, True
        ),
    }
    path = OperationBoundary(bindings, policy, CALLER, store)
    assert path.invoke(Operation.REGISTRY_READ, target=TARGET).outcome == Outcome.SUCCESS
    policy.enabled = False
    assert path.invoke(Operation.REGISTRY_USE, target=TARGET).outcome == Outcome.REFUSED
    assert path.invoke(Operation.REGISTRY_READ, target=TARGET).outcome == Outcome.SUCCESS
    assert snapshots[TARGET] == ("exact-profile-r1",)
    policy.revoked = True
    assert path.invoke(Operation.REGISTRY_READ, target=TARGET).outcome == Outcome.REFUSED
    assert "used" not in calls


def test_current_restriction_rechecked_after_waiting_for_transaction(store):
    class ChangedPolicy:
        calls = 0

        def permits(self, *args):
            self.calls += 1
            return self.calls == 1

    calls = []
    result = boundary(store, lambda *args: calls.append(args), policy=ChangedPolicy()).invoke(
        Operation.REGISTRY_USE, target=TARGET
    )
    assert result.outcome == Outcome.REFUSED
    assert not calls


def test_uncertain_effects_are_not_replayed_or_claimed_rolled_back(store):
    calls = []

    def handler(tx, target):
        calls.append("possibly committed")
        raise RuntimeError("SENSITIVE_EFFECT_ERROR")

    result = boundary(store, handler, transactional=False).invoke(
        Operation.REGISTRY_USE, target=TARGET
    )
    assert result.outcome == Outcome.UNCERTAIN
    assert result.reason == Reason.UNCERTAIN
    assert calls == ["possibly committed"]
    assert "SENSITIVE" not in repr(result)


def test_commit_or_rollback_failure_is_uncertain(store, monkeypatch):
    from sqlalchemy.engine import Transaction

    original = Transaction.commit

    def commit_then_fail(transaction):
        original(transaction)
        raise RuntimeError("SENSITIVE_COMMIT_ACK")

    monkeypatch.setattr(Transaction, "commit", commit_then_fail)
    result = boundary(
        store,
        lambda tx, target: tx.execute(text("CREATE TABLE committed_fixture (value TEXT)")),
    ).invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.UNCERTAIN
    with store.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM sqlite_master WHERE name='committed_fixture'"
            ).scalar()
            == 1
        )


def test_real_composition_grants_only_local_foundation(store):
    app = Application(Configuration(store.path))
    try:
        assert app.operations.invoke(Operation.CHECK).outcome == Outcome.SUCCESS
        assert (
            app.operations.invoke(Operation.REGISTRY_USE, target=TARGET).outcome
            == Outcome.REFUSED
        )
        assert (
            app.operations.invoke(Operation.REGISTRY_READ, target=TARGET).outcome
            == Outcome.REFUSED
        )
    finally:
        app.close()


def test_failed_rollback_is_uncertain_and_does_not_leak_driver_errors(
    store, monkeypatch, capsys
):
    from sqlalchemy.engine import Transaction

    original = Transaction.rollback

    def rollback_then_fail(transaction):
        original(transaction)
        raise RuntimeError("SENSITIVE_ROLLBACK_ERROR")

    monkeypatch.setattr(Transaction, "rollback", rollback_then_fail)

    def fail(tx, target):
        raise RuntimeError("SENSITIVE_HANDLER_ERROR")

    result = boundary(store, fail).invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.UNCERTAIN
    output = capsys.readouterr()
    assert "SENSITIVE" not in output.out + output.err + repr(result)
