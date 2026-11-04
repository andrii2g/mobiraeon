"""Registry Project connections and Coordination forge bridge evidence."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    statements = [
        """CREATE TABLE forge_connections (
            project TEXT PRIMARY KEY, id TEXT NOT NULL UNIQUE,
            version INTEGER NOT NULL CHECK(version>0),
            revision TEXT NOT NULL REFERENCES forge_revisions(id)
                DEFERRABLE INITIALLY DEFERRED)""",
        """CREATE TABLE forge_revisions (
            id TEXT PRIMARY KEY, connection TEXT NOT NULL REFERENCES forge_connections(id),
            version INTEGER NOT NULL CHECK(version>0), definition TEXT NOT NULL,
            sha256 TEXT NOT NULL, actor TEXT NOT NULL, request TEXT NOT NULL,
            UNIQUE(connection,version))""",
        """CREATE TABLE forge_links (
            id TEXT PRIMARY KEY, task TEXT NOT NULL UNIQUE REFERENCES coordination_tasks(id),
            project TEXT NOT NULL REFERENCES forge_connections(project),
            connection TEXT NOT NULL REFERENCES forge_connections(id),
            revision TEXT NOT NULL REFERENCES forge_revisions(id),
            provider TEXT NOT NULL, origin TEXT NOT NULL, repository TEXT NOT NULL,
            account TEXT NOT NULL, issue TEXT NOT NULL, issue_number INTEGER NOT NULL,
            version INTEGER NOT NULL CHECK(version>0),
            generation TEXT REFERENCES forge_cycles(id),
            comment TEXT, observation TEXT, publication TEXT, conflict TEXT, approval TEXT,
            UNIQUE(provider,origin,repository,issue))""",
        """CREATE TABLE forge_requests (
            id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, project TEXT NOT NULL,
            task TEXT, actor TEXT NOT NULL, operation TEXT NOT NULL)""",
        """CREATE TABLE forge_receipts (
            id TEXT PRIMARY KEY REFERENCES forge_requests(id), result TEXT NOT NULL)""",
        """CREATE TABLE forge_cycles (
            id TEXT PRIMARY KEY, link TEXT NOT NULL REFERENCES forge_links(id),
            request TEXT NOT NULL UNIQUE REFERENCES forge_requests(id),
            version INTEGER NOT NULL CHECK(version>0), record TEXT NOT NULL)""",
        """CREATE TABLE forge_intents (
            id TEXT PRIMARY KEY, link TEXT NOT NULL REFERENCES forge_links(id),
            cycle TEXT NOT NULL REFERENCES forge_cycles(id), record TEXT NOT NULL)""",
        """CREATE TABLE forge_intent_state (
            id TEXT PRIMARY KEY REFERENCES forge_intents(id),
            link TEXT NOT NULL REFERENCES forge_links(id), generation TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN
             ('prepared','armed','uncertain','confirmed','not_attempted','rejected')))""",
        """CREATE UNIQUE INDEX forge_one_pending ON forge_intent_state(link)
            WHERE state IN ('prepared','armed','uncertain')""",
        """CREATE TABLE forge_conflicts (
            id TEXT PRIMARY KEY, link TEXT NOT NULL REFERENCES forge_links(id),
            version INTEGER NOT NULL CHECK(version>0), record TEXT NOT NULL)""",
        """CREATE TABLE forge_approvals (
            id TEXT PRIMARY KEY, conflict TEXT NOT NULL REFERENCES forge_conflicts(id),
            link TEXT NOT NULL REFERENCES forge_links(id),
            version INTEGER NOT NULL CHECK(version>0), record TEXT NOT NULL)""",
        """CREATE TABLE forge_consumptions (
            approval TEXT PRIMARY KEY REFERENCES forge_approvals(id),
            intent TEXT NOT NULL UNIQUE REFERENCES forge_intents(id))""",
        """CREATE TABLE forge_history (
            sequence INTEGER PRIMARY KEY, at TEXT NOT NULL, project TEXT NOT NULL,
            link TEXT, invocation TEXT NOT NULL, actor TEXT, kind TEXT NOT NULL,
            reference TEXT, outcome TEXT NOT NULL, record TEXT NOT NULL)""",
    ]
    # The head/revision cycle is inserted with deferred foreign keys in one transaction.
    for statement in statements:
        op.execute(statement)
    for table in (
        "forge_revisions",
        "forge_requests",
        "forge_receipts",
        "forge_cycles",
        "forge_intents",
        "forge_conflicts",
        "forge_approvals",
        "forge_consumptions",
        "forge_history",
    ):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'forge evidence is immutable'); END"
            )
    op.execute("""CREATE TRIGGER forge_pairing_immutable BEFORE UPDATE OF
        id,task,project,connection,provider,origin,repository,account,issue,issue_number
        ON forge_links BEGIN SELECT RAISE(ABORT, 'forge pairing is immutable'); END""")
    op.execute("""CREATE TRIGGER forge_comment_binding BEFORE UPDATE OF comment ON forge_links
        WHEN NEW.comment IS NOT OLD.comment AND NOT EXISTS (
          SELECT 1 FROM forge_intents i JOIN forge_intent_state s ON s.id=i.id
          WHERE i.link=OLD.id AND s.state='confirmed'
            AND i.id=json_extract(NEW.publication,'$.intent')
            AND json_extract(i.record,'$.method')='POST'
            AND (OLD.comment IS NULL OR json_extract(i.record,'$.approval') IS NOT NULL))
        BEGIN SELECT RAISE(ABORT, 'forge comment replacement requires confirmation'); END""")
    op.execute("""CREATE TRIGGER forge_intent_transition
        BEFORE UPDATE OF state ON forge_intent_state
        WHEN NOT (NEW.state=OLD.state
          OR (OLD.state='prepared' AND NEW.state IN ('armed','not_attempted'))
          OR (OLD.state IN ('armed','uncertain')
              AND NEW.state IN ('uncertain','confirmed','rejected')))
        BEGIN SELECT RAISE(ABORT, 'forge intent transition is invalid'); END""")
    for table in ("forge_connections", "forge_links", "forge_intent_state"):
        op.execute(
            f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'forge records are retained'); END"
        )


def downgrade():
    raise RuntimeError("automatic downgrade is unsupported")
