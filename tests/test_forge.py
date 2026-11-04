"""Disk-backed production bridge and transport regression/fault contracts."""

import copy
import json
import secrets
import sqlite3
import threading
import time
from contextlib import closing
from dataclasses import asdict

import pytest
from sqlalchemy import event

from mobiraeon.access import execute
from mobiraeon.contracts import BusinessTarget, Operation, Outcome
from mobiraeon.errors import Reason, SafeError
from mobiraeon.forge import ForgeService
from mobiraeon.forge_credentials import import_token, read_token, validate_token
from mobiraeon.forge_schema import connection, decode, validate
from mobiraeon.forge_verification import TARGET, definition, exercise, fixture
from mobiraeon.persistence import Store
from mobiraeon.private_state import durable_new, harden

NAME_FIELDS = [("repository", "owner"), ("repository", "name"), ("account", "name")]


@pytest.mark.parametrize("section,field", NAME_FIELDS)
def test_i5_r1_all_c1_controls_are_rejected(section, field):
    for codepoint in range(0x80, 0xA0):
        config = definition("http://localhost")
        config[section][field] = "before" + chr(codepoint) + "after"
        with pytest.raises(ValueError):
            connection(config)


@pytest.mark.parametrize("section,field", NAME_FIELDS)
def test_i5_r1_existing_component_refusals(section, field):
    for name in ("", ".", "..", "a/b", "a\\b", "x" * 101, "a\x00b", "a\x1fb", "a\x7fb"):
        config = definition("http://localhost")
        config[section][field] = name
        with pytest.raises(ValueError):
            connection(config)


@pytest.mark.parametrize("section,field", NAME_FIELDS)
def test_i5_r1_permitted_unicode_is_preserved(section, field):
    # Include decomposed text, spaces and a non-Cc format character: the repair
    # must neither normalize names nor broaden rejection to all Unicode C*.
    for name in ("Café", "Пример", "示例", "e\u0301", " surrounded ", "a\u200db", "x" * 100):
        config = definition("http://localhost")
        config[section][field] = name
        assert connection(config)[section][field] == name


def connection_records(app):
    """Compare business records only; failed-attempt audit is permitted."""
    with app.store.engine.connect() as tx:
        return {
            table: tuple(tuple(row) for row in tx.exec_driver_sql(f"SELECT * FROM {table}"))
            for table in ("forge_connections", "forge_revisions")
        }


@pytest.mark.parametrize("section,field", NAME_FIELDS)
def test_i5_r1_valid_names_configure_read_offline(section, field):
    with fixture() as (app, server):
        for version, name in enumerate(("Café", "Пример", "示例", "e\u0301", "x" * 100), 1):
            config = definition(server.origin)
            config[section][field] = name
            configured = app.call(
                "forge.connection.configure",
                operation_id=f"unicode-{version}",
                expected_version=version,
                connection=config,
            )
            assert configured.outcome == Outcome.SUCCESS
            current = app.call("forge.connection.read")
            retained = app.call(
                "forge.connection.read", connection_revision=configured.data.reference
            )
            assert current.data == retained.data
            assert current.data.records[0]["definition"] == connection(config)
        assert not server.routes


@pytest.mark.parametrize("section,field", NAME_FIELDS)
@pytest.mark.parametrize("control", [0x80, 0x85, 0x9F])
@pytest.mark.parametrize("replacement", [False, True], ids=["creation", "replacement"])
def test_i5_r1_configure_refusal_preserves_version(section, field, control, replacement):
    with fixture() as (app, server):
        target = TARGET if replacement else TARGET | {"identity": "project-unconfigured"}
        expected = 1 if replacement else 0

        def invoke(operation, **inputs):
            return app.service.invoke(operation, target, inputs, proof=app.proof)

        before_read = invoke("forge.connection.read")
        if replacement:
            assert before_read.outcome == Outcome.SUCCESS
            assert before_read.data.version == 1
            assert before_read.data.records[0]["connection_revision"] == app.revision
        else:
            assert before_read.outcome == Outcome.FAILURE
            assert before_read.reason.value == "reference_missing"
        before = connection_records(app)
        config = definition(server.origin)
        config[section][field] = "before" + chr(control) + "after"
        refused = invoke(
            "forge.connection.configure",
            operation_id="invalid-control",
            expected_version=expected,
            connection=config,
        )
        assert refused.outcome == Outcome.INVALID
        assert refused.reason.value == "invalid_input"
        assert connection_records(app) == before
        after_read = invoke("forge.connection.read")
        assert after_read.outcome == before_read.outcome
        assert after_read.reason == before_read.reason
        assert after_read.data == before_read.data
        if replacement:
            retained = invoke("forge.connection.read", connection_revision=app.revision)
            assert retained.data == before_read.data
        assert not server.routes

        # A new operation ID with the SAME expected version must still work.
        config[section][field] = "Café-Пример-示例-e\u0301"
        configured = invoke(
            "forge.connection.configure",
            operation_id="valid-after-refusal",
            expected_version=expected,
            connection=config,
        )
        assert configured.outcome == Outcome.SUCCESS
        assert configured.data.version == expected + 1
        current = invoke("forge.connection.read")
        retained = invoke(
            "forge.connection.read", connection_revision=configured.data.reference
        )
        assert current.data == retained.data
        assert current.data.records[0]["definition"] == connection(config)
        assert (
            len(connection_records(app)["forge_revisions"])
            == len(before["forge_revisions"]) + 1
        )
        assert not server.routes


def test_runtime_only_scenario():
    assert exercise()["result"] == "passed"


@pytest.mark.parametrize("value", [b"", b"x" * 4097, b"a b", b"a\t", b"a\n\n", b"a\r", b"\xff"])
def test_token_bounds(value):
    with pytest.raises((ValueError, SafeError)):
        validate_token(value)


def test_full_token_no_truncation_and_pat_refusal():
    assert validate_token(b"x" * 4096 + b"\r\n") == "x" * 4096
    value = "mbr_" + secrets.token_hex(16) + "_" + secrets.token_urlsafe(32)
    with pytest.raises((ValueError, SafeError)):
        validate_token(value.encode())


