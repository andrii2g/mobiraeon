# Local simulated Coordination contracts (Increment 3)

The [minimum Coordination workflow](implementation-plan.md#increment-3-coordination-and-scheduling)
is implemented, independently reassessed and accepted by the human owner, extending
the accepted foundation and Registry. These contracts own its local simulated
scope. The broader [workflow](workflow.md) remains design direction; acceptance of
this slice does not qualify live Agent execution or later Coordination capabilities.

## Contract selected before dependent implementation

Use `coordination.supply`, `.allocate`, `.dispatch`, `.observe`, `.submit`,
`.assess`, `.accept`, `.status`. Each action is separately granted. The target is
`{kind:"entity",entity_kind:"task",identity:"task-1"}` without a revision.
Local `coordination` CLI requests contain exactly `operation`, `target`, `inputs`.
Unknown fields (including actor, Role claims and qualification switches) fail.
No Coordination action is routed by the Registry HTTP API.

All mutations require `operation_id` (stable caller-chosen ASCII token).
Except supply they require a strict positive integer `expected_version`.
Status takes `{}`. Mutations atomically append their distinct fact, operation
receipt and attributable history and advance the Task version. The first version
is 1. An identical operation ID, actor, target, action and full inputs returns its
existing receipt after current authorization; conflicting reuse fails. Receipt
replay does not repeat effects or change state. Invocation UUIDs are distinct from
these stable IDs. New IDs cannot duplicate an existing stage fact.

| Action | Additional inputs and guard |
| --- | --- |
| supply | `work`: project, request, initiative IDs; project_context, request_outcome, initiative_outcome, objective, scope, exclusions (nonempty strings); deliverables (nonempty list of IDs); inputs (nonempty versioned artifacts); criteria (criterion ID → `{requirement,evidence}` with observable requirement text and required evidence artifact ID); role (exact Registry-shaped reference). Author comes from trusted context. |
| allocate | `assignment_id`, `attempt_id`, `configuration`: exact agent/profile/role/context references. Required Role must match; configuration must resolve and be suitable in the trusted isolated fixture source. Ordinary execution allocation reports unavailable. Owner is the authenticated author. |
| dispatch | `attempt_id`; same owner, current allocation authority and exact configuration; no other unresolved/allocated attempt. Records the durable reservation before any simulated effect. |
| observe | `attempt_id`, `observation` = succeeded/failed/unknown, `detail` (nonempty string); current owner, reserved attempt. Observations are distinct from result claims. Unknown remains unresolved. |
| submit | `attempt_id`, `submission_id`, `artifacts` (nonempty list); successful known observation and current owner. Must contain every declared deliverable and criterion evidence artifact ID. |
| assess | `submission_id`, `submission_digest`, `evidence` (exact submitted artifact list), `decision` = approve/reject, `rationale`; authorized human independent of author, exact submission and all criteria evidence. |
| accept | `submission_id`, `submission_digest`, `assessment_id` (assessment operation ID); exact approved independent assessment, evidence, contract and current accept permission. Explicit action only. |
| status | Original work, immutable stage facts/receipts, current version/state, current caller's allowed workflow actions, chronological history, Request=open, Initiative=unaccepted. Reserved/unknown attempt is visibly unresolved. |

Artifact wire shape: `{identity,revision,sha256,content}`; SHA-256 must match UTF-8
content. Small supplied text is retained, not fetched from mutable URIs. Exact
revisions use ASCII token syntax; conflicting identities/revisions in one set are
invalid. Submission digest hashes the canonical full submission record, including
Task contract, attempt, author and artifacts. There is no implicit latest or edit
operation. Missing references fail; conflicting revisions/versions fail without
mutation. These inline artifacts are scenario inputs, not a general blob store.
Artifact IDs are scoped to their Task. Reusing an input artifact's exact ID/revision
with different content/hash in the submission is refused; earlier evidence is retained.

## Authority and identities

Normal CLI uses the established protected credential file, Access authentication
and invocation-local CallerContext. PATs all identify the same installation human;
two tokens cannot supply independent assessment. Add explicit workflow grants with
the existing access administration operations, using `task:task-1`, `task:*` or
`*` scopes. Catalog grants, OS ownership and Role text grant no workflow permission.
Every read and receipt replay checks current credentials, scope, expiry and grants;
mutations recheck inside the writer transaction, requiring literal `True`.

The separate `mobiraeon.scenario` driver provisions a **new disposable installation**
with synthetic credentials and hardcoded trusted author/assessor composition.
Only that fixture composition maps authenticated scenario credentials to distinct
synthetic humans. No ordinary CLI/HTTP field or configuration selects identity or
qualification. The assessor has assess/accept/status; the author has the authoring
actions/status. Necessary exact Registry reads require their own applicable scopes.
Fixture configuration uses immutable `fixture-v1` references in its own source,
never qualifies/enables actual Registry Agents. All actual Agents remain disabled
and unqualified; Agent execution and forge integration remain unavailable.

## State, interruption and examples

Task: supplied → allocated → unresolved (dispatch reserved) → observed → submitted
→ assessed → accepted. Failed observations cannot submit; unknown observations
remain unresolved. Run completion cannot assess or accept. One active allocation
or unresolved attempt occupies this slice's single slot. Ownership never expires.
No rework, retry, reassignment, reconciliation mutation or parent acceptance exists.

The trusted driver effects boundary is an exclusive local simulated marker created
only after a newly committed reservation. A duplicate reservation is inspection,
never permission to execute. Interruption before reservation permits a first
dispatch; after reservation it requires deliberate inspection. Missing effect or
commit acknowledgement is not a reason to relaunch. Known receipts may establish
already recorded facts after an uncertain commit; absent receipts do not prove a
safe retry. Status retains enough exact facts for inspection; automatic recovery
and universal replay guarantees remain deferred.

Uncertain commits also attempt a separate retained uncertainty history entry.
Without a matching receipt this fences later mutations, including acceptance.
Matching requires the original Task and the fingerprint of its action, target,
authenticated actor and full inputs; a shared operation ID alone is insufficient.
For older uncertainty entries without a fingerprint, only the original invocation's
atomic success history with the same Task/action/actor and exact receipt contents
can establish the outcome. Unrelated or conflicting receipts leave the fence intact.
An exact committed receipt may establish an outcome after an uncertain mutation or
receipt replay, but never starts the attempt again. Current authority still applies.
If storage also prevents that recording, the result explicitly reports
`audit_status=unavailable`; missing records cannot authorize retry. These guarantees
depend on retained local storage, not disaster recovery or hostile OS interference.

Forward migration `0003` adds Coordination-owned Task projections, immutable
stage facts (separate Assignment, dispatch/Run, observation, submission, assessment
and acceptance rows), stable operation receipts and ordered immutable history.
The supplied fact retains Project/Initiative/Request context and outcomes. Each
stage stores original inputs, authenticated actor and credential/version provenance.
Status reconstructs all facts and links after restart; the projection never replaces
the evidence. The history sequence establishes ordering and records UTC epoch time.

Successful example: supply task-1 at version 1; allocate at 1; dispatch at 2;
observe succeeded at 3; submit at 4; independent approve at 5; explicit accept at 6.
Acceptance creates version 7 and leaves the Request open and Initiative unaccepted.
Refusals: Registry-only administrator; revoked workflow token; author assessment;
non-owner observations; stale expected version; changed submission digest/evidence;
second active attempt; conflicting operation ID; unknown attempt submission.

Safe results use the six foundation outcomes. Schema errors are invalid input;
current authority failures are refused; missing/stale/gate failures are verified
transaction failures with allowlisted reasons. Writer acquisition is unavailable;
commit acknowledgement failure is uncertain. Mutation and history roll back together.
Failed attempts have a separate best-effort Coordination history entry, with audit
availability reported explicitly. Status success describes inspection, not resolution.
