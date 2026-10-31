# Gitea infrastructure

**Status:** Configuration complete for final review and commit; first startup and restore validation remain pending in WSL. This configuration provides Gitea and its PostgreSQL database on Docker Engine in Linux under WSL. It does not start Möbiræon Coordination, Workers, or Gitea Actions.

The [Compose file](../infra/gitea/compose.yaml) and [environment example](../infra/gitea/.env.example) live in `infra/gitea/`. Use `docker compose` (Compose v2) from that directory for all commands below, except where another directory is explicitly specified. Keep the real, ignored `.env` alongside `compose.yaml`.

```text
infra/
  gitea/
    compose.yaml
    .env.example
    postgres/init/10-create-gitea.sh
    .env          # local only, ignored
    backups/      # local only, ignored
```

## Scope and configuration

| Item | Configuration |
| --- | --- |
| Gitea | `docker.gitea.com/gitea:28.2.0-rootless`, non-root container user, built-in SSH |
| PostgreSQL | `docker.io/library/postgres:18.6-trixie`, dedicated to Gitea |
| Web and Git over HTTP | `http://localhost:3000/`, bound to WSL loopback by default |
| Git over SSH | `ssh://git@localhost:2222/OWNER/REPOSITORY.git` |
| Database access | Internal Docker network only; no published database port |
| Database identities | `postgres` administrator; separate `gitea` application role owning the `gitea` database |
| Persistence | Docker named volumes for PostgreSQL, Gitea data, and Gitea configuration |
| Accounts | Self-registration disabled; sign-in required to view content; new repositories private by default |
| Optional services | Mail and Actions disabled; no runner, proxy, or webhook receiver |

The fixed Compose project name `mobiraeon` keeps resource names stable across checkout locations. Volumes are `mobiraeon_postgres-data`, `mobiraeon_gitea-data`, and `mobiraeon_gitea-config`. Do not run a second checkout under this same project name against the same Docker daemon. A separate test installation must use `docker compose -p ANOTHER_NAME ...` consistently.

Gitea uses PostgreSQL for its own records. Möbiræon's future authoritative coordination storage remains SQLite under [D-11](decisions.md#d-11-implementation-technology-and-topology). Gitea issues represent Initiatives and substantive Tasks; milestones represent delivery targets under [D-07](decisions.md#d-07-forge-integration-and-initial-platform). Labels and issue closure do not independently establish internal acceptance.

Release tags are pinned, but image digests have not yet been recorded. Record the pulled digests and Linux/WSL, Docker, and Compose versions during deployment qualification. The rootless Gitea image runs as a non-root user; this does not imply that the Docker daemon itself is rootless.

### Release and image selection