@pytest.mark.parametrize(
    "field,value",
    [
        ("origin", "http://example.com"),
        (
            "origin",
            "https://" + secrets.token_hex(8) + ":" + secrets.token_hex(8) + "@localhost",
        ),
        ("origin", "https://localhost/path"),
        ("origin", "https://localhost/?q=x"),
        ("origin", "https://localhost/#x"),
        ("origin", "http://localhost.example.com"),
        ("origin", "http://localhost:0"),
        ("origin", "https://@localhost"),
        ("origin", "https://localhost?"),
        ("origin", "https://localhost/#"),
        ("tls_ca_file", "relative.pem"),
        ("allow_loopback_http", 1),
        ("provider", "other"),
    ],
)
def test_connection_validation(field, value):
    config = definition("http://localhost")
    config[field] = value
    with pytest.raises((ValueError, SafeError)):
        connection(config)


@pytest.mark.parametrize(
    "field,value",
    [
        ("cycle_seconds", True),
        ("cycle_seconds", float("inf")),
        ("request_seconds", 100),
        ("finalization_seconds", 11),
        ("max_requests", 1.0),
        ("max_pages", 0),
        ("response_bytes", 1023),
        ("total_read_bytes", 1024),
        ("comment_bytes", 65537),
    ],
)
def test_limit_validation(field, value):
    config = definition("http://localhost")
    config["limits"][field] = value
    with pytest.raises((ValueError, SafeError)):
        connection(config)


@pytest.mark.parametrize("value", ["0", "01", "+1", "9223372036854775808", 1, True])
def test_native_ids_are_not_local_tokens_or_coerced(value):
    config = definition("http://localhost")
    config["repository"]["id"] = value
    with pytest.raises((ValueError, SafeError)):
        connection(config)


@pytest.mark.parametrize(
    "raw",
    [b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}', b"{}" + b" " * 131071, b'{"a":NaN}', b"\xff"],
)
def test_strict_file_decoder(raw):
    with pytest.raises((ValueError, SafeError)):
        decode(raw)


def test_offline_historical_configuration_and_current_guard():
    with fixture() as (app, server):
        prior = app.revision
        config = definition(server.origin)
        config["limits"]["max_requests"] = 19
        changed = app.call(
            "forge.connection.configure",
            operation_id="configure-2",
            expected_version=1,
            connection=config,
        )
        assert changed.outcome == Outcome.SUCCESS
        assert not server.routes
        historical = app.call("forge.connection.read", connection_revision=prior)
        assert historical.data.version == 1
        assert historical.data.records[0]["current_version"] == 2
        assert app.link().outcome != Outcome.SUCCESS
        app.revision = changed.data.reference
        assert app.link("current").outcome == Outcome.SUCCESS
        config["repository"]["id"] = "9"
        refused = app.call(
            "forge.connection.configure",
            operation_id="retarget",
            expected_version=2,
            connection=config,
        )
        assert refused.outcome != Outcome.SUCCESS


def test_secrets_protection_rotation_no_overwrite_and_links():
    with fixture() as (app, server):
        value = secrets.token_urlsafe(100)
        source = app.directory / "rotation-source"
        durable_new(source, value.encode())
        import_token(app.store, app.private, source, "forge-v2")
        assert read_token(app.private, "forge-v2", store=app.store) == value
        with pytest.raises((ValueError, SafeError)):
            import_token(app.store, app.private, source, "forge-v2")
        assert source.read_text() == value
        assert app.link().outcome == Outcome.SUCCESS
        config = definition(server.origin)
        config["credential"] = {"name": "forge-v2", "revision": "v2"}
        rotated = app.call(
            "forge.connection.configure",
            operation_id="rotate",
            expected_version=1,
            connection=config,
        )
        assert rotated.outcome == Outcome.SUCCESS
        app.revision = rotated.data.reference
        server.token = value
        assert app.sync("rotated").outcome == Outcome.SUCCESS
        dest = app.private.credential_path("forge-v2")
        dest.unlink()
        dest.hardlink_to(source)
        with pytest.raises((ValueError, SafeError)):
            read_token(app.private, "forge-v2", store=app.store)
        dest.unlink()
        harden(source)


def test_replay_pair_reuse_versions_and_no_task_progression():
    with fixture() as (app, server):
        first = app.link()
        assert app.link().data == first.data
        assert app.link("same-pair").data.state == "already_linked"
        original = dict(
            operation_id="sync",
            expected_version=1,
            task_id="task-1",
            connection_revision=app.revision,
        )
        initial = app.call("forge.sync", **original)
        assert app.call("forge.sync", **original).data.state == "published"
        assert (
            app.call("forge.sync", **(original | {"expected_version": 2})).outcome
            != Outcome.SUCCESS
        )
        assert len(server.writes) == 1
        assert initial.data.version == 2
        with app.store.engine.connect() as tx:
            assert tx.exec_driver_sql("SELECT version FROM coordination_tasks").scalar() == 1
        assert app.sync("new-cycle").data.version == 3
        server.issue_state = "closed"
        assert app.sync("closed-issue").data.state == "unchanged"
        assert app.status().data.records[0]["last_observed"]["state"] == "closed"
        assert len(server.writes) == 1


@pytest.mark.parametrize("missing", ["forge.sync", "coordination.status"])
def test_current_authority_and_replay_revocation(missing):
    with fixture() as (app, server):
        assert app.link().outcome == Outcome.SUCCESS
        assert app.sync("sync").outcome == Outcome.SUCCESS
        with app.store.transaction() as tx:
            grants = json.loads(
                tx.execute(
                    __import__("sqlalchemy").text("SELECT grants FROM access_credentials")
                ).scalar()
            )
            grants = [g for g in grants if g["action"] != missing]
            execute(tx, "UPDATE access_credentials SET grants=:g", {"g": json.dumps(grants)})
        replay = app.call(
            "forge.sync",
            operation_id="sync",
            expected_version=1,
            task_id="task-1",
            connection_revision=app.revision,
        )
        assert replay.outcome == Outcome.REFUSED
        assert len(server.writes) == 1


