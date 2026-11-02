# Möbiræon

**Möbiræon** is inspired by **Möbius**, representing continuity and interconnected workflows, and **æon**, a word of Greek origin evoking vast spans of time. The name reflects a continuous cycle of planning, building, verifying, and improving software through coordinated AI agents. The **ö** and **æ** preserve these references visually, while the repository uses the ASCII spelling `mobiraeon`.

Möbiræon is a platform for orchestrating and automating software development lifecycle activities through coordinated AI agents. It turns human intent into specifications, bounded assignments, and software changes assessed against explicit acceptance criteria.

## Purpose

Möbiræon reduces repeated human coordination while preserving control over product intent, delivery quality, and resource use. Specialized agents perform assigned work, resolve questions within their authority, and continue when required inputs or decisions become available.

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

Möbiræon coordinates work across:

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

The [implementation plan](docs/implementation-plan.md) records the accepted foundation, Agent Registry, minimum Coordination and supervised fixture execution increments, their verification limits, and the remaining roadmap.

The [repository repair pass](docs/reviews/2026-11-02-repairs-acceptance.md) is accepted:
FR-01–FR-05, residual FR-02-R1 and FR-06 are resolved. Its latest independent checks
passed 338 Windows tests and 336 Linux/WSL tests plus one skip, with all 14 commands
passing on each platform, including clean installed wheels and real Linux
source/installed Worker suites. The existing fixture and qualification limits remain.

## Application foundation (Increment 1)

