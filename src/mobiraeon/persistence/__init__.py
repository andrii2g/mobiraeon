"""SQLite ownership-neutral infrastructure; no domain records or module commits."""

import logging
import os
import sqlite3
import warnings
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import NullPool

from mobiraeon.errors import Reason, SafeError

STORE_ID = "mobiraeon-foundation-v1"


class TransactionFailure(Exception):
    def __init__(self, *, rolled_back, reason=None):
        self.rolled_back = rolled_back
        self.reason = reason
        super().__init__("transaction failed")


class TransactionAcquisitionFailure(Exception):
    """The participant was never entered, so requested effects have not started."""


class Transaction:
    """Participants receive execute access, never commit/rollback ownership.

    This is an internal trusted-code boundary, not a sandbox for hostile Python.
    Module-specific repositories retain ownership of SQL and records.
    """

    def __init__(self, connection):
        self._connection = connection

    def execute(self, statement, parameters=None):
        return self._connection.execute(statement, parameters or {})


class Store:
    def __init__(self, path: Path, timeout=5.0):
        self.path = path
        # SQLAlchemy's pool error paths may log raw driver exception text even
        # with echo disabled. Isolate this application's engine/pool loggers.
        for name in (
            "sqlalchemy.engine.Engine.mobiraeon",
            "sqlalchemy.pool.impl.NullPool.mobiraeon",
        ):
            logging.getLogger(name).disabled = True
        self.engine = create_engine(
            "sqlite://",
            creator=self._connect,
            poolclass=NullPool,
            echo=False,
            hide_parameters=True,
            logging_name="mobiraeon",
            pool_logging_name="mobiraeon",
        )
        self.timeout = timeout

        @event.listens_for(self.engine, "begin")
        def begin(connection):
            # Explicit SQL BEGIN makes DDL transactional, unlike sqlite3 legacy mode.
            mode = " IMMEDIATE" if connection.info.get("write") else ""
            connection.exec_driver_sql("BEGIN" + mode)

    def _connect(self):
        # URI constructed by us, never supplied by a caller. mode=rw cannot create.
        connection = sqlite3.connect(
            self.path.as_uri() + "?mode=rw",
            uri=True,
            timeout=self.timeout,
            isolation_level=None,
        )
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            if connection.execute("PRAGMA foreign_keys").fetchone() != (1,):
                raise SafeError(Reason.STORAGE_FAILURE)
            if connection.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                raise SafeError(Reason.STORE_INVALID)
        except BaseException:
            connection.close()
            raise
        return connection

    def close(self):
        self.engine.dispose()

    @contextmanager
    def transaction(self):
        """Known failure only when body failed and rollback was verified.

        A commit exception is uncertain even if a subsequent rollback succeeds.
        No automatic replay is performed.
        """
        connection = None
        try:
            connection = self.engine.connect()
            connection.info["write"] = True
            transaction = connection.begin()
            driver = connection.connection.driver_connection
        except Exception:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass  # No participant ran; cleanup cannot introduce its effects.
            raise TransactionAcquisitionFailure from None

        with connection:
            # SQLite parses transaction-control SQL for us, including comments and
            # alternate spellings. Participants cannot end or replace this transaction.
            # The guard is removed before application-owned commit/rollback.
            def authorize(action, arg1, arg2, database, trigger):
                if action in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            driver.set_authorizer(authorize)
            try:
                try:
                    yield Transaction(connection)
                finally:
                    driver.set_authorizer(None)
            except Exception as error:
                if not driver.in_transaction:
                    raise TransactionFailure(rolled_back=False) from None
                try:
                    transaction.rollback()
                    if driver.in_transaction:
                        raise RuntimeError("rollback not established")
                except Exception:
                    raise TransactionFailure(rolled_back=False) from None
                raise TransactionFailure(
                    rolled_back=True,
                    reason=error.reason if isinstance(error, SafeError) else None,
                ) from None
            else:
                if not driver.in_transaction:
                    raise TransactionFailure(rolled_back=False)
                try:
                    transaction.commit()
                    if driver.in_transaction:
                        raise RuntimeError("commit not established")
                except Exception:
                    raise TransactionFailure(rolled_back=False) from None

    @contextmanager
    def _scripts(self, migration_path=None):
        resource = files("mobiraeon.persistence").joinpath("migrations")
        with as_file(resource) as packaged:
            try:
                config = Config()
                # ConfigParser interpolation requires escaping literal percent signs.
                config.set_main_option(
                    "script_location", str(migration_path or packaged).replace("%", "%%")
                )
                with warnings.catch_warnings():
                    warnings.simplefilter("error")
                    scripts = ScriptDirectory.from_config(config)
                    revisions = list(scripts.walk_revisions())
                if (
                    not revisions
                    or len(scripts.get_heads()) != 1
                    or len(scripts.get_bases()) != 1
                ):
                    raise ValueError("nonlinear migrations")
                for revision in revisions:
                    if revision.dependencies or isinstance(revision.down_revision, tuple):
                        raise ValueError("nonlinear migrations")
                base = revisions[-1]
                if base.revision != "0001" or base.down_revision is not None:
                    raise ValueError("missing application base")
            except Exception:
                raise SafeError(Reason.MIGRATION_CHAIN) from None
            yield config, scripts, [r.revision for r in reversed(revisions)]

    def _revision(self, connection, chain):
        try:
            identity = connection.execute(
                text("SELECT identity FROM foundation_identity")
            ).all()
            if identity != [(STORE_ID,)]:
                raise SafeError(Reason.STORE_INVALID)
            heads = MigrationContext.configure(connection).get_current_heads()
        except SafeError:
            raise
        except Exception:
            raise SafeError(Reason.STORE_INVALID) from None
        if len(heads) != 1 or heads[0] not in chain:
            raise SafeError(Reason.STORE_REVISION)
        return heads[0]

    def check(self, *, migration_path=None):
        if not self.path.is_file():
            raise SafeError(Reason.STORE_MISSING)
        with self._scripts(migration_path) as (_, _, chain):
            try:
                with self.engine.connect() as connection:
                    revision = self._revision(connection, chain)
                    if revision != chain[-1]:
                        raise SafeError(Reason.UPGRADE_REQUIRED)
                    return revision
            except SafeError:
                raise
            except Exception:
                raise SafeError(Reason.STORAGE_FAILURE) from None

    def initialize(self):
        # Exclusive file creation prevents adopting empty or unrecognized existing files.
        with self._scripts():
            pass
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return self.check()
        except OSError:
            raise SafeError(Reason.STORAGE_FAILURE) from None
        os.close(descriptor)
        return self.upgrade(_new=True)

    def upgrade(self, *, migration_path=None, _new=False):
        if not self.path.is_file():
            raise SafeError(Reason.STORE_MISSING)
        with self._scripts(migration_path) as (config, _, chain):
            while True:
                try:
                    with self.engine.connect() as connection:
                        connection.info["write"] = True
                        # Acquire the writer lock BEFORE reading version/identity.
                        # Recheck after every committed revision; competing upgrade
                        # processes cannot apply the same revision twice.
                        transaction = connection.begin()
                        try:
                            if _new:
                                tables = connection.exec_driver_sql(
                                    "SELECT name FROM sqlite_master WHERE type='table'"
                                ).all()
                                if tables:
                                    raise SafeError(Reason.STORE_INVALID)
                                current = None
                            else:
                                current = self._revision(connection, chain)
                            if current == chain[-1]:
                                transaction.rollback()
                                return current
                            next_revision = (
                                chain[0] if current is None else chain[chain.index(current) + 1]
                            )
                            config.attributes["connection"] = connection
                            command.upgrade(config, next_revision)
                        except Exception as error:
                            try:
                                transaction.rollback()
                            except Exception:
                                raise SafeError(Reason.UNCERTAIN) from None
                            if isinstance(error, SafeError):
                                raise
                            raise SafeError(Reason.MIGRATION_FAILED) from None
                        try:
                            transaction.commit()
                        except Exception:
                            raise SafeError(Reason.UNCERTAIN) from None
                        _new = False
                except SafeError:
                    raise
                except Exception:
                    raise SafeError(Reason.MIGRATION_FAILED) from None

    def recorded_revision(self):
        """Best-effort safe metadata, including after a failed upgrade."""
        try:
            with self._scripts() as (_, _, chain), self.engine.connect() as connection:
                return self._revision(connection, chain)
        except Exception:
            return None