@pytest.mark.parametrize(
    "change", ["pull_request", "wrong_id", "wrong_url", "unsupported_version"]
)
def test_remote_identity_refusals(change):
    with fixture() as (app, server):
        if change == "pull_request":
            server.issue_extra = {"pull_request": {}}
        elif change == "wrong_id":
            server.issue_extra = {"id": True}
        elif change == "wrong_url":
            server.issue_extra = {"html_url": "http://example.invalid/"}
        else:
            server.version = "28.2.0+other"
        assert app.link().outcome != Outcome.SUCCESS
        assert not server.writes


@pytest.mark.parametrize(
    "phase",
    [
        "admission_committed",
        "preflight_observed",
        "before_prepare_commit",
        "prepared_committed",
        "before_arm_commit",
        "armed_committed",
        "write_observed",
        "before_finalize_commit",
        "finalized_committed",
    ],
)
def test_durable_phase_faults_no_blind_retry(phase):
    with fixture() as (app, server):
        assert app.link().outcome == Outcome.SUCCESS

        def fault(at):
            if at == phase:
                raise RuntimeError("injected local phase failure")

        app.service.fault = fault
        first = app.sync("fault")
        app.service = ForgeService(app.store, app.private)
        count = len(server.writes)
        repeat = app.call(
            "forge.sync",
            operation_id="fault",
            expected_version=1,
            task_id="task-1",
            connection_revision=app.revision,
        )
        assert len(server.writes) == count
        if phase in {"armed_committed", "write_observed", "before_finalize_commit"}:
            assert first.outcome == Outcome.UNCERTAIN
            assert repeat.outcome == Outcome.UNCERTAIN
            reconciled = app.sync("reconcile")
            assert len(server.writes) == count
            assert reconciled.outcome == (
                Outcome.UNCERTAIN if phase == "armed_committed" else Outcome.SUCCESS
            )
        elif phase == "finalized_committed":
            assert repeat.outcome == Outcome.SUCCESS
        else:
            assert first.outcome != Outcome.SUCCESS
            assert count == 0


@pytest.mark.parametrize("mode", ["redirect", "compressed", "oversize", "slow", "stall"])
def test_transport_full_request_bounds_and_no_writes(mode):
    def smaller(config):
        config["limits"].update(
            request_seconds=0.15, cycle_seconds=2, finalization_seconds=0.1, response_bytes=1024
        )

    with fixture(smaller) as (app, server):
        server.mode = mode
        started = time.monotonic()
        result = app.link()
        assert result.outcome != Outcome.SUCCESS
        assert time.monotonic() - started < 2
        assert not server.writes
        assert len(server.routes) == 1


def test_delayed_create_zero_lookup_never_resends():
    def small(config):
        config["limits"]["request_seconds"] = 0.15

    with fixture(small) as (app, server):
        app.link()
        server.mode = "delayed"
        assert app.sync("slow-create").outcome == Outcome.UNCERTAIN
        assert app.sync("zero-matches").outcome == Outcome.UNCERTAIN
        assert not server.writes
        server.release.set()
        for _ in range(100):
            if server.writes:
                break
            time.sleep(0.01)
        server.mode = None
        assert app.sync("eventually-observed").outcome == Outcome.SUCCESS
        assert server.writes == [("POST", 1)]


def test_duplicate_markers_and_partial_absence_stay_held():
    with fixture() as (app, server):
        app.link()
        server.mode = "lost"
        app.sync("lost")
        server.mode = None
        duplicate = copy.deepcopy(server.comments[0])
        duplicate["id"] = 99
        server.comments.append(duplicate)
        assert app.sync("duplicate").outcome == Outcome.UNCERTAIN
        status = app.status()
        assert status.data.records[0]["pending_intent"]
        result = app.call(
            "forge.resolve",
            operation_id="cannot-clear",
            expected_version=status.data.version,
            task_id="task-1",
            conflict_id="invented",
            action="replace",
            rationale="Cannot force",
        )
        assert result.outcome != Outcome.SUCCESS
        assert len(server.writes) == 1


def test_two_real_cli_processes_only_one_write_and_busy_no_increment():
    with fixture() as (app, server):
        app.link()
        server.mode = "block"
        results = []
        thread = threading.Thread(
            target=lambda: results.append(
                app.cli(
                    "forge.sync",
                    operation_id="one",
                    expected_version=1,
                    task_id="task-1",
                    connection_revision=app.revision,
                )
            )
        )
        thread.start()
        assert server.started.wait(5)
        competing = app.cli(
            "forge.sync",
            operation_id="two",
            expected_version=1,
            task_id="task-1",
            connection_revision=app.revision,
        )
        assert competing.returncode == 1
        assert app.status().data.version == 2
        server.release.set()
        thread.join(10)
        assert not thread.is_alive() and results[0].returncode == 0
        assert server.writes == [("POST", 1)]


@pytest.mark.parametrize("change", ["task", "connection", "grant"])
def test_changes_before_arm_stop_dispatch(change):
    with fixture() as (app, server):
        app.link()

        def fault(phase):
            if phase == "prepared_committed":
                with app.store.transaction() as tx:
                    if change == "task":
                        execute(tx, "UPDATE coordination_tasks SET version=version+1")
                    elif change == "connection":
                        execute(tx, "UPDATE forge_connections SET version=version+1")
                    else:
                        execute(tx, "UPDATE access_credentials SET revoked=1")

        app.service.fault = fault
        assert app.sync("before-arm").outcome != Outcome.SUCCESS
        assert not server.writes


def test_history_failure_rolls_back_configuration_and_intent():
    with fixture() as (app, server):
        app.link()

        @event.listens_for(app.store.engine, "before_cursor_execute")
        def fail_history(conn, cursor, statement, parameters, context, many):
            if statement.startswith("INSERT INTO forge_history"):
                raise RuntimeError("audit unavailable")

        result = app.sync("audit-outage")
        assert result.outcome != Outcome.SUCCESS
        assert result.data.audit_status == "unavailable"
        assert not server.writes
        with app.store.engine.connect() as tx:
            assert tx.exec_driver_sql("SELECT version FROM forge_links").scalar() == 1


