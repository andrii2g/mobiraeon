"""Regressions for the five findings against the original Increment 1 submission."""

import json
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from importlib.resources import files

import pytest
from sqlalchemy import text
from test_application import SECRET, clean_env, run
from test_operations import TARGET, boundary

from mobiraeon.contracts import Operation, Outcome
from mobiraeon.errors import Reason, SafeError
from mobiraeon.persistence import Store


def fixture_table(store):
    with store.transaction() as tx:
        tx.execute(text("CREATE TABLE repair_fixture (value TEXT)"))


def rows(store):
    with store.engine.connect() as connection:
        return connection.exec_driver_sql("SELECT value FROM repair_fixture").all()


@pytest.mark.parametrize("statement", ["COMMIT", "ROLLBACK", "-- comment\n END TRANSACTION"])
def test_r1_participants_cannot_complete_the_owned_transaction(store, statement):
    fixture_table(store)

    def handler(tx, target):
        tx.execute(text("INSERT INTO repair_fixture VALUES ('pending')"))
        tx.execute(text(statement))
        if statement == "COMMIT":
            raise RuntimeError("handler failed after participant commit")
        # The original ROLLBACK probe returns normally here.

    result = boundary(store, handler).invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.FAILURE
    assert result.reason == Reason.ROLLED_BACK
    assert rows(store) == []


def test_r1_caught_control_denial_does_not_prevent_application_commit(store):
    from sqlalchemy.exc import DatabaseError

    fixture_table(store)

    def handler(tx, target):
        tx.execute(text("INSERT INTO repair_fixture VALUES ('owned')"))
        with pytest.raises(DatabaseError):
            tx.execute(text("ROLLBACK"))

    result = boundary(store, handler).invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.SUCCESS
    assert rows(store) == [("owned",)]


def test_r1_commit_attempt_followed_by_handler_exception_rolls_back_real_data(store):
    from sqlalchemy.exc import DatabaseError

    fixture_table(store)

    def handler(tx, target):
        tx.execute(text("INSERT INTO repair_fixture VALUES ('pending')"))
        try:
            tx.execute(text("COMMIT"))
        except DatabaseError:
            pass
        raise RuntimeError("handler failure after COMMIT attempt")

    result = boundary(store, handler).invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.FAILURE and result.reason == Reason.ROLLED_BACK
    assert rows(store) == []


@pytest.mark.parametrize("control", ["COMMIT", "ROLLBACK"])
def test_r1_lost_driver_ownership_never_claims_commit_or_verified_rollback(store, control):
    fixture_table(store)

    def handler(tx, target):
        tx.execute(text("INSERT INTO repair_fixture VALUES ('possibly committed')"))
        # Fault injection through private internals is deliberately outside the
        # public participant API. It proves the finalizer also checks driver state.
        driver = tx._connection.connection.driver_connection
        driver.set_authorizer(None)
        driver.execute(control)
        if control == "COMMIT":
            raise RuntimeError("handler failed after ownership was lost")

    result = boundary(store, handler).invoke(Operation.REGISTRY_USE, target=TARGET)
    assert result.outcome == Outcome.UNCERTAIN
    assert result.reason == Reason.UNCERTAIN
    assert rows(store) == ([("possibly committed",)] if control == "COMMIT" else [])


@pytest.mark.parametrize("decision", ["denied", 1, 0, None, [], [True], {}, {"grant": True}])
@pytest.mark.parametrize("check", ["initial", "post_lock"])
def test_r2_only_literal_boolean_grants_allow_execution(store, decision, check):
    fixture_table(store)
    calls = []

    class Policy:
        checks = 0

        def permits(self, *args):
            self.checks += 1
            return True if check == "post_lock" and self.checks == 1 else decision

    def handler(tx, target):
        calls.append(target)
        tx.execute(text("INSERT INTO repair_fixture VALUES ('unauthorized')"))

    policy = Policy()
    result = boundary(store, handler, policy=policy).invoke(
        Operation.REGISTRY_USE, target=TARGET
    )
    assert result.outcome == Outcome.REFUSED
    assert policy.checks == (1 if check == "initial" else 2)
    assert not calls
    assert rows(store) == []


