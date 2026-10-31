# Implementation plan

This is the single checklist for remaining specifications, implementation preparation, and verification under the approved [requirements](requirements.md) and [decisions](decisions.md). Design agreement, provisioning, implementation, execution qualification, and delivery acceptance remain separate records.

## Current position

The high-level [architecture](architecture.md), [workflow](workflow.md), and [first-Agent preparation](agent-registry.md#first-agent-preparation) are established. The Registry is a Python module in `mobiraeon`, with an authenticated, versioned API and SQLite persistence. An authorized human administrator prepares the five Role-specific Agents through the Registry API/CLI, initially disabled and bound to exact Profile revisions. Publication, authorized qualification, and administrative enablement remain distinct steps.

The [forge-account policy](agent-registry.md#forge-identities) and first-Agent preparation are established. The concrete repository and feature for the first end-to-end validation will be selected during implementation planning under D-12. Gitea configuration and reusable template assets exist; their recorded checks and remaining operational verification are in the [infrastructure guide](infrastructure.md#verification-before-relying-on-the-instance). Application implementation and qualification remain unfinished.

## Implementation increments

Use the following work breakdown to turn the agreed components into bounded implementation Tasks. Complete each increment's applicable contracts and checks; Registry and Coordination work can proceed in parallel once their shared references and interfaces are stable. Detailed execution choices and operating values remain in the checklist below.

| Increment | Deliverable | Completion evidence |
| --- | --- | --- |
| 1. Shared contracts and application foundation | Python application structure, persistence ownership and migration contracts, domain and lifecycle contracts, and authorized operation boundaries. | Contracts trace to requirements; application startup and storage initialization are verified against the defined ownership and migration rules. |
| 2. Agent Registry and bootstrap | SQLite-backed Registry API/CLI, immutable publication and reference resolution, administrator-led setup, and disabled creation of the initial Agent catalog. | Configuration survives restart; invalid or conflicting changes are rejected; published revisions remain retrievable; creation/publication cannot authorize ordinary execution. |
| 3. Coordination and scheduling | Persistent work records, validated Assignments, deterministic dispatch eligibility, waiting and human controls, and recovery against simulated execution and forge operations. | Required state, dependency, authority, duplicate, interruption, and stale-owner scenarios pass without live model calls. |
| 4. Supervised execution | Worker and Runner Adapter contracts implemented with bounded execution, input/output capture, trusted permission enforcement, cancellation, and cleanup or containment. | Process, workspace, tool, resource, and secret boundaries pass the applicable acceptance checks before privileged or provider-backed operation. |
| 5. Gitea integration | Forge adapter, polling and publication, authenticated project mappings, and retry-safe or reconciled external operations. | Managed observations and authorized updates remain traceable; duplicates and interrupted operations do not create duplicate work or bypass authority. |
| 6. Primary execution qualification | One concrete runtime/provider/model/environment combination, declared capability scope, and independently configured review. | Authorized qualification checks pass with versioned configuration, operating limits, evidence, and limitations; only qualified scope becomes eligible for ordinary work. |
| 7. End-to-end delivery validation | One bounded change in a prepared existing repository selected through the D-12 validation contract. | The complete delivery, acceptance, waiting, recovery, duplicate, and stale-result scenarios pass for identified revisions. |

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
| Deployment and recovery | Framework/packaging and service identities; recorded application, host, container, forge, runtime, and enforcement versions; migrations, startup/shutdown, persistence, backups, restoration, and operator controls. | A reproducible environment and tested restoration of coordination state together with Artifacts and referenced Registry revisions; linked observations for blocked, uncertain, and failed work. |

## Verification and evidence

The [acceptance scenarios](requirements.md#acceptance-scenarios) and requirement-specific checks define observable completion. Verification includes:

- **Registry and bootstrap:** authorized administration, validation/publication, immutable references, exact Agent/Profile bindings, and separate qualification and enablement. Optional imports cannot bypass publication controls.
- **Forge adapter:** qualify Gitea against the versioned forge-neutral contract, declared capabilities, traceable mappings, actor authentication, and authority boundary. Project migration and cross-forge synchronization remain separately scoped.
- **Runner capabilities:** establish supported noninteractive behavior, options, tool boundaries, output contracts, cancellation, and cleanup for the declared execution combinations. One qualified path does not establish support for every requested runtime family.
- **Controlled delivery:** exercise intake and clarification, specification and baseline approval, bounded implementation, independent review, authorized integration, fresh validation of the exact combined revision, and outcome acceptance under D-12.
- **Recovery and continuity:** exercise waiting and continuation, interruption recovery, duplicate reconciliation, stale-owner rejection, configuration/context revision changes, and coherent restoration of Registry revisions, coordination records, and retained Artifacts.
- **Operating controls:** verify configured budgets and concurrency, isolation, secret protection, status and required human action, stop controls, and integration credentials for the selected environment.

Each check records the tested software, configuration and policy revisions, environment, method, observed result, and limitations. Distinguish performed checks from planned checks and supplied evidence. A passing demonstration establishes only its evidenced scope; missing inputs or inconsistent references block affected work rather than establishing success.

## Maintaining the plan

Record completion against the governing specification and verification evidence. Changes to the design baseline follow its designated decision authority and update the [decision register](decisions.md) and relevant owning documents. Implementation and qualification Tasks retain their applicable permissions, limits, and acceptance requirements.
