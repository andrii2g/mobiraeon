# Implementation plan

This is the single checklist for remaining specifications, implementation preparation, and verification under the approved [requirements](requirements.md) and [decisions](decisions.md). Design agreement, provisioning, implementation, execution qualification, and delivery acceptance remain separate records.

## Current position

Increment 1 is implemented, independently reviewed, and accepted by the human owner within the [foundation scope below](#increment-1-shared-contracts-and-application-foundation). Increment 2, Agent Registry and bootstrap, is now in high-level planning; its proposed Task breakdown is below. Later increments remain planned.

The [architecture](architecture.md), [workflow](workflow.md), [forge-account policy](agent-registry.md#forge-identities), and [first-Agent preparation](agent-registry.md#first-agent-preparation) remain the design baseline. Registry business operations, Coordination workflows, supervised Agent execution, and integration qualification remain unfinished. The concrete repository and feature for end-to-end validation will be selected under D-12. Existing Gitea setup checks and operational gaps remain in the [infrastructure guide](infrastructure.md#verification-before-relying-on-the-instance).

## Implementation increments

Use the following work breakdown to turn the agreed components into bounded implementation Tasks. Complete each increment's applicable contracts and checks; Registry and Coordination work can proceed in parallel once their shared references and interfaces are stable. Detailed execution choices and operating values remain in the checklist below.

| Increment | Position | Deliverable | Completion evidence |
| --- | --- | --- | --- |
| 1. Shared contracts and application foundation | Accepted | Python application, minimum shared contracts, configuration/diagnostics, SQLite migrations and transactions, and controlled operation boundaries. | Independent reassessment resolved R1–R5; Windows and Linux/WSL checks passed; the human owner accepted the identified snapshot with recorded limitations. |
| 2. Agent Registry and bootstrap | Planning | SQLite-backed Registry API/CLI, immutable publication and reference resolution, administrator-led setup, and disabled creation of the initial Agent catalog. | Configuration survives restart; invalid or conflicting changes are rejected; published revisions remain retrievable; creation/publication cannot authorize ordinary execution. |
| 3. Coordination and scheduling | Planned | Persistent work records, validated Assignments, deterministic dispatch eligibility, waiting and human controls, and recovery against simulated execution and forge operations. | Required state, dependency, authority, duplicate, interruption, and stale-owner scenarios pass without live model calls. |
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

The Registry ownership, configuration fields, authenticated/versioned HTTP API, administrator CLI, and initial five-Agent catalog are established by [D-05](decisions.md#d-05-registry), the [configuration contract](requirements.md#agent-configuration-contract), and the [Registry design](agent-registry.md). The bounded outcome and Task breakdown below are **proposed for discussion**. Implementation has not started.

### Proposed outcome and scope

An authorized human administrator can prepare, validate, review, publish, and retrieve a persistent Agent catalog through the CLI and authenticated HTTP API. Published definitions and their exact dependencies remain retrievable after later edits or disablement. The five initial Agents can be prepared disabled; publication does not qualify or authorize execution.

Build on the accepted foundation and shared database, with Registry-owned records and operations. Cover Agents, Profiles, instruction snapshots, policies, capability declarations, and the references needed to connect them. Include controlled administrative enable/disable operations and audit provenance. Preserve separation from Coordination-owned qualification and operational state.

Do not implement scheduling, Assignments/Runs, Workers, actual runtime qualification, model invocation, live forge operations or account provisioning in this increment. Optional Git import/export is outside the required initial path. Project/forge integration details remain with their applicable later contracts; reusable catalog definitions must not depend on a live forge.

### Proposed Tasks

| Task | Scope and deliverable | Completion evidence |
| --- | --- | --- |
| 1. Define Registry contracts | Bound authoring, review/publication, exact references, current restrictions, conflict handling, and permitted overrides using the approved configuration fields. | Representative valid/invalid examples distinguish immutable content from current control state and authority. |
| 2. Implement Registry persistence | Add owned catalog/history records, migrations, atomic changes, attribution, and protection against stale concurrent edits in the existing database. | Restart preserves catalog revisions; upgrades preserve the foundation; conflicting edits cannot silently overwrite one another. |
| 3. Implement controlled catalog operations | Manage definitions, validation, review/publication, exact retrieval, and enable/disable through the shared authorized operation path. | Published content cannot be overwritten; exact dependencies resolve consistently; invalid or unauthorized changes produce no unauthorized mutation; credentials stay outside catalog content. |
| 4. Provide API and CLI administration | Expose the same operations through an authenticated, versioned HTTP API described by OpenAPI and the administrator CLI. | Both interfaces enforce consistent validation/authority rules; unauthenticated or unauthorized requests cannot mutate or disclose protected records. |
| 5. Prepare the initial catalog | Import reviewed Role/shared-rule snapshots with provenance and create the five named Agents disabled, bound to explicit Role-specific Profile revisions. | Repeated preparation avoids duplicate identities or silent overwrites and cannot enable Agents or dispatch work. No existing Orchestrator is required. |
| 6. Verify and independently assess the Registry | Exercise the combined persistent catalog, API/CLI, publication, current controls, bootstrap, and failure paths. | Repeatable checks and independent review assess the same combined source. Retain Increment 1's evidence and identify Increment 2's snapshot/results separately; designated acceptance follows the established process. |

### Boundaries to settle before implementation

- **Authoring and publication:** define the minimum authoring/review/publication progression, exact-reference validation, current controls, permitted overrides, and stale-edit behavior.
- **Administrator access:** define bootstrap authority and authenticated API/CLI behavior. The foundation's local OS operator grants and test policy doubles do not automatically grant Registry administration.
- **Bootstrap inputs:** deliberately select complete nonsecret candidate Profile settings and their instruction/policy/capability references. Missing inputs cannot become published placeholders; fixture definitions prove tests without becoming qualified operational entries.
- **Enablement and qualification:** initial Agents remain disabled. Administrative controls must respect qualification and governing authority; the Registry cannot own or fabricate Coordination's qualification evidence or authorize ordinary execution merely by publishing or enabling a definition.
- **Implementation detail:** select the API framework, physical schema, concrete operation contracts, and bootstrap commands after the high-level scope is agreed. Live runtime/model values and operating profiles remain separately governed.

Start discussion with the outcome, exclusions, and Task breakdown, then authoring/publication and current-control behavior, administrator access, and bootstrap inputs/evidence. These proposals do not start implementation or approve unselected mechanisms.

## Remaining specifications

Complete the applicable contract before implementing its dependent capability. Independent specification and implementation work can proceed when its own inputs and contracts are sufficient. The items below finish the selected design without choosing additional mechanisms or operating values implicitly.

| Area | Unfinished specification | Governing baseline |
| --- | --- | --- |
| Lifecycles and assignments | Exact Task, Run, Decision, Initiative, Request-closure, and acceptance transitions; actor/guard rules; assignment progression; pause, resume, cancellation, takeover, and recovery effects. Preserve Task identity through rework and reassignment. | D-03, D-04; F-12, F-19, F-20, F-22 |
| Authority and independence | Concrete actors, permitted operations and targets, baseline approval and delegation, acceptance grants, administration authority, reviewer eligibility, and context/provenance checks. Specify authentication of human actions and enforcement of Orchestrator-only escalation. | D-08, D-10; S-03, F-18, F-20, F-25 |
| Coordinator state and recovery | Durable records, operation identities, transactional guarantees, dispatch and exclusive ownership, expiry/supersession and reassignment conditions, uncertain-effect reconciliation, stale-result rejection, and capacity reuse after cleanup or containment. | D-04, D-11; F-22, F-23; N-02, N-05 |
| Registry API and bootstrap | Authorized API/CLI operations, schemas and exact references, draft/review/publication contracts, administrator bootstrap checks, disabled initial creation, qualification/enablement separation, retention, and optional import/export. Historical enabled revisions cannot bypass current restrictions. | D-05, D-11; F-07 through F-09, F-15; N-04, N-05 |
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

- **Registry and bootstrap:** authorized administration, validation/publication, immutable references, exact Agent/Profile bindings, and separate qualification and enablement. Optional imports cannot bypass publication controls.
- **Forge adapter:** qualify Gitea against the versioned forge-neutral contract, declared capabilities, traceable mappings, actor authentication, and authority boundary. Project migration and cross-forge synchronization remain separately scoped.
- **Runner capabilities:** establish supported noninteractive behavior, options, tool boundaries, output contracts, cancellation, and cleanup for the declared execution combinations. One qualified path does not establish support for every requested runtime family.
- **Controlled delivery:** exercise intake and clarification, specification and baseline approval, bounded implementation, independent review, authorized integration, fresh validation of the exact combined revision, and outcome acceptance under D-12.
- **Recovery and continuity:** exercise waiting and continuation, interruption recovery, duplicate reconciliation, stale-owner rejection, configuration/context revision changes, and coherent restoration of Registry revisions, coordination records, and retained Artifacts.
- **Operating controls:** verify configured budgets and concurrency, isolation, secret protection, status and required human action, stop controls, and integration credentials for the selected environment.

Each check records the tested software, configuration and policy revisions, environment, method, observed result, and limitations. Distinguish performed checks from planned checks and supplied evidence. A passing demonstration establishes only its evidenced scope; missing inputs or inconsistent references block affected work rather than establishing success.

Identify the exact combined source assessed. A commit may identify it; for uncommitted work, retain the base revision and a source snapshot or patch covering relevant tracked and untracked files, with a manifest or hashes to verify contents. Independent review and verification assess that same source. Later changes require affected checks and reassessment. Keep local execution evidence with its submission or review record rather than adding standing status documents to the design baseline; local `submissions/` output is ignored by Git.

## Maintaining the plan

Record completion against the governing specification and verification evidence. Changes to the design baseline follow its designated decision authority and update the [decision register](decisions.md) and relevant owning documents. Implementation and qualification Tasks retain their applicable permissions, limits, and acceptance requirements.