@pytest.mark.parametrize("command", ["initialize", "upgrade", "check", "start"])
def test_r3_cleanup_failure_is_safe_and_terminal_in_a_real_process(store, tmp_path, command):
    counter = tmp_path / "close-count"
    script = """
import sys, threading
from pathlib import Path
from mobiraeon import cli
from mobiraeon.persistence import Store
original = Store.close
def close(self):
    counter = Path(sys.argv[1])
    count = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(count + 1))
    original(self)
    raise RuntimeError("SYNTHETIC_SENSITIVE_9f0e")
Store.close = close
stop = threading.Event()
serve = cli.serve
cli.serve = lambda: serve(stop)
threading.Timer(0.2, stop.set).start()
raise SystemExit(cli.main(sys.argv[2:]))
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(counter), "--database", str(store.path), command],
        cwd=tmp_path,
        env=clean_env(),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert process.returncode == 1
    assert counter.read_text() == "1"
    assert SECRET not in process.stdout + process.stderr
    assert "Traceback" not in process.stderr
    outputs = [json.loads(line) for line in process.stdout.splitlines()]
    terminal = outputs[-1]
    assert terminal["phase"] == "terminal"
    assert terminal["reason"] == "cleanup_failed"
    assert terminal["outcome"] == "uncertain_effects"
    assert not terminal.get("foundation_ready", False)
    if command == "start":
        assert outputs[0]["phase"] == "ready" and outputs[0]["foundation_ready"]
        assert outputs[0]["invocation_id"] == terminal["invocation_id"]
    else:
        assert len(outputs) == 1
    events = [json.loads(line) for line in process.stderr.splitlines()]
    assert events[-1]["event"] == "command_error"
    assert events[-1]["reason"] == "cleanup_failed"
    assert "stopped" not in [event["event"] for event in events]
    assert run("--database", store.path, "check", cwd=tmp_path).returncode == 0


def test_r4_packaged_migrations_work_after_percent_path_relocation(tmp_path):
    installed = tmp_path / "100%valid"
    installed.mkdir()
    shutil.copytree(
        files("mobiraeon"),
        installed / "mobiraeon",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    script = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import mobiraeon
from mobiraeon.persistence import Store
assert "100%valid" in mobiraeon.__file__
store = Store(Path(sys.argv[2]))
try:
    assert store.initialize() == "0003"
    assert store.upgrade() == "0003"
    assert store.check() == "0003"
finally:
    store.close()
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(installed), str(tmp_path / "relocated.db")],
        cwd=tmp_path,
        env=clean_env(),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert process.returncode == 0, process.stderr


def test_r4_migration_configuration_failures_are_normalized(store, monkeypatch):
    def fail(*args):
        raise ValueError(SECRET)

    monkeypatch.setattr("mobiraeon.persistence.Config.set_main_option", fail)
    with pytest.raises(SafeError) as error:
        store.check()
    assert error.value.reason == Reason.MIGRATION_CHAIN
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("acquisition", ["writer_lock", "connection"])
def test_r5_pre_execution_acquisition_failures_have_known_no_effects(
    store, tmp_path, acquisition
):
    fixture_table(store)
    calls = []

    def handler(tx, target):
        calls.append(target)
        tx.execute(text("INSERT INTO repair_fixture VALUES ('not allowed to start')"))

    if acquisition == "connection":
        missing = Store(tmp_path / "missing.db", timeout=0.1)
        try:
            result = boundary(missing, handler).invoke(Operation.REGISTRY_USE, target=TARGET)
        finally:
            missing.close()
        assert not (tmp_path / "missing.db").exists()
    else:
        with closing(sqlite3.connect(store.path)) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            result = boundary(store, handler).invoke(Operation.REGISTRY_USE, target=TARGET)
            blocker.rollback()
    assert result.outcome == Outcome.UNAVAILABLE
    assert result.reason == Reason.STORAGE_FAILURE
    assert not calls
    assert rows(store) == []