def test_schema_does_not_admit_claims_or_coercion():
    target = BusinessTarget(**TARGET)
    for inputs in ({"task_id": "task-1", "caller": "owner"}, {"task_id": True}):
        with pytest.raises((ValueError, SafeError)):
            validate(Operation.FORGE_STATUS, target, inputs)
    with fixture() as (app, server):
        result = app.call("forge.status", task_id="task-1", caller="owner")
        assert result.outcome == Outcome.INVALID
        assert not server.routes


@pytest.mark.parametrize("change", ["project", "expired", "revoked"])
def test_membership_and_current_credential_state(change):
    with fixture() as (app, server):
        if change == "project":
            wrong = TARGET | {"identity": "another-project"}
            result = app.service.invoke(
                "forge.status", wrong, {"task_id": "task-1"}, proof=app.proof
            )
        elif change == "expired":
            app.service.access.clock = lambda: time.time() + 4000
            result = app.link()
        else:
            with app.store.transaction() as tx:
                execute(
                    tx,
                    "UPDATE access_credentials SET revoked=1",
                )
            result = app.link()
        assert result.outcome == Outcome.REFUSED
        assert not server.routes


@pytest.mark.parametrize("budget", ["requests", "total_read", "pages"])
def test_shared_cycle_budgets_stop_publication(budget):
    def limits(config):
        if budget == "requests":
            config["limits"]["max_requests"] = 4
        elif budget == "total_read":
            config["limits"].update(response_bytes=1024, total_read_bytes=1024)
        else:
            config["limits"]["max_pages"] = 1

    with fixture(limits) as (app, server):
        assert app.link().outcome == Outcome.SUCCESS
        if budget == "total_read":
            server.issue_extra = {"body": "x" * 800}
            assert app.sync("bytes").outcome != Outcome.SUCCESS
            assert not server.writes
        elif budget == "requests":
            assert app.sync("request-budget").outcome == Outcome.UNAVAILABLE
            assert not server.writes
            assert app.status().data.records[0]["pending_intent"] is None
        else:
            # Exercise the shared page counter through the real adapter, not list mocks.
            import asyncio

            from mobiraeon.errors import SafeError
            from mobiraeon.forge_adapter import Gitea

            async def check():
                async with Gitea(
                    connection(definition(server.origin))
                    | {"limits": dict(definition(server.origin)["limits"], max_pages=1)},
                    server.token,
                ) as adapter:
                    await adapter.preflight(1)
                    await adapter.comments()
                    with pytest.raises(SafeError):
                        await adapter.comments()

            asyncio.run(check())


def test_changed_observation_needs_new_approval_and_one_intent_consumption():
    with fixture() as (app, server):
        app.link()
        app.sync("initial")
        server.comments[0]["body"] += "edit-1"
        app.sync("conflict-1")
        status = app.status()
        old_conflict = status.data.records[0]["conflict"]
        app.call(
            "forge.resolve",
            operation_id="approve-1",
            expected_version=status.data.version,
            task_id="task-1",
            conflict_id=old_conflict,
            action="refresh",
            rationale="Approved",
        )
        server.comments[0]["body"] += "edit-2"
        assert app.sync("changed-conflict").outcome != Outcome.SUCCESS
        status = app.status()
        assert status.data.records[0]["conflict"] != old_conflict
        app.call(
            "forge.resolve",
            operation_id="approve-2",
            expected_version=status.data.version,
            task_id="task-1",
            conflict_id=status.data.records[0]["conflict"],
            action="refresh",
            rationale="Approved new facts",
        )

        def fault(phase):
            if phase == "prepared_committed":
                raise RuntimeError("known unarmed interruption")

        app.service.fault = fault
        app.sync("consume-but-not-arm")
        app.service.fault = lambda _: None
        assert app.sync("no-second-use").outcome != Outcome.SUCCESS
        assert len(server.writes) == 1


def test_ambiguous_404_incomplete_list_does_not_authorize_replacement():
    with fixture() as (app, server):
        app.link()
        app.sync("create")
        server.comments.clear()
        server.list_count = 1
        assert app.sync("incomplete-absence").outcome != Outcome.SUCCESS
        assert app.status().data.records[0]["conflict"] is None
        assert len(server.writes) == 1


def test_delayed_update_old_body_cannot_authorize_resend():
    def small(config):
        config["limits"]["request_seconds"] = 0.15

    with fixture(small) as (app, server):
        app.link()
        app.sync("initial")
        app.progress()
        server.mode = "delayed"
        assert app.sync("delayed-update").outcome == Outcome.UNCERTAIN
        assert app.sync("old-body-read").outcome == Outcome.UNCERTAIN
        assert len(server.writes) == 1
        server.release.set()
        for _ in range(100):
            if len(server.writes) == 2:
                break
            time.sleep(0.01)
        server.mode = None
        assert app.sync("observe-new-body").outcome == Outcome.SUCCESS
        assert server.writes == [("POST", 1), ("PATCH", 1)]


@pytest.mark.parametrize(
    "phase", ["before_prepare_commit", "before_arm_commit", "before_finalize_commit"]
)
def test_actual_local_commit_then_ack_loss(monkeypatch, phase):
    from sqlalchemy.engine import Transaction

    with fixture() as (app, server):
        app.link()
        armed = False
        original = Transaction.commit

        def fault(at):
            nonlocal armed
            if at == phase:
                armed = True

        def commit(transaction):
            nonlocal armed
            original(transaction)
            if armed:
                armed = False
                raise RuntimeError("commit acknowledgement lost")

        app.service.fault = fault
        monkeypatch.setattr(Transaction, "commit", commit)
        result = app.sync("commit-loss")
        assert len(server.writes) == (1 if phase == "before_finalize_commit" else 0)
        if phase == "before_arm_commit":
            assert result.outcome == Outcome.UNCERTAIN
            assert app.sync("cannot-retry").outcome == Outcome.UNCERTAIN
        elif phase == "before_finalize_commit":
            assert result.outcome == Outcome.SUCCESS  # Exact committed receipt establishes it.
        else:
            assert result.outcome != Outcome.SUCCESS


