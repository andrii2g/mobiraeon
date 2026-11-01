# Implementation plan

This is the single checklist for remaining specifications, implementation preparation, and verification under the approved [requirements](requirements.md) and [decisions](decisions.md). Design agreement, provisioning, implementation, execution qualification, and delivery acceptance remain separate records.

## Current position

Increment 1 is implemented, independently reviewed, and accepted by the human owner within the [foundation scope below](#increment-1-shared-contracts-and-application-foundation). Increment 2, Agent Registry and bootstrap, has an agreed scope, six Tasks, and an active [developer brief](implementation-instructions.md). Implementation has not started; the brief assigns concrete contracts before dependent code, and actual candidate values remain required before Task 5 publication. Later increments remain planned.

The [architecture](architecture.md), [workflow](workflow.md), [forge-account policy](agent-registry.md#forge-identities), and [first-Agent preparation](agent-registry.md#first-agent-preparation) remain the design baseline. Registry business operations, Coordination workflows, supervised Agent execution, and integration qualification remain unfinished. The concrete repository and feature for end-to-end validation will be selected under D-12. Existing Gitea setup checks and operational gaps remain in the [infrastructure guide](infrastructure.md#verification-before-relying-on-the-instance).

## Implementation increments

Use the following work breakdown to turn the agreed components into bounded implementation Tasks. Complete each increment's applicable contracts and checks; Registry and Coordination work can proceed in parallel once their shared references and interfaces are stable. Detailed execution choices and operating values remain in the checklist below.

| Increment | Position | Deliverable | Completion evidence |
| --- | --- | --- | --- |
| 1. Shared contracts and application foundation | Accepted | Python application, minimum shared contracts, configuration/diagnostics, SQLite migrations and transactions, and controlled operation boundaries. | Independent reassessment resolved R1–R5; Windows and Linux/WSL checks passed; the human owner accepted the identified snapshot with recorded limitations. |
| 2. Agent Registry and bootstrap | Brief prepared | SQLite-backed Registry API/CLI, immutable publication and reference resolution, administrator-led setup, and disabled creation of the initial Agent catalog. | Configuration survives restart; invalid or conflicting changes are rejected; published revisions remain retrievable; creation/publication cannot authorize ordinary execution. |
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

The Registry ownership, configuration fields, authenticated/versioned HTTP API, administrator CLI, and initial five-Agent catalog are established by [D-05](decisions.md#d-05-registry), the [configuration contract](requirements.md#agent-configuration-contract), and the [Registry design](agent-registry.md). The outcome, exclusions, and six-Task breakdown below define Increment 2's agreed scope. The [implementation brief](implementation-instructions.md) assigns remaining concrete contracts before their dependent implementation; application implementation has not started.

### Outcome and scope

An authorized human administrator can prepare, validate, review, publish, and retrieve a persistent Agent catalog through the CLI and authenticated HTTP API. Published definitions and their exact dependencies remain retrievable after later edits or disablement. The five initial Agents can be prepared disabled; publication does not qualify or authorize execution.

Build on the accepted foundation and shared database, with Registry-owned records and operations. Cover Agents, Profiles, instruction snapshots, policies, capability declarations, and the references needed to connect them. Include controlled administrative enable/disable operations and audit provenance. Preserve separation from Coordination-owned qualification and operational state.

Do not implement scheduling, Assignments/Runs, Workers, actual runtime qualification, model invocation, live forge operations or account provisioning in this increment. Optional Git import/export is outside the required initial path. Project/forge integration details remain with their applicable later contracts; reusable catalog definitions must not depend on a live forge.

### Tasks

| Task | Scope and deliverable | Completion evidence |
| --- | --- | --- |
| 1. Define Registry contracts | Bound logical operation groups, business targets/inputs/read results, trusted per-operation caller context, authoring, review/publication, exact references, current restrictions, conflict handling, and permitted overrides using the approved fields and foundation outcomes. | Representative valid/invalid examples distinguish immutable content from current control state and authority; caller identity comes from trusted entry paths rather than request fields. |
| 2. Implement Registry persistence | Add logically owned catalog, access, current-control, and history records, migrations, per-operation mutation/audit commits, and protection against stale concurrent edits in the existing database. | Restart preserves revisions and controls; upgrades preserve the foundation; conflicting edits cannot silently overwrite another change; failed and uncertain operations preserve truthful effect boundaries. |
| 3. Implement controlled catalog operations | Manage definitions, validation, review/publication, exact retrieval, explicit current selection, enable/disable, and declared ceiling-reduction overrides through the shared authorized operation path. | Published content cannot be overwritten; exact dependencies and controls resolve consistently; invalid or unauthorized changes produce no unauthorized mutation. Unavailable qualification leaves enablement unchanged; authorized disablement remains usable. Credentials stay outside catalog content. |
| 4. Provide API and CLI administration | Expose the same operations through an authenticated, versioned HTTP API described by OpenAPI and the administrator CLI, with protected setup and recovery under the access model. | Both interfaces enforce consistent validation/authority rules; unauthorized requests cannot mutate or disclose protected records. Repeated bootstrap cannot reset access; revocation and last-administrator protection are enforced and attributable. |
| 5. Prepare the initial catalog | Use the reviewed bootstrap inputs to publish complete Role-specific candidate Profiles and instruction/policy/capability dependencies, then prepare the five named Agents disabled with exact Profile bindings. | The five published Agent/Profile revisions, dependencies, provenance, and disabled state remain retrievable after restart. Repeating or resuming avoids duplicate identities and silent overwrites; preparation cannot enable Agents or dispatch work. No existing Orchestrator is required. |
| 6. Verify and independently assess the Registry | Exercise the combined persistent catalog, API/CLI, publication, current controls, bootstrap, and failure paths. | Repeatable checks and independent review assess the same combined source. Retain Increment 1's evidence and identify Increment 2's snapshot/results separately; designated acceptance follows the established process. |

### Authoring and publication baseline

The [Registry authoring model](agent-registry.md#authoring-and-publication) governs Tasks 1–6: editable drafts, validation, review of exact candidates and dependencies, and immutable publication with no partial published result on failure. Candidate edits require renewed review. The same authorized human may author, review, and publish when policy permits. Publishing a Profile does not update dependent Agent bindings automatically; restoring earlier settings creates a new reviewed revision under current checks. Publication remains separate from qualification, enablement, and authorization for work.

### Administrator access and bootstrap baseline

The [access model](agent-registry.md#administrator-access-and-bootstrap-authority) establishes one designated human administrator through protected local setup, with persistent initialization separate from the Agent catalog. API and CLI use the same current authorization checks, including protected reads. Catalog management and administrative-grant permissions remain distinct; the owner may hold both. Agents receive no Registry administration, and later Coordination access is limited to its service needs. Retain attributable audit records, revocation, protection against accidental loss of the last usable administrator, and explicit owner-controlled recovery that keeps first-time bootstrap closed. The foundation's local OS grants do not establish Registry administration.

Use [personal access tokens](agent-registry.md#authentication-and-protected-first-owner-setup) for the stable human identity, with verification hashes/metadata in access-owned records and protected local raw-token delivery. Explicit local CLI setup verifies installation-owner access and durably establishes owner/grants and closes bootstrap; local recovery preserves initialization/history. API and local CLI use the same credential/current-grant checks, and administrative CLI use requires no HTTP server.

Provisioning identifies the trusted OS owner and protects private state paths; setup/recovery verify the actual principal and resource protections. Grants distinguish actions and target scopes. [Protected credential delivery](agent-registry.md#protected-credential-delivery) saves the new secret durably before database activation. Register the verifier, access changes, and audit together; uncertain registration is reconciled using a nonsecret identifier while retaining the protected file. Rotation keeps this ordering. Filesystem and database effects are separate, and last-administrator removal requires an established replacement or recovery path.

### API hosting baseline

Use [FastAPI and Uvicorn](agent-registry.md#api-hosting) inside the existing Python application, initially with one server process bound to loopback. Credential-bearing HTTP access uses HTTPS; broader exposure is explicit. Reuse the shared application operations and SQLite ownership. Coordinate configuration/store validation, truthful API readiness, signal handling, shutdown, and cleanup with the foreground lifecycle.

Verify direct package versions with CPython 3.14.10 before pinning, retain the complete `uv.lock` resolution, and let FastAPI select compatible Starlette. Use direct Uvicorn TLS with operator-provisioned certificate/key files and explicit client CA/endpoint verification. Extend the single strict configuration resolver and pass resolved settings programmatically. Keep caller context immutable per invocation and connections/transactions operation-owned. Distinguish listener, administrative, and execution availability; administration remains locked before owner setup, and unavailable qualification does not block catalog administration. Shutdown withdraws readiness, stops admission, drains within a configured deadline, and closes once; HTTP cancellation cannot establish rollback.

### Operation and persistence baseline

The [operation contract](agent-registry.md#operation-contracts) groups authoring, assessment/publication, retrieval, current controls, and separately authorized access administration behind explicit targets, validated inputs, trusted caller context, and safe business results under the existing outcomes. The [persistence rules](agent-registry.md#persistence-and-failure-boundaries) retain separate logical Registry/access ownership and application-owned transactions. Each logical mutation commits with its required audit record; publication rechecks current applicability and exact references. Retain referenced history and keep transactions short. Earlier successful preparation steps survive a later failure; resume inspects them. Unsuccessful attempts have separate audit handling with truthful audit-unavailability reporting. Uncertain effects require reconciliation before replay.

Distinguish stable identities, drafts, exact publications, current controls, and access targets; creation identifies the intended identity or collection. Keep mutable edit versions separate from immutable publication IDs, and check expected mutable versions inside changes. Use strict operation-specific inputs and safe read results with observed references/versions. Declare override types, units, and bounds per field. API and CLI preserve one logical outcome contract; transport/exit codes add precision. Repeat reads under current authorization, enforce uniqueness and expected versions for writes, and provide no general automatic write-replay guarantee.

The [retention contract](agent-registry.md#retention-and-reconciliation) preserves published revisions, required dependencies, review provenance, and audit without hard deletion in Increment 2. Authorized draft discard preserves required history. Reconcile using exact revisions/control versions and correlated audit; insufficient evidence preserves uncertainty. Raw credential-file cleanup follows established registration/revocation status separately, retaining nonsecret identifiers and revocation history.

### Bootstrap inputs and evidence baseline

The [preparation contract](agent-registry.md#bootstrap-inputs-and-preparation-evidence) requires reviewed Role/shared-rule snapshots, complete candidate Profiles for one primary execution path, exact published governing definitions, and applicable administrator authority. Required missing values keep definitions in draft; test fixtures do not substitute for the prepared catalog. Completion evidence identifies all five published Agent/Profile revisions, dependencies, provenance, and current disabled state, with restart preservation, repeat/resume behavior, explicit conflict handling, and representative controlled failure checks. Retain identified inputs, application versions, results, and limitations in generated submission evidence. Qualification, enablement, execution, project/forge bindings, and external accounts remain later activities.

The [candidate specification](agent-registry.md#bootstrap-candidate-specification) supplies actual execution settings, versioned nonsecret connection/credential references, exact governing definitions, applicable numeric ceilings, and captured instruction source versions. Preserve the five agreed Role intents and keep every Agent disabled with no administrative grants. Installed use must receive explicit packaged or supplied inputs rather than silently reading the checkout.

### Current controls and overrides baseline

The [current controls](agent-registry.md#current-controls) distinguish explicit selected revisions and present enablement from immutable history. Publication does not select or enable; disablement prevents selection for ordinary work and dispatch while administrative revision selection remains available. Stopping active work remains a separate authorized control. Initial [Agent overrides](agent-registry.md#permitted-overrides) only lower declared execution ceilings and remain explicit, validated, reviewed, and versioned. Other changes to Profile settings use reviewed Profile revisions. All governing constraints and qualification requirements still apply; existing Run records remain pinned while current revocations and stop controls follow enforcement/recovery rules.

### Initial enablement baseline

The [Coordination-owned qualification-check boundary](agent-registry.md#enablement-before-coordination-qualification) reports unavailable in Increment 2 production. Authorized enable requests leave current enablement unchanged; unauthorized requests are refused. Authorized disablement remains independent of qualification availability and commits with its required audit. Preparing, publishing, and administratively selecting disabled revisions remain ordinary authorized operations. Later enablement requires an explicit request and fresh exact-configuration checks; no automatic/pending enablement, forced-enable path, or manual qualification assertion is introduced. Stored enabled flags do not establish current eligibility. Positive qualification doubles stay isolated from production and bootstrap evidence; the five prepared Agents remain disabled.

### Review of current position

The documentation review covered definitions, requirements/configuration, decisions, responsibilities, all Roles and shared rules, architecture, workflow, infrastructure boundaries, the Registry guide, this plan, and all diagram views. No unresolved high-level contradiction remains. Wording distinguishes Agent delivery review from human Registry review and administrative revision selection from selection for ordinary work.

Increment 1 remains the accepted implemented foundation. A read-only refresh verified the retained archive hash and all 36 non-Markdown manifest files against the checkout; documentation has evolved separately. No application tests or live infrastructure checks were repeated for this documentation review.

Increment 2 remains unimplemented: Registry declarations have no business handlers, the application reports its business capabilities unavailable, only the foundation migration exists, and FastAPI/Uvicorn are not runtime dependencies yet. The current operation boundary handles foundation inputs/results and a composed local caller; Task 1 must define business targets/read payloads and isolated trusted caller context for real administrative requests. Hosting and credential configuration also require deliberate extensions.

The [developer brief](implementation-instructions.md) assigns the remaining concrete contracts within the agreed baseline; review each contract before its dependent implementation. Physical tables and endpoint names can be developer proposals under these rules. Required candidate values are needed for Task 5 publication and completion. This review and handoff preparation do not establish Increment 2 implementation, verification, or acceptance.

### Developer handoff

Use the fresh [Increment 2 implementation brief](implementation-instructions.md) for the six Tasks, positive/failure examples, required checks, and handoff contents. Retain foundation regressions; verify real disk transactions/migrations, access/credential protections, TLS/caller isolation, API/CLI parity, lifecycle behavior, and installed-wheel bootstrap with explicit inputs.

Capture Increment 2 separately under ignored `submissions/increment-2/`, preserving Increment 1's accepted archives. Identify the combined source and input versions, environment/dependencies, performed commands, raw results, failures, and limitations. Adapt Increment 1-oriented capture/wheel tools without overwriting prior evidence or suppressing meaningful regressions. Independent assessment reviews the same source and reproduces material checks; the developer's verification and designated acceptance remain separate.

### Remaining decisions for Increment 2

The high-level scope, authoring/publication, administrator authority and authentication, first-owner setup, API hosting, operation/persistence behavior, bootstrap preparation, controls/overrides, and initial unavailable-enablement behavior are agreed. The following implementation choices remain open. Settle each contract before its dependent code; concrete candidate inputs are required for Task 5 publication and completion, rather than for every earlier foundation step.

| Area | Remaining decision or contract | Needed by |
| --- | --- | --- |
| Administrator access | Exact OS ownership/protection checks, token verification format/lifetimes, protected-file durability checks, grant actions/targets, revocation/recovery and last-administrator procedures, and registration reconciliation under the delivery-before-activation contract. | Authorized administration and its API/CLI adapters. |
| API hosting | Tested package pins, bind/port values, certificate provisioning/trust steps, concrete configuration and request/status formats, safe error mapping, and signal/drain/cleanup integration under the agreed lifecycle. | API hosting and composition. |
| Registry operations | Concrete target/reference/input/read-result schemas and mutable versions, review/stale-edit checks, declared override fields/units/bounds, per-operation uniqueness/retry details, API/CLI mappings, and unavailable qualification-check formats. | Dependent operations and storage. |
| Persistence and history | Physical schema/migrations and integrity constraints, concrete transaction/audit-outage paths, reconciliation lookups, and implementation of retained published history, authorized draft discard, and separate credential cleanup. | Durable publication, administration, and controls. |
| Concrete bootstrap inputs | Candidate runtime/model/transport, connection references, numeric limits, governing definitions, and instruction source versions under the agreed preparation contract. Required missing settings remain publication blockers. | Task 5 publication and completion. |

The active brief assigns the remaining concrete contracts under the agreed rules; no further broad Registry architecture choice is required. Do not defer security/failure boundaries to accidental implementation defaults. Live provider access, qualification Runs, scheduling, Workers, Gitea/project integration, production qualification, and optional Git import/export remain outside Increment 2's required implementation path.

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
