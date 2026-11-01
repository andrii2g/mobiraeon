"""Bounded Coordination records, receipts and history; prior migrations unchanged."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "coordination_tasks",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("state", sa.Text, nullable=False),
        sa.CheckConstraint("version > 0"),
    )
    op.create_table(
        "coordination_facts",
        sa.Column("task", sa.Text, sa.ForeignKey("coordination_tasks.id"), primary_key=True),
        sa.Column("stage", sa.Text, primary_key=True),
        sa.Column("identity", sa.Text, nullable=False, unique=True),
        sa.Column("record", sa.Text, nullable=False),
    )
    op.create_table(
        "coordination_receipts",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("task", sa.Text, sa.ForeignKey("coordination_tasks.id"), nullable=False),
        sa.Column("fingerprint", sa.Text, nullable=False),
        sa.Column("record", sa.Text, nullable=False),
    )
    op.create_table(
        "coordination_history",
        sa.Column("sequence", sa.Integer, primary_key=True),
        sa.Column("task", sa.Text, nullable=False),
        sa.Column("invocation", sa.Text, nullable=False),
        sa.Column("actor", sa.Text),
        sa.Column("operation", sa.Text, nullable=False),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("record", sa.Text, nullable=False),
    )
    for table in ("coordination_facts", "coordination_receipts", "coordination_history"):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'coordination evidence is immutable'); END"
            )


def downgrade():
    raise RuntimeError("automatic downgrade is unsupported")