def test_post_arm_revocation_retains_effect_without_task_disclosure():
    with fixture() as (app, server):
        app.link()

        def fault(phase):
            if phase == "armed_committed":
                with app.store.transaction() as tx:
                    execute(tx, "UPDATE access_credentials SET revoked=1")

        app.service.fault = fault
        result = app.sync("post-arm-revoked")
        assert result.outcome == Outcome.REFUSED and result.data is None
        assert server.writes == [("POST", 1)]
        with app.store.engine.connect() as tx:
            assert (
                tx.exec_driver_sql("SELECT state FROM forge_intent_state").scalar()
                == "confirmed"
            )
            assert tx.exec_driver_sql("SELECT version FROM coordination_tasks").scalar() == 1


def test_crash_releases_guard_but_retains_potentially_sent_intent():
    import subprocess
    import sys

    with fixture() as (app, server):
        app.link()
        server.mode = "delayed"
        request = app.directory / "crash-request.json"
        request.write_text(
            json.dumps(
                dict(
                    operation="forge.sync",
                    target=TARGET,
                    inputs=dict(
                        operation_id="crash",
                        expected_version=1,
                        task_id="task-1",
                        connection_revision=app.revision,
                    ),
                )
            )
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "mobiraeon",
                "--config",
                str(app.config),
                "--request-file",
                str(request),
                "forge",
            ],
            cwd=app.directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            assert server.started.wait(5)
            process.kill()
            process.communicate(timeout=5)
            assert app.sync("after-crash-zero").outcome == Outcome.UNCERTAIN
            server.release.set()
            for _ in range(100):
                if server.writes:
                    break
                time.sleep(0.01)
            server.mode = None
            assert app.sync("after-crash-observed").outcome == Outcome.SUCCESS
            assert server.writes == [("POST", 1)]
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)


def test_sql_evidence_and_pairing_protection_and_status_bounds():
    from mobiraeon.persistence import TransactionFailure

    with fixture() as (app, server):
        app.link()
        app.sync("initial")
        for statement in (
            "UPDATE forge_intents SET record='{}'",
            "DELETE FROM forge_history",
            "UPDATE forge_links SET issue='99'",
            "UPDATE forge_links SET comment='99'",
        ):
            with pytest.raises(TransactionFailure), app.store.transaction() as tx:
                execute(tx, statement)
        for index in range(22):
            assert app.sync("history-" + str(index)).outcome == Outcome.SUCCESS
        status = app.status()
        record = status.data.records[0]
        assert len(record["history"]) == 20 and record["history_has_more"]
        assert len(json.dumps(asdict(status.data)).encode()) <= 65536
        assert '"body":' not in json.dumps(asdict(status.data))


def test_external_pairing_unique_across_projects():
    from mobiraeon.forge_verification import TASK

    with fixture() as (app, server):
        assert app.link().outcome == Outcome.SUCCESS
        other = TARGET | {"identity": "project-2"}
        configured = app.service.invoke(
            "forge.connection.configure",
            other,
            dict(
                operation_id="other-config",
                expected_version=0,
                connection=definition(server.origin),
            ),
            proof=app.proof,
        )
        assert configured.outcome == Outcome.SUCCESS
        with app.store.engine.connect() as tx:
            work = json.loads(
                tx.exec_driver_sql(
                    "SELECT record FROM coordination_facts WHERE stage='supply'"
                ).scalar()
            )["inputs"]["work"]
        work["project"] = "project-2"
        supplied = app.coordinator.invoke(
            "coordination.supply",
            TASK | {"identity": "task-2"},
            dict(operation_id="supply-2", work=work),
            proof=app.proof,
        )
        assert supplied.outcome == Outcome.SUCCESS
        refused = app.service.invoke(
            "forge.link",
            other,
            dict(
                operation_id="duplicate-external",
                expected_version=0,
                task_id="task-2",
                connection_revision=configured.data.reference,
                issue_number=1,
            ),
            proof=app.proof,
        )
        assert refused.outcome != Outcome.SUCCESS
        with app.store.engine.connect() as tx:
            assert tx.exec_driver_sql("SELECT count(*) FROM forge_links").scalar() == 1
        assert not server.writes


def test_explicit_0004_upgrade_and_unchanged_migrations(tmp_path, monkeypatch):
    import shutil
    from importlib.resources import files

    from mobiraeon.errors import SafeError
    from mobiraeon.persistence import Store

    legacy = tmp_path / "migrations"
    shutil.copytree(str(files("mobiraeon.persistence").joinpath("migrations")), legacy)
    (legacy / "versions/0005_forge.py").unlink()
    store = Store((tmp_path / "old.db").absolute())
    original = Store._scripts
    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                Store, "_scripts", lambda self, migration_path=None: original(self, legacy)
            )
            assert store.initialize() == "0004"
        with store.transaction() as tx:
            execute(tx, "CREATE TABLE retained_fixture(value TEXT)")
            execute(tx, "INSERT INTO retained_fixture VALUES('retained')")
        with pytest.raises(SafeError):
            store.check()
        assert store.upgrade() == "0005"
        with store.engine.connect() as tx:
            assert (
                tx.exec_driver_sql("SELECT value FROM retained_fixture").scalar() == "retained"
            )
    finally:
        store.close()


