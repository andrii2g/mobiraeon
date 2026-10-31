#!/usr/bin/env bash
# The official PostgreSQL entrypoint runs/sources this only on an empty PGDATA.
# The file may be sourced; isolate shell options from the image entrypoint.
(
set -euo pipefail

: "${POSTGRES_USER:?PostgreSQL bootstrap user is required}"
: "${GITEA_DB_PASSWORD:?Gitea database password is required}"

# Read the password from the environment inside psql, not from command arguments.
# psql's quoted interpolation escapes the value as an SQL string literal.
psql --no-psqlrc --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 <<'SQL'
\getenv gitea_password GITEA_DB_PASSWORD
CREATE ROLE gitea WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD :'gitea_password';
CREATE DATABASE gitea OWNER gitea;
REVOKE ALL ON DATABASE gitea FROM PUBLIC;
\connect gitea
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
)
