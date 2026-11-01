# Implementation plan

This is the single checklist for remaining specifications, implementation preparation, and verification under the approved [requirements](requirements.md) and [decisions](decisions.md). Design agreement, provisioning, implementation, execution qualification, and delivery acceptance remain separate records.

## Current position

Increments 1–3 are implemented, independently reviewed, and accepted by the human owner within their recorded scopes below. The application includes the foundation, authenticated persistent Agent Registry with its disabled initial test catalog, and the [minimum local simulated Coordination workflow](#increment-3-coordination-and-scheduling). Supervised execution remains the next planned roadmap area; its small implementation boundary has not yet been selected. Broader Coordination capabilities remain deferred to later increments.

The [architecture](architecture.md), [workflow](workflow.md), [forge-account policy](agent-registry.md#forge-identities), and [first-Agent preparation](agent-registry.md#first-agent-preparation) remain the design baseline. The local simulated Coordination slice is implemented; broader Coordination workflows, supervised Agent execution, forge integration, and execution qualification remain unfinished. The concrete repository and feature for end-to-end validation will be selected under D-12. Existing Gitea setup checks and operational gaps remain in the [infrastructure guide](infrastructure.md#verification-before-relying-on-the-instance).

## Implementation increments

Use the following work breakdown to turn the agreed components into bounded implementation Tasks. Build subsequent increments on the accepted foundation and Registry interfaces, completing their applicable contracts and checks. Detailed execution choices and operating values remain in the checklist below.

| Increment | Position | Deliverable | Completion evidence |
| --- | --- | --- | --- |
| 1. Shared contracts and application foundation | Accepted | Python application, minimum shared contracts, configuration/diagnostics, SQLite migrations and transactions, and controlled operation boundaries. | Independent reassessment resolved R1–R5; Windows and Linux/WSL checks passed; the human owner accepted the identified snapshot with recorded limitations. |
| 2. Agent Registry and bootstrap | Accepted | SQLite-backed Registry API/CLI, immutable publication and reference resolution, protected administrator setup, and the disabled initial test Agent catalog. | Independent reassessment resolved I2-R1/I2-R2; Windows and Linux/WSL checks passed; the human owner accepted the identified repaired snapshot with its execution-readiness limitations. |
| 3. Minimum Coordination workflow | Accepted | One locally supplied Request/Initiative/Task, authorized Assignment and simulated Run, result, independent assessment and explicit Task acceptance, with persistent status/history and basic duplicate protection. | Independent reassessment resolved I3-R1; Windows and Linux/WSL checks passed; the human owner accepted the identified repaired snapshot within its local simulation and storage limits. |
| 4. Supervised execution | Planned | Worker and Runner Adapter contracts implemented with bounded execution, input/output capture, trusted permission enforcement, cancellation, and cleanup or containment. | Process, workspace, tool, resource, and secret boundaries pass the applicable acceptance checks before privileged or provider-backed operation. |
| 5. Gitea integration | Planned | Forge adapter, polling and publication, authenticated project mappings, and retry-safe or reconciled external operations. | Managed observations and authorized updates remain traceable; duplicates and interrupted operations do not create duplicate work or bypass authority. |
| 6. Primary execution qualification | Planned | One concrete runtime/provider/model/environment combination, declared capability scope, and independently configured review. | Authorized qualification checks pass with versioned configuration, operating limits, evidence, and limitations; only qualified scope becomes eligible for ordinary work. |
| 7. End-to-end delivery validation | Planned | One bounded change in a prepared existing repository selected through the D-12 validation contract. | The complete delivery, acceptance, waiting, recovery, duplicate, and stale-result scenarios pass for identified revisions. |

## Increment 1: shared contracts and application foundation

**Accepted by the human owner.** Acceptance covers Tasks 1–6 of the independently reviewed, repaired 77-file foundation snapshot with archive SHA-256:

```text
9a53a51b85cdd3cff39e11d04f451ee94811b40b144d7ca87a2b465fc4051d3b
```

R1–R5 are resolved. Independent verification reproduced 116 passing tests on Windows 11 and 115 on Ubuntu 24.04/WSL2, plus locked dependency checks, lint, formatting, builds, clean installed-wheel checks beneath a percent-containing path, and the recorded native interruption checks. The count difference is a Windows-only SIGBREAK unit case.

| Task | Accepted result |
| --- | --- |
| 1. Minimum shared contracts | Stable identities and exact revision references, configuration-reference consistency, operation/result contracts, and evidence/acceptance separation. |
| 2. Python application | Installable package, console/module entry points, application composition, foreground lifecycle, and truthful capability reporting. |
| 3. SQLite persistence | Explicit initialization/opening/upgrades, packaged immutable migration chain, store identity/revision guards, shared transactions, bounded contention, and truthful failure boundaries. |
| 4. Configuration and diagnostics | One immutable configuration resolution path, strict source validation and precedence, source-relative paths, safe JSON diagnostics, and controlled terminal reporting. |
| 5. Operation boundaries | Explicit owner routing, trusted caller context, current permission checks requiring a valid boolean grant, safe attribution, and distinct success/refusal/failure/uncertainty outcomes. |
| 6. Combined verification and assessment | Integrated checks and captured source/evidence, independent reassessment of repairs, and human acceptance of the foundation scope. |

Acceptance retains the recorded limits:

- Windows native signal checks passed through the recorded uv launcher. Direct interpreter execution in a restricted tool context timed out on SIGINT; restoring Ctrl+C processing in the isolated controller passed both signals. Evidence is launcher/context-qualified.
- Readiness precedes signal-handler registration, and the verifier waits 0.2 seconds before sending a signal. The checks cover steady-state interruption rather than the exact readiness boundary or every terminal's manual keyboard delivery.
- Windows and Linux/WSL foundation evidence does not qualify a production Linux host, full authentication, disaster recovery, or later Registry, Coordination, Worker, model, or forge capabilities.

The original and repaired source archives, manifests, handoffs, and independent review remain locally retained under the ignored `submissions/increment-1/` tree. Documentation finalization records this acceptance and retires the completed assignment brief; it does not rewrite those captured snapshots or claim that the updated documentation still has their original file hashes.

The [D-11 technical baseline](decisions.md#d-11-implementation-technology-and-topology), [foundation setup and configuration guide](../README.md#application-foundation-increment-1), [storage/authorization boundaries](../README.md#storage-and-authorization-boundaries), and [application operation contract](../README.md#application-operation-contract) govern subsequent work. The old implementation instructions are no longer an active assignment; their exact text remains in the reviewed source archives.

## Increment 2: Agent Registry and bootstrap

**Accepted by the human owner.** Acceptance covers Tasks 1–6 of the independently reassessed, repaired 102-file Registry snapshot with archive SHA-256:

```text
013654178835b0194d0f2641eff63f8653029664839a588f48f697fbe21502b1
```

I2-R1 and I2-R2 are resolved. Independent verification reproduced 156 passing tests on Windows 11 and 155 on Ubuntu 24.04/WSL2, plus locked dependency checks, lint, formatting, builds, installed-wheel checks beneath a percent-containing path, TLS trust/hostname rejection, and source/installed foundation/API interruption checks. The same 14 repair regressions produced nine failures against the original reviewed source and all passed against the repaired source.

| Task | Accepted result |
| --- | --- |
| 1. Define Registry contracts | Strict operation targets/inputs/read results, exact revisions, mutable versions, invocation-local trusted identity, authoring/review/publication, control and override bounds, and truthful input/effect outcomes. |
| 2. Implement Registry persistence | Forward migration with catalog/access ownership, immutable publication/dependency/history records, current controls, stale-edit protection, and per-operation mutation/audit transactions. |
| 3. Implement controlled catalog operations | Authorized authoring, validation, exact-candidate review/publication, retrieval/history, explicit selection, reduced ceilings, unavailable enablement and usable disablement. |
| 4. Provide API and CLI administration | Protected owner setup/recovery, revocable credentials/grants, coordinated delivery/registration/cleanup, authenticated API/CLI, direct TLS, caller isolation and bounded lifecycle handling. |
| 5. Prepare the initial catalog | Five complete initial test Agent/Profile pairs and dependencies, approved logical account/credential references, exact selections, disabled state, restart persistence and repeat/resume/conflict evidence. |
| 6. Verify and independently assess the Registry | Source-bound developer verification, preserved original review, independent reassessment of both repairs, and human acceptance of this bounded result. |

Acceptance retains these limits:

- All five Agents remain disabled, unqualified and without administrative grants. Approved [initial test settings](initial-agent-configuration.md) and internal references are complete catalog configuration; external credentials, connectivity and runtime enforcement remain unprovisioned or unverified.
- Authorized enablement remains unavailable without mutation; disablement is usable. Registry acceptance grants no execution, provider calls or delivery-acceptance authority.
- Credential lifecycle exclusion is verified for cooperating application processes on tested local Windows/POSIX stores. Network-filesystem/distributed locking, hostile OS interference, power-loss durability and disaster recovery are not qualified. The persistent lock sidecar must not be manually removed.
- Windows signal evidence covers the exercised native console context. Linux/WSL evidence does not qualify a production Linux/container deployment; live disconnect and hung-handler scenarios retain their recorded limits.
- Coordination, scheduling, Workers/Runner Adapters, forge integration, execution qualification and end-to-end delivery remain later increments. Optional Registry Git import/export remains separately scoped.

The original and repaired source archives, manifests, handoffs, original review and separate reassessment remain locally preserved under ignored `submissions/increment-2/`. The acceptance record identifies this exact repaired snapshot; documentation finalization does not rewrite captured evidence or claim that the updated documentation retains the snapshot's original hashes.

The [Registry design](agent-registry.md), [operation contracts](registry-contracts.md), [initial configuration](initial-agent-configuration.md), and [application guide](../README.md#agent-registry-increment-2) govern ongoing use. The completed implementation assignment is retired from active documentation; its original text remains in the reviewed archives. Subsequent increments build on these accepted interfaces without implicitly enabling the initial Agents or introducing live execution.

## Increment 3: Coordination and scheduling

**Accepted by the human owner.** Acceptance covers Tasks 1–6 of the independently reassessed, repaired 111-file minimum Coordination snapshot with archive SHA-256:

```text
5a32ddb559c590ab77bb5b817cf99ea66687341eac5c388af436b72acb04b21f
```

I3-R1 is resolved. Independent verification reproduced 207 passing tests on Windows 11 and 206 on Ubuntu 24.04/WSL2, locked dependency checks, lint, formatting, builds, installed-wheel checks beneath a percent-containing path, Registry/TLS checks, source/installed foundation/API interruption checks and the simulated workflow. The same 19 regression cases produced six expected failures and 13 passes against the original reviewed source, then all passed against the repaired source. The platform count difference remains the Windows-only SIGBREAK case.

| Task | Accepted result |
| --- | --- |
| 1. Minimum contracts and workflow authority | Strict local actions and explicit scoped grants, trusted invocation-local callers, current authorization and separate workflow/Registry authority. Synthetic author/assessor identities exist only in isolated composition. |
| 2. Persistent work and history | Forward migration 0003, retained Project/Request/Initiative/Task context, separate immutable stage facts, exact configuration/artifact references, transactional history and stable receipts. |
| 3. Narrow workflow progression | Supplied bounded work through submitted evidence, independent exact-submission assessment and explicit Task acceptance. Run completion cannot accept the Task or its parent outcome. |
| 4. Explicit allocation and simulated dispatch | One explicit fixture allocation, current authority/reference/ownership checks and durable reservation before the isolated simulated effect. Ordinary Agent execution remains unavailable. |
| 5. Restart and duplicate safety | Persistent inspection, replay/conflict protection, stale/non-owner refusal and uncertainty fences. I3-R1 binds resolving receipts to the original operation, with conservative legacy-history handling. |
| 6. Combined verification and handoff | Source-bound developer verification, preserved original review, independent regression comparison/reassessment and human acceptance of this bounded result. |

Acceptance retains these limits:

- One local supplied Request/Initiative/Task scenario, CLI actions/status and an isolated scripted simulator. Preserve `Project → Initiative → Task`; the Request is a separate origin link. No live Orchestrator, Coordination HTTP surface or background service is delivered.
- Synthetic assessment/Task acceptance demonstrates application policy mechanics; it is distinct from independent review and acceptance of this increment. The Request stays open and the Initiative stays unaccepted.
- All five initial Registry Agents remain disabled and unqualified. No Worker, provider/model, forge or repository-integration capability is qualified or enabled. Ordinary tokens still represent one installation human; two tokens cannot establish reviewer independence.
- Uncertain outcomes remain fenced unless exact retained evidence establishes the original recorded operation. Legacy replay history without sufficient provenance can remain conservatively unresolved. There is no automatic retry, reassignment or general reconciliation workflow.
- If both commit acknowledgement and separate uncertainty-history recording fail, audit availability is explicitly unavailable; missing records cannot authorize retry. Retained local storage and deliberate inspection remain necessary. Power loss, hostile OS interference and disaster recovery are not qualified.
- Native interruption evidence retains its console/readiness-timing limits; Linux/WSL is not production Linux qualification. Broader [Coordination capabilities](#deferred-coordination-capabilities), supervised execution and later roadmap work remain deferred.

The original archive/review, repaired submission under `submissions/increment-3/repair-i3-r1/`, and separate independent reassessment remain locally preserved under ignored `submissions/increment-3/`. This acceptance identifies the exact repaired snapshot; documentation finalization does not rewrite evidence or claim that updated documentation retains the snapshot's original hashes.

The [Coordination contracts](coordination-contracts.md) and [application guide](../README.md#local-coordination-increment-3) own the maintained interface and operation details. The completed developer brief is retired from active documentation; its exact text remains in the reviewed archives. Select the next small delivery boundary before preparing another implementation assignment.

## Deferred Coordination capabilities

These behaviors remain agreed product direction, but are **not Increment 3 completion requirements**. Select bounded later increments as the next useful capability becomes necessary. Existing roadmap numbers 4–7 are retained; the placement of additional Coordination increments will be selected during later planning.

| Later capability | Deferred behavior and governing reference |
| --- | --- |
| Multi-Task delivery | Dependencies, accepted prerequisites, Decision waits, automated review/rework and changed-context reassessment under the [workflow](workflow.md#intake-and-task-readiness). |
| Scheduling across work | Work-class preferences, permitted alternatives, priority with stable equal-priority ordering, capacity and cumulative-limit scheduling under [Assignment and selection](workflow.md#agent-assignment-and-selection). |
| Human controls and scope changes | Pause/resume/cancel/reprioritize/takeover and baseline-change effects under [human controls](workflow.md#human-controls-and-scope-changes). |
| Advanced recovery | Retries, reassignment, ownership expiry/supersession, uncertain-effect continuation and cleanup/containment before capacity reuse under [waiting and recovery](workflow.md#waiting-and-recovery). |
| Overall outcome and closure | Initiative outcome acceptance and Request closure independently of Run/Task completion under [Initiative acceptance](workflow.md#initiative-outcome-acceptance) and [Request closure](workflow.md#request-closure-and-follow-up). |
| Live integration | Supervised execution, forge synchronization, primary qualification and end-to-end delivery under the existing later-increment roadmap. |

Later increments must implement and verify the safeguards their capabilities rely on before use. In particular, real supervised execution still requires applicable stopping, ownership and cleanup controls. Deferral does not weaken authority, independence, isolation or qualification requirements. Exact transitions, grants, schemas, commands and operating values are decided for the capability being implemented.

## Remaining specifications

The accepted foundation, Registry and local simulated workflow contracts are implemented within their recorded scopes. The rows below cover broader capabilities beyond that slice; they do not reopen completed Increment 3 work. Complete each applicable contract before implementing its dependent capability. Independent work can proceed when its own inputs are sufficient.

| Area | Unfinished specification | Governing baseline |
| --- | --- | --- |
| Lifecycles and assignments | Transitions beyond the accepted one-Task simulation: multi-Task/dependency and Decision progression, Initiative/Request outcomes, rework, reassignment, human controls and recovery. Preserve Task identity and exact evidence when extending the current contracts. | D-03, D-04; F-12, F-19, F-20, F-22 |
| Authority and independence | Production service/Agent identities and broader delegated workflow authority, baseline approval, review eligibility, human intervention and Orchestrator-only escalation. Extend current local scoped grants and exact-evidence gates without inferring execution authority from Registry administration. | D-08, D-10; S-03, F-18, F-20, F-25 |
| Coordinator state and recovery | Extend current durable records, operation identities, transactional history and uncertainty fences to supervised execution, ownership expiry/supersession, reassignment and deliberate recovery. Define capacity reuse after verified cleanup or containment. | D-04, D-11; F-22, F-23; N-02, N-05 |
| Coordination access to the Registry | Least-privilege service access for live dispatch, exact published configuration/current controls and qualification/enablement integration. Preserve the accepted Registry interfaces and local scoped-read behavior; isolated fixture resolution does not qualify ordinary execution. | D-05, D-11; F-07 through F-09, F-15; N-04, N-05 |
| Runner and configuration contracts | Inputs and machine-readable outcomes, Artifact/evidence references, cancellation and errors, compatibility validation, explicit overrides, and requested/effective configuration resolution under the approved fields. Bind immutable per-Run settings and context. | D-05, D-08; F-03 through F-09 |
| Enforcement boundary | Threat assumptions and trusted enforcement for processes, workspaces, network, resources, repository operations, Coordinator actions, and secrets, including subprocess activity and revoked access. Specify demonstrable cleanup and containment criteria. | D-06, D-10; N-02 through N-04 |
| Forge contract | Supported operations/events, capability declarations, per-field authority, stable mappings, actor authentication, external edit/close/reopen behavior, duplicate handling, reconciliation, and conflict treatment. Keep project forge bindings separate from reusable Agent/Profile definitions. | D-07; F-16, F-18, F-22, F-24 |
| Artifacts, context, and integration | Beyond supplied local text artifacts: durable external publication/resolution, context assembly and freshness, dependency evidence, shared-target coordination, exact combined-result validation and retention/deletion. Preserve current immutable references and acceptance applicability checks. | D-05, D-11; F-13 through F-15, F-21, F-27; N-05 |

## Gates before qualification or live pilot execution

Apply each gate to the relevant activity. Qualification and live execution require their configured authority, operating values, and verified controls; design approval alone does not establish readiness to run.

| Area | What remains to be specified | Completion evidence |
| --- | --- | --- |
| End-to-end scenario and release coverage | Select a prepared existing repository, baseline revision, and bounded feature. Specify its outcome criteria, inclusions/exclusions, feature and system checks, permitted operations, and outcome acceptor. Declare release coverage and deferred execution integrations against F-02. | Approved, versioned validation contract traceable to D-12 and S-05; no broader support claim than the qualified scope. |
| Primary execution path | Record the concrete runtime/harness, provider/account reference, model, reasoning/options, versions, tools, and independently configured review for the primary qualification path. Identify included capability scope and deferred integrations. | Versioned capability definitions, authorized qualification configuration, and passing support-matrix checks for the declared scope. Applicable authority precedes privileged or paid checks; ordinary Runs require qualification. |
| Operating profile | Numeric budgets, allocation estimates, concurrency, deadlines, retry/failure thresholds, ownership conditions, cleanup criteria, retention/deletion, recovery objectives, and treatment of measured, estimated, or unavailable usage/cost. | Approved values and executed checks demonstrating enforcement, cleanup, and recovery for the tested environment. |
| Deployment and recovery | API hosting, deployment packaging and service identities under D-11; recorded application, host, container, forge, runtime, and enforcement versions; migrations, startup/shutdown, persistence, backups, restoration, and operator controls. | A reproducible environment and tested restoration of coordination state together with Artifacts and referenced Registry revisions; linked observations for blocked, uncertain, and failed work. |

## Verification and evidence

The [acceptance scenarios](requirements.md#acceptance-scenarios) and requirement-specific checks define observable completion. Verification includes:

- **Registry and bootstrap:** protected first-owner setup, persistent access initialization, consistent API/CLI authorization including protected reads, revocation, last-administrator protection, audited recovery that keeps bootstrap closed, validation/publication, immutable references, exact Agent/Profile bindings, and separate qualification and enablement. Optional imports cannot bypass publication controls.
- **Registry controls and resolution:** explicit selected revisions and persistent current enablement, historical-value bypass prevention, reviewed ceiling-reduction overrides, rejection of unsupported or conflicting changes, and the defined response when required qualification/authority evidence is unavailable. Registry checks do not implement Coordination dispatch or qualification.
- **Unavailable enablement:** unauthorized refusal, authorized unavailable/no-mutation behavior through API and CLI, preserved disabled state after restart, authorized disablement, no forced/manual/automatic enablement, and isolation of positive qualification doubles from production and bootstrap evidence.
- **Registry operations and persistence:** validated targets/inputs and safe results, stale-edit/review protection, mutation/audit commit integrity, separate unsuccessful-attempt audit including unavailable storage, referenced-history preservation, per-operation preparation progress, and reconciliation before replay after uncertain effects.
- **Forge adapter:** qualify Gitea against the versioned forge-neutral contract, declared capabilities, traceable mappings, actor authentication, and authority boundary. Project migration and cross-forge synchronization remain separately scoped.
- **Runner capabilities:** establish supported noninteractive behavior, options, tool boundaries, output contracts, cancellation, and cleanup for the declared execution combinations. One qualified path does not establish support for every requested runtime family.
- **Controlled delivery:** exercise intake and clarification, specification and baseline approval, bounded implementation, independent review, authorized integration, fresh validation of the exact combined revision, and outcome acceptance under D-12.
- **Recovery and continuity:** exercise waiting and continuation, interruption recovery, duplicate reconciliation, stale-owner rejection, configuration/context revision changes, and coherent restoration of Registry revisions, coordination records, and retained Artifacts.
- **Operating controls:** verify configured budgets and concurrency, isolation, secret protection, status and required human action, stop controls, and integration credentials for the selected environment.

Each check records the tested software, configuration and policy revisions, environment, method, observed result, and limitations. Distinguish performed checks from planned checks and supplied evidence. A passing demonstration establishes only its evidenced scope; missing inputs or inconsistent references block affected work rather than establishing success.

Identify the exact combined source assessed. A commit may identify it; for uncommitted work, retain the base revision and a source snapshot or patch covering relevant tracked and untracked files, with a manifest or hashes to verify contents. Independent review and verification assess that same source. Later changes require affected checks and reassessment. Keep local execution evidence with its submission or review record rather than adding standing status documents to the design baseline; local `submissions/` output is ignored by Git.

## Maintaining the plan

Record completion against the governing specification and verification evidence. Changes to the design baseline follow its designated decision authority and update the [decision register](decisions.md) and relevant owning documents. Implementation and qualification Tasks retain their applicable permissions, limits, and acceptance requirements.
