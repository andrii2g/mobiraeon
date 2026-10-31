"""Migrations run only through Store, on its locked, explicit transaction."""

from alembic import context

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    transactional_ddl=True,
    render_as_batch=True,
)
with context.begin_transaction():
    context.run_migrations()
