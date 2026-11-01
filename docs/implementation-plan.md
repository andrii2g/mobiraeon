# Implementation plan

This is the single checklist for remaining specifications, implementation preparation, and verification under the approved [requirements](requirements.md) and [decisions](decisions.md). Design agreement, provisioning, implementation, execution qualification, and delivery acceptance remain separate records.

## Current position

Increments 1 and 2 are implemented, independently reviewed, and accepted by the human owner within their recorded scopes below. The application now includes the foundation and authenticated, persistent Agent Registry with its disabled initial test catalog. Increment 3, Coordination and scheduling, is next for high-level scope and Task planning; its detailed breakdown is not yet confirmed.

The [architecture](architecture.md), [workflow](workflow.md), [forge-account policy](agent-registry.md#forge-identities), and [first-Agent preparation](agent-registry.md#first-agent-preparation) remain the design baseline. Coordination workflows, supervised Agent execution, forge integration, and execution qualification remain unfinished. The concrete repository and feature for end-to-end validation will be selected under D-12. Existing Gitea setup checks and operational gaps remain in the [infrastructure guide](infrastructure.md#verification-before-relying-on-the-instance).

## Implementation increments

Use the following work breakdown to turn the agreed components into bounded implementation Tasks. Build subsequent increments on the accepted foundation and Registry interfaces, completing their applicable contracts and checks. Detailed execution choices and operating values remain in the checklist below.

| Increment | Position | Deliverable | Completion evidence |
| --- | --- | --- | --- |
| 1. Shared contracts and application foundation | Accepted | Python application, minimum shared contracts, configuration/diagnostics, SQLite migrations and transactions, and controlled operation boundaries. | Independent reassessment resolved R1–R5; Windows and Linux/WSL checks passed; the human owner accepted the identified snapshot with recorded limitations. |
| 2. Agent Registry and bootstrap | Accepted | SQLite-backed Registry API/CLI, immutable publication and reference resolution, protected administrator setup, and the disabled initial test Agent catalog. | Independent reassessment resolved I2-R1/I2-R2; Windows and Linux/WSL checks passed; the human owner accepted the identified repaired snapshot with its execution-readiness limitations. |
| 3. Coordination and scheduling | Next: scope discussion | Persistent work records, validated Assignments, deterministic dispatch eligibility, waiting and human controls, and recovery against simulated execution and forge operations. | Required state, dependency, authority, duplicate, interruption, and stale-owner scenarios pass without live model calls. |
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

The [Registry design](agent-registry.md), [operation contracts](registry-contracts.md), [initial configuration](initial-agent-configuration.md), and [application guide](../README.md#agent-registry-increment-2) govern ongoing use. The completed implementation assignment is retired from active documentation; its original text remains in the reviewed archives. Increment 3 planning starts from these accepted interfaces without enabling the initial Agents or introducing live execution.

## Remaining specifications

Complete the applicable contract before implementing its dependent capability. Independent specification and implementation work can proceed when its own inputs and contracts are sufficient. The items below finish the selected design without choosing additional mechanisms or operating values implicitly.

| Area | Unfinished specification | Governing baseline |
| --- | --- | --- |
| Lifecycles and assignments | Exact Task, Run, Decision, Initiative, Request-closure, and acceptance transitions; actor/guard rules; assignment progression; pause, resume, cancellation, takeover, and recovery effects. Preserve Task identity through rework and reassignment. | D-03, D-04; F-12, F-19, F-20, F-22 |
| Authority and independence | Concrete actors, permitted operations and targets, baseline approval and delegation, acceptance grants, administration authority, reviewer eligibility, and context/provenance checks. Specify authentication of human actions and enforcement of Orchestrator-only escalation. | D-08, D-10; S-03, F-18, F-20, F-25 |
| Coordinator state and recovery | Durable records, operation identities, transactional guarantees, dispatch and exclusive ownership, expiry/supersession and reassignment conditions, uncertain-effect reconciliation, stale-result rejection, and capacity reuse after cleanup or containment. | D-04, D-11; F-22, F-23; N-02, N-05 |
| Coordination access to the Registry | Trusted service identity and least-privilege access to exact published configuration and current restrictions; qualification/enablement integration when implemented. Preserve the accepted Registry contracts and prevent historical-value bypass. | D-05, D-11; F-07 through F-09, F-15; N-04, N-05 |
| Runner and configuration contracts | Inputs and machine-readable outcomes, Artifact/evidence references, cancellation and errors, compatibility validation, explicit overrides, and requested/effective configuration resolution under the approved fields. Bind immutable per-Run settings and context. | D-05, D-08; F-03 through F-09 |
| Enforcement boundary | Threat assumptions and trusted enforcement for processes, workspaces, network, resources, repository operations, Coordinator actions, and secrets, including subprocess activity and revoked access. Specify demonstrable cleanup and containment criteria. | D-06, D-10; N-02 through N-04 |
| Forge contract | Supported operations/events, capability declarations, per-field authority, stable mappings, actor authentication, external edit/close/reopen behavior, duplicate handling, reconciliation, and conflict treatment. Keep project forge bindings separate from reusable Agent/Profile definitions. | D-07; F-16, F-18, F-22, F-24 |
| Artifacts, context, and integration | Durable publication and revision references, summary format/freshness, dependency satisfaction, evidence applicability, missing-reference behavior, shared-target coordination, exact combined-result validation, and retention/deletion rules. | D-05, D-11; F-13 through F-15, F-21, F-27; N-05 |

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
