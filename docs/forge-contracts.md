# Bounded manual forge bridge (Increment 5)

Increment 5 implements the [agreed scope](implementation-plan.md#increment-5-forge-integration-gitea-first)
under [D-07](decisions.md#d-07-forge-integration-and-initial-platform). Developer
verification does not establish designated acceptance. The [final repair reassessment](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md) closes the last P2 exact-replay finding. Implementation and technical verification are complete within this scope; no material finding remains.
Existing Registry, Coordination and execution contracts retain their scopes.
All five real Agents remain disabled/unqualified.

## Ownership and authority

Registry owns Project connection heads and immutable definition revisions, distinct
from the model-provider `connection` catalog kind. Coordination owns existing
Task/issue pairings, sync versions, requests/cycles/intents, receipts, conflicts,
approvals and history. The forge-neutral `ForgeAdapter` protocol returns normalized
observations; `Gitea` implements the bounded transport. Runner Adapters are separate.

Use `mobiraeon --config CONFIG --request-file FILE forge`. Forge operations have no
Registry HTTP route. `check` and startup perform no forge HTTP. Capability
`forge_integration=gitea_manual_task_comment` describes implementation independently
of connection readiness. No polling, Task creation from issues, automatic execution,
PR/merge actions or additional provider is available.

The exact envelope is `operation`, `target`, `inputs`. Target is
`{"kind":"entity","entity_kind":"project","identity":"project-1"}`, optionally
with `revision:null`. UTF-8 files are capped at 128 KiB before parsing. Duplicate or
unknown fields, coercion, caller/Role claims and credential fields fail. Local IDs
use the existing ASCII-token contract. Each action needs its own current Project
grant (`project:ID`, `project:*`, `*`). Task operations also require
`coordination.status` on the existing Task, whose immutable supply record must name
that Project. OS ownership, Registry administration and a forge token grant no
forge workflow authority. Expiry/revocation apply before inspection and replay.

| Operation | Exact inputs |
| --- | --- |
| `forge.connection.configure` | `operation_id`, `expected_version`, `connection` |
| `forge.connection.read` | `{}` or `connection_revision` only |
| `forge.link` | `operation_id`, `expected_version`, `task_id`, `connection_revision`, `issue_number` |
| `forge.status` | `task_id` |
| `forge.sync` | `operation_id`, `expected_version`, `task_id`, `connection_revision` |
| `forge.resolve` | `operation_id`, `expected_version`, `task_id`, `conflict_id`, `action`, `rationale` |

Configure uses version zero to create, then the current positive connection version.
It stores a complete offline definition and returns an exact immutable `fcr_...`
revision. Read may inspect retained revisions; link/sync require the selected
revision. One connection per Project is supported. Once linked, provider, canonical
origin, repository ID and service-user ID cannot change. Names are verified against
stable IDs at use. Rotation uses a new protected filename/revision and connection
revision, preserving mappings and history; old credential files are never removed.

Link creation uses zero; identical create-zero reuse is `already_linked`. Positive
versions must match. There is no unlink/relink/merge. Task and external issue pairings
are unique, including across Projects naming the same instance/repository/issue.
Linking verifies API/account/repository/ordinary-issue identities and publishes
nothing. Issue text is human content, never an imported Task contract.

Sync admission increments the link version once, including unchanged and read-only
reconciliation cycles. Resolve increments it once. Internal steps do not increment
it. Busy refusal, failed admission, reads, exact completed replay and same-pair reuse
do not increment it. Task workflow versions and acceptance are separate. Stable
operation IDs bind authenticated actor/action/target/full inputs; exact completed
replay precedes stale checks after current authorization. Unfinished matching
requests report retained uncertainty without executing again.
Retained failed-attempt fingerprints also fence conflicting ID reuse after a failed
admission; retrying deliberately requires a fresh operation ID and current versions.
Exact failed replay preserves the recorded outcome and reason, including when it
is discovered inside the writer transaction. The recorded non-success outcome
survives verified body rollback; failed commit or rollback remains uncertain.

## Configuration and protected tokens

The [connection example](../examples/forge-connection.json) supplies all required
fields/defaults. Origins normalize scheme/lowercase host/effective port, with no
userinfo/query/fragment/non-root path. HTTPS verifies system trust or an absolute
CA-file path. No verification-disable or expansion exists. HTTP requires explicit
loopback opt-in and literal loopback/exact localhost. Native IDs are canonical
positive signed-64-bit strings; API numeric IDs and issue numbers are strict positive
signed-64-bit integers. Route components are encoded. Origin/CA path byte caps are
2048/4096; names are nonempty single components capped at 100 characters, excluding
`.`/`..`, separators, C0 controls (U+0000–U+001F), DEL and C1 controls
(U+007F–U+009F). Other Unicode characters retain their exact spelling: no trimming,
normalization or ASCII-only restriction is applied. This validation guards new
configure inputs; retained immutable definitions and revisions are not rewritten.
Every nested field is mandatory; only the CA file may be null.

| Limit | Default | Range |
| --- | ---: | --- |
| Cycle seconds | 100 | finite 2–3600 |
| Complete request seconds | 10 | finite 0.1–300; at most cycle minus reserve |
| Finalization reserve seconds | 1 | finite 0.1–10; less than cycle |
| Requests | 20 | strict integer 1–100 |
| Lookup responses (`max_pages`) | 5 | strict integer 1–20 |
| Response bytes | 1048576 | strict integer 1024–8388608 |
| Total read bytes | 5242880 | response limit through 33554432 |
| Complete comment UTF-8 bytes | 16384 | strict integer 1024–65536 |

The importer is an OS-owner protected utility independent of Project grants:

```text
python -m mobiraeon.forge_credentials --config CONFIG --source-file PROTECTED_SOURCE --destination-name gitea-coordination-v1
```

Create the source with a trusted secret-entry/editor facility that does not echo,
log or add the value to shell history. On POSIX use an owner-only directory,
`umask 077` and `chmod 600 PROTECTED_SOURCE`; verify ancestor ownership/permissions.
On Windows create an owner-controlled directory, remove inherited ACLs and grant
only the actual owner and SYSTEM full control. The packaged `private_state.harden`
and `protected` helpers implement those file protections for generated fixtures.
Protect ancestry as well: a shared/sandbox-modified temporary directory may correctly
be refused. Never paste the token into argv, TOML, request JSON or evidence.

Source/destination must be protected ordinary files outside any Git checkout.
Links/junctions/hardlinks and untrusted parents are refused at import/read time.
The database is an immediate private-root child; credential files are immediate
`credentials/` children. Import preserves the source and uses flushed durable
no-overwrite delivery. Import and read also verify the private marker's installation
UUID/principal against the database's access installation, using the same bound store.
Tokens contain 1–4096 printable non-whitespace ASCII bytes,
optionally one LF/CRLF. Overflow, whitespace and Möbiræon PATs are refused without
truncation. Existing Registry PAT reading is unchanged. The service token is attached
only to validated-origin HTTP Authorization headers. Read/status return only its
nonsecret reference. Provision a dedicated Coordination user with `read:user`,
`read:repository`, `write:issue` and repository access. The adapter enforces its
narrower method/target allowlist despite those broader native scopes.

## Publication, conflicts and recovery

Gitea `/api/v1/version` must return exact string `28.2.0`. Only version/user/repository/
linked issue/comment reads, complete issue-comments lookup and managed-comment
POST/PATCH are permitted. Write JSON is exactly `{"body":"..."}`. Comment ID,
author and verified issue HTML URL are checked on mapped/reconciled observations;
response URLs are never destinations. The pinned list endpoint is unpaginated.
HTML identity compares scheme, lowercase host, effective port and the exact generated
issue path, so normal omission of default `:80`/`:443` remains valid. Userinfo, query,
fragment, control characters and foreign identities remain refused.
Absence proof requires one bounded complete array, matching `X-Total-Count`, unique
IDs and valid issue identities. A direct 404 alone cannot establish deletion.

One AsyncClient/zero-retry AsyncHTTPTransport per cycle disables environment trust
and redirects, verifies TLS, requests identity encoding and rejects compression.
System trust ignores ambient `SSL_CERT_FILE`/`SSL_CERT_DIR`; a custom trust file must
be the explicit absolute path in the connection revision.
Absolute asyncio deadlines cover headers and streamed body; phase timeouts add
inactivity protection. Preflight/reconciliation share request/read/lookup budgets.
Chunks are at most 4096 bytes; processing stops on the first overflow chunk.
Network admission ends before the finalization reserve. Local lock waits use bounded
remaining time. Cancellation/local persistence/OS/DNS shutdown may add practical
delay; this is not a hard-real-time process-exit guarantee.

The deterministic comment includes installation/link/intent markers, exact source
Task version/state, latest attempt/result and evidence ID/revision/SHA-256 references.
It includes no freeform Task text, Artifact contents, local paths or invented URLs.
Inline fixture evidence has no hosted resolver. The semantic hash excludes fresh
intent markers. Unchanged facts and unchanged expected body cause no write.
Human issue fields/state and discussion comments are preserved.

A persistent protected per-Task OS lock excludes cooperating processes; never unlink
the inode. Acquire it outside SQL, nonblocking, for sync and remote-free resolve.
Immutable cycle facts/current generation fences prevent stale finalization. Process
death releases the OS lock but retains pending intent. A new authorized cycle may
claim an old intent only for read-only resolution, preserving its original payload.

Preparation commits exact body/destination/Task/configuration provenance. A separate
short writer transaction rechecks current authority/versions and arms that one write.
Only positively acknowledged preparation and arm permit dispatch. One cycle attempts
at most one write; no SQL transaction spans HTTP. After local acknowledgement loss,
a fresh writer can establish a prepared intent was never armed and retain it as not
attempted. Its consumed approval stays consumed. Armed means potentially delivered,
even if the process died before sending it.

Lost/truncated/malformed write responses, redirects, 5xx and generic errors remain
uncertain. This implementation implements no HTTP-status-only rejection exception.
An uncertain create may adopt exactly one complete lookup match with exact
body/marker/issue/author; zero matches cannot exclude delayed delivery. An uncertain
update may confirm the exact intended body at its known ID. Observing the old body
does not permit resend. Confirmed reconciliation ends the cycle without another
write. Unresolved holds never expire and resolve cannot clear them.

Observed edits hold for exact `refresh` approval; established deletion holds for
exact `replace` approval. Rationale is nonempty, capped at 4096 UTF-8 bytes. Approval
binds the observed conflict and at most one intent, even after not-attempted outcomes.
Bookkeeping increments preserve unchanged approvals; changed facts require fresh
conflict/approval. Resolve itself performs no HTTP.

**Accepted cooperative-edit limitation:** Gitea supplies no client-observed-revision
precondition. A human edit between the read and server update load can be overwritten.
Local locks/body hashes cannot eliminate that race. Humans must establish idle sync
with no unresolved publication before editing the managed comment. Ordinary human
discussion uses separate comments. No atomic edit protection is claimed.

Revocation before arm prevents dispatch. Revocation after dispatch cannot retract
the request: trusted intent finalization retains the observed effect without Task
progression, further external action or newly unauthorized Task-data disclosure.

## Persistence and inspection

Forward migration 0005 adds bounded tables, foreign keys, positive versions, unique
pairings/pending-intent constraints and immutable evidence triggers. Migrations
0001–0004 are unchanged. Old stores require explicit upgrade; normal check/open never
upgrades. Mutation and required history/receipt commit together. Failed attempts
use separate best-effort audit with truthful unavailable metadata. No deletion,
retention expiry, downgrade or force recovery is introduced.

Read/status are local last-observed inspections, never current remote verification.
Business data is capped at 64 KiB. Status returns references/hashes, last-confirmed
source Task version, pending/conflict/approval references, allowed actions and the
newest 20 UTC/sequence history summaries plus `history_has_more`. No full comment
body, Task contract or Artifact content is returned.

The [application guide](../README.md#manual-forge-bridge-increment-5) documents
verification. Actual-provider qualification uses pinned rootless Gitea with SQLite
in disposable Docker resources, generated accounts/tokens and a controlled fault
proxy. Reports record image/API/host/Docker identities, scopes/routes/limits/cleanup.
It does not qualify the owner's PostgreSQL deployment, production Linux, ordinary
Agents or acceptance.
If Docker's published loopback socket is inaccessible, actual API checks may still
run through the isolated loopback proxy's verified private-container backend. That
records `api_checks_result=passed` but overall `result=incomplete` and nonzero exit;
published-port reachability remains explicitly unqualified.

The fixture publishes on literal Linux loopback `127.0.0.2`, with a random port.
The qualified WSL context routes this address through Linux `lo`; its historical
`127.0.0.1` route through `loopback0` remains a separate limitation. This is an
actual Docker bridge publication, not a relay to a private address. Reports include
the inspected binding/ownership, client UID/network namespace, Engine identity,
direct exact-version readiness and every proxy request's upstream. A passing
qualification requires affirmative published-route evidence throughout all nine
assertions; private fallback remains incomplete/nonzero. No production connection
schema, authority, transport deadline or retry policy changes for this fixture.

The fixture retains the existing 25-second startup budget when publication is initially unavailable. A ready private endpoint is diagnostic fallback evidence and cannot end published readiness testing early. Only after that finite budget may private fallback be selected; it still produces incomplete qualification and a nonzero requested-mode exit. Deterministic controls cover transient publication refusal, sustained refusal, unavailable endpoints, wrong versions and non-200 responses. This fixture correction does not explain the retained sustained `127.0.0.1` routing failure or alter production transport deadlines or retry policy.

The fixture address is within IANA's [127.0.0.0/8 loopback block](https://www.iana.org/assignments/iana-ipv4-special-registry/); Docker's [port-publishing documentation](https://docs.docker.com/engine/network/port-publishing/) describes host-address-bound publication. The qualified path is the inspected Docker publication itself, with the required fault proxy forwarding to that publication. This identifies the named WSL qualification context and does not repair or qualify the original 127.0.0.1 route.
