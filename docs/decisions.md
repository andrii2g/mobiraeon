# Decision register

This register records the confirmed design baseline and identifies details that remain to be specified. D-01 through D-12 are confirmed. Further recommendations remain Proposed until approved by the applicable authority. Agreement status is separate from implementation and qualification progress.

## Confirmed direction

- Prepare and review definitions and requirements before further implementation work.
- Keep architecture and workflow concise, and distinguish logical contracts from selected implementation technologies.
- Support configurable agents and a stored agent collection, including the requested Codex CLI, Claude Code CLI, and Ollama execution paths.
- Keep human review of the initial brief/specification and route later human escalation through the Orchestrator Agent.
- Use the confirmed D-02 terminology and separate Coordinator, Scheduler, and Orchestrator Agent responsibilities logically; this does not require separate services.
- Use Gitea as the initial local forge through a versioned, forge-neutral adapter contract; Möbiræon retains workflow and acceptance authority.
- Implement the first release in Python with one active Coordinator/Scheduler service, supervised isolated runner processes, and SQLite on local persistent disk.
- The confirmed system name is **Möbiræon**, with **mobiraeon** as the repository name and ASCII identifier.

## Decision register

| ID | Status | Choice to resolve | Current recommendation or next clarification |
| --- | --- | --- | --- |
| D-01 | Confirmed | System and repository name | Keep **Möbiræon** as the system name and **mobiraeon** as the repository name and ASCII identifier. Confirmed on 2026-10-30; earlier candidates are superseded. See the [name explanation](../README.md). |
| D-02 | Confirmed | Agent and component terminology | Agent is a logical AI actor with stable registered identity; Agent Profile is reusable versioned execution configuration; Worker supplies execution capacity; Runner Adapter invokes a runtime through a transport; Run is one bounded attempt. Coordinator, Scheduler, and Orchestrator Agent have separate logical responsibilities. See [definitions](definitions.md). Confirmed on 2026-10-30. |
| D-03 | Confirmed | Project and work hierarchy | Use Project → Initiative → Task. Initiatives represent outcomes, Tasks produce bounded deliverables, and milestones group delivery targets. Initially decompose into linked Tasks within the Initiative, preserving origin traceability, rather than nested Task trees. See the [agreed hierarchy](#d-03-hierarchy). |
| D-04 | Confirmed | Lifecycles | Keep Task, Run, Decision, and acceptance state separate. Review and verification normally use assignments/Runs within the Task workflow; rework starts another Run of the same Task. Completion does not establish acceptance. Exact state names and transitions remain to be agreed. See [lifecycle principles](#d-04-lifecycles). |
| D-05 | Confirmed | Agent Registry storage and editing | Use a dedicated Git repository with JSON configuration and Markdown instructions. Published revisions are identified by exact Git commits, immutable, and retrievable. Git-based editing/review and any future editor share validation/publication; operational state and per-Run snapshots remain separate. See the [publication boundary](#d-05-registry). |
| D-06 | Confirmed | Execution boundary | Start with one Linux control host and locally attached, isolated container Workers; authorized cloud/local model connections are independent of Worker placement. Qualify the first workflow before adding remote transports and other host operating systems. See the [execution boundary](#d-06-execution-boundary). |
| D-07 | Confirmed | Forge integration and initial platform | Use local Gitea as the initial human-facing forge interface through the versioned, forge-neutral contract. Map Initiatives/substantive Tasks to issues, delivery targets to milestones, and code submissions to pull requests. Möbiræon retains workflow/acceptance authority and operational records. See the [agreed boundary](#d-07-forge-integration-and-initial-platform). |
| D-08 | Confirmed | Initial profiles and qualification | Use strong reasoning Profiles for planning and consequential Decisions, medium Profiles for routine implementation, and independently configured review. Qualify one primary path first, then remaining requested integrations; concrete combinations are enabled only for qualified scope. See [profile policy](#d-08-initial-profiles). |
| D-09 | Confirmed | Operating policy | Adopt an approved, versioned pilot operating profile with explicit limits, cumulative accounting, controlled exhaustion handling, and qualified enforcement/recovery targets. Numeric values remain to be approved. See [operating policy](#d-09-operating-policy). |
| D-10 | Confirmed | Authority | Human approval establishes the baseline and delegation policy. Agents act within delegation, including independent review, explicitly delegated acceptance, and authorized local integration; the Coordinator enforces gates and authority. See [authority](#d-10-authority). |
| D-11 | Confirmed | Implementation technology and topology | Use Python, one active Coordinator/Scheduler service, supervised isolated runner processes, and SQLite on local persistent disk. Retain published Profiles/instructions in Git and substantial artifacts separately. See the [confirmed baseline](#d-11-implementation-technology-and-topology). |
| D-12 | Confirmed | First live validation and release scope | Deliver one bounded feature in a prepared demonstration repository using local Gitea, the approved Linux/container environment, and one primary qualified execution path. Exercise the full delivery loop and recovery cases within an approved pilot contract. See [pilot scope](#d-12-first-live-validation-and-release-scope). |

## D-03 Hierarchy

**Confirmed on 2026-10-30.** Use **Project → Initiative → Task**. An Initiative represents an intended outcome; Tasks produce bounded deliverables. Milestones group delivery targets. Avoid nested Task trees initially: decomposition creates linked Tasks within the Initiative, with traceability to their origin.

Parent relationships describe scope membership; execution dependencies remain separate under F-12 and F-13.

## D-04 Lifecycles

**Confirmed on 2026-10-30.** Keep Task, Run, Decision, and acceptance state separate. Review and verification normally use assignments/Runs within a Task’s workflow, rather than automatically creating more Tasks. Rework starts another Run of the same Task.

A completed Run does not establish Task acceptance; acceptance follows the Task’s contract, designated authority, and required evidence.

This confirms lifecycle principles, not the previously proposed state-name lists or a complete transition model. Those details remain to be agreed consistently with the approved requirements, including the separate patch-delivery and integration contracts allowed by F-21.

## D-05 Registry

**Confirmed on 2026-10-30.** Use a dedicated Git repository containing **JSON configuration and Markdown instructions**. Published configuration revisions are identified by exact Git commits, immutable, and retrievable. Begin with Git-based editing and review; a future editor uses the same validation and publication process. Store operational state and immutable per-Run configuration snapshots separately.

This applies F-07 and F-08. Credential values remain in the configured secret-management mechanism. This selects the catalog format and publication boundary; it does not create a repository or authorize publication. Detailed schemas, project/global catalog organization, and permitted override resolution follow the approved configuration contract.

## D-06 Execution boundary

**Confirmed on 2026-10-30.** Start with **one Linux control host and locally attached, isolated container Workers**. Permit authorized cloud or local model connections independently of Worker placement. Add remote Worker transports and other host operating systems after the first workflow is qualified.

Isolation must be demonstrated against N-02 through N-04, including subprocess cleanup, workspace boundaries, network access, credentials, and resource controls. Container placement alone does not establish qualification. Exact host/container versions, the container runtime and enforcement configuration, and executable compatibility require qualification evidence; this decision does not provision them.

## D-07 Forge integration and initial platform

**Confirmed on 2026-10-30; interface and mapping scope reaffirmed on the same date.** Use **local Gitea as the initial human-facing forge interface** through the confirmed versioned, forge-neutral adapter contract.

Map Initiatives and substantive Tasks to issues, delivery targets to milestones, and code submissions to pull requests. Keep authoritative workflow state, Runs, execution ownership, retry state, policy enforcement, and acceptance authority in Möbiræon. Routine review events do not require separate forge items.

Adapters translate supported operations and events, declare capabilities, and preserve traceable external mappings.

Qualify the Gitea adapter first. Add GitLab and other forge integrations through the same contract.

Begin with an in-process adapter and one active operational forge per project. Project migration and cross-forge synchronization are separately scoped capabilities.

This selects the first forge and its integration boundary while preserving Möbiræon ownership of workflow authority. The decision applies F-16, F-20, F-21, F-22, F-24, and F-25. It records an approved design choice; adapter implementation and qualification evidence remain separate.

## D-08 Initial profiles

**Confirmed on 2026-10-30.** Use strong reasoning Profiles for clarification, architecture, specifications, and consequential Decisions; use medium Profiles for routine implementation. Configure review independently. Qualify **one primary execution path first**, then the remaining requested integrations. Interpret reasoning settings through each integration’s versioned capabilities; enable concrete combinations only for their qualified scope.

This confirms selection intent and qualification order, not support for untested model identifiers, accounts, versions, reasoning values, or options. The same model may serve authoring and reviewing roles when the separate review assignment and Run satisfy the configured independence policy. Any fallback remains subject to F-06 and the immutable Run-record rules in F-08.

## D-09 Operating policy

**Confirmed on 2026-10-30.** Adopt an approved, versioned pilot operating profile with explicit execution, concurrency, retry, spending, recovery, and retention limits. Apply cumulative limits across retries, reassignments, and fallbacks. Exhaustion causes a controlled stop, pause, or Orchestrator Agent triage under policy; it does not automatically create a human ticket. Qualify enforcement and recovery targets before live operation.

Numeric limits belong in a linked operating profile, with approval and qualification evidence recorded separately. This confirms the policy direction, not the previously suggested numeric values or evidence that controls have been implemented. The profile must satisfy N-01, N-02, N-05, and N-07, including treatment of estimated or unavailable usage and cost.

## D-10 Authority

**Confirmed on 2026-10-30.** Human approval establishes the initial baseline and delegation policy. Within that policy, Agents may resolve ordinary decisions, perform independent review, exercise explicitly delegated acceptance authority, and integrate into the designated local delivery target without additional human approval. The Coordinator enforces authority and records acceptance only when required evidence and gates are satisfied. Changes to scope, authority, infrastructure, or spending outside delegation require escalation through the Orchestrator Agent.

This applies S-03, S-05, S-06, F-18, F-20, F-21, and F-25. The concrete delegation policy must identify authorized actors, operations, targets, and applicable gates. This decision does not itself grant repository, infrastructure, or deployment permissions. Independent assessment and acceptance authority remain distinct responsibilities that policy may explicitly assign to the same reviewer.

## D-11 Implementation technology and topology

**Confirmed on 2026-10-30.** Implement the first release in **Python**, with a single active Coordinator/Scheduler service and supervised, isolated Agent runner processes.

Use **SQLite on local persistent disk** for durable coordination state. The Coordinator controls authoritative database changes; runners submit results through authorized operations. Keep published Agent Profiles and instructions Git-versioned, and retain substantial artifacts separately with durable, versioned references.

Integrate Gitea through the confirmed, versioned forge-adapter contract.

Preserve transactional state changes, durable dispatch and operation records, recoverable ownership, stale-result rejection, idempotency or reconciliation, audit history, and tested backup, restoration, and recovery.

Reassess PostgreSQL or other infrastructure when multi-instance operation, availability requirements, or measured workload justify it.

This applies F-07, F-08, F-16, F-22, F-23, F-25, and N-02 through N-05. Recovery qualification must include retained artifacts and referenced configuration revisions alongside the database. The Python framework, packaging, exact host/runtime versions, and detailed isolation enforcement configuration remain subsequent decisions within the Linux/container boundary confirmed by D-06. Process supervision alone does not establish the isolation required by N-03 and N-04. This is an approved design baseline, not implementation or qualification evidence.

## D-12 First live validation and release scope

**Confirmed on 2026-10-31.** Deliver one bounded feature in a prepared, existing demonstration repository using local Gitea, the approved Linux/container environment, and one primary qualified execution path. Cover intake, clarification, specification and baseline approval, Task planning, implementation, independent review, authorized integration, validation of the exact combined revision, and outcome acceptance. Demonstrate Decision waiting and continuation, interrupted-Run recovery, duplicate-event reconciliation, and rejection of stale results. Before execution, approve the target repository and revision, feature acceptance criteria, permitted operations, operating limits, and required evidence. Greenfield project creation and production deployment remain outside this pilot.

This establishes the pilot workflow and qualification scope, not the concrete target repository, feature, execution configuration, permissions, or numeric limits. A .NET demonstration repository and filtered `GET /projects` endpoint remain candidates; neither is selected by this decision. Möbiræon itself uses Python under D-11. The pilot must identify which requested integrations are included in its release and which are deferred, without implying that one qualified execution path satisfies all of F-02.

## How to resolve a decision

Record the chosen option, rationale, constraints, affected requirement IDs, and approval date. Update the definitions, requirements, architecture, or workflow at its authoritative location. Preserve the earlier decision when a later revision supersedes it.

D-01 through D-12 are confirmed. Detailed contracts, numeric operating-profile values, the concrete delegation policy, and the executable pilot specification remain to be completed. See the [implementation readiness review](implementation-readiness-review.md) for outstanding clarifications and their timing. Qualification evidence remains separate from decision approval.