def test_stale_generation_cannot_finalize_retained_intent():
    from uuid import uuid4

    from mobiraeon.forge import row
    from mobiraeon.forge_adapter import Comment
    from mobiraeon.persistence import TransactionFailure

    with fixture() as (app, server):
        app.link()

        def fault(phase):
            if phase == "armed_committed":
                raise RuntimeError("lost armed owner")

        app.service.fault = fault
        app.sync("old")
        with app.store.engine.connect() as tx:
            old_link = dict(row(tx, "forge_links", "task", "task-1"))
            pending = dict(app.service._pending(tx, old_link["id"]))
        app.service.fault = lambda _: None
        assert app.sync("new").outcome == Outcome.UNCERTAIN
        record = json.loads(pending["record"])
        with pytest.raises(TransactionFailure):
            app.service._confirm(
                pending["id"],
                record,
                Comment("1", "3", "2", record["body"]),
                old_link,
                app.service.access.caller(app.proof),
                BusinessTarget(**TARGET),
                {"task_id": "task-1", "operation_id": "old"},
                uuid4(),
                time.monotonic() + 1,
            )
        assert app.status().data.records[0]["pending_intent"]
        assert not server.writes


def test_scoped_signal_cancellation_is_coalesced_and_handlers_restored():
    import signal

    previous = signal.getsignal(signal.SIGINT)
    with fixture() as (app, server):
        app.link()

        def fault(phase):
            if phase == "armed_committed":
                signal.raise_signal(signal.SIGINT)
                signal.raise_signal(signal.SIGINT)

        app.service.fault = fault
        assert app.sync("signals").outcome == Outcome.UNCERTAIN
        assert signal.getsignal(signal.SIGINT) == previous
        assert app.status().data.records[0]["pending_intent"]
        assert len(server.writes) <= 1


@pytest.mark.parametrize("value", [b"x" * 4097, b"trailing ", b"two\nlines"])
def test_import_rejects_before_delivery_and_source_is_preserved(value):
    with fixture() as (app, server):
        source = app.directory / "malformed-source"
        durable_new(source, value)
        with pytest.raises(SafeError):
            import_token(app.store, app.private, source, "must-not-deliver")
        assert source.read_bytes() == value
        assert not app.private.credential_path("must-not-deliver").exists()
        assert not server.routes


@pytest.mark.parametrize("mode", ["write-oversize-error", "write-redirect", "write-malformed"])
def test_ambiguous_write_responses_hold_and_reconcile_without_resend(mode):
    def limit(config):
        config["limits"]["response_bytes"] = 2048

    with fixture(limit) as (app, server):
        app.link()
        server.mode = mode
        assert app.sync("ambiguous").outcome == Outcome.UNCERTAIN
        server.mode = None
        assert app.sync("reconcile").outcome == Outcome.SUCCESS
        assert server.writes == [("POST", 1)]


def test_http_cleanup_failure_retains_confirmed_publication(monkeypatch):
    import httpx2

    from mobiraeon.errors import Reason

    with fixture() as (app, server):
        app.link()
        original = httpx2.AsyncClient.aclose

        async def close_then_lose_ack(client):
            await original(client)
            raise RuntimeError("injected cleanup acknowledgement loss")

        monkeypatch.setattr(httpx2.AsyncClient, "aclose", close_then_lose_ack)
        result = app.sync("close-fault")
        assert result.outcome != Outcome.SUCCESS and result.reason == Reason.CLEANUP_FAILED
        assert server.writes == [("POST", 1)]
        status = app.status().data.records[0]
        assert status["pending_intent"] is None and status["last_confirmed_publication"]


def test_reader_checks_database_installation_binding():
    from uuid import uuid4

    with fixture() as (app, server):
        marker = app.private.directory / "installation.json"
        record = json.loads(marker.read_text())
        record["installation"] = uuid4().hex
        marker.write_text(json.dumps(record))
        with pytest.raises(SafeError):
            read_token(app.private, "forge-v1", store=app.store)
        assert not server.routes


def test_reader_rejects_a_different_store_binding():
    with fixture() as (app, server):
        original = app.store.path
        try:
            app.store.path = app.directory / "different.db"
            with pytest.raises(SafeError):
                read_token(app.private, "forge-v1", store=app.store)
        finally:
            app.store.path = original
        assert not server.routes


def test_recursive_parser_fault_is_cli_invalid_input(monkeypatch, capsys):
    from mobiraeon import forge_schema
    from mobiraeon.cli import main

    with fixture() as (app, server):
        request = app.directory / "parser-fault.json"
        request.write_text(
            json.dumps(
                dict(operation="forge.status", target=TARGET, inputs={"task_id": "task-1"})
            )
        )
        original = json.loads

        def recursive(value, *args, **kwargs):
            if kwargs.get("object_pairs_hook") is forge_schema.pairs:
                raise RecursionError("trusted parser fault injection")
            return original(value, *args, **kwargs)

        monkeypatch.setattr(forge_schema.json, "loads", recursive)
        assert main(["--config", str(app.config), "--request-file", str(request), "forge"]) == 2
        output = capsys.readouterr()
        assert original(output.out)["outcome"] == "invalid_input"
        assert not server.routes


def test_deeply_nested_request_is_invalid_without_transport():
    import subprocess
    import sys

    with fixture() as (app, server):
        request = app.directory / "deep.json"
        request.write_text(
            '{"operation":"forge.status","target":'
            + json.dumps(TARGET)
            + ',"inputs":{"task_id":'
            + "[" * 2000
            + "0"
            + "]" * 2000
            + "}}"
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mobiraeon",
                "--config",
                str(app.config),
                "--request-file",
                str(request),
                "forge",
            ],
            cwd=app.directory,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 2
        assert json.loads(result.stdout)["outcome"] == "invalid_input"
        assert not server.routes


def test_retained_edit_conflict_needs_approval_after_body_is_restored():
    with fixture() as (app, server):
        app.link()
        app.sync("initial")
        original = server.comments[0]["body"]
        server.comments[0]["body"] += "human edit"
        assert app.sync("detected-edit").outcome != Outcome.SUCCESS
        old_conflict = app.status().data.records[0]["conflict"]
        server.comments[0]["body"] = original
        app.progress()
        assert app.sync("restored-body").outcome != Outcome.SUCCESS
        assert len(server.writes) == 1
        status = app.status()
        assert status.data.records[0]["conflict"] != old_conflict
        approved = app.call(
            "forge.resolve",
            operation_id="approve-restored",
            expected_version=status.data.version,
            task_id="task-1",
            conflict_id=status.data.records[0]["conflict"],
            action="refresh",
            rationale="Approve current exact observation",
        )
        assert approved.outcome == Outcome.SUCCESS
        assert app.sync("approved").outcome == Outcome.SUCCESS
        assert len(server.writes) == 2


