# MÃ¶birÃ¦on

**MÃ¶birÃ¦on** is inspired by **MÃ¶bius**, representing continuity and interconnected workflows, and **Ã¦on**, a word of Greek origin evoking vast spans of time. The name reflects a continuous cycle of planning, building, verifying, and improving software through coordinated AI agents. The **Ã¶** and **Ã¦** preserve these references visually, while the repository uses the ASCII spelling `mobiraeon`.

MÃ¶birÃ¦on is a platform for orchestrating and automating software development lifecycle activities through coordinated AI agents. It turns human intent into specifications, bounded assignments, and software changes assessed against explicit acceptance criteria.

## Purpose

MÃ¶birÃ¦on reduces repeated human coordination while preserving control over product intent, delivery quality, and resource use. Specialized agents perform assigned work, resolve questions within their authority, and continue when required inputs or decisions become available.

The human owner supplies the initial brief, participates in clarification and early review, and resolves decisions outside the agents' authority. Human participation and agent autonomy follow the governing project policy.

## Product goals

- Coordinate multiple specialized agents working toward a shared project or change.
- Configure agent responsibilities, AI providers, models, reasoning settings, tools, and execution limits.
- Produce research, specifications, architecture descriptions, data contracts, implementation, tests, and supporting documentation.
- Organize bounded work, dependencies, milestones where useful, progress, and acceptance evidence.
- Support parallel work when prerequisites and shared boundaries permit it.
- Resolve answerable questions within delegated authority and route unresolved decisions through the orchestrator.
- Resume eligible work without repeated human prompting.
- Preserve continuity across waiting periods, interruptions, and subsequent requests.

## Supported work

The product scope covers:

- New projects.
- Features in existing projects.
- Bug fixes.
- Refactoring.
- Investigations and research.
- Documentation changes.

Each request type has activities and acceptance criteria appropriate to its intended outcome. Each release specifies the capabilities and request types it supports.

## Engineering coverage

MÃ¶birÃ¦on coordinates work across:

- **Data and persistence:** database architecture, schemas, migrations, Redis structures, and data access contracts.
- **Domain:** constants, enumerations, models, DTOs, abstractions, and shared contracts.
- **Business logic:** data management, business rules, use cases, and application workflows.
- **Workers and integrations:** polling, consumers, network services, and background processing.
- **Presentation:** web, Blazor, mobile, desktop, console, and other user interfaces.

These areas define engineering coverage. Their execution order follows the dependencies and acceptance criteria of the work.

## Delivery boundaries and authority

The governing request and project policy define the delivery boundary and the evidence required for acceptance.

Production deployment, destructive changes to live data, and operation of delivered applications are controlled by their applicable authorization and acceptance policies. Authorization is established through the relevant policy or an explicit decision by the designated authority.

Only the orchestrator creates requests requiring human decisions or intervention. Agents submit unresolved questions for resolution within the system, and independent work continues while affected assignments wait for an answer.

## Documentation

See the [documentation index](docs/README.md) for requirements, architecture, workflow, and decisions.

The [implementation plan](docs/implementation-plan.md) records the accepted foundation and Agent Registry increments, their verification limits, and the next Coordination increment.

## Application foundation (Increment 1)

