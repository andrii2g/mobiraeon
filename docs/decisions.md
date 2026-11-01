# Decision register

This document defines Möbiræon’s design baseline for implementation and the first live demonstration. Detailed workflows, operating parameters, and integration qualification build on these decisions.

| ID | Decision |
| --- | --- |
| [D-01](#d-01-system-and-repository-name) | System and repository name |
| [D-02](#d-02-agent-and-component-terminology) | Agent and component terminology |
| [D-03](#d-03-hierarchy) | Project and Task hierarchy |
| [D-04](#d-04-lifecycles) | Lifecycles and acceptance |
| [D-05](#d-05-registry) | Agent Registry storage and editing |
| [D-06](#d-06-execution-boundary) | Execution boundary |
| [D-07](#d-07-forge-integration-and-initial-platform) | Forge integration and initial platform |
| [D-08](#d-08-initial-profiles) | Initial Profiles and qualification |
| [D-09](#d-09-operating-policy) | Operating policy |
| [D-10](#d-10-authority) | Authority and delegation |
| [D-11](#d-11-implementation-technology-and-topology) | Implementation technology and topology |
| [D-12](#d-12-first-live-validation-and-release-scope) | First live validation and release scope |

## D-01 System and repository name

The system name is **Möbiræon**. The repository name and ASCII identifier are **`mobiraeon`**. The [README](../README.md) describes the name’s origin.

## D-02 Agent and component terminology

| Term | Meaning |
| --- | --- |
| **Agent** | A logical AI actor with a stable registered identity. |
| **Agent Profile** | Reusable, versioned execution configuration. |
| **Worker** | Execution capacity for Agent Runs. |
| **Runner Adapter** | An adapter that invokes a configured runtime through a transport. |
| **Run** | One bounded execution attempt with an immutable configuration record. |
| **Coordinator** | The component enforcing authoritative workflow state, permissions, and acceptance gates. |
| **Scheduler** | The component applying deterministic eligibility and dispatch rules within configured limits. |
| **Orchestrator Agent** | The Agent responsible for planning, routing, and decision reasoning through authorized operations. |

These are logical responsibilities and may share a service or process. Runtime integration, runner transport, provider, and model identities remain separate configuration properties. The [definitions](definitions.md) provide the governing vocabulary.

## D-03 Hierarchy

Use **Project → Initiative → Task**. A Project contains Initiatives; an Initiative represents an intended outcome; Tasks produce bounded deliverables. Milestones group delivery targets.

Initial decomposition creates linked Tasks within the Initiative, preserving traceability to their originating Task. Avoid nested Task trees in the first release.

Parent relationships describe scope membership. Execution dependencies identify prerequisites independently, following F-12 and F-13.

## D-04 Lifecycles

Model Task, Run, and Decision lifecycles separately, with acceptance recorded independently of execution status.

Review and verification normally use assignments and Runs within a Task’s workflow. Rework starts another Run of the same logical Task.

A Task is accepted when its deliverable contract, designated authority, and required evidence establish acceptance. A reviewed-patch Task may finish before a separately assigned integration Task when its contract permits this. Overall code delivery requires validation of the exact combined revision under F-21.

In the initial workflow, the Coordinator routes routine assessment and in-scope rework under approved rules; independent review and required verification do not need another Orchestrator Run merely for routing. A separate Verifier/QA Agent Run is needed when the contract or policy requires it. Ordinary implementation Task contracts include authorized integration and fresh validation of the exact combined revision; reviewed-patch acceptance is permitted when integration is explicitly assigned separately. See the [workflow defaults](workflow.md#initial-defaults).

The [integration handoff](workflow.md#integration-and-combined-result-validation) connects reviewed work, authorized integration, validation of the combined result, and acceptance or rework. Initiative acceptance remains an assessment of the overall intended outcome.

Complete an Initiative when its required delivery obligations are satisfied, current evidence establishes its overall outcome, no unresolved required condition prevents acceptance, and its designated authority accepts. The Coordinator enforces and records the determination. The Orchestrator coordinates any missing assessment or work under the [Initiative outcome workflow](workflow.md#initiative-outcome-acceptance).

Record Request fulfillment when accepted delivery satisfies its own agreed outcome under the [closure rule](workflow.md#request-closure-and-follow-up), rather than requiring every related Initiative to finish. Later defects normally lead to linked repair work, and changed goals to a linked new Request. Reassess and correct affected acceptance or closure when evidence undermines the original fulfillment, preserving its history. Cancellation, rejection, and duplicate handling have distinct closure reasons.

Workflow specifications define the state names, transitions, and recovery behavior.

## D-05 Registry

Implement the Agent Registry as a forge-independent **Python module in the Möbiræon repository and application**, with its own authenticated, versioned management API and authoritative **SQLite persistence**. Initially share the application and database with Coordination while preserving separate logical ownership. Gitea is an external forge integration, not the Registry's store or administrative interface.

Manage stable Agent identities, reusable Profiles, versioned instructions, and their policy and integration references through the approved configuration contract. Publish reviewed, validated definitions under immutable, retrievable **Registry revision IDs**, not Git commit identities. Resolve exact references for each Run and retain its immutable configuration snapshot. Authorized edits produce new revisions; concurrent editing must not silently overwrite another change.

Use [editable drafts, validation, review, and immutable publication](agent-registry.md#authoring-and-publication). Review applies to the exact candidate and dependencies; subsequent edits require renewed review. The same authorized human may author, review, and publish when policy permits. Publication validates published dependencies, leaves no partial published result on failure, and does not automatically change dependent Agent/Profile bindings. Returning to earlier settings creates a new reviewed revision under current checks.

Use the [shared operation contracts](agent-registry.md#operation-contracts) for authoring, assessment/publication, retrieval, current controls, and separately authorized access administration. Keep Registry and access-owned records logically distinct under the existing SQLite foundation and application-owned transactions. Each logical mutation and its required audit record commit together; unsuccessful attempts use separate audit handling. Publication rechecks current applicability, and retained history preserves exact references. Preparation composes per-operation commits, so earlier successful steps survive a later failure. Reconcile uncertain effects before replay; concrete schemas and failure/audit mappings remain contracts under the [persistence rules](agent-registry.md#persistence-and-failure-boundaries).

For Increment 2, [retention and reconciliation](agent-registry.md#retention-and-reconciliation) preserve published revisions, required dependencies, review provenance, and audit without hard deletion. Authorized draft discard preserves required history. Reconciliation uses exact revisions/control versions and correlated audit; insufficient evidence preserves uncertainty. Raw credential-file cleanup is separate and follows established registration/revocation status while retaining nonsecret identifiers and revocation history.

Publication, execution qualification, administrative enablement, and authority for particular work remain separate determinations. Registry administration is authorized and audited; changing configuration cannot grant permissions beyond governing policy. External forge-account bindings remain distinct from reusable Profiles and model-provider accounts.

Keep [current revision selection and enablement](agent-registry.md#current-controls) auditable and distinct from immutable history; publication does not select or enable a revision. Disablement prevents selection for ordinary work and dispatch; administrative revision selection for a disabled Agent remains available. Active stopping remains a separate control. Initially permit only [declared execution-ceiling reductions](agent-registry.md#permitted-overrides) as reviewed Agent overrides. Other changes to Profile settings use new reviewed Profile revisions. All governing constraints and qualification checks still apply; reject conflicts, unsupported settings, budget resets, and silent substitutions.

While Coordination qualification is unimplemented, [authorized enable requests report unavailable](agent-registry.md#enablement-before-coordination-qualification) without changing current enablement; authorized disablement remains usable independently. The production qualification-check boundary creates no qualification evidence or manual bypass. Later enablement requires an explicit request and fresh exact-configuration checks; no automatic/pending enablement or forced-enable path is introduced. Stored enabled flags are separate from present eligibility, and positive qualification test doubles remain isolated from production and bootstrap evidence.

Use one explicitly designated human administrator initially, established through protected local first-owner setup. Keep administrative access controls outside publishable Agent definitions. [Bootstrap initialization](agent-registry.md#administrator-access-and-bootstrap-authority) persists independently of catalog contents; recovery does not reopen first-time setup. API and CLI enforce the same current permissions, including protected reads. Catalog and administrative-grant permissions remain distinct; Agents receive no Registry administration in Increment 2. Audit bootstrap, access changes, recovery, and catalog actions; preserve revocation and protection against accidental loss of the last usable administrator.

Authenticate the stable human identity with [individually revocable personal access tokens](agent-registry.md#authentication-and-protected-first-owner-setup). Keep verification hashes and metadata in access-owned records and deliver raw credentials through protected local storage. Explicit local CLI setup verifies installation-owner access and durably establishes owner/grants and closed bootstrap; protected local recovery preserves initialization and history. API and local CLI use the same current authorization operations; administrative CLI use does not require the HTTP server. Concrete credential and ownership-proof procedures remain implementation contracts.

Provisioning identifies the trusted OS owner and protects private application state; setup/recovery verify the actual principal and Linux permissions or Windows ACLs. Grants specify actions and target scopes. [Credential delivery precedes activation](agent-registry.md#protected-credential-delivery): durably save a new protected credential, then commit its verifier, access changes, and audit together. Filesystem and database effects remain separate; uncertain registration requires reconciliation. Rotation preserves this ordering, and removal of the last usable administrative access requires an established replacement or recovery path.

Git import/export is optional and follows the same validation and authority rules. SQLite remains the single authoritative Registry store; imports, exports, and any Git repository do not become a second live authority. Keep Worker availability, active Runs, and other operational state logically outside the Registry. Store credential values in the configured secret-management mechanism and use references in configuration.

Backup and recovery must preserve Registry revisions and the references used by historical Runs alongside coordination state and retained Artifacts. Detailed API, persistence, and override-resolution contracts remain specifications.

Start with the five Agents in the [initial catalog](agent-registry.md#initial-agent-catalog), using Role-specific Profiles and [administrator-led preparation](agent-registry.md#first-agent-preparation). An authorized human uses the Registry CLI to create disabled Agents, review and publish definitions, qualify the candidate configuration, and enable eligible selection. Qualification checks do not dispatch a disabled Agent or override revoked access. Catalog changes in the pilot remain administrator-led; Agents do not create or enable other Agents.

For Increment 2, [bootstrap preparation](agent-registry.md#bootstrap-inputs-and-preparation-evidence) completes with a reviewed, published, persistent catalog of those five Agents, all disabled. Use identified instruction snapshots, complete candidate Profiles, exact published governing definitions, and applicable administrator authority. Evidence covers exact retrieval/provenance, restart, repeat/resume and conflict handling, and representative controlled failures. Required missing inputs remain drafts; test fixtures do not substitute for the prepared catalog. Qualification, enablement, execution, project/forge bindings, and external accounts remain later activities.

The [bootstrap candidate specification](agent-registry.md#bootstrap-candidate-specification) requires actual selected execution settings, nonsecret versioned connections/credential references, governing definitions, applicable ceilings, and identified captured instructions before publication. Keep this input set distinct from test fixtures; packaging or supplied inputs must support installed use outside the checkout.

## D-06 Execution boundary

The initial deployment uses **one Linux control host and locally attached, isolated container Workers**. Authorized cloud or local model connections are configured independently of Worker placement.

Qualify the first workflow before adding remote Worker transports and other host operating systems.

Execution qualification covers process-tree cleanup, workspace boundaries, network access, credentials, and resource controls under N-02 through N-04. Record the supported host, container, runtime, and enforcement versions with the qualification evidence.

## D-07 Forge integration and initial platform

Use **local Gitea** as the initial human-facing forge interface through a versioned, forge-neutral adapter contract.

Represent each Request as a separate intake issue, retaining its discussion and links to the resulting existing or new Initiative and Tasks. The normal human entry point is a Request; authorized humans may also submit Task candidates for the same validation and readiness checks.

Map Initiatives and substantive Tasks to issues, delivery targets to milestones, and code submissions to pull requests. Möbiræon owns authoritative workflow state, Runs, execution ownership, retry state, policy enforcement, and acceptance. Routine review events do not require separate forge items.

Adapters translate supported operations and events, declare capabilities, and preserve traceable mappings between internal and external records. Qualify the Gitea adapter first, then add GitLab and other forge integrations through the same contract.

Begin with an in-process adapter and one active operational forge per Project. Project migration and cross-forge synchronization are separate capabilities.

Use one stable Gitea automation account for each registered Agent that acts in the forge, plus a separate Coordination service account. Project integration configuration binds forge identities and permitted operations separately from reusable Profiles and model-provider accounts.

Account access grants no workflow authority and does not establish review independence. Privileged operations remain subject to Coordinator enforcement; configuration retains secret references rather than credential values. The [forge identity model](agent-registry.md#forge-identities) describes these boundaries.

## D-08 Initial Profiles

Use strong reasoning Profiles for clarification, architecture, specifications, and consequential Decisions. Use medium reasoning Profiles for routine implementation and configure review independently.

The requested execution paths are Codex CLI, Claude Code CLI, and an Ollama-backed coding harness. Qualify one primary path first, then the remaining integrations. Enable concrete runtime, provider, account, model, reasoning, and option combinations for their qualified scope under F-09.

Interpret reasoning settings through each integration’s versioned capabilities. Review may use the same model as authoring when its separate assignment and Run satisfy the independence policy. Changing the author’s role or Profile alone does not establish independence.

Fallbacks follow F-06 and F-08: substitutions require explicit authorization and validation, and changes to pinned execution configuration create a new Run under the same Task.

## D-09 Operating policy

Use an approved, versioned pilot operating profile defining execution, concurrency, retry, spending, recovery, and retention limits. Enforce cumulative limits and accounting across retries, reassignments, and fallbacks.

On exhaustion, preserve progress and stop, pause, or return control to the Orchestrator Agent according to policy. Create a human escalation when resolution requires human authority or input.

Apply the [waiting and recovery rules](workflow.md#waiting-and-recovery): wait durably for missing conditions, retry only recoverable authorized work through a new Run within remaining limits, reassign eligible execution under the same Task, or stop affected automation when continuation is not permitted. Preserve exclusive ownership, history, cumulative limits, and human holds across restart. Reconcile uncertain effects before repeating operations; return capacity only after cleanup or effective containment.

The operating profile supplies numeric limits, measurement methods, enforcement boundaries, and treatment of estimated or unavailable usage and cost. Verify enforcement, recovery, and retention behavior before live operation under N-01, N-02, N-05, and N-07.

## D-10 Authority

Human approval establishes the initial baseline and delegation policy. Within that policy, Agents may resolve ordinary Decisions, perform independent review, exercise explicitly delegated acceptance authority, and integrate into the designated local delivery target without additional human approval.

The Coordinator enforces authority and records acceptance when the required evidence and gates are satisfied. The delegation policy identifies authorized actors, operations, targets, and applicable gates. Execution configuration and project policy govern repository, infrastructure, and deployment permissions.

Independent assessment and acceptance authority are distinct responsibilities. Policy may explicitly assign both to the same eligible reviewer.

For the initial workflow, explicitly delegate ordinary Task acceptance to an eligible independent reviewer, conditional on all required current evidence and gates. The Coordinator enforces and records that determination. A contract or policy may require another designated authority; the default does not grant authority through Role text alone.

Use an eligible independent Reviewer with explicit Initiative-level delegation for Initiative outcome acceptance; human acceptance applies where policy reserves it. Ordinary Task acceptance authority does not automatically extend to Initiative acceptance. Reuse applicable assessment and validation evidence, arranging additional assessment where needed.

An explicit Request closure rule may use accepted outcomes without another approval or Run. Broader or unresolved Request-level judgment requires applicable authority; Task or Initiative delegation alone does not supply that grant.

Authorized [human controls](workflow.md#human-controls-and-scope-changes) reach the Coordinator directly. Pause holds new starts and winds down affected Runs; resume lifts only the selected hold and rechecks conditions before new execution. Cancellation ends selected work without establishing acceptance or automatic undo. Reprioritization changes eligible pending order without automatic preemption. Takeover holds automation and retires prior execution ownership, with cleanup or containment before exclusive human work. Returning to automation is explicit; human-produced changes follow normal acceptance gates. Controls and authorized scope changes preserve history and respect broader holds, cancellation, and limits.

Changes to scope, authority, infrastructure, or spending outside delegation require escalation through the Orchestrator Agent. Only the Orchestrator Agent initiates agent-generated requests for human decisions or intervention; ordinary human review follows project policy.

## D-11 Implementation technology and topology

Implement the first release in **Python**, with one active Coordinator/Scheduler service and supervised, isolated Agent runner processes.

Target **CPython 3.14**, initially pinning **3.14.10**, with `requires-python = ">=3.14,<3.15"`. Package one installable `mobiraeon` distribution under `src/mobiraeon`, with a separate test tree. Use `pyproject.toml`, **uv**, the **uv_build** backend, and a committed `uv.lock`; keep runtime and development dependencies separate. Use **pytest** and **Ruff** for development checks. Record tool versions and control dependency updates; expand the Python target range after verification.

Use **SQLite on local persistent disk** for authoritative Registry definitions and durable coordination state. The first deployment shares one application and database: the Registry module owns catalog changes through its authorized API, while the Coordinator controls authoritative workflow changes. Runners submit results through authorized operations. Retain substantial artifacts separately with durable, versioned references.

Use synchronous **SQLAlchemy Core** with Python's `sqlite3` driver and **Alembic** for one application-level migration sequence. Keep domain contracts independent of storage types. Explicit creation and upgrades are separate from ordinary startup, which validates an existing store. Preserve atomic migration/revision updates and module transaction ownership. Start with SQLite's rollback journal. The [foundation guide](../README.md#storage-and-authorization-boundaries) details the storage and authorization contract.

The first foundation uses a foreground local application host and CLI. Host the Registry HTTP API with **FastAPI and Uvicorn in the same application**, initially using one server process bound to loopback. Require HTTPS for credential-bearing HTTP access; broader exposure requires explicit configuration. API and CLI share application operations and SQLite ownership. Preserve one coordinated lifecycle, truthful API readiness after configuration/store validation, signal handling, and cleanup before terminal success. See the [hosting model](agent-registry.md#api-hosting), [FastAPI OpenAPI support](https://fastapi.tiangolo.com/features/), [lifespan integration](https://fastapi.tiangolo.com/advanced/events/), and [Uvicorn configuration](https://www.uvicorn.org/settings/). Package versions, port/TLS configuration, and operating values remain implementation contracts.

Verify and pin FastAPI/Uvicorn direct versions with CPython 3.14.10, retain the complete `uv.lock` resolution, and let FastAPI select compatible Starlette. Use direct Uvicorn TLS with operator-provisioned certificates and explicit client CA/endpoint verification. Extend the single strict configuration resolver; construct immutable caller context per invocation and operation-owned synchronous database connections. Distinguish listener, administrative, and execution availability. Shutdown withdraws readiness, stops admission, drains within a configured deadline, and closes resources once; request cancellation cannot establish rollback. Exact pins, TLS provisioning, fields, and deadlines remain concrete contracts.

Integrate Gitea through the forge-adapter contract.

Preserve transactional state changes, durable dispatch and operation records, recoverable ownership, stale-result rejection, idempotency or reconciliation, and audit history. Test backup, restoration, and recovery across Registry revisions, coordination and per-Run records, and retained artifacts so their durable references remain resolvable.

Reassess PostgreSQL or other infrastructure when multi-instance operation, availability requirements, or measured workload justify it.

## D-12 First live validation and release scope

Deliver one bounded feature in a prepared, existing repository using local Gitea, the Linux/container execution environment, and one primary qualified execution path. Prepare and review its working baseline before automated feature execution; repository creation and application scaffolding are preparation outside the pilot.

Exercise the complete delivery workflow:

1. Intake and clarification.
2. Specification and baseline approval.
3. Task planning and implementation.
4. Independent review and authorized integration.
5. Validation of the exact combined revision and outcome acceptance.

Demonstrate Decision waiting and continuation, interrupted-Run recovery, duplicate-event reconciliation, and rejection of stale results.

Before execution, approve a pilot contract identifying the repository and revision, bounded feature, acceptance criteria, permitted operations, execution configuration, operating limits, and required evidence. The release scope identifies included integrations and those deferred to later increments.

Greenfield project creation and production deployment are outside this pilot.

Select the concrete repository, bounded feature, starting revision, and scenario-specific acceptance criteria during [implementation planning](implementation-plan.md).

## Implementation specifications

Implementation preparation supplies:

- detailed workflow states, transitions, acceptance gates, and recovery procedures;
- Registry API and persistence contracts, schemas, publication and concurrent-edit rules, and override resolution;
- authenticated API integration contracts, remaining dependency and execution versions, and isolation controls under D-11's selected technology baseline;
- numeric operating limits, recovery targets, retention rules, and verification methods;
- concrete delegation rules, authorized identities, operations, and targets;
- the executable pilot contract and integration qualification evidence.

The [implementation plan](implementation-plan.md#remaining-specifications) tracks these specifications and their required timing. Its [qualification and live-pilot gates](implementation-plan.md#gates-before-qualification-or-live-pilot-execution) identify execution prerequisites; [verification and evidence](implementation-plan.md#verification-and-evidence) defines the required records. Qualification results identify the tested revisions and environments.

## Maintaining decisions

Changes to this baseline follow the designated decision authority. Record the chosen option, rationale, constraints, affected requirements, and artifact revisions; update the authoritative documentation and retain links to superseded decisions.

Implementation, qualification, and delivery progress are tracked through their own Tasks, evidence, and acceptance records.
