# Agent Registry operation contracts

These contracts describe the Registry delivered in [accepted Increment 2](implementation-plan.md#increment-2-agent-registry-and-bootstrap), under D-05/D-11 and the [Registry design](agent-registry.md). Authority is separate from catalog content; every protected operation rechecks current grants inside its transaction; publication changes neither selection nor enablement; no positive qualification path exists. Independent reassessment resolved the credential-cleanup and input-classification findings. The [initial Agent configuration](initial-agent-configuration.md) owns the approved test settings; later Coordination and execution contracts remain separate work.

## Operations, targets and results

One shared OperationBoundary serves foundation and Registry adapters. Foundation
commands retain their OS-operator scope. Registry services retain no mutable caller;
each invocation constructs a frozen context from verified credentials or protected
installation-owner proof. Neither JSON fields nor a Role establishes identity.

Registry requests contain exactly `operation`, `target`, `inputs`. Targets contain
`kind` (entity/draft/publication/control/access/audit), `entity_kind`, `identity`, and
optional exact `revision`. IDs use ASCII letters/digits/underscore/dot/hyphen, max128.
References are objects with exact `kind`, `identity`, `revision`; publication IDs are
random `r_` UUIDs, not edit versions or Git commits. Versions are positive strict ints;
creation has uniqueness checks rather than an expected version. No implicit latest.

| Operation | Target | Inputs |
| --- | --- | --- |
| registry.create | entity | document (possibly incomplete) |
| registry.edit | draft | expected_version, document (full replacement) |
| registry.discard | draft | expected_version |
| registry.validate | draft | expected_version |
| registry.review | draft | expected_version, decision=approve, rationale |
| registry.publish | draft | expected_version, review_id |
| registry.read | draft/publication/control/entity | empty |
| registry.history | entity | empty |
| registry.select | control (Agent) | expected_version, revision |
| registry.enable / registry.disable | control (Agent) | expected_version |
| access.issue / access.rotate | access | destination (new basename), lifetime_seconds, grants; rotate also expected_version |
| access.grants | access | expected_version, grants |
| access.revoke | access | expected_version |
| access.reconcile | access | empty; protected local owner or access permission |
| registry.reconcile | audit (invocation UUID) | empty |

Each action is a separate grant. Scopes are `*`, `kind:*`, or `kind:identity` (access
uses `credential:id`). There are no Agent administrative grants. HTTP `POST
/v1/operations` and local `--request-file FILE registry` (protected credential path from resolved configuration) share
validation and handlers. API OpenAPI is protected; readiness events distinguish listener, administrator initialization and execution eligibility. Unknown fields/types/coercion are rejected.

The six foundation outcomes remain. HTTP: 200 success, 422 invalid input, 401 invalid
credential, 403 refused, 404 missing reference, 409 stale/review/conflict/incomplete,
503 unavailable (attempt audit outage is explicit metadata), 500 verified failure, 202 uncertain effects (explicitly
not a successful mutation). CLI: 0 success, 2 invalid input, otherwise1. Business data
contains explicit references/versions, validated nonsecret documents or history and
audit availability; no credential verification hashes, raw credentials or SQL; nonsecret provenance URIs belong to documents.
Do not replay uncertain mutations. Reconcile exact references/control versions AND
correlated audit first. Absent/insufficient evidence preserves uncertainty, not success.

## Documents, review and overrides

Kinds: Agent, Profile, instruction, Role, capability, policy, connection, transport,
context and output. Wire spelling is lowercase. Full required Profile field names
follow requirements.md. Nested settings and reference kinds are strict. Capability
declarations constrain runtime/provider/model/effort/options; they declare compatibility,
not qualification. Published dependencies must exist with the stated identity/kind.
Instruction content includes source URI/revision/SHA-256 and its hash must match text.
Connections contain nonsecret endpoint/account/credential references, never credentials.
Policies describe permissions but cannot alter access grants or enforce future Workers.

Drafts may be incomplete, but not contain unknown fields, malformed present values,
raw personal tokens or private key material. Publication requires completeness and
consistent exact dependencies. Review binds candidate version, canonical document
hash, dependencies and reviewer. Editing invalidates review applicability, including
editing back to earlier content. Self-review is refused unless an explicit installation
policy permits it; no default grants it. Discard tombstones the draft, preserving
versions/reviews/publications. No published/history/audit deletion operation exists.

Limits: integer duration_seconds (1..86400), retries (0..10, zero=no retries), tokens
(1..10000000 total accounted tokens), cost_microusd (0..1000000000, zero=no spend),
concurrency (1..64). All fields required at publication; unspecified/null is incomplete.
Only these fields may appear in Agent overrides; each must be <= the exact Profile
ceiling. Other settings require a new reviewed Profile. Registry validates ceilings;
it does not meter or enforce Agent execution. Missing measurable/enforceable capability
must be explicit in the capability declaration and blocks later qualification, not
silently interpreted as unlimited. No fallback reference means no substitution.

## Storage and audit

Forward migration 0002 adds Registry identities, versioned draft history, candidate
reviews, immutable publications/dependencies, versioned controls, access installation,
credential verifiers/grants and append-only audit. SQL foreign keys/uniqueness and
immutable-record triggers supplement application checks. Migration0001 is unchanged.

Each protected operation owns a short synchronous connection/transaction. Current
credential expiry/revocation/grants, expected versions, review applicability and
dependencies are checked after writer-lock acquisition in that same transaction.
Mutation and required audit commit together. Audit failure rolls back mutations;
commit acknowledgement failure remains uncertain. Refused/failed attempts use a
separate audit transaction; outage is reported as `data.audit_status=unavailable`, never hidden
or permission-granting. Audit carries operation/actor/target/ref/version/outcome and
invocation ID, not request bodies or credentials. Preparation commits per operation;
previous publications survive later failure. There is no universal replay guarantee.
Provisioning precedes database creation and reports `audit_status=not_applicable`;
preparation reports `operations_recorded` for its separately audited child operations.
Neither claims an orchestration-level database audit that does not exist.

## Owner, tokens, delivery and recovery

Provisioning explicitly creates a NEW private directory outside a checkout and records
the actual OS principal and installation UUID. SQLite must reside inside it. Setup
and recovery verify that principal and resource protections afresh, including inside
the mutation. POSIX: effective UID owns private directories (0700), state/credential
files (0600), no symlinks or extra hard links. Windows: native current-user SID and
owner/DACL inspection; directory inheritance removed and only owner plus LocalSystem
allowed full control. Children must retain those protections; no username argument
or loopback trust. Failure to verify a platform's protections refuses the action.

One stable human owner identity; tokens bind only to it, never Agents. Format
`mbr_<32 hex ID>_<43 URL-safe chars>`: 256 random secret bits. Store SHA-256 verifier
of the full token, compare with constant-time comparison. Each has a required lifetime
300..2592000 seconds, creation/expiry/revocation timestamps and mutable version.
There is no perpetual token or global bypass. Explicit setup input supplies initial
grants and self-review policy; setup must establish usable access administration.
Bootstrap closes in the same transaction as first verifier/grants/audit. Catalog
changes cannot reopen it. Local recovery uses owner proof, preserves initialized
state/history, saves a replacement and transactionally revokes previous credentials.

Issuance saves a new credential in owner-protected storage BEFORE registration.
Exclusive creation, file flush/fsync, protection verification and directory sync on
POSIX establish delivery. Windows uses file flush and a non-replacing write-through
rename. No success claim is a power-loss/disaster-recovery qualification. Failure of
delivery cannot activate a credential. Database failure/uncertainty retains the file;
return only its nonsecret ID and delivery/registration status. Rotation registers the
saved replacement and revokes old access in one audited transaction. Do not knowingly
remove the last current unexpired credential with full access-administration grants
unless a usable replacement is established. Expiry can still require owner recovery.
Explicit protected cleanup requires reconciled revoked/absent registration, preserves
IDs/audit, and never automatically removes a file after uncertain registration.

Credential lifecycle exclusion spans processes: a persistent owner-protected lock
file in the private installation root is locked with native Windows byte-range
locking or POSIX flock. Setup/recovery/issue/rotation hold it from before delivery
until registration finishes (including ambiguous acknowledgement); cleanup holds
the same lock across fresh reconciliation, file removal and cleanup audit. Acquisition
is nonblocking: contention returns unavailable with no requested effects. Never
unlink the lock file. Process exit releases the OS lock; subsequent explicit cleanup
still requires protected owner proof and established absent/revoked registration.
The lock grants no authority, spans no filesystem delivery inside a DB transaction,
and does not replace transactional current-authority checks or last-admin protection.

Bootstrap package read, encoding and JSON parse failures are invalid input before
preparation begins (CLI exit 2, safe diagnostics). Normalize only this input boundary;
post-mutation uncertainty remains uncertain and requires reconciliation before retry.

## HTTPS, configuration and lifecycle

API disabled by default; foundation start/check remain available without TLS/access
configuration. Optional `access.private_dir` and `access.credential_file` are paths,
not credentials. Hosting fields: `api.enabled=false`, `host=127.0.0.1`, `port=8443`,
`allow_remote=false`, `cert_file`, `key_file`, `client_ca`, `client_url`,
`startup_timeout_seconds=10`, `drain_timeout_seconds=10` (positive <=60). Require
explicit non-loopback opt-in, valid operator-provided certificate/key and private
state before serving. Client endpoints require HTTPS and explicit CA/hostname
verification. No proxy-header authority, certificate creation, insecure fallback or
global trust changes. Sources retain defaults→selected TOML→recognized env→CLI;
validate even overridden values, resolve source-relative paths once, reject unknowns.

Uvicorn is programmatically configured with one process, no reload, no access logs,
safe application errors, no raw request/framework exceptions. Bound listener readiness
is distinct from admin availability (locked until setup) and execution eligibility
(unavailable). One signal owner withdraws readiness/admission, drains in-flight
synchronous operations within the deadline and closes application resources once.
Cancellation/disconnect does not prove rollback. Deadline exhaustion returns terminal
uncertainty/nonzero rather than success; outstanding work is not replayed.

Implementation/dependency source guidance: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[Uvicorn settings](https://uvicorn.dev/settings/), [server shutdown](https://uvicorn.dev/server-behavior/),
[Windows ACLs](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-acl),
[Windows flushing](https://learn.microsoft.com/en-us/windows/win32/fileio/flushing-system-buffered-i-o-data-to-disk).


### Initial internal connection references

The initial disabled catalog uses `openai-primary-account-v1` and `openai-primary-credential-v1`. These are application-owned logical identifiers, not external OpenAI IDs or provisioned credentials. They may be published while their external mappings and credential resolution remain unprovisioned/unverified. External mapping, provisioning, connectivity and qualification are execution-readiness requirements, not catalog-publication prerequisites. No secret manager is implemented. Future binding changes require explicit versioned configuration changes. Publication authorizes no execution, provider calls or enablement.
