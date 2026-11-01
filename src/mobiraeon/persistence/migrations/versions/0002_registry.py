"""Registry/access ownership and retained publication/audit history."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "access_installation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("installation", sa.Text, nullable=False, unique=True),
        sa.Column("principal", sa.Text, nullable=False),
        sa.Column("actor", sa.Text, nullable=False, unique=True),
        sa.Column("self_review", sa.Boolean, nullable=False),
        sa.CheckConstraint("id = 1"),
    )
    op.create_table(
        "access_credentials",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column(
            "installation_id",
            sa.Integer,
            sa.ForeignKey("access_installation.id"),
            nullable=False,
        ),
        sa.Column("verifier", sa.Text, nullable=False),
        sa.Column("created", sa.Integer, nullable=False),
        sa.Column("expires", sa.Integer, nullable=False),
        sa.Column("revoked", sa.Integer),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("grants", sa.Text, nullable=False),
        sa.CheckConstraint("version > 0 AND expires > created"),
    )
    op.create_table(
        "registry_entities",
        sa.Column("kind", sa.Text, primary_key=True),
        sa.Column("identity", sa.Text, primary_key=True),
    )
    op.create_table(
        "registry_drafts",
        sa.Column("kind", sa.Text, primary_key=True),
        sa.Column("identity", sa.Text, primary_key=True),
        sa.Column("version", sa.Integer, primary_key=True),
        sa.Column("document", sa.Text, nullable=False),
        sa.Column("digest", sa.Text, nullable=False),
        sa.Column("author", sa.Text, nullable=False),
        sa.Column("discarded", sa.Boolean, nullable=False),
        sa.ForeignKeyConstraint(
            ["kind", "identity"], ["registry_entities.kind", "registry_entities.identity"]
        ),
        sa.CheckConstraint("version > 0"),
    )
    op.create_table(
        "registry_reviews",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("identity", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("digest", sa.Text, nullable=False),
        sa.Column("reviewer", sa.Text, nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.ForeignKeyConstraint(
            ["kind", "identity", "version"],
            ["registry_drafts.kind", "registry_drafts.identity", "registry_drafts.version"],
        ),
    )
    op.create_table(
        "registry_publications",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("identity", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("review", sa.Text, sa.ForeignKey("registry_reviews.id"), nullable=False),
        sa.Column("document", sa.Text, nullable=False),
        sa.Column("digest", sa.Text, nullable=False),
        sa.UniqueConstraint("kind", "identity", "version"),
        sa.ForeignKeyConstraint(
            ["kind", "identity", "version"],
            ["registry_drafts.kind", "registry_drafts.identity", "registry_drafts.version"],
        ),
    )
    op.create_table(
        "registry_dependencies",
        sa.Column(
            "publication", sa.Text, sa.ForeignKey("registry_publications.id"), primary_key=True
        ),
        sa.Column(
            "dependency", sa.Text, sa.ForeignKey("registry_publications.id"), primary_key=True
        ),
    )
    op.create_table(
        "registry_controls",
        sa.Column("kind", sa.Text, primary_key=True),
        sa.Column("identity", sa.Text, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("selected", sa.Text, sa.ForeignKey("registry_publications.id")),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.CheckConstraint("version > 0 AND kind = 'agent'"),
        sa.ForeignKeyConstraint(
            ["kind", "identity"], ["registry_entities.kind", "registry_entities.identity"]
        ),
    )
    op.create_table(
        "registry_audit",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invocation", sa.Text, nullable=False),
        sa.Column("operation", sa.Text),
        sa.Column("actor", sa.Text),
        sa.Column("target", sa.Text),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("record", sa.Text, nullable=False),
        sa.Column("at", sa.Integer, nullable=False),
    )
    op.create_index("ix_registry_audit_invocation", "registry_audit", ["invocation"])
    for table in (
        "registry_drafts",
        "registry_reviews",
        "registry_publications",
        "registry_dependencies",
        "registry_audit",
        "registry_entities",
    ):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'retained history is immutable'); END"
            )
    op.execute(
        "CREATE TRIGGER access_installation_no_delete BEFORE DELETE ON access_installation "
        "BEGIN SELECT RAISE(ABORT, 'bootstrap remains closed'); END"
    )
    op.execute(
        "CREATE TRIGGER access_installation_no_update BEFORE UPDATE ON access_installation "
        "BEGIN SELECT RAISE(ABORT, 'owner identity is immutable'); END"
    )


def downgrade():
    raise RuntimeError("automatic downgrade is unsupported")
