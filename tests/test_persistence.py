import sqlite3
import subprocess
import sys
import time
from contextlib import closing

import pytest
from conftest import revision
from sqlalchemy import text

from mobiraeon.errors import Reason, SafeError
from mobiraeon.persistence import Store, TransactionFailure


def scalar(store, sql):
    with store.engine.connect() as connection:
        return connection.exec_driver_sql(sql).scalar()


def test_initialize_repeat_open_missing_and_preserve_restart(store, tmp_path):
    assert store.initialize() == "0002"
    with store.transaction() as tx:
        tx.execute(text("CREATE TABLE fixture (value TEXT)"))
        tx.execute(text("INSERT INTO fixture VALUES ('retained')"))
    path = store.path
    store.close()
    reopened = Store(path)
    assert reopened.check() == "0002"
    assert scalar(reopened, "SELECT value FROM fixture") == "retained"
    reopened.close()
    absent = Store(tmp_path / "missing.db")
    with pytest.raises(SafeError) as error:
        absent.check()
    assert error.value.reason == Reason.STORE_MISSING
    assert not absent.path.exists()


@pytest.mark.parametrize("data", [b"", b"not a database", None])
def test_unrecognized_store_not_adopted(tmp_path, data):
    path = tmp_path / "unrecognized"
    if data is None:
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE unrelated(value)")
            connection.commit()
    else:
        path.write_bytes(data)
    before = path.read_bytes()
    store = Store(path)
    with pytest.raises(SafeError):
        store.initialize()
    with pytest.raises(SafeError):
        store.upgrade()
    assert path.read_bytes() == before
    store.close()


@pytest.mark.parametrize("unknown", ["future-9999", "unknown", ""])
def test_unknown_newer_revision_never_changes_store(store, unknown):
    with store.transaction() as tx:
        tx.execute(
            text("UPDATE alembic_version SET version_num=:version"), {"version": unknown}
        )
    before = store.path.read_bytes()
    with pytest.raises(SafeError) as error:
        store.upgrade()
    assert error.value.reason == Reason.STORE_REVISION
    assert store.path.read_bytes() == before


def test_supported_batch_upgrade_and_per_migration_failure(store, migrations):
    revision(
        migrations,
        "0003",
        "0002",
        """    op.create_table("fixture", sa.Column("value", sa.Text()))
    op.execute("INSERT INTO fixture VALUES ('preserved')")""",
    )
    revision(
        migrations,
        "0004",
        "0003",
        """    with op.batch_alter_table("fixture", recreate="always") as batch:
        batch.add_column(sa.Column("extra", sa.Text(), server_default="new"))""",
    )
    assert store.upgrade(migration_path=migrations) == "0004"
    assert scalar(store, "SELECT value FROM fixture") == "preserved"
    assert scalar(store, "SELECT extra FROM fixture") == "new"
    revision(
        migrations,
        "0005",
        "0004",
        """    op.create_table("should_rollback", sa.Column("value", sa.Text()))
    op.execute("UPDATE fixture SET value='corrupted'")
    raise RuntimeError("SENSITIVE_MIGRATION_ERROR")""",
    )
    with pytest.raises(SafeError) as error:
        store.upgrade(migration_path=migrations)
    assert error.value.reason == Reason.MIGRATION_FAILED
    assert scalar(store, "SELECT version_num FROM alembic_version") == "0004"
    assert scalar(store, "SELECT value FROM fixture") == "preserved"
    assert scalar(store, "SELECT count(*) FROM sqlite_master WHERE name='should_rollback'") == 0
    assert (
        scalar(store, "SELECT count(*) FROM sqlite_master WHERE name LIKE '_alembic_tmp%'") == 0
    )
    with pytest.raises(SafeError):
        store.check(migration_path=migrations)


@pytest.mark.parametrize("fault", ["missing_base", "missing_parent", "heads", "duplicate"])
def test_invalid_packaged_chain_fails_before_changes(store, migrations, fault):
    if fault == "missing_base":
        (migrations / "versions" / "0001_identity.py").unlink()
    elif fault == "missing_parent":
        revision(migrations, "0004", "0003", "    pass")
    elif fault == "heads":
        revision(migrations, "0003", "0002", "    pass")
        revision(migrations, "0004", "0002", "    pass")
    else:
        revision(migrations, "0002", None, "    pass")
    before = store.path.read_bytes()
    with pytest.raises(SafeError) as error:
        store.upgrade(migration_path=migrations)
    assert error.value.reason == Reason.MIGRATION_CHAIN
    assert store.path.read_bytes() == before


def test_foreign_keys_every_connection_rollback_and_bounded_lock(store):
    for _ in range(2):
        assert scalar(store, "PRAGMA foreign_keys") == 1
        assert scalar(store, "PRAGMA journal_mode") == "delete"
    with store.transaction() as tx:
        tx.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        tx.execute(text("CREATE TABLE child (id INTEGER REFERENCES parent(id))"))
    with pytest.raises(TransactionFailure) as error, store.transaction() as tx:
        tx.execute(text("INSERT INTO child VALUES (12)"))
    assert error.value.rolled_back
    assert scalar(store, "SELECT count(*) FROM child") == 0
    with closing(sqlite3.connect(store.path)) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        start = time.monotonic()
        with pytest.raises(SafeError):
            store.upgrade()
        assert 0.05 < time.monotonic() - start < 2
        blocker.rollback()
    assert store.check() == "0002"


def test_requires_explicit_upgrade(store, migrations):
    revision(migrations, "0003", "0002", "    pass")
    with pytest.raises(SafeError) as error:
        store.check(migration_path=migrations)
    assert error.value.reason == Reason.UPGRADE_REQUIRED
    assert scalar(store, "SELECT version_num FROM alembic_version") == "0002"


def test_prior_migration_commits_survive_later_failure_in_one_upgrade(store, migrations):
    revision(
        migrations,
        "0003",
        "0002",
        """    op.create_table(
        "prior_fixture", sa.Column("value", sa.Text()))
    op.execute("INSERT INTO prior_fixture VALUES ('retained')")""",
    )
    revision(
        migrations,
        "0004",
        "0003",
        """    op.execute("DELETE FROM prior_fixture")
    raise RuntimeError("SENSITIVE_FAILURE")""",
    )
    with pytest.raises(SafeError):
        store.upgrade(migration_path=migrations)
    assert scalar(store, "SELECT version_num FROM alembic_version") == "0003"
    assert scalar(store, "SELECT value FROM prior_fixture") == "retained"


def test_concurrent_upgrade_steps_serialize_and_recheck_revision(store, migrations):
    revision(
        migrations,
        "0003",
        "0002",
        """    import time
    time.sleep(0.15)
    op.create_table("once_fixture", sa.Column("value", sa.Text()))
    op.execute("INSERT INTO once_fixture VALUES ('once')")""",
    )
    script = """
import sys
from pathlib import Path
from mobiraeon.persistence import Store
store = Store(Path(sys.argv[1]), timeout=5)
try:
    print(store.upgrade(migration_path=Path(sys.argv[2])))
finally:
    store.close()
"""
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(store.path), str(migrations)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    for process in processes:
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stderr
        assert stdout.strip() == "0003"
    assert scalar(store, "SELECT count(*) FROM once_fixture") == 1