Checked on **2026-10-31**: [Gitea 28.2.0](https://github.com/go-gitea/gitea/releases/tag/v28.2.0) and [PostgreSQL 18.6](https://www.postgresql.org/docs/release/) are the latest stable releases. PostgreSQL 19 is still a release candidate and is not selected. The [official PostgreSQL image list](https://hub.docker.com/_/postgres) publishes `18.6-trixie`. Pin explicit versions and review updates rather than using a moving `latest` tag.

The official Gitea rootless image is already a Linux image: its [release Dockerfile](https://github.com/go-gitea/gitea/blob/v28.2.0/Dockerfile.rootless) uses Alpine Linux 3.24, includes Git, certificates, curl and SSH key tools, and runs as UID/GID 1000. Docker containers share the WSL Linux kernel; Gitea's Alpine userspace and PostgreSQL's Debian userspace do not need to match the WSL distribution. The official package supplies the startup and configuration handling used by this Compose file. A custom Debian/Ubuntu image would require maintaining dependencies, binary verification, user permissions, signal handling, initialization, and update builds. Keep the official image unless a concrete dependency or organizational requirement justifies a custom build. Do not install or upgrade Gitea interactively inside a running container; replace the pinned image through a reviewed update.

PostgreSQL 18 stores data at `/var/lib/postgresql/18/docker`; its volume must mount at `/var/lib/postgresql`. This configuration is for a **new installation**. If the earlier PostgreSQL 17 configuration has already been run, stop and plan a database migration before using this revision. Reusing its old volume with PostgreSQL 18 is not a supported upgrade.

## Prepare the WSL checkout

Install Docker Engine and the Compose v2 plugin in the chosen WSL distribution. Ensure the Docker daemon is running and your Linux user can access it. Keep the checkout in the WSL Linux filesystem, such as `~/projects/mobiraeon`, rather than `/mnt/c`. Named volumes belong to the selected Docker daemon, not to the checkout; choose one daemon consistently if Docker Desktop is also installed.

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/andrii2g/mobiraeon.git
cd mobiraeon
git pull --ff-only
docker version
docker compose version
cd infra/gitea
cp .env.example .env
chmod 600 .env
openssl rand -hex 32  # POSTGRES_ADMIN_PASSWORD
openssl rand -hex 32  # GITEA_DB_PASSWORD; use a different value
```

For an existing checkout, run `git pull --ff-only` from the repository root, then `cd infra/gitea`. Alternatively, select both files explicitly when operating from the repository root:

```bash
docker compose --env-file infra/gitea/.env -f infra/gitea/compose.yaml config --quiet
docker compose --env-file infra/gitea/.env -f infra/gitea/compose.yaml up -d
```

The remaining operational commands assume the current directory is `infra/gitea/`.

Paste the two distinct generated passwords into `POSTGRES_ADMIN_PASSWORD` and `GITEA_DB_PASSWORD` in `.env` using a local editor. The empty example deliberately fails Compose validation until both are supplied. The administrator password goes only to PostgreSQL; Gitea receives only the application password. Do not commit either password, administrator credentials, access tokens, or generated Gitea configuration. Passwords are supplied to container environments; the application password is also written into Gitea's persistent configuration. Docker administrators can access them. Protect the WSL account, Docker access, and backups accordingly.

Keep the default loopback binding for the first installation. If port 3000 is occupied, change both `GITEA_HTTP_PORT` and the port in `GITEA_ROOT_URL`. If port 2222 is occupied, change `GITEA_SSH_PORT`; the internal SSH listener remains 2222.

## First startup

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=100 gitea postgres
```

`config --quiet` validates without printing the resolved environment. Avoid sharing plain `docker compose config` or container inspection output because it can contain the password. PostgreSQL readiness gates Gitea startup. Gitea may remain unhealthy until its installation is completed. Health checks report status; they do not automatically restart an unhealthy running process.

Open `http://localhost:3000/` in Windows or WSL. Windows normally forwards localhost access to WSL; if unavailable, first verify access inside WSL with `curl -I http://127.0.0.1:3000/` and check WSL localhost networking settings. Do not broaden the bind address just to bypass this check.

Complete Gitea's installation page:

1. Verify PostgreSQL, host `postgres:5432`, database/user `gitea`, and the password from `.env`. Leave database TLS disabled for this local internal network.
2. Verify web base URL `http://localhost:3000/`, SSH domain `localhost`, and advertised SSH port `2222` (or your configured replacements). Keep the rootless image's prefilled storage paths.
3. Expand the administrator account section and create the initial human administrator with a separate strong password. Do this during installation because ordinary registration is disabled.
4. Finish installation and sign in. Confirm installation is locked: `/install` must no longer offer the setup form. Gitea stores `INSTALL_LOCK` and generated secrets in `/etc/gitea/app.ini` on the configuration volume; do not force `INSTALL_LOCK=false` on subsequent starts.

Compose environment settings are reapplied on container startup. Change managed settings in `.env` or the Compose file rather than relying on conflicting manual `app.ini` edits. After environment changes, run `docker compose up -d` to recreate affected containers.

### Database initialization and credentials

On an empty PostgreSQL volume, the image first creates administrator `postgres` with `POSTGRES_ADMIN_PASSWORD`. The read-only [initialization script](../infra/gitea/postgres/init/10-create-gitea.sh) then creates login role `gitea` with `GITEA_DB_PASSWORD` and database `gitea` owned by that role. The application role has no superuser, database-creation, role-creation, replication, or row-security-bypass privileges. Database ownership permits Gitea to manage its schema and apply migrations. Public access to the Gitea database and public schema creation are revoked. PostgreSQL remains dedicated to Gitea; this does not claim that the application role cannot connect to PostgreSQL's default maintenance databases.

The script runs only on the first initialization of an empty data directory. It does not change users or passwords in existing volumes, and it deliberately fails on SQL errors. TCP readiness avoids declaring the socket-only initialization server healthy before initialization finishes. Git enforces LF line endings for the script; do not convert it to CRLF or remove its bind-mounted source file.

If initial database creation fails, inspect PostgreSQL logs before proceeding. The image can leave a partially initialized volume and does not automatically rerun initialization scripts on restart. Recover or rebuild that new, unused installation deliberately; do not delete volumes holding useful data. An earlier installation in which `gitea` was the bootstrap superuser requires a separate role/ownership migration; these files do not silently alter it.

Changing either password in `.env` does not rotate an existing database role password. Coordinate the appropriate `ALTER ROLE`/interactive `psql` password change with the environment update while Gitea is stopped. Keep the two credentials separate, then recreate affected containers. Restore the saved `.env` together with the matching database backup.

## Verification before relying on the instance

Record observations and exact revisions when running these checks; none has yet been live-validated by this change.

- Confirm both services become healthy and `curl --fail http://localhost:3000/api/healthz` succeeds.
- Verify the Gitea login and role privileges using the commands below. The role flags must all be `f`, with database owner `gitea`.
- Create a private test repository, push and clone over HTTP using an appropriate access token, then repeat over SSH with an uploaded public key. Verify the advertised clone URLs and SSH host key fingerprint. Avoid embedding tokens in remote URLs or shell history.
- Create an issue, label, milestone, comment, branch, pull request, and review. Confirm an ordinary user cannot access administrator functions or unassigned private repositories.
- Run `docker compose down`, then `docker compose up -d`. Confirm repositories, accounts, issues, and milestones survive container recreation. **Do not add `--volumes` or `-v`: that deletes persistent data.**
- Perform the backup and isolated restore below and repeat login, clone, and issue checks on the restored instance.

```bash
docker compose exec postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
  -c "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname = 'gitea';" \
  -c "SELECT datname, pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname = 'gitea';"
docker compose exec postgres bash -c \
  'PGPASSWORD="$GITEA_DB_PASSWORD" psql -h 127.0.0.1 -U gitea -d gitea -v ON_ERROR_STOP=1 -c "SELECT current_user, current_database();"'
```

## Routine operation and upgrades

```bash
docker compose ps
docker compose logs --tail=100 gitea postgres
docker compose stop
docker compose start
```

`unless-stopped` restarts services when Docker restarts unless they were deliberately stopped. WSL and the Docker daemon must themselves be running; this setup does not configure Windows boot or unattended WSL startup. Logs rotate at approximately three 10 MB files per service. Watch disk usage and keep backup copies outside the WSL virtual disk.

For upgrades, take and verify a backup first, review upstream release notes, update the pinned image tag deliberately along with the image references in these backup/restore instructions, then pull and recreate the affected service. Re-run the verification checks. Gitea can migrate its database during startup; rollback may require restoring the complete backup with the previous images. Never switch a rootless installation to a rootful image in place. PostgreSQL major upgrades require a planned migration, not merely a tag change.

## Backup and isolated restore

This initial procedure uses downtime and cold volume archives, including PostgreSQL's physical data directory. Restore with the same image versions and compatible CPU architecture. It is not a cross-version database migration procedure.

Run in Bash from `infra/gitea/` in the WSL checkout. Backups are created in its ignored `backups/` subdirectory. Stop all writes and archive all three volumes together:

```bash
(
set -eu
umask 077
backup_dir="$PWD/backups/$(date -u +%Y%m%dT%H%M%SZ)"
# Check every source first: Docker otherwise creates a missing named volume.
for volume in postgres-data gitea-data gitea-config; do
  docker volume inspect "mobiraeon_${volume}" >/dev/null
done
mkdir -p -m 700 "$PWD/backups"
mkdir -m 700 "$backup_dir"
docker compose stop gitea postgres
docker compose ps --all
if [ -n "$(docker compose ps --status running -q)" ]; then
  echo 'Backup aborted: services are still running.' >&2
  exit 1
fi
cp .env compose.yaml "$backup_dir/"
cp -R postgres "$backup_dir/"
git rev-parse HEAD > "$backup_dir/source-revision.txt"
docker image inspect --format '{{json .RepoDigests}}' \
  docker.gitea.com/gitea:28.2.0-rootless \
  docker.io/library/postgres:18.6-trixie > "$backup_dir/image-digests.txt"
for volume in postgres-data gitea-data gitea-config; do
  docker run --rm --user 0:0 --entrypoint /bin/sh \
    -v "mobiraeon_${volume}:/source:ro" \
    -v "$backup_dir:/backup" \
    docker.gitea.com/gitea:28.2.0-rootless \
    -c 'tar -czpf "/backup/$1.tgz" -C /source .' sh "$volume"
  tar -tzf "$backup_dir/$volume.tgz" >/dev/null
done
echo "Backup verified: $backup_dir"
)
```

The subshell stops on an error and does not print the success message for a partial backup. If it fails, resolve the error and treat that backup directory as incomplete. Services remain stopped after the archive attempt; restart them explicitly with `docker compose start` when safe. Copy a completed backup to a protected destination outside this WSL disk. Archives and `.env` contain credentials and private repository data; encrypt off-host copies. These backup commands assume the default project name. Archive readability does not replace the isolated restore drill.

For a restore drill, use a separate directory and a **new, unused** project name so the live volumes are untouched. Copy the saved `compose.yaml`, `.env`, and entire `postgres/` initialization directory into that directory, preserving the relative layout. The bind-mounted initialization file must exist even though it will not run against the restored database. Restrict `.env` to mode 600 and change its web port/base URL and SSH port to unused values (for example, 3100 and 2322). Keep loopback binding. Change into the restore directory, set `backup_dir` to the absolute directory containing the saved archives, then:

```bash
(
set -eu
: "${backup_dir:?Set backup_dir to the absolute backup directory}"
for volume in postgres-data gitea-data gitea-config; do
  tar -tzf "$backup_dir/$volume.tgz" >/dev/null
  if docker volume inspect "mobiraeon-restore_${volume}" >/dev/null 2>&1; then
    echo "Restore aborted: mobiraeon-restore_${volume} already exists." >&2
    exit 1
  fi
done
docker compose -p mobiraeon-restore config --quiet
docker compose -p mobiraeon-restore create
for volume in postgres-data gitea-data gitea-config; do
  docker run --rm --user 0:0 --entrypoint /bin/sh \
    -v "mobiraeon-restore_${volume}:/target" \
    -v "$backup_dir:/backup:ro" \
    docker.gitea.com/gitea:28.2.0-rootless \
    -c 'set -eu; test -z "$(ls -A /target)"; tar -xzpf "/backup/$1.tgz" -C /target' sh "$volume"
done
docker compose -p mobiraeon-restore up -d
)
```

The drill rejects existing target volumes and starts services only after all extractions succeed. A failed drill can leave partially restored volumes: investigate them and use a fresh project name consistently for the next attempt. Verify health, administrator login, repository history/clone, issues, milestones, and attachments. Record the restoration time and results. Stop the drill with `docker compose -p mobiraeon-restore down`; retain its volumes until the result is accepted.

## Next integration steps

Create an organization, a dedicated Agent Registry repository, and a demonstration repository. Add a separate automation account with access only to managed repositories, scoped API tokens, and branch protections. Qualify issue/comment/milestone/pull-request operations against this installed Gitea version before connecting the Coordinator. Initial observation uses polling under the agreed [architecture](architecture.md#coordination-and-agent-reasoning).

`localhost` is a deliberate bootstrap address: inside a Worker container it refers to that Worker, not Gitea. Before container integration, select a canonical hostname reachable from Windows, WSL, and Workers; configure resolution, `GITEA_DOMAIN`, `GITEA_ROOT_URL`, and the published binding together. Services on the `mobiraeon_forge` network can reach `gitea:3000` internally, but advertised clone URLs also need to be reachable. Workers should not join the database network. Review TLS and access restrictions before exposing HTTP beyond the local machine; this Compose file supplies neither a reverse proxy nor certificates.

GitHub remains the source used to obtain this infrastructure checkout for now. This change does not migrate the existing repository or change its remotes.

## References

- [Gitea rootless Docker installation](https://docs.gitea.com/installation/install-with-docker-rootless/)
- [Gitea Docker configuration and PostgreSQL setup](https://docs.gitea.com/installation/install-with-docker/)
- [Gitea configuration reference](https://docs.gitea.com/administration/config-cheat-sheet/)
- [Gitea backup and restore](https://docs.gitea.com/administration/backup-and-restore/)
- [PostgreSQL official image and volume layout](https://hub.docker.com/_/postgres)
