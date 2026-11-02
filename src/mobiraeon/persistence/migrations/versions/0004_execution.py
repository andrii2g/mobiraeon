"""Fixture execution ownership and retained effects; accepted migrations unchanged."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "execution_runs",
        sa.Column("task", sa.Text, sa.ForeignKey("coordination_tasks.id"), primary_key=True),
        sa.Column("attempt", sa.Text, nullable=False, unique=True),
        sa.Column("handoff", sa.Text, nullable=False),
        sa.Column("generation", sa.Integer, nullable=False),
        sa.Column("held", sa.Boolean, nullable=False),
        sa.Column("record", sa.Text, nullable=False),
    )
    op.create_table(
        "execution_events",
        sa.Column("sequence", sa.Integer, primary_key=True),
        sa.Column("task", sa.Text, sa.ForeignKey("execution_runs.task"), nullable=False),
        sa.Column("record", sa.Text, nullable=False),
    )
    op.create_table(
        "execution_receipts",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("task", sa.Text, sa.ForeignKey("execution_runs.task"), nullable=False),
        sa.Column("fingerprint", sa.Text, nullable=False),
    )
    for table in ("execution_events", "execution_receipts"):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'retained execution evidence'); END"
            )
    op.execute(
        "CREATE TRIGGER execution_handoff_immutable BEFORE UPDATE OF handoff,attempt,task "
        "ON execution_runs BEGIN SELECT RAISE(ABORT, 'immutable handoff'); END"
    )
    op.execute(
        "CREATE TRIGGER execution_no_delete BEFORE DELETE ON execution_runs "
        "BEGIN SELECT RAISE(ABORT, 'retained execution'); END"
    )


def downgrade():
    raise RuntimeError("automatic downgrade is unsupported")
