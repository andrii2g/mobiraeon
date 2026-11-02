# Minimum supervised execution contracts (Increment 4)

These contracts govern the implemented, independently reassessed and human-accepted [Increment 4](implementation-plan.md#increment-4-supervised-execution) supervised fixture scope. They preserve the accepted [Coordination contracts](coordination-contracts.md), including I3-R1 receipt provenance, and the [Registry contracts](registry-contracts.md). Acceptance covers the tested fixture mechanics; ordinary Agent execution and production deployment remain unqualified.

## Boundary and authority

One local Linux Docker Worker executes one predefined fixture Run at a time. The Worker supplies isolation/capacity; its fixture Runner Adapter invokes the program; the Coordinator owns authoritative records and acceptance gates. All five real Registry Agents remain disabled/unqualified. Ordinary Agent execution remains unavailable. No HTTP execution surface, arbitrary command/image selection, general identity system, automatic retry/resumption or new scheduler is included.

Use existing protected credential files, Access authentication, invocation-local caller context and literal-`True` current permission checks. Define `execution.run`, `execution.status` and `execution.stop` as separately grantable actions on the existing Task target/scopes (`task:task-1`, `task:*`, `*`). Registry administration and OS ownership do not imply these permissions. Launch additionally requires current dispatch authority and the accepted allocation/ownership checks. Protected reads, duplicates and stop requests recheck current authority; mutation checks occur again inside short writer transactions.

Trusted composition creates the supervisor's reporting context, bound to the exact Task/Assignment/attempt, Worker and fencing generation. The program never receives this context, caller credentials or Docker-management access. Report fields cannot choose the actor or grant authority. An existing supervisor retains responsibility for confined safety cleanup and recording observations if caller authority is later revoked. A new protected invocation still needs current authority. Retaining safety evidence cannot impersonate the original caller or bypass current Coordinator progression/acceptance permissions; preserve the evidence and any unresolved hold when progression is unavailable.

Use a distinct `supervised-fixture-v1` configuration resolved only through trusted isolated fixture composition. Its allocation identifies the supervised mode before launch; public simulated dispatch cannot substitute for `execution.run`. The mode comes from trusted allocation/configuration, never request claims or the presence/absence of an execution row. Existing `fixture-v1` marker behavior, immutable records and accepted scenarios keep their meaning. Actual Registry Agents are not enabled to make the fixture work.

Prepare this mode using the fixed packaged helper in the maintained [application guide](../README.md#supervised-fixture-execution-increment-4), against a fresh disposable private root. Reuse protected application setup/credential/grant operations and the disabled test catalog. Use ordinary Access author identity consistently through allocation and public execution CLI; only the trusted verification driver supplies a distinct synthetic assessor. No provider credentials, human identity-selection flag or ordinary Agent qualification override is introduced.

The fixed configuration references have kinds `agent`, `profile`, `role`, `context`, identities `supervised-fixture-agent`, `supervised-fixture-profile`, `supervised-fixture-role`, `supervised-fixture-context` respectively, and revision `supervised-fixture-v1`. They describe the predefined fixture rather than actual Registry Agents. Operating settings remain operator configuration pinned at Run admission. The prepared example uses `task-1`, `assignment-1`, `attempt-1`, one input `fixture-input` at `v1` and one deliverable `fixture-summary`; all criteria name that deliverable as evidence. Generate the output's revision/hash from its sealed captured content.

## Local operations

The confirmed forms are:

```text
mobiraeon --config SETTINGS --request-file REQUEST execution run
mobiraeon --config SETTINGS --request-file REQUEST execution status
mobiraeon --config SETTINGS --request-file REQUEST execution stop
```

Requests contain exactly `operation`, `target`, `inputs`; target is `{kind:"entity",entity_kind:"task",identity:"task-1"}` without revision. Reject unknown fields and disagreement between CLI action and request operation. IDs retain the shared ASCII-token rules.

| Operation | Inputs and result |
| --- | --- |
| `execution.run` | `operation_id`, positive strict-integer `expected_version` of the allocated Task, `attempt_id`, permitted fixture `mode`. Load the existing Assignment and its exact input/configuration references; no caller-selected host paths, image, command or container ID. Reserve, launch and supervise in the foreground. Terminal output distinguishes operation effect, execution outcome, artifact validity and cleanup. |
| `execution.status` | `attempt_id` only. Return persisted identities, versions, pinned settings, observed phases, stop intent, outcome, exact artifact/evidence references and cleanup/Worker availability. Read-only: no create/start/stop/remove, reconciliation, hold clearing or success inferred from missing runtime state. |
| `execution.stop` | `operation_id`, `attempt_id`, bounded `reason`. Target the immutable attempt rather than a rapidly changing progress version. Durably acknowledge stop intent, then perform bounded stopping/inspection/cleanup when safely controlled. Return stop acknowledgement separately from completion; status can inspect progress. |

Mutating operation identities bind action, full target, actor and complete inputs. Conflicting reuse fails; current authority precedes replay. An exact duplicate launch returns the recorded attempt and never starts it again. Repeated stop converges on the existing intent/current cleanup; any continued cleanup needs current authority and exclusive fenced control, and can never create/start an attempt. Terminal cleaned attempts return their established outcome without another execution.

Use the existing safe operation-result envelope and six effect outcomes. Retain the CLI convention of exit 0 for a successful operation, 2 for invalid input and 1 for other operation outcomes. A successful status or stop acknowledgement describes that operation, not successful execution. Callers must inspect explicit execution, artifact and cleanup results. The foreground command emits machine-readable operation/progress records and a terminal record when supervision returns; an interrupted/lost terminal response cannot establish success. Invalid input, refused authority, unavailable prerequisites, verified failure and unknown external/commit effects remain distinct. Protect raw credential values, environment values and unexpected exceptions from output.

For a terminal `execution.run` result, `success` requires established successful execution, valid sealed output and verified cleanup; an established failure with verified cleanup is `known_failure`; unknown execution, unverified cleanup or uncertain commit/effect is `uncertain_effects`. Pre-launch validation, authority and unavailable-prerequisite results retain their existing mappings. An exact duplicate may return a successful read of a still-active reservation, but must clearly identify it as nonterminal and never claim successful execution. Status success means the protected persisted inspection succeeded. Stop acknowledgement must remain explicit even if subsequent cleanup is uncertain.

## Configuration and prepared Worker

Extend the existing strict resolver and source precedence. Add a separate execution configuration namespace; the Registry API's existing timeout validation is not the execution timeout policy. Operator configuration selects the approved fixture image/digest, local Docker executable/access, retained-storage location and limits. Run requests cannot override them. Reject unknown settings, nonfinite/nonpositive times or CPU values, noninteger byte/PID limits, unsupported controls, overflowing values, conflicting paths and configurations exceeding the finite input/output envelope.

Defaults are startup **100 s**, execution **100 s**, graceful stopping **5 s**, forced cleanup/verification **10 s**, **1 CPU**, **256 MiB** memory with no swap, **32** processes/threads including helpers, **64 KiB** input, **64 KiB** result, **256 KiB combined** captured stdout/stderr and **32 MiB** total declared writable scratch. One active Run and zero automatic retries are scope invariants. Settings are configurable within the supported fixture boundary; later edits affect future Runs. Pin nonsecret effective settings with each attempt and use them for cleanup after interruption.

Prepare the image before admission from `python:3.14.10-slim-trixie`; record the base registry digest, resulting fixture identity/build provenance, OS/architecture and tested Engine/CLI versions. A locally built fixture's immutable `sha256` image ID is sufficient; no registry publication/push is required. Resolve that exact local content and refuse a missing/unprepared image; admission never builds or pulls. The developer collects actual values without another owner-selection gate.

Bind the Worker/Run to the actual Docker Engine ID and its nonsecret connection destination, not merely a context name or CLI path. Pin that binding with the attempt and verify the same Engine before subsequent management or absence/cleanup conclusions. A retargeted context, mismatched daemon or inaccessible identity is unavailable/uncertain and cannot clear the original hold. Never expose connection credentials in this record.

Validate host enforcement before reserving work. Configure non-root execution, read-only root, private namespaces, no external network, no credentials/management socket and least privilege. All writable surfaces, including temporary/shared-memory mounts, share the scratch budget; memory-backed storage counts toward the memory cap. Use non-TTY bounded attach capture with Docker logging disabled (`none`) so daemon logs cannot escape the capture cap. CPU quota normally throttles; report observed allocation/OOM/limit failures truthfully. Missing enforcement is unavailable, not successful isolation.

## Durable launch and exclusive control

Keep SQLite transactions short and free of Docker calls, stream waits or process execution. Atomically retain the Coordinator dispatch reservation, execution ownership/Worker slot, immutable handoff and attributable history before launch. The handoff includes exact scope/input/configuration, mode, effective limits, image identity, managed paths and output contract. A failed/uncertain reservation is not launch permission.

Retain a unique never-reused container name/nonce and the binding to its immutable Docker ID when established. Record create/start intent before each external effect. Make one create/start attempt; an unknown acknowledgement cannot justify repeating either. Inspect only the recorded Run's identity, checking its expected binding before management. User-supplied labels, arbitrary IDs and process IDs alone are not ownership evidence.

Use a per-Worker local actuation lock for cooperating application processes, covering the final ownership/stop-fence recheck and create/start/cleanup acts. Never wait for that lock while holding a SQLite writer transaction. Do not hold it throughout the Run or attached-output wait: release after the bounded start act is established, with capture/wait proceeding separately so stop can acquire control. Persistent stop intent/fencing prevents an old supervisor from issuing a late start or overwriting newer cleanup. Status/stop acknowledgement remain responsive while foreground supervision runs; no blocking call may hide a stop or deadline indefinitely. Every external command has a finite deadline within its phase budget.

Define the start-ordering point as a durable start authorization committed under the actuation lock after the final current-owner/generation/stop check. It authorizes only the one recorded start delivery; it is not proof that Docker received it or that execution began. Stop intent committed before this point blocks startup. Stop committed afterward treats pending delivery as in flight, requires bounded stopping/inspection and forbids successful sealing. Do not promise atomicity between a SQLite check and Docker CLI issuance. Unknown delivery retains the hold; a replay cannot deliver the start again.

Record observed startup separately from dispatch. The startup allowance begins with admission of the prepared Worker; execution time begins with observed execution start. Unknown startup remains unknown. Continuous supervision retains bounded diagnostics and observations without holding a writer transaction. Reserve the Worker through execution and cleanup, including unknown effects.

The immutable fixture image includes a small trusted lifetime guard, with no Docker or host-management authority, that bounds fixture/descendant activity if the foreground supervisor disappears. It receives the recorded bounded lifetime through trusted composition. This is fixed fixture machinery, not a general Agent sandbox or recovery service. Supervisor loss still leaves outcome/cleanup uncertain and capacity held until verified; the guard cannot publish authoritative results or clear a hold.

An absent container is insufficient proof of safe cleanup when a create/start request could still take effect. Keep that uncertainty held until quiescence is proved. For an established binding, fence stale actors, stop the Run, capture required evidence, remove the exact container and verify retirement before reuse. A stale queued start of a retired ID cannot recreate it. If management acknowledgement or quiescence is unknown, retain the hold; there is no general recovery or force-clear shortcut.

## Stopping, interruption and truthful completion

Ordinary interruption requests the same bounded stop path where possible. Persistent stop intent is ordered against durable start authorization as defined above. If sealed authoritative terminal Run completion, including required cleanup and artifact applicability, commits before stop intent, preserve that fact. Receipt of exit 0 alone is not terminal completion. Otherwise a later zero exit cannot erase the accepted stop or become successful Task evidence. Record race ordering and actual observations rather than inventing a completed cancellation.

Request graceful termination, escalate within the configured grace, then verify Run-owned descendant cleanup within the cleanup deadline. The parent process's exit or a successful stop-command exit is insufficient alone. Until verified cleanup, affected capacity remains unavailable. Effective containment requires retained trusted evidence; the initial implementation may conservatively keep capacity held whenever cleanup is not established.

After supervisor loss, `status` only reports. An authorized `stop` may acquire exclusive fenced cleanup control, inspect the retained binding and finish cleanup without launch/resume. Concurrent stop invocations converge; late supervisor reports cannot advance authoritative state. Historical uncertainty and evidence remain append-only. A cleanup-only observation never converts an unknown execution into success or bypasses an unrelated I3-R1 fence.

Execution, output validity, cleanup and Task acceptance are independent facts. Preserve known reasons such as failure, timeout, explicit stop, output violation or observed resource termination. If the actual execution outcome cannot be established, retain unknown even when cleanup succeeds.

## Fixture output and Coordinator bridge

The supervised fixture Task declares exactly one nonempty UTF-8 input artifact without NUL and one result deliverable. Its criteria reference that same result artifact as evidence; other Coordination modes retain their existing artifact cardinality. The program emits one UTF-8 JSON result on stdout. Stderr carries diagnostics. The public modes have these fixed behaviors:

| Mode | Behavior |
| --- | --- |
| `success` | Emit the deterministic summary and exit 0. |
| `failure` | Emit a bounded diagnostic to stderr and exit 1 without a valid result. |
| `wait` | Stay active until authorized stop, execution deadline or the trusted lifetime guard. |
| `excess_output` | Keep emitting output until supervisor capture enforcement stops the Run. |
| `stubborn_child` | Start a descendant that ignores graceful termination and remain active so forced descendant stopping/cleanup is exercised. |

Fixed test-only variants may exercise invalid output and CPU/memory/PID/scratch enforcement through trusted test composition; ordinary requests cannot select them. Modes never provide shell/code execution.

The success JSON has `schema="fixture-summary-v1"`, `input_sha256`, `utf8_bytes`, `characters`, `lines`, `words`. Hash original UTF-8 bytes; characters count Unicode code points; lines use `splitlines()`; words use whitespace `split()`. Output is one JSON object with an optional final newline and no extra stdout material. Validate its exact fields, strict nonnegative integer counts, schema, input digest/counts and byte limits. Nonzero exit, truncation, invalid output, stop or unknown execution cannot yield a successful deliverable.

The result's bytes count toward both result and combined stdout/stderr budgets. Establish attached capture before the program can emit output; a start-then-attach race can lose a fast fixture's result. Stop on capture overflow, retain a bounded prefix and mark truncation. Persist output outside container tmpfs through bounded supervisor capture; seal content/revision/hash only after writers have stopped. Partial/invalid output remains diagnostic evidence. Failed or lost capture is explicit and cannot be reconstructed as success after restart; disabled daemon logging cannot provide a recovery copy.

Retain immutable content durably before publishing its database reference. Filesystem and database effects are separate: record missing, orphaned or uncertain publication truthfully, preserve recoverable evidence and never delete referenced material. A database acknowledgement failure cannot imply a safe replay. No general blob service is required.

Execution events/projection are separate append-only records; I3's single immutable `coordination.observe` stage must not be overwritten to model progress. Bridge one trusted final observation after outcome and cleanup are established. For every supervised-fixture allocation, public observation/submission claims cannot substitute for the exact sealed execution receipt and captured artifact; verify that provenance before progression, including when no execution row exists. Successful output then uses existing submission, independent assessment and explicit acceptance; Request/Initiative outcomes remain unchanged. Unknown launch/cleanup observations retain the execution hold without repeatedly creating that terminal stage.

Current shared decoders and Coordination artifact strings are smaller than the selected byte budgets. Add a narrow execution/Coordination ingestion bridge supporting actual configured UTF-8 input/artifact limits, with a **1 MiB request envelope** and explicit metadata limits. Preserve unrelated Registry limits and ordinary field validation. Reject requests whose configured content/encoding cannot fit the envelope; do not advertise 64 KiB support behind a 4 KiB content cap.

Runtime details follow Docker's documentation for [attach](https://docs.docker.com/reference/cli/docker/container/attach/), [start with attached streams](https://docs.docker.com/reference/cli/docker/container/start/), [logging configuration](https://docs.docker.com/engine/logging/configure/), [tmpfs storage](https://docs.docker.com/engine/storage/tmpfs/) and [resource constraints](https://docs.docker.com/engine/containers/resource_constraints/). Verify their actual enforcement on the recorded host.

## Verification and delivery

Implementation choices: migration `0004` owns `execution_runs` projections,
immutable handoffs, `execution_events` and stable `execution_receipts`. The fixed
Worker is installation-local, with a persistent `execution-worker.lock` in the
protected root. Settings live in `[execution]`; retained output lives in its
configured private `data_dir`. Actuation uses an explicit Unix Docker endpoint
and pinned Engine ID, never ambient Docker context. Each attempt gets a random
container name/nonce and generation; cleanup uses its original settings. The
packaged build helper pins base RepoDigest and labels the image with build-input
hashes. Writable tmpfs ceilings partition the total scratch limit across `/tmp`,
`/dev` and `/dev/shm`. Fixture-only content ingestion has a 1 MiB envelope; ordinary
Registry decoding and marker-fixture cardinality remain unchanged.

The bounded `/dev` mount includes a fixed read-only bind of the host's null
device at `/dev/null`, required by the tested OCI runtime to start the container.
It provides no stored host content or management access. No other host mount is
provided. An unacknowledged create remains unresolved even after an absent-name
inspection; only an acknowledged immutable container binding can establish its
retirement. This conservative hold has no automatic recovery or retry operation.

An established cleaned terminal failure bridges one `failed` Coordination
observation tied to its seal, while a valid cleaned success bridges `succeeded`
and verifies retained artifact bytes. Unknown execution/cleanup does not bridge.
Only the successful seal can support submission; a failed observation provides
no successful deliverable or acceptance authority.

Review repair implementation choices (I4-R1–R3): capture records each channel as
`pending`, `eof` or `failed` under the capture lock; only successful EOF on both
channels can establish complete capture. A capture failure requests bounded
supervisor cleanup and remains diagnostic, even after a valid summary prefix.
Foreground execution scopes SIGINT/SIGTERM handlers to supervision, coalesces
ordinary interruption into a recorded stop and restores prior handlers after
cleanup. Repeated signals cannot interrupt that cleanup; SIGKILL still uses the
separate abrupt-loss/guard path. Submission and assessment validate result bytes
against the exact retained attempt's handoff, not later operator settings;
assessment resolves that attempt through its exact retained submission. Current
authorization and the fixed transport/metadata limits still apply. These choices
use existing execution records and require no migration or fixture build change.

Residual I4-R2 implementation choice: the scoped signal handler performs only
an idempotent assignment to a main-thread-owned pending boolean. It does not call
Event methods, acquire locks, log or coordinate storage. Normal execution checks
that flag and performs the existing synchronized stop/cleanup work. Nested signal
delivery is tested with a bounded timing-window probe that requires observed
reentry and both handler returns; separate untraced spaced-signal controls do not
claim a natural occurrence rate. Capture and pinned-allowance repairs, handler
restoration, generation/authority fences and the SIGKILL guard remain unchanged.

Demonstrate successful source and installed-package flows on the real Linux Docker path, plus refusal, timeout/stop, output/resource bounds, stubborn children, duplicate launches/stops, stale reports, stop/completion races and injected interruption/acknowledgement windows. Include stop between the final database check/start authorization and Docker CLI issuance. Prove pre-effect failures do not launch, unknown effects keep holds, cleanup-only recovery cannot relaunch and capacity is never unsafely reused. Test configured values distinct from defaults and shorter trusted failure-test deadlines.

Retain accepted foundation/Registry/Coordination regressions, especially I3-R1, and verify forward migration from the accepted store without rewriting migrations. Windows verifies application contracts and explicit unavailable behavior where native Linux execution is absent; real Worker checks use Linux/WSL and do not qualify production deployment. For subsequent changes, capture exact source, image/configuration/environment identities, commands, raw results and limits under the [verification and evidence rules](implementation-plan.md#verification-and-evidence). Passing fixture checks does not enable real Agents or replace independent review and designated acceptance. The completed implementation brief is retired; its exact text remains in the accepted source archives.
