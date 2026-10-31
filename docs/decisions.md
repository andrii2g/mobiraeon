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

Use a dedicated Git repository containing **JSON configuration and Markdown instructions**. Identify published configuration revisions by exact Git commits and retain them as immutable, retrievable sources.

Begin with Git-based editing and review. Future editors use the same validation and publication process. Resolve configuration to specific revisions for each Run and retain immutable configuration snapshots in operational storage.

Keep Worker availability, active Runs, and other operational state outside the Registry. Store credential values in the configured secret-management mechanism and use references in configuration.

Detailed schemas, global/project catalog organization, and permitted override resolution follow the Agent configuration contract and configuration specifications.

The [Agent onboarding and forge-identity proposal](pilot-and-agent-setup.md#registry-and-gitea-identities) builds on this storage choice; its concrete repository and account mappings remain under discussion.

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

Use **SQLite on local persistent disk** for durable coordination state. The Coordinator controls authoritative database changes; runners submit results through authorized operations. Keep published Agent Profiles and instructions in Git and retain substantial artifacts separately with durable, versioned references.

Integrate Gitea through the forge-adapter contract.

Preserve transactional state changes, durable dispatch and operation records, recoverable ownership, stale-result rejection, idempotency or reconciliation, and audit history. Test backup, restoration, and recovery across the database, retained artifacts, and referenced configuration revisions.

Reassess PostgreSQL or other infrastructure when multi-instance operation, availability requirements, or measured workload justify it.

## D-12 First live validation and release scope

Deliver one bounded feature in a prepared, existing demonstration repository using local Gitea, the Linux/container execution environment, and one primary qualified execution path.

Exercise the complete delivery workflow:

1. Intake and clarification.
2. Specification and baseline approval.
3. Task planning and implementation.
4. Independent review and authorized integration.
5. Validation of the exact combined revision and outcome acceptance.

Demonstrate Decision waiting and continuation, interrupted-Run recovery, duplicate-event reconciliation, and rejection of stale results.

Before execution, approve a pilot contract identifying the repository and revision, bounded feature, acceptance criteria, permitted operations, execution configuration, operating limits, and required evidence. The release scope identifies included integrations and those deferred to later increments.

Greenfield project creation and production deployment are outside this pilot.

The concrete repository, feature, and setup sequence are proposed in the [pilot discussion](pilot-and-agent-setup.md#demonstration-pilot); they do not become selected merely by appearing as candidates.

## Implementation specifications

Implementation preparation supplies:

- detailed workflow states, transitions, acceptance gates, and recovery procedures;
- Registry schemas, catalog organization, and override-resolution rules;
- the Python framework, packaging, exact execution versions, and isolation controls;
- numeric operating limits, recovery targets, retention rules, and verification methods;
- concrete delegation rules, authorized identities, operations, and targets;
- the executable pilot contract and integration qualification evidence.

The [implementation readiness review](implementation-readiness-review.md) tracks these specifications and their required timing. Qualification results are recorded against the tested revisions and environments.

## Maintaining decisions

Changes to this baseline follow the designated decision authority. Record the chosen option, rationale, constraints, affected requirements, and artifact revisions; update the authoritative documentation and retain links to superseded decisions.

Implementation, qualification, and delivery progress are tracked through their own Tasks, evidence, and acceptance records.