def test_all_six_operations_through_actual_cli_with_returned_references():
    with fixture() as (app, server):

        def cli(operation, **inputs):
            result = app.cli(operation, **inputs)
            assert result.returncode == 0, result.stdout
            return json.loads(result.stdout)["data"]

        config = definition(server.origin)
        config["limits"]["max_requests"] = 19
        configured = cli(
            "forge.connection.configure",
            operation_id="cli-configure",
            expected_version=1,
            connection=config,
        )
        read = cli("forge.connection.read")
        assert read["reference"] == configured["reference"]
        linked = cli(
            "forge.link",
            operation_id="cli-link",
            expected_version=0,
            task_id="task-1",
            connection_revision=read["reference"],
            issue_number=1,
        )
        assert linked["state"] == "linked"
        status = cli("forge.status", task_id="task-1")
        published = cli(
            "forge.sync",
            operation_id="cli-sync",
            expected_version=status["version"],
            task_id="task-1",
            connection_revision=read["reference"],
        )
        assert published["state"] == "published"
        server.comments[0]["body"] += "human edit"
        refused = app.cli(
            "forge.sync",
            operation_id="cli-detect",
            expected_version=published["version"],
            task_id="task-1",
            connection_revision=read["reference"],
        )
        assert refused.returncode == 1
        status = cli("forge.status", task_id="task-1")
        approved = cli(
            "forge.resolve",
            operation_id="cli-resolve",
            expected_version=status["version"],
            task_id="task-1",
            conflict_id=status["records"][0]["conflict"],
            action="refresh",
            rationale="Restore exact recorded projection",
        )
        assert approved["state"] == "approval_recorded"


def test_failed_admission_keeps_exact_request_identity_without_version_increment():
    with fixture() as (app, server):
        app.link()
        inputs = dict(
            operation_id="stale-request",
            expected_version=2,
            task_id="task-1",
            connection_revision=app.revision,
        )
        first = app.call("forge.sync", **inputs)
        assert first.outcome != Outcome.SUCCESS
        assert app.status().data.version == 1
        changed = app.call("forge.sync", **(inputs | {"expected_version": 1}))
        assert changed.outcome != Outcome.SUCCESS
        repeated = app.call("forge.sync", **inputs)
        assert repeated.reason == first.reason
        assert not server.writes and app.status().data.version == 1
        assert app.sync("fresh-request").outcome == Outcome.SUCCESS


@pytest.mark.parametrize("reconciliation", [False, True])
def test_absolute_cycle_deadline_includes_preflight_and_reconciliation(reconciliation):
    def limit(config):
        config["limits"].update(cycle_seconds=2, request_seconds=0.7, finalization_seconds=0.1)

    with fixture(limit) as (app, server):
        if reconciliation:
            app.link()
            server.mode = "lost"
            assert app.sync("lost").outcome == Outcome.UNCERTAIN
        server.mode = "cycle"
        started = time.monotonic()
        result = app.sync("cycle") if reconciliation else app.link()
        assert time.monotonic() - started < 2.7
        assert result.outcome != Outcome.SUCCESS
        assert len(server.writes) == int(reconciliation)
        if reconciliation:
            assert app.status().data.records[0]["pending_intent"]


@pytest.mark.parametrize(
    "origin,url,accepted",
    [
        ("https://example.invalid", "https://example.invalid/fixture/bridge/issues/1", True),
        (
            "https://example.invalid",
            "https://EXAMPLE.invalid:443/fixture/bridge/issues/1",
            True,
        ),
        ("http://localhost", "http://localhost/fixture/bridge/issues/1", True),
        ("http://[::1]", "http://[::1]/fixture/bridge/issues/1", True),
        ("https://example.invalid", "https://other.invalid/fixture/bridge/issues/1", False),
        (
            "https://example.invalid",
            "https://example.invalid:444/fixture/bridge/issues/1",
            False,
        ),
        ("https://example.invalid", "https://example.invalid/fixture/bridge/issues/2", False),
        ("https://example.invalid", "https://example.invalid/fixture/bridge/issues/1?", False),
        ("https://example.invalid", "https://example.invalid/fixture/bridge/issues/1#", False),
        ("https://example.invalid", " https://example.invalid/fixture/bridge/issues/1", False),
    ],
)
def test_canonical_comment_issue_url_identity(origin, url, accepted):
    from mobiraeon.forge_adapter import Gitea, Issue

    adapter = Gitea(connection(definition(origin)), secrets.token_urlsafe(32))
    adapter.issue = Issue("3", 1, "open")
    item = dict(id=1, user={"id": 2}, body="Fixture body", issue_url=url, pull_request_url=None)
    if accepted:
        assert adapter.normalize(item).issue == "3"
    else:
        with pytest.raises(SafeError):
            adapter.normalize(item)


def test_production_https_transport_custom_ca_and_untrusted_refusal(monkeypatch):
    import ipaddress
    import ssl
    from datetime import UTC, datetime, timedelta

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    with fixture() as (app, server):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
            .not_valid_after(datetime.now(UTC) + timedelta(hours=1))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .sign(key, hashes.SHA256())
        )
        ca_path, key_path = app.directory / "ca.pem", app.directory / "server.key"
        ca_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        harden(key_path)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(ca_path, key_path)
        server.server.socket = context.wrap_socket(server.server.socket, server_side=True)
        server.origin = server.origin.replace("http:", "https:")
        config = definition(server.origin)
        config["tls_ca_file"] = str(ca_path.absolute())
        configured = app.call(
            "forge.connection.configure",
            operation_id="tls-configure",
            expected_version=1,
            connection=config,
        )
        assert configured.outcome == Outcome.SUCCESS
        app.revision = configured.data.reference
        assert app.link().outcome == Outcome.SUCCESS
        assert app.sync("tls-create").outcome == Outcome.SUCCESS
        config["tls_ca_file"] = None
        configured = app.call(
            "forge.connection.configure",
            operation_id="remove-trust",
            expected_version=2,
            connection=config,
        )
        assert configured.outcome == Outcome.SUCCESS
        app.revision = configured.data.reference
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_path))
        assert app.sync("untrusted").outcome != Outcome.SUCCESS
        assert len(server.writes) == 1


