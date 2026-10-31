"""Application store identity. Applied revisions are immutable release artifacts."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "foundation_identity",
        sa.Column("identity", sa.String(64), primary_key=True),
        sa.CheckConstraint("identity = 'mobiraeon-foundation-v1'"),
    )
    op.bulk_insert(table, [{"identity": "mobiraeon-foundation-v1"}])


def downgrade():
    raise RuntimeError("automatic downgrade is unsupported")
