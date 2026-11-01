import json
import os

from conftest import revision

from mobiraeon import cli
from mobiraeon.persistence import Store


def test_real_host_refuses_pending_and_failed_upgrade_reports_resulting_version(
    store, migrations, monkeypatch, capsys
):
    # Packaged migration-source fixture injected behind the real storage boundary;
    # no production migration-path switch or deployed fixture handlers.
    original = Store._scripts
    monkeypatch.setattr(
        Store, "_scripts", lambda self, migration_path=None: original(self, migrations)
    )
    monkeypatch.setattr(
        os, "environ", {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    )
    revision(
        migrations,
        "0003",
        "0002",
        """    op.create_table(
        "retained_fixture", sa.Column("value", sa.Text()))
    op.execute("INSERT INTO retained_fixture VALUES ('retained')")""",
    )
    args = ["--database", str(store.path)]
    assert cli.main([*args, "start"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out)["reason"] == "upgrade_required"
    assert "foundation_ready" not in output.out + output.err
    assert cli.main([*args, "upgrade"]) == 0
    capsys.readouterr()
    revision(
        migrations,
        "0004",
        "0003",
        """    op.create_table(
        "rolled_back_fixture", sa.Column("value", sa.Text()))
    op.execute("UPDATE retained_fixture SET value='SENSITIVE_MUTATION'")
    raise RuntimeError("SENSITIVE_MIGRATION_EXCEPTION")""",
    )
    assert cli.main([*args, "upgrade"]) == 1
    output = capsys.readouterr()
    assert "SENSITIVE" not in output.out + output.err
    result = json.loads(output.out)
    assert result["reason"] == "migration_failed"
    assert result["schema_revision"] == "0003"
    assert "foundation_ready" not in output.out + output.err
    with store.engine.connect() as connection:
        assert (
            connection.exec_driver_sql("SELECT value FROM retained_fixture").scalar()
            == "retained"
        )
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM sqlite_master WHERE name='rolled_back_fixture'"
            ).scalar()
            == 0
        )
    assert cli.main([*args, "start"]) == 1
    output = capsys.readouterr()
    assert "foundation_ready" not in output.out + output.err


def test_migration_commit_ack_failure_preserves_uncertainty(
    store, migrations, monkeypatch, capsys
):
    from sqlalchemy.engine import Transaction

    original_scripts = Store._scripts
    monkeypatch.setattr(
        Store, "_scripts", lambda self, migration_path=None: original_scripts(self, migrations)
    )
    original_commit = Transaction.commit

    def commit_then_fail(transaction):
        original_commit(transaction)
        raise RuntimeError("SENSITIVE_COMMIT_ACK")

    revision(migrations, "0003", "0002", "    pass")
    monkeypatch.setattr(Transaction, "commit", commit_then_fail)
    assert cli.main(["--database", str(store.path), "upgrade"]) == 1
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result["outcome"] == "uncertain_effects"
    assert result["reason"] == "effects_uncertain"
    assert result["schema_revision"] == "0003"
    assert "SENSITIVE" not in output.out + output.err