def test_exact_failed_replay_preserves_unavailable_outcome(monkeypatch):
    from contextlib import contextmanager

    from mobiraeon.persistence import TransactionAcquisitionFailure

    with fixture() as (app, server):
        app.link()
        original = app.store.transaction
        first = True

        @contextmanager
        def unavailable_once(**kwargs):
            nonlocal first
            if first:
                first = False
                raise TransactionAcquisitionFailure()
            with original(**kwargs) as tx:
                yield tx

        monkeypatch.setattr(app.store, "transaction", unavailable_once)
        inputs = dict(
            operation_id="writer-unavailable",
            expected_version=1,
            task_id="task-1",
            connection_revision=app.revision,
        )
        original_result = app.call("forge.sync", **inputs)
        repeated = app.call("forge.sync", **inputs)
        assert original_result.outcome == repeated.outcome == Outcome.UNAVAILABLE
        assert original_result.reason == repeated.reason
        assert not server.writes and app.status().data.version == 1
        assert app.sync("new-after-writer").outcome == Outcome.SUCCESS


@pytest.mark.parametrize("revoke", [False, True], ids=["exact-replay", "current-authority"])
def test_configure_failed_replay_between_outer_read_and_writer(monkeypatch, revoke):
    with fixture() as (app, server):
        inputs = dict(
            operation_id="configure-writer-gap",
            expected_version=1,
            connection=definition(server.origin),
        )

        def business_records():
            with app.store.engine.connect() as tx:
                return {
                    table: tuple(tuple(r) for r in tx.exec_driver_sql(f"SELECT * FROM {table}"))
                    for table in (
                        "forge_connections",
                        "forge_revisions",
                        "forge_requests",
                        "forge_receipts",
                    )
                }

        before = business_records()
        other_store = Store(app.private.database, timeout=0.025)
        other = ForgeService(other_store, app.private)
        observed = {}
        original = app.service._configure

        def invoke_other(**values):
            return other.invoke("forge.connection.configure", TARGET, values, proof=app.proof)

        def writer_gap(*args):
            # _handle has closed its outer read and found no replay. A matching
            # request now fails real BEGIN IMMEDIATE, then records its attempt.
            with closing(sqlite3.connect(app.private.database)) as blocker:
                blocker.execute("BEGIN IMMEDIATE")
                busy = []

                def release_blocker(context):
                    busy.append(
                        (context.statement, context.original_exception.sqlite_errorcode)
                    )
                    blocker.rollback()  # Let the ordinary failed-attempt audit persist.

                event.listen(other_store.engine, "handle_error", release_blocker)
                try:
                    observed["original"] = invoke_other(**inputs)
                finally:
                    event.remove(other_store.engine, "handle_error", release_blocker)
                assert busy == [("BEGIN IMMEDIATE", sqlite3.SQLITE_BUSY)]
            observed["ordinary"] = invoke_other(**inputs)
            assert observed["original"].outcome == Outcome.UNAVAILABLE
            assert observed["original"].reason == Reason.STORAGE_FAILURE
            assert observed["ordinary"].outcome == observed["original"].outcome
            if revoke:
                monkeypatch.setattr(app.service.access, "permits", lambda *args: False)
            return original(*args)

        try:
            with monkeypatch.context() as scoped:
                scoped.setattr(app.service, "_configure", writer_gap)
                delayed = app.call("forge.connection.configure", **inputs)
            later = invoke_other(**inputs)
            changed = invoke_other(**(inputs | {"expected_version": 2}))
            after = business_records()
            with app.store.engine.connect() as tx:
                attempts = tx.exec_driver_sql(
                    "SELECT outcome,record FROM forge_history WHERE kind='attempt' "
                    "AND reference='configure-writer-gap' ORDER BY sequence"
                ).all()
        finally:
            other_store.close()

        assert before == after
        assert not server.routes and not server.writes
        assert later.outcome == observed["ordinary"].outcome == Outcome.UNAVAILABLE
        assert later.reason == observed["ordinary"].reason == Reason.STORAGE_FAILURE
        assert changed.outcome == Outcome.FAILURE and changed.reason == Reason.CONFLICT
        assert len(attempts) == 5
        expected = Outcome.REFUSED if revoke else Outcome.UNAVAILABLE
        reason = Reason.REFUSED if revoke else Reason.STORAGE_FAILURE
        assert delayed.outcome == expected
        assert delayed.reason == reason
        assert attempts[2][0] == expected.value
        assert json.loads(attempts[2][1])["reason"] == reason.value


def test_local_expected_version_is_not_a_native_forge_id():
    with fixture() as (app, server):
        result = app.call(
            "forge.connection.configure",
            operation_id="large-local-version",
            expected_version=2**80,
            connection=definition(server.origin),
        )
        assert result.outcome == Outcome.FAILURE
        assert not server.routes


@pytest.mark.parametrize(
    "case",
    [
        "recovery",
        "error_refused",
        "error_conflict",
        "atomic_original",
        "atomic_recovery",
        "atomic_history",
        "error_atomic_original",
        "error_atomic_recovery",
        "error_atomic_history",
        "lost_ack",
        "recover_without_project",
        "recover_without_task",
        "replay_without_project",
        "replay_without_task",
        "revoke_admission",
        "revoke_preflight",
        "fingerprint",
        "same_refused",
        "same_conflict",
        "existing_receipt",
        "incompatible_receipt",
        "approval",
        "armed",
    ],
)
def test_f7_r2_known_unarmed_receipts_real_death_disk_service(case):
    from mobiraeon.verification_final07_controls import forge_recovery_control

    report = forge_recovery_control(case)
    assert report["required_behavior"], report