Increment 1 is accepted for the independently reviewed foundation scope recorded in
the [implementation plan](docs/implementation-plan.md#increment-1-shared-contracts-and-application-foundation).

The foundation provides shared contracts, a foreground local host, validated application
configuration, controlled internal operations, and SQLite/Alembic persistence. The
[accepted Registry increment](#agent-registry-increment-2) adds authenticated Registry
operations and HTTP administration. The [local simulated Coordination slice](#local-coordination-increment-3)
and [supervised fixture execution](#supervised-fixture-execution-increment-4) are available.
Ordinary Agent execution and forge integration remain unavailable. Foundation readiness
does not establish their qualification or acceptance.

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

Settings resolve once per invocation: defaults → explicitly selected TOML file →
recognized environment settings → explicitly supplied CLI options. Restart applies
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
| Lock wait | `MOBIRAEON_DATABASE_TIMEOUT_SECONDS` | `--database-timeout-seconds` | Default 5 seconds; positive finite number ≤60, excluding booleans. TOML requires a number. |
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

Registry and Coordination own their operations, tables and business records. Internal
participants receive a shared transaction handle without commit/rollback methods;
the application coordinates commit. SQLite's authorizer denies participant transaction
and savepoint-control SQL; finalization also checks the driver's transaction state.
Lost ownership cannot establish successful commit or verified rollback. A failed
connection/writer-lock acquisition reports unavailable with known no requested effects;
an ambiguous commit acknowledgement remains uncertain. This is a trusted module contract, not
isolation against hostile Python code. No transaction spans a model, forge, process,
or human wait, including the foreground host's idle wait.

Local foundation commands trust the OS user's access to the process and database and identify
that boundary as `local-os-operator`, without claiming a verified personal username.
They grant only initialization, upgrade, local checks, and foreground startup.
They grant no Agent administration or workflow authority. Authenticated business
adapters supply trusted caller/policy context to the same operation boundary;
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
increments. Completed reviews and human acceptance for Increments 1–4 are recorded
in the plan; runtime readiness remains a separate observation.


## Agent Registry (Increment 2)

Increment 2 is implemented, independently reviewed, and accepted by the human owner
within the [recorded Registry scope and limitations](docs/implementation-plan.md#increment-2-agent-registry-and-bootstrap).
The application provides authenticated Registry administration, exact immutable
publications, versioned drafts/current controls, transactional audits and protected
local owner setup/recovery. The five configured initial test Agents remain disabled.
Authorized enablement reports unavailable while execution qualification is unavailable;
authorized disablement remains usable. Agent execution and forge integration remain
unavailable. Coordination is limited to the [isolated local slice](#local-coordination-increment-3).
See the [operation contracts](docs/registry-contracts.md)
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
Malformed/unreadable packages and unresolved package-local publication references
are rejected before preparation as `invalid_input` (exit 2), without catalog changes.
Stopped preparation returns `data.state="preparation_stopped"` with safe publications,
per-operation progress, the failed definition/step and `reconciliation_required`.
Acknowledged mutations followed by a known failure return `known_failure` (exit 1);
genuinely uncertain mutations retain `uncertain_effects`. Child attribution and
unavailable audit information remain explicit. Inspect this progress and retained
audits before deliberate resume; no automatic retry is introduced.

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
uv run --locked python tools/verify_foundation.py --increment increment-2 --output-directory submissions/increment-2/local-verification --uv .tools/bin/uv.exe
```

On Linux pass the available native uv path instead. Wheel checks install into a
fresh `100%valid` path outside the checkout, consume explicit bootstrap inputs, run
CLI and TLS probes and verify real SQLite persistence. Interruption probes exercise
native Windows Ctrl+C/Ctrl+Break or Linux SIGINT/SIGTERM for both foundation and TLS
hosts. Windows console-context and WSL observations do not qualify a production
Linux deployment. No provider calls are made by these checks.

## Local Coordination (Increment 3)

Increment 3 is implemented, independently reassessed, and accepted by the human
owner within its [recorded scope and limitations](docs/implementation-plan.md#increment-3-coordination-and-scheduling).
The accepted repaired snapshot resolves I3-R1; independent checks reproduced
207 Windows and 206 Linux/WSL tests, with the same 19 regression cases producing
six expected failures on the original snapshot and all passing after repair.
The bounded local workflow supplies one
Request/Initiative/Task within a Project, records an authorized Assignment, reserves
one simulated attempt, observes its result, submits exact artifacts, records an
independent synthetic human assessment, and explicitly accepts that Task.
The Request stays open and the Initiative stays unaccepted. No Agent runs.

[Coordination contracts](docs/coordination-contracts.md) define strict actions,
current workflow authority, exact references, lifecycle and uncertainty behavior.
Forward migration `0003` preserves the accepted migrations and Registry records.
Existing installations require explicit `upgrade` before using normal operations.

Run this scripted demonstration with explicit scenario and catalog inputs. Choose
a **new absolute private directory outside the checkout**; its parent must exist.
Replace `SCENARIO_DIRECTORY` below with that path. Commands work after wheel
installation as well (`python` refers to that installation's interpreter):

```text
uv run --locked python -m mobiraeon.scenario run --directory SCENARIO_DIRECTORY --input examples/coordination.json --catalog-input bootstrap/initial-test.json
uv run --locked python -m mobiraeon.scenario status --directory SCENARIO_DIRECTORY
```

`run` creates a disposable protected installation, synthetic author/assessor
credentials, a separate trusted simulator configuration and the unchanged disabled
five-Agent catalog. It refuses an existing directory. `status` opens it in another
process without dispatching. The driver composes synthetic human identities only
inside this isolated installation. This assessment demonstrates the gate and is
not independent review or acceptance of the Increment 3 implementation.
Synthetic credentials expire after one hour; no real accounts or provider access
are required. Input contents and hashes, exact links and all stage facts are retained.

Normal local CLI actions use the existing protected credential file:

```text
uv run --locked mobiraeon --config settings.toml --request-file examples/coordination-status.json coordination
```

The config selects the store/private directory and protected credential path just
as for Registry administration. Requests use `{operation,target,inputs}`; target
is `{kind:"entity",entity_kind:"task",identity:"task-1"}`. The contracts table
lists every action and its inputs. `coordination.status` returns readable JSON
state, exact evidence, current version and ordered attributable history. Supply
requests carry `work` from `examples/coordination.json`; result submissions carry
its `artifacts`. The scripted driver is the runnable example for all eight actions.

Add each workflow grant explicitly through existing `access.issue` or `access.grants`
with scopes `task:task-1`, `task:*` or `*`. Registry-only grants and OS ownership
give no workflow authority. Necessary Registry reads need their own scoped grants.
All ordinary tokens identify the same human; a second token cannot independently
assess that human's work. Ordinary allocation cannot execute real or fixture Agents.
Identity injection and qualification overrides are absent from normal CLI/API inputs.
Coordination actions are rejected by the existing Registry HTTP routes.

Mutation `operation_id` identifies full inputs/action/target/actor; identical
authorized repetitions return the receipt. A changed ID cannot repeat a stage.
Dispatch first commits an unresolved reservation; only a new acknowledged reservation
allows the driver to create its exclusive simulated marker. Restart never creates
that marker or automatically accepts. Unknown observations stay unresolved. Unknown
commits without a receipt proving the original operation's exact provenance are
fenced by retained uncertainty history when
storage permits. If that separate recording is unavailable, `audit_status=unavailable`
requires inspection of storage and external evidence; absence is not permission to
retry. No automated reconciliation/retry or general multi-user administration exists.

Run all regression, installed-wheel (including literal percent paths), TLS and
native interruption checks and capture a source-bound Increment 3 submission:

```text
uv run --locked python tools/verify_foundation.py --increment increment-3 --output-directory submissions/increment-3/local-verification --uv .tools/bin/uv.exe
uv run --locked python tools/verify_coordination.py --input examples/coordination.json --catalog-input bootstrap/initial-test.json
```

Use a native uv path on Linux and choose a separate output directory beneath
`submissions/` for a new verification. Keep accepted submissions and review evidence
unchanged. Capture archives existing files within the selected output directory
before replacing them. Exact-source Linux/WSL
checks use `tools/verify_platform.py` on the extracted archive with `--manifest`,
`--output` and `--uv`. Capability reporting is
`coordination_workflows=local_simulated_task_acceptance`, with Agent execution and
forge integration still unavailable. No background Coordinator, HTTP surface,
provider/Worker/forge integration, multi-Task scheduler, recovery controls,
Initiative acceptance or Request closure is delivered by this slice.

## Supervised fixture execution (Increment 4)

Increment 4 is implemented, independently reassessed, and accepted by the human
owner within its [recorded scope and limitations](docs/implementation-plan.md#increment-4-supervised-execution).
I4-R1–R3, including the residual I4-R2 nested-signal defect, are resolved. At its
original acceptance, independent checks reproduced 271 Windows tests and 269
Linux/WSL tests plus one platform skip,
with passing source/installed-wheel signal and Linux Docker Worker regressions.

The Linux-only foreground supervisor runs the packaged fixed fixture in one
isolated Docker container. The [execution contracts](docs/execution-contracts.md)
define its authority, handoff, limits and uncertainty rules. Capability reporting
is `fixture_execution=supervised_fixture_only`; all five Registry Agents remain
disabled/unqualified and `agent_execution=unavailable`.

Use the existing Linux Docker Engine (WSL is supported for development). Prepare
the approved image before admitting work; run this from the source environment
or a clean installation containing the packaged build assets:

```text
uv run --locked python -m mobiraeon.execution_fixture build
```

The JSON output records the base RepoDigest, immutable `image_id`, Engine/CLI
identity, asset hashes and raw build results. No image is published. The tested
developer image is
`sha256:0a8b7aa53e80af9edebaa8ea21803b9b70ee9325a16751c7dd6a1465c8a5f8f8`,
on Engine `0fc089f8-7374-43a4-a1aa-7381a79669e6` at
`unix:///var/run/docker.sock`, using `/snap/bin/docker` 29.8.0. These identities
describe the recorded development environment; a new installation builds and
records its own approved image and Engine binding.

Prepare a fresh private installation using ordinary Access authentication:

```text
uv run --locked python -m mobiraeon.execution_fixture prepare --directory /tmp/mobiraeon-fixture-new --input examples/execution.json --catalog-input bootstrap/initial-test.json --image-id sha256:0a8b7aa53e80af9edebaa8ea21803b9b70ee9325a16751c7dd6a1465c8a5f8f8
uv run --locked mobiraeon --config /tmp/mobiraeon-fixture-new/settings.toml --request-file /tmp/mobiraeon-fixture-new/run.json execution run
uv run --locked mobiraeon --config /tmp/mobiraeon-fixture-new/settings.toml --request-file /tmp/mobiraeon-fixture-new/status.json execution status
uv run --locked mobiraeon --config /tmp/mobiraeon-fixture-new/settings.toml --request-file /tmp/mobiraeon-fixture-new/stop.json execution stop
```

The private root must not exist. The helper supplies the bounded work, allocates
`assignment-1` / `attempt-1` to the ordinary author, and writes actual Task versions,
protected local credentials, strict settings and request files. It prints paths
and identifiers only. Credentials stay in protected files selected by the
established `[access]` configuration; do not paste them into requests or logs.
For installed use replace `uv run --locked` with the installed interpreter/CLI,
and supply the explicitly distributed example and catalog files.

Run stays in the foreground and emits JSON progress and a terminal operation
result. Use status or stop from another terminal with the same settings. Request
action and CLI action must match. Public modes are `success`, `failure`, `wait`,
`excess_output` and `stubborn_child`; there are no arbitrary commands or images.
Registry administration grants no execution authority. Grant `execution.run`,
`execution.status`, `execution.stop` separately using Task scopes; launch also
requires current allocation ownership and Coordination dispatch authority.
Ordinary PATs all identify the installation owner, so an additional PAT cannot
establish independent assessment.

Settings use the single resolver's defaults → TOML → environment → CLI precedence.
`[execution]` has `docker_executable`, `endpoint`, `engine_id`, `image_id`,
`data_dir`, plus `startup_seconds=100`, `execution_seconds=100`, `grace_seconds=5`,
`cleanup_seconds=10`, `cpus=1`, `memory_bytes=268435456`, `pids=32`,
`input_bytes=65536`, `result_bytes=65536`, `capture_bytes=262144` and
`scratch_bytes=33554432`. Recognized `MOBIRAEON_EXECUTION_*` variables follow the
same names in uppercase. Time bounds are 0.05–600 seconds, CPU 0.01–16, RAM
32–1024 MiB, PIDs 8–256, input/result 1–131072 bytes, capture 256 bytes–2 MiB,
scratch 4–256 MiB; RAM must exceed scratch by at least 16 MiB. Unsupported settings
are refused. Settings are pinned before dispatch; changes affect future Runs,
while stop uses the retained Engine/image/settings binding.

Execution requires Linux cgroup v2 resource enforcement. The container uses UID
65532, read-only root, no external network, no credentials/management socket,
dropped capabilities and no-new-privileges. Writable storage totals the configured
scratch budget across `/tmp`, `/dev` and `/dev/shm`; the fixed read-only `/dev/null`
device bind is required by the tested runtime. CPU is throttled, memory has no
swap, PIDs and combined attached output are bounded. Daemon logging is disabled.
The packaged lifetime guard bounds fixture activity if the supervisor dies.

Migration 0004 adds execution projections, immutable handoffs, append-only events
and stable receipts. Short database transactions reserve/report; a fenced local
actuation lock serializes effects. One active attempt and zero retries apply per
private installation. Lost acknowledgements, changed/unreachable Engine identity,
or unverified cleanup retain capacity. Status is read-only after restart. Authorized
stop can inspect and clean the retained attempt, never resume it. An uncertain
create cannot be cleared by merely observing an absent name. Terminal run success
requires successful execution, valid sealed captured output and verified cleanup;
known failure and uncertainty have distinct operation outcomes. A later stop
preserves an already sealed terminal fact.

The supervisor retains bounded capture and exact revision/hash references beneath
the protected `data_dir`. Only its sealed successful artifact can pass through
Coordination submission, independent exact-submission assessment and explicit
Task acceptance. Public simulated dispatch/observe/submit cannot replace execution,
including before any execution row exists. Request and Initiative outcomes remain
unchanged. The narrow UTF-8 bridge supports configured content byte budgets with
a 1 MiB envelope while preserving unrelated Registry/Coordination limits.

Run the complete source/installed checks with a fresh evidence directory:

```text
uv run --locked python tools/verify_foundation.py --increment increment-4 --output-directory submissions/increment-4/local-verification --uv .tools/bin/uv.exe --fixture-image-id sha256:0a8b7aa53e80af9edebaa8ea21803b9b70ee9325a16751c7dd6a1465c8a5f8f8
uv run --locked python tools/verify_execution.py --input examples/execution.json --catalog-input bootstrap/initial-test.json --image-id sha256:0a8b7aa53e80af9edebaa8ea21803b9b70ee9325a16751c7dd6a1465c8a5f8f8
```

Use the actual native uv executable on Linux and `tools/verify_platform.py` on an
isolated extraction with `--manifest`, `--output`, `--uv` and `--fixture-image-id`.
Windows covers portable contracts and explicit unavailable behavior; it has no
native Linux Worker. Real enforcement checks run on Linux/WSL from source and a
clean wheel outside the checkout, including percent-containing paths. WSL results
do not qualify production Linux deployment. No provider/forge integration,
background service, automatic retry/reassignment or general recovery is included.

I4-R1–R3 developer repairs retain per-channel EOF/failure evidence: a stopped
reader alone cannot establish complete capture, and failed capture cannot support
successful observation/submission. Foreground execution records SIGINT/SIGTERM
as bounded stop requests and restores prior signal handlers after cleanup;
SIGKILL remains the separate lifetime-guard/cleanup-only case. Submission and
assessment retain the exact attempt's pinned result allowance when settings
change, while future Runs use current settings. Current authority, exact sealed
artifact bytes, human independence and the fixed transport limits still apply.
The full source/installed fixture verifier includes these repair regressions;
`python -m mobiraeon.execution_repair_verification --input examples/execution.json
--catalog-input bootstrap/initial-test.json --image-id IMAGE_ID` runs them alone
on Linux. The findings are independently resolved in the accepted repaired
snapshot; the implementation plan records its exact source identity and evidence.

The residual I4-R2 nested-signal repair uses only a pending-boolean assignment
inside the execution signal handler; synchronized stop/cleanup stays in normal
execution flow. `python -m mobiraeon.execution_signal_verification` runs bounded
single-signal, deterministic nested-delivery and untraced spaced-signal controls
on Windows/Linux. Nested cases must observe reentry and both returns, including
after the Event-based implementation is removed. This is timing-window evidence,
not a measured natural occurrence rate. Source tests and clean-wheel verification
include these checks. Independent reassessment reproduced the baseline deadlock
and verified the repaired cases on both platforms; prior reviews and evidence
remain preserved.

Source captures retain present bytes in `files` and sorted tracked deletions in
`deleted_paths`, covering staged and unstaged changes without altering Git. Frozen
verification requires those deleted paths to remain absent; older manifests imply
no deletions. Failed reads or private inputs do not publish a completed manifest.

Foreground foundation SIGINT/SIGTERM/Windows SIGBREAK callbacks only record a
pending boolean; normal bounded wait flow signals the stop event and restores
previous handlers, including on failure. Supervised success additionally requires
terminal-zero container evidence and successful attachment capture **before**
cleanup; attachment EOF or cleanup exit zero alone cannot establish success.