Increment 1 is accepted for the independently reviewed foundation scope recorded in
the [implementation plan](docs/implementation-plan.md#increment-1-shared-contracts-and-application-foundation).

The foundation provides shared contracts, a foreground local host, validated application
configuration, controlled internal operations, and SQLite/Alembic persistence. The
[accepted Registry increment](#agent-registry-increment-2) adds authenticated Registry
operations and HTTP administration. Coordination workflows, Agent execution, scheduling,
and forge integration remain unavailable; foundation readiness does not establish their
qualification or acceptance.

Use CPython **3.14.10** and **uv 0.13.6**. `.python-version` pins the interpreter;
`pyproject.toml` pins `uv_build` and separates runtime dependencies from development
tools. `uv.lock` records the resolved dependencies. Install uv using its
[official installation instructions](https://docs.astral.sh/uv/getting-started/installation/),
then run from the repository root:

```text
uv python install 3.14.10
uv sync --locked
uv run --locked mobiraeon --help
uv run --locked python -m mobiraeon --version
```

Create the parent directory yourself, then explicitly initialize a new store. These
commands work in PowerShell and Linux shells (`mkdir var` is needed only once):

```text
mkdir var
uv run --locked mobiraeon --database var/mobiraeon.sqlite3 initialize
uv run --locked mobiraeon --database var/mobiraeon.sqlite3 check
uv run --locked mobiraeon --database var/mobiraeon.sqlite3 start
```

`start` runs in the foreground. Ctrl+C requests shutdown and releases resources;
SIGTERM on Linux and Ctrl+Break on Windows use the same stop path. There is no
remote status or stop command. `check` checks this invocation's installation,
configuration and store; it cannot inspect a different process. `--help` and
`--version` need neither configuration nor storage. Put options before the command.

After deliberately installing a release with new migrations, stop the host and run:

```text
uv run --locked mobiraeon --database var/mobiraeon.sqlite3 upgrade
uv run --locked mobiraeon --database var/mobiraeon.sqlite3 check
uv run --locked mobiraeon --database var/mobiraeon.sqlite3 start
```

Startup and checks never initialize or upgrade storage. Repeated initialization of a
recognized current store is safe; an existing empty, unrecognized, or incompatible
file is never adopted or replaced. Missing parent directories fail. An interrupted
or failed first initialization may leave an unrecognized file: inspect it and recover
explicitly rather than expecting automatic reset. Unknown/newer revisions and broken
packaged migration chains block changes. Downgrades are unsupported.

### Configuration

Settings resolve once per invocation: defaults â†’ explicitly selected TOML file â†’
recognized environment settings â†’ explicitly supplied CLI options. Restart applies
changes. No files are discovered automatically, and no `.env`, interpolation, or
includes are loaded. Agent Profiles are separate Registry data.

Create an optional `app.toml` (example; choose a suitable path):

```toml
[database]
path = "var/mobiraeon.sqlite3"
timeout_seconds = 5.0

[logging]
level = "INFO"
```

```text
uv run --locked mobiraeon --config app.toml check
uv run --locked mobiraeon --config app.toml start
```

| Setting | Environment | CLI | Rules |
| --- | --- | --- | --- |
| Config selector | `MOBIRAEON_CONFIG` | `--config` | Optional; CLI selects the file when both exist. |
| Database path | `MOBIRAEON_DATABASE_PATH` | `--database` | Required; no default, memory database, URL, or SQLite URI. |
| Lock wait | `MOBIRAEON_DATABASE_TIMEOUT_SECONDS` | `--database-timeout-seconds` | Default 5 seconds; positive finite number â‰¤60, excluding booleans. TOML requires a number. |
| Log level | `MOBIRAEON_LOG_LEVEL` | `--log-level` | DEBUG, INFO, WARNING, ERROR, CRITICAL; case normalized; default INFO. |

File-relative database paths resolve against the selected file's directory;
environment/CLI paths resolve against the invocation directory. Unknown TOML keys,
unknown `MOBIRAEON_*` names, and invalid values fail, including values later
overridden. Unrelated environment settings are ignored. Only the effective database
location is opened, and validation/startup do not create directories or a database.

Results are JSON on stdout; allowlisted UTC JSON events are on stderr. Readiness
and terminal errors remain observable at CRITICAL. Status excludes configuration
values and paths; diagnostics omit raw arguments, unknown names, environment values,
SQL parameters, and exception text even at DEBUG. Exit codes: 0 success, 2 invalid
CLI/configuration, 1 storage/operation/startup failure or uncertain effects. After a
failed upgrade the result includes the recognized resulting schema revision when it
can be established; inspect uncertain effects before retrying.

Ordinary commands emit one `phase: "terminal"` result after cleanup. The foreground
host first emits `phase: "ready"`, then emits its terminal result after stopping and
cleanup, using the same invocation ID. Readiness is an intermediate observation;
consumers must check the terminal result and process exit status. Cleanup runs once;
a cleanup failure returns exit code 1 with `cleanup_failed`, no raw exception text,
and no successful terminal completion. The host uses bounded waits so pending native
interruption handlers can run on Windows as well as Linux.

### Storage and authorization boundaries

SQLite uses the rollback (`delete`) journal, verified foreign keys on every connection,
and bounded lock waiting. SQLAlchemy Core emits explicit `BEGIN` for reads and
`BEGIN IMMEDIATE` for writes/migrations, making DDL and its Alembic revision update
transactional. Each migration commits separately; writer locking and revision checks
under that lock serialize competing migration steps. Earlier committed revisions
survive a later failure. Packaged migrations form one reviewed linear chain; applied
revisions remain immutable, and corrections use new forward revisions. Missing
required scripts and conflicting heads block upgrades. API versions, published
configuration revisions, and database schema versions identify different changes.
Run upgrades before normal operation. Connections use
existing-file-only opening and `NullPool`; transactions close their connections and
shutdown disposes the engine. WAL conversion, runtime migration checksums, production
backup/recovery qualification, and automatic retries are outside this increment.

Registry and Coordination own their operations and future records. Internal
participants receive a shared transaction handle without commit/rollback methods;
the application coordinates commit. SQLite's authorizer denies participant transaction
and savepoint-control SQL; finalization also checks the driver's transaction state.
Lost ownership cannot establish successful commit or verified rollback. A failed
connection/writer-lock acquisition reports unavailable with known no requested effects;
an ambiguous commit acknowledgement remains uncertain. This is a trusted module contract, not
isolation against hostile Python code. No transaction spans a model, forge, process,
or human wait, including the foreground host's idle wait.

Local commands trust the OS user's access to the process and database and identify
that boundary as `local-os-operator`, without claiming a verified personal username.
They grant only initialization, upgrade, local checks, and foreground startup.
They grant no Agent administration or workflow authority. Later authenticated
adapters must supply trusted caller/policy context to the same operation boundary;
request fields and Role labels cannot confer it. Both authorization checks require
the literal boolean `True`; malformed policy results are non-grants. Test-only handlers demonstrate
module mutations and current restrictions; none are deployed as commands. Operation
success, evidence, Run completion, independent assessment, and acceptance remain
separate. Invocation UUIDs correlate handling and do not make retries safe.

### Application operation contract

Entry adapters supply trusted caller context. The shared boundary validates a known
operation code, target and input, checks current permission/restrictions, and invokes
an explicitly bound owning operation. Inputs cannot select arbitrary methods.
Mutation success follows the required successful commit. Exact historical content
references remain distinct from current permission to use that content.

| Outcome | Meaning |
| --- | --- |
| Success | The implemented operation completed with its stated effects. |
| Invalid input | Validation failed before execution, including an unknown operation code. |
| Refused | Current permission or restrictions prohibit the operation. |
| Unavailable | A known capability is unimplemented or unavailable before requested effects begin. |
| Known failure | Failure and its effect boundary are established, such as verified rollback. |
| Uncertain effects | Effects cannot be established; neither success, rollback, nor automatic retry is inferred. |

Results carry a boundary-generated invocation ID, a recognized operation code when
known, an outcome/reason, and applicable evidence references. Actor context and
target references are included only when established; unavailable attribution is
explicit rather than copied from caller assertions. Invalid raw operation names
and other sensitive input stay out of results and diagnostics. These operation
results cannot themselves establish Run completion or acceptance.

### Verification and independent assessment

```text
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
uv run --locked python tools/verify_wheel.py
```

The wheel check exports runtime constraints from the unchanged lock, creates a clean
temporary environment beneath a `100%valid` installation path, installs the built wheel,
removes `PYTHONPATH`, and runs both
entry points, packaged migrations, initialization, upgrade, checks, foreground host,
and shutdown from outside the checkout. Supply `--uv PATH` if uv is not on `PATH`.
Run `uv build` first, with only the intended version's wheel in `dist`.

Tests use real temporary disk databases for restart preservation, table reconstruction,
atomic migration failure, foreign keys, lock contention, shared module transactions,
and operation controls. Synthetic sensitive values exercise parser, configuration,
storage, and migration failures. They also test uncertain commit acknowledgement
without replay. Process tests use a controlled stop-event fixture; native signal
delivery can be exercised separately with:

```text
uv run --locked python tools/verify_interruptions.py --output interruption-results.json
```

On Windows this uses a hidden console and real Ctrl+C/Ctrl+Break events; on Linux it
sends SIGINT/SIGTERM. It checks clean termination and a subsequent store check. See
the [accepted foundation scope](docs/implementation-plan.md#increment-1-shared-contracts-and-application-foundation)
for performed checks and the Windows console-context and readiness-timing limits.
Linux is still the deployment target; Windows and WSL observations do not qualify a
production Linux host.

Verification tools default to `submissions/increment-2/`; `--increment increment-1` explicitly selects the earlier location. Existing Increment 1 evidence is preserved. Submission outputs are ignored by Git. These outputs are
generated locally rather than distributed as repository documentation. The
[implementation plan](docs/implementation-plan.md#verification-and-evidence) defines
source identification, independent assessment, and evidence requirements for later
increments. Completed reviews and human acceptance for Increments 1 and 2 are recorded
in the plan; runtime readiness remains a separate observation.


## Agent Registry (Increment 2)

Increment 2 is implemented, independently reviewed, and accepted by the human owner
within the [recorded Registry scope and limitations](docs/implementation-plan.md#increment-2-agent-registry-and-bootstrap).
The application provides authenticated Registry administration, exact immutable
publications, versioned drafts/current controls, transactional audits and protected
local owner setup/recovery. The five configured initial test Agents remain disabled.
Authorized enablement reports unavailable while execution qualification is unavailable;
authorized disablement remains usable. Coordination, Agent execution and forge
integration remain unavailable. See the [operation contracts](docs/registry-contracts.md)
and [initial Agent configuration](docs/initial-agent-configuration.md).

Use CPython 3.14.10 and the locked dependencies:

```text
uv sync --locked
uv run --locked mobiraeon --help
```

On this Windows checkout uv is `.tools/bin/uv.exe`; use that executable explicitly
when uv is absent from PATH. For a new private installation, create its parent
outside the checkout and select a **new** private directory. Example settings TOML
(replace the example paths with the installation owner's paths):

```toml
[database]
path = "C:/Users/OWNER/AppData/Local/Mobiraeon/initial-test/catalog.db"
[access]
private_dir = "C:/Users/OWNER/AppData/Local/Mobiraeon/initial-test"
credential_file = "C:/Users/OWNER/AppData/Local/Mobiraeon/initial-test/credentials/owner.token"
[api]
enabled = false
```

On Linux use an owner-controlled parent, for example `$HOME/.local/share/mobiraeon`.
The application protects its private root/files with Linux owner permissions or
Windows owner/SYSTEM ACLs, records the actual OS principal, and requires the database
directly inside that private root. Existing roots, links, unsafe ownership/protection
and setup after initialization are refused. Foundation `initialize`/`upgrade` never
grant Registry administrator authority.

Review the explicit grants, 30-day lifetime and self-review policy in
`bootstrap/owner-setup.example.json` before using it. This example grants the one
human administrator all catalog/access actions; publishing Agents creates no grants.
These local commands require no HTTP listener:

```text
uv run --locked mobiraeon --config settings.toml provision
uv run --locked mobiraeon --config settings.toml initialize
uv run --locked mobiraeon --config settings.toml --request-file bootstrap/owner-setup.example.json setup
uv run --locked mobiraeon --config settings.toml --input-file bootstrap/initial-test.json prepare
uv run --locked mobiraeon --config settings.toml --request-file bootstrap/read-control.example.json registry
```

An existing Increment 1 database requires explicit `upgrade`, never an implicit
startup migration. Provision is for a new installation; do not overwrite an existing
store to adopt it. Installations and credentials remain outside source captures.
Malformed/unreadable package files and invalid package structure are rejected before preparation as `invalid_input` (exit 2), without catalog changes or sensitive diagnostics. Possible post-mutation failures retain uncertainty.

`prepare` consumes the supplied input, publishes dependencies and five independently
configured Agents, explicitly selects their published revisions administratively,
and leaves all disabled. Repeat/resume compares exact content, versions, references
and audit evidence; conflicts or unresolved uncertainty stop preparation. No fallback,
real account binding or provider credential is supplied. The approved references
`openai-primary-account-v1` and `openai-primary-credential-v1` are internal identifiers,
with external mapping/resolution unprovisioned. Connectivity, limit enforcement and
qualification remain unverified. Future changes require new reviewed revisions.

Requests use `{operation,target,inputs}` as documented in the contracts. Raw credentials
are generated into a new protected destination before registration, never printed or
accepted as arguments. `access.issue`, `access.rotate`, `access.grants`, `access.revoke`
and `access.reconcile` use the same `registry` command. `recover` accepts an
`access.recover` request with explicit replacement grants/lifetime/destination and
protected OS owner proof; recovery revokes previous credentials and preserves history.
After failed/uncertain registration retain the delivered file and reconcile its ID.
Never blindly replay uncertain mutations. `registry.reconcile` uses an audit target
whose identity is the invocation UUID. Credential cleanup is a protected local
`cleanup` command using an `access.reconcile` request plus `--credential-name NAME`;
it refuses deletion of an active registered credential, verifies the delivered ID,
and preserves nonsecret history. Filesystem/database completion is not atomic. Credential delivery/registration and cleanup now share a persistent protected OS lock across CLI/API processes. A pending registration makes cleanup unavailable (exit 1), with no file removed. After it finishes, reconcile afresh before cleanup; never remove `credential-lifecycle.lock`. Process exit releases the OS lock. The lock does not replace current authorization or last-administrator checks.

For API hosting add operator-provided TLS paths; no certificate/trust provisioning is
performed by the application:

```toml
[api]
enabled = true
host = "127.0.0.1"
port = 8443
allow_remote = false
cert_file = "server-cert.pem"
key_file = "server-key.pem"
client_ca = "operator-ca.pem"
client_url = "https://localhost:8443"
startup_timeout_seconds = 10
drain_timeout_seconds = 10
```

```text
uv run --locked mobiraeon --config settings.toml start
uv run --locked mobiraeon --config settings.toml --request-file bootstrap/read-control.example.json remote
```

`POST /v1/operations` and `GET /v1/openapi.json` require a current personal Bearer token
and HTTPS. The client reads its protected file and verifies CA and hostname; it never
follows redirects or disables verification. Setup/recovery stay local. A literal
non-loopback bind requires `allow_remote=true`. No proxy header establishes identity.
Listener readiness follows binding; administration remains locked until setup;
execution eligibility is always false. Shutdown stops admission and drains within the
configured deadline. Deadline exhaustion reports uncertain effects/nonzero; disconnect
or cancellation cannot establish rollback. One final cleanup precedes terminal output.
Do not interpret a ready event as command completion.

Configuration retains defaults → selected TOML → recognized environment → CLI
precedence, validates overridden values and resolves file paths relative to that
TOML. Additional environment names use `MOBIRAEON_ACCESS_PRIVATE_DIR`,
`MOBIRAEON_ACCESS_CREDENTIAL_FILE` and `MOBIRAEON_API_<UPPERCASE_KEY>` (for the keys
above); boolean environment values are exactly `true`/`false`. Unknown settings fail
safely. Secrets never belong in TOML, environment settings or request documents.

Run the complete checks and outside-checkout installed package probes:

```text
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
uv run --locked python tools/verify_wheel.py --uv .tools/bin/uv.exe
uv run --locked python tools/verify_interruptions.py --api --output api-interruptions.json
uv run --locked python tools/verify_foundation.py --increment increment-2 --uv .tools/bin/uv.exe
```

On Linux pass the available native uv path instead. Wheel checks install into a
fresh `100%valid` path outside the checkout, consume explicit bootstrap inputs, run
CLI and TLS probes and verify real SQLite persistence. Interruption probes exercise
native Windows Ctrl+C/Ctrl+Break or Linux SIGINT/SIGTERM for both foundation and TLS
hosts. Windows console-context and WSL observations do not qualify a production
Linux deployment. No provider calls are made by these checks.
