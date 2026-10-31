# Workflow summary

**Status:** The high-level Coordination loop, intake/readiness, Agent assignment, Run lifecycle, assessment/rework model and initial defaults, integration/combined-result validation, Initiative outcome acceptance, Request closure/follow-up, waiting/recovery routing, human controls/scope changes, context continuity/shared work, and Agent onboarding are confirmed alongside the [Coordination operating model](architecture.md#initial-coordination-operating-model). Registry organization and the first registered Agents remain proposed in the [Agent Registry discussion](agent-registry.md). Exact lifecycle states, transitions, contracts, and further workflow detail remain open where they extend the confirmed requirements and decisions. See [definitions](definitions.md), the approved [requirements](requirements.md), and D-02 through D-04 for the governing terminology, hierarchy, and lifecycle principles.

The [versioned Mermaid views](diagrams/README.md) show the [high-level system](diagrams/high-level.md) and focused workflow parts: [intake/readiness](diagrams/intake-and-readiness.md), [assignment/selection](diagrams/assignment-and-selection.md), the [shared Run lifecycle](diagrams/run-lifecycle.md), [assessment/rework](diagrams/assessment-and-rework.md), [integration/validation](diagrams/integration-and-validation.md), [Initiative acceptance](diagrams/initiative-acceptance.md), [Request closure/follow-up](diagrams/request-closure-and-follow-up.md), [waiting/recovery](diagrams/waiting-and-recovery.md), [human controls](diagrams/human-controls.md), and [context/shared work](diagrams/context-and-shared-work.md). Each view identifies the agreed/proposed boundary.

## Coordination loop

Architecture defines which component owns an action; workflow defines which action is required next and what permits it. The initial service connects Gitea observation, authoritative coordination, and bounded Agent execution:

| Activity | Responsibility and result |
| --- | --- |
| Observe | Forge Synchronization polls new and changed managed Gitea items through the adapter. Relevant replies and review activity are inputs alongside newly created issues. Internal Run results, accepted prerequisites, and recovery conditions also trigger coordination. |
| Reconcile | The Coordinator maps observations to internal records, validates the applicable actor and requested operation, and identifies meaningful changes. Existing mapped Tasks retain their identity. Repeated observations and the system's own published updates do not create duplicate work. |
| Reason when needed | For a new Request needing interpretation, an intake rule supplies the Orchestrator Agent/Profile; the Coordinator authorizes its bounded Assignment and the Scheduler dispatches it. The Orchestrator proposes clarification, planning, suitable Roles and Agent Profiles, Assignments, or Decisions. Already planned work can proceed without another reasoning Run. |
| Authorize | The Coordinator validates proposed actions against the governing baseline, policy, inputs, and prerequisites, then records the authorized work and waiting conditions. A discovered issue or proposed plan alone does not authorize implementation. |
| Dispatch | The Scheduler dispatches eligible, authorized Runs for recorded Assignments within capacity and limits. Agent execution starts and supervises the selected Agent through its configured Runner Adapter. |
| Assess and continue | The Coordinator records submitted results and evidence. The approved workflow determines the next review, verification, integration, or acceptance action. New ambiguity or changes needing judgment activate the Orchestrator; established progression can go directly to scheduling. |
| Publish | Authorized work-item, status, and evidence updates reach Gitea through Forge Synchronization and the adapter. Routine Runs, retries, and review events remain internal unless the mapping calls for a substantive forge item. |

The loop can pause at any prerequisite and continue independent work. Polling unchanged external state creates no Agent Run. A human answer resumes affected work only after its authority and meaning are established, required artifact updates are recorded, and prerequisites are satisfied; unresolved interpretation returns to the Orchestrator.

The Gitea intake conventions must distinguish a new Request, an existing planned Task, an ordinary discussion, and an authorized decision or approval. Exact labels/templates, transition names, polling intervals, and message contracts remain follow-up design work.

## Intake and Task readiness

### Distinguishing issues

Use explicit issue kinds and suitable creation templates. The normal human entry point is a Request; the Orchestrator proposes the bounded Tasks needed to deliver it. An authorized human can also submit a Task candidate for already understood work.

| Kind | Meaning and example | Initial handling |
| --- | --- | --- |
| **Request** | A desired outcome, such as "Allow users to export reports as CSV." May still contain unanswered questions. | Record the intake and authorize an Orchestrator Assignment to interpret, clarify, or plan the work as needed. |
| **Initiative** | An overall delivery outcome within a Project, such as "Report export." | Link its originating Request and related Tasks; track overall outcome acceptance. |
| **Task** | A bounded contribution with explicit inputs, Deliverables, and acceptance criteria, such as "Define the CSV format" or "Implement export against the accepted format." | Validate the work contract and context, then assess readiness for assignment. A Task can be well defined while still awaiting a prerequisite. |

Use visible kind labels, with exact names remaining to be specified; `kind/request`, `kind/initiative`, and `kind/task` are illustrative. Gitea supports [issue templates that can set labels](https://docs.gitea.com/usage/issues-prs/issue-pull-request-templates/). Templates collect the appropriate information; the Coordinator validates and records the classification and stable external mapping. Label edits request classification changes and cannot grant authority or make work Ready by themselves.

[D-07](decisions.md#d-07-forge-integration-and-initial-platform) maps Requests to separate intake issues and Initiatives and substantive Tasks to their delivery issues. Keep the Request and its discussion linked to the resulting work. A Request can contribute to an existing Initiative or lead to a new one; its origin link does not add a hierarchy tier above **Project → Initiative → Task**. The Request is not silently replaced by a Task, and decomposition creates linked Tasks within the Initiative rather than nested Task trees.

A human-created Task issue remains a candidate until its Initiative, governing context, work contract, and authority have been validated. Missing or ambiguous information returns to clarification. Ordinary unclassified issues remain outside automated execution unless an explicit intake rule brings them into managed scope.

### Readiness for assignment

The Coordinator establishes readiness from the Task contract and recorded evidence, informed by the Orchestrator's proposals. Apply four checks:

| Check | What must be established |
| --- | --- |
| **Bounded work** | Objective, scope and exclusions, expected Deliverables, and observable acceptance criteria are clear. The Task is linked to its Initiative, and the required Role or responsibility is identified. |
| **Usable inputs** | Required governing documents, source revisions, and other inputs are available, resolvable, and consistent. The review and acceptance expectations are known. |
| **Satisfied prerequisites** | Required Deliverables and Decisions meet their acceptance and revision conditions. Dependencies form an acyclic graph; a closed issue alone is insufficient. |
| **Authority to begin** | The applicable baseline approval or delegation covers the work and permitted operations, with no unresolved question preventing the assigned work. |

These checks apply to the work being assigned. A clarification, research, or architecture Task needs sufficient inputs and authority for that investigation; it does not require the implementation specification it is intended to produce. An implementation Task requires its applicable approved brief/specification and accepted prerequisites. Ordinary Tasks covered by approved delegation do not require a fresh human approval each time.

Keep three determinations separate:

- **Task readiness:** the work has the definition, inputs, prerequisites, and authority needed to begin.
- **Assignment eligibility:** a selected Agent/Profile is suitable and permitted for the Task or stage, including any review-independence conditions. Selecting a specific Agent is not a prerequisite for Task readiness.
- **Run dispatch:** the Assignment remains authorized and ready, its resolved execution configuration is qualified, and ownership, capacity, and limits permit starting.

A Ready Task may therefore wait for a suitable Agent or execution capacity. Any visible readiness label reflects the Coordinator's determination. Changes to governing inputs trigger reassessment; readiness is not permanent, and the Task's original history is retained. These checks apply the existing definitions and F-13 through F-15 without choosing exact lifecycle states.

## Agent assignment and selection

An Assignment records who is authorized to perform a Task or workflow stage. A **Role** defines the responsibility, an **Agent** supplies a stable registered identity, and its **Profile** supplies versioned execution configuration. A **Worker** supplies capacity when a Run starts. A registered Agent does not require a permanently running process.

### Selection and authorization

| Step | High-level rule and owner |
| --- | --- |
| Identify the responsibility | The Task or stage identifies the needed responsibility, such as architecture, development, review, or verification. The Orchestrator proposes the Role when planning or clarifying the work; an approved workflow can already establish it. |
| Find eligible configurations | For ordinary delivery work, Coordination considers enabled registered Agents whose referenced Profiles support the Role, instructions, required tools, and applicable qualified execution scope. Project permissions, effective limits, and any review-independence conditions must permit the work. |
| Apply an approved preference | For routine work, an assignment rule supplies preferred registered Agents and explicitly permitted alternatives. Filter for eligibility before applying the preference. Ambiguous suitability or a consequential exception goes to the Orchestrator for a proposal. |
| Record the Assignment | The Coordinator validates the proposed selection and records the Task/stage, assigned responsibility, selected Agent and Profile revisions, governing references, expected outputs and evidence, and applicable authority, review expectations, and limits. Assignment does not start execution. |
| Dispatch a Run | The Scheduler dispatches the recorded selection when readiness, ownership, qualification, capacity, and limits permit. Before execution, the Run receives its immutable effective configuration and context record under F-08. |

Select an existing registered Agent revision together with the exact Profile revision it references. Profile selection is part of finding a suitable registered configuration; the Scheduler does not attach an arbitrary Profile or model to an Agent. A different binding or permitted override follows the versioned Registry process. Roles and Profiles may be reused across assignments where instruction bindings and policy allow, as described in [responsibilities](responsibilities.md#role-and-profile-assignments).

### Initial selection policy

Begin with approved defaults for work classes and a small, explicit preference order. [D-08](decisions.md#d-08-initial-profiles) supplies the intent: strong reasoning Profiles for clarification, architecture, specifications, and consequential Decisions; medium Profiles for routine implementation; independently configured review. Concrete runtime/model settings and support claims remain subject to qualification.

Eligibility comes before preference: a favored configuration must still provide the required capabilities within governing permissions, qualification, and limits. The Orchestrator can recommend another eligible configuration within delegation; exceptions outside that authority follow the Decision process. No new model call is needed merely to repeat a routine approved selection.

If no eligible Agent configuration exists, preserve the Task and record the missing capability, configuration, qualification, or candidate permission. The Task remains Ready only while its own readiness gates still hold; loss of governing authority or required inputs triggers reassessment. Route the unresolved choice through the Orchestrator when an eligible Orchestrator can run; otherwise expose the required authorized action. Temporary lack of execution capacity normally means waiting. Any alternative must be explicitly permitted and validated; never silently substitute a model/runtime, weaken required capability, or broaden permissions.

### Handoff and reassignment

One Task can use separate Assignments for implementation, review, and verification. Review requires a separate Assignment and Run with the applicable independence checks; a different Role, Profile, or Agent name alone does not establish independence. The same model remains permissible when policy allows.

Retries and reassignment retain Task identity and preserve previous allocations, results, and evidence. Record a changed authorized allocation without overwriting the former one, and reject updates from superseded execution ownership. A change to configuration already bound to a Run requires a new authorized, validated Run; it cannot rewrite the old attempt's configuration. Exact assignment transitions and recovery mechanisms follow in the detailed workflow specification.

## Run launch and result reporting

A Run is one bounded attempt under an authorized Assignment. Its launch, reported work, observed execution outcome, and acceptance remain separate facts. The conditions below do not choose exact lifecycle state names.

### Preparing and launching

| Step | Responsibility and result |
| --- | --- |
| Select eligible work | The Scheduler selects an authorized Assignment whose work is eligible to run. Selection alone does not start execution or grant new authority. |
| Bind and record the attempt | The Coordinator rechecks readiness, permissions, ownership, qualification, capacity, and limits. It resolves configuration and context revisions, establishes exclusive recoverable execution ownership, and durably records the Run and dispatch before launch. |
| Start supervised execution | The Scheduler dispatches the recorded Run. A Worker supplies isolated capacity; the Runner Adapter starts the configured runtime noninteractively with the Assignment, shared rules, Role instructions, governing context, and output contract. Trusted controls enforce permissions and limits, including subprocess operations. |

The immutable Run record identifies the selected Agent/Profile and Worker, runtime and provider configuration, requested and effective settings, governing revisions, and applicable permissions and limits under F-08. Later observations cannot rewrite it. Ordinary Runs require qualified execution; explicitly authorized qualification Runs follow F-09. Interactive input requests produce a controlled failure or recorded internal decision request rather than an unattended terminal wait.

### Returning and recording results

The Agent reports produced Artifacts and exact revisions, validation actually performed and its environment, results and limitations, unresolved questions or prerequisites, and the proposed next action. This report follows the shared role rules and configured output contract; a claim of completion or successful process exit does not establish Task acceptance.

The Runner Adapter separately captures observed execution facts, including exit or interruption, cancellation, usage when available, output truncation, and cleanup status. Keep Agent claims distinct from supervisor observations and identify missing or uncertain information. Reports and captured records must protect secrets.

The Coordinator authenticates the submitting execution identity and checks current ownership, authority, governing revisions, and referenced evidence before applying authorized updates. Expired or superseded execution cannot advance authoritative state or have its results accepted. An Agent's completion claim cannot establish acceptance; the required independent assessment and designated authority must establish it under policy. The Developer Role explicitly prohibits self-acceptance.

### Outcomes and continuation

- **Produced work** proceeds to the applicable review, verification, integration, or acceptance gate; submission alone does not satisfy that gate.
- **Blocked work** records the missing prerequisite or Decision and preserves progress. The Orchestrator handles unresolved interpretation or routing; waiting requires no active model session.
- **A failed attempt** records the failure and follows bounded recovery policy; it does not itself determine the Task's final outcome.
- **Cancellation** records the authorized stop and any retained work or uncertain effects; it is distinct from failure and successful delivery.
- **An unknown or interrupted outcome** requires reconciliation. Missing acknowledgement cannot establish success, failure, or permission to repeat an operation blindly.

Stable operation identities let duplicate dispatches or reports converge without duplicate launches, changes, or acceptance. Before retrying uncertain operations, check their existing effects. Retries preserve Task identity, original evidence, and cumulative limits; changes to bound configuration require a new authorized Run.

Execution capacity returns to service only after Run-owned processes are cleaned up or effectively contained. Record incomplete cleanup and withhold affected capacity while it remains unsafe to reuse. The Coordinator then records waiting, recovery, or the next authorized work without inferring acceptance from Run completion.

## Review, verification, acceptance, and rework

After a submission is recorded, the Task contract and project policy determine the required assessments, evidence, and next action. Review and verification can overlap or repeat where dependencies permit; the agreed model does not require every Task to follow a fixed review-then-QA sequence.

The Coordinator applies approved routing rules, checks recorded gates, and records authorized determinations. Reviewers and verifiers supply judgments and evidence about the work; the Coordinator does not independently reason about correctness. Routine assessment and in-scope rework can proceed without another Orchestrator Run when policy already determines the next action. Unresolved interpretation, disputed findings, or exceptions needing judgment return to the Orchestrator.

### Initial defaults

Concrete actor assignments, policy contracts, and exact transitions remain follow-up specifications.

| Choice | Initial default |
| --- | --- |
| Assessment routing | After an authoring submission, arrange independent review and any verification required by the Task contract or policy. Existing applicable evidence can satisfy checks where permitted; a separate Verifier/QA Agent Run is required only when the contract or policy calls for it. |
| Acceptance delegation | Explicitly delegate ordinary Task acceptance to an eligible independent reviewer, conditional on all required current evidence and gates. The Coordinator enforces and records the determination. Use another designated authority where the contract or policy requires it. |
| Implementation Task boundary | Normally include authorized integration and fresh combined-revision validation in the implementation Task's acceptance contract. Permit reviewed-patch acceptance only when integration is explicitly assigned to separate work; retain that delivery obligation. |

### Assess exact submissions

Assess the identified Artifact revisions against their governing baseline and acceptance criteria. Supply the author handoff and existing evidence, while keeping authoritative sources available for direct inspection. Supplied evidence is distinct from checks reproduced by an assessor.

| Responsibility | Result and boundary |
| --- | --- |
| Independent review | Assess correctness, completeness, and conformance; return grounded findings and an acceptance recommendation for the exact assessed revisions. Agent review uses a separate Assignment and Run satisfying the configured independence policy. |
| Verification | Execute the required checks against identified revisions and environments; record results, failures, and limitations. Assign a Verifier/QA Role when required by the work contract or policy; a passing check alone does not establish acceptance. |
| Acceptance | The designated authority determines whether the required criteria and evidence are satisfied. The Coordinator enforces the gates and records the determination, its authority, and the accepted revisions. |

A different Role, Profile, Agent name, or model does not establish independence by itself. Assessors disclose authorship, repairs, and conflicts; policy governs eligibility. An eligible reviewer may also hold acceptance authority when explicitly delegated, but its assessment alone does not supply that authority.

A completed assessment Run can report required changes or a failed product check; that is distinct from a failed assessor execution. Assessment reports contribute evidence to the Task's gates rather than automatically creating a new authoring submission that requires another review of the report itself. Any separately required assessment of such material follows its own contract. Later evidence or changed revisions may require an updated acceptance judgment; an earlier recommendation alone does not authorize acceptance.

### Acceptance and code delivery

Record acceptance only when all applicable gates pass; missing evidence, unresolved required findings, or unavailable authority leaves it pending. Ordinary acceptance within approved delegation does not require another human approval.

- A documentation or planning Task can finish when its own identified Deliverable is independently assessed and accepted, even while related implementation continues.
- An implementation Task follows its own contract. A reviewed patch can be accepted before integration only when that contract assigns integration to a separate Task.
- Overall code delivery requires authorized integration into the designated target and fresh validation of the exact combined revision. Serialize conflicting integration operations; a reviewed branch, successful push, or merge alone cannot establish delivered success.

Changed submissions, governing inputs, or intervening target changes trigger reassessment of affected review, verification, and approvals. Evidence for revision A does not automatically establish revision B; reuse requires an explicit applicability determination under policy. Initiative acceptance still assesses its overall outcome rather than counting accepted Tasks.

### Rework and unresolved questions

Findings identify the assessed revision, unmet criterion or concrete failure, evidence, and required correction or Decision. Distinguish defects from missing evidence, environment limitations, disputed expectations, and optional suggestions.

| Condition | Next authorized action |
| --- | --- |
| Required correction within scope | Return the findings to the responsible author for rework; preserve the logical Task and its existing history. |
| Missing or inconclusive evidence | Arrange the needed verification or investigation; keep acceptance pending rather than inventing a pass or assuming a product defect. |
| Ambiguous requirement or disputed finding | Route a Decision request through the Orchestrator. Only it initiates human escalation when resolution exceeds delegated authority. |
| Applicable criteria and evidence satisfied | Obtain the designated acceptance determination and let the Coordinator record it; continue remaining delivery obligations. |

Rework starts another Run under the same Task, using a new Assignment when the authorized allocation changes. Retain previous submissions, findings, configuration, and evidence; reassess repaired revisions and affected behavior before acceptance. Assessors return repairs to the author unless separately authorized to repair, disclose their changes, and preserve subsequent assessment independence.

Changes to scope or governing contracts require the applicable authorized Decision and artifact updates before affected work resumes. Exhausted recovery or budgets preserves progress and returns control under policy; it cannot establish acceptance. Exact findings, acceptance, and rework transitions remain follow-up workflow specifications under F-15, F-20, F-21, D-04, and D-10.

## Integration and combined-result validation

Integration brings reviewed changes into the designated delivery target. An authorized Assignment performs that work, and required verification assesses the combined result. The Coordinator records the identified version, evidence, and authorized determination; it does not judge correctness itself. The [focused diagram](diagrams/integration-and-validation.md) shows this handoff.

The default keeps integration and combined-result validation within the implementation Task's acceptance contract. Separate integration work is an explicit exception: accepting its reviewed-patch prerequisite leaves the overall delivery obligation outstanding.

- Validate the exact combined revision against the applicable acceptance criteria; individually reviewed changes do not establish that the whole result works.
- Reassess affected evidence when the combined revision or governing context changes.
- Route a required correction to the responsible Task for rework; unclear responsibility, disputed expectations, or scope changes return to the Orchestrator.
- Record acceptance under the existing designated authority only when the required current evidence and gates are satisfied. Integration does not add a new acceptance Role or routine human approval.

Task acceptance confirms its contribution; Initiative acceptance assesses the overall intended outcome. A merge alone does not establish either acceptance or production-deployment authority.

## Initiative outcome acceptance

The overall outcome is assessed under Initiative-level authority, as shown in the [focused diagram](diagrams/initiative-acceptance.md).

An Initiative is complete when:

- Its required delivery obligations are satisfied; optional follow-up work is distinguished by the approved scope.
- Current evidence establishes the overall agreed outcome, including validation of the exact combined code revision where applicable.
- No unresolved required finding, prerequisite, or Decision prevents acceptance.
- The designated Initiative authority accepts the outcome and the Coordinator enforces and records that determination.

The authority default is an eligible independent Reviewer with explicit Initiative-level delegation; human acceptance applies where policy reserves it. Ordinary Task acceptance delegation does not automatically grant Initiative acceptance. Reuse applicable review and validation evidence, arranging further assessment only where needed to establish the overall outcome.

The Orchestrator coordinates the outcome assessment and missing work. If individual Tasks are accepted but the outcome is unmet, keep the Initiative open and arrange missing assessment, rework, or bounded additional work within approved scope. Preserve valid Task acceptance and its history; scope changes follow the Decision process.

Request closure and later follow-up follow the rules below; the [remaining agenda](implementation-plan.md#remaining-high-level-discussions) tracks further high-level discussions.

## Request closure and follow-up

The Coordinator records a Request as fulfilled when accepted delivery covers its agreed requested outcome under an explicit closure rule. That rule may use already accepted outcomes without another approval or Run; broader or unresolved Request-level judgment requires applicable authority. Initiative acceptance delegation does not automatically grant that broader authority. Closure follows the Request's own outcome rather than requiring every related Initiative to finish.

Preserve the original Request and its delivery links within the existing hierarchy. The Orchestrator classifies later reports as baseline defects, changed goals, or questions needing resolution. Scope changes require an authorized Decision before affected work proceeds; existing delegation applies without an automatic new human approval. The [focused diagram](diagrams/request-closure-and-follow-up.md) shows this handling.

| Situation | Handling |
| --- | --- |
| Defect before Request fulfillment | Return the correction to the responsible Task as rework, preserve its identity, and reassess the changed result and affected acceptance. |
| Baseline defect after fulfilled closure | Normally create linked repair work or a new Request. Reassess affected acceptance and closure; correct or reopen them when evidence shows original fulfillment was unsupported, preserving the history. |
| Changed goal or unresolved expectation | Use a linked new Request for the changed goal; resolve uncertainty through the Decision process before classifying or authorizing affected work. |
| Cancellation, duplicate, or rejection | Record the distinct closure reason; these outcomes do not establish fulfillment. |

## Delivery loop

| Stage | Main activity | Outcome |
| --- | --- | --- |
| 1. Intake | Human supplies a goal, initial requirements, ideas, constraints, and exclusions. | A classified Request linked to a Project and delivery scope. |
| 2. Clarification | Orchestrator Agent coordinates requirements analysis, research, architecture, and writing. It consolidates unresolved questions for the human. | A reviewed brief and initial specification approved by the human. |
| 3. Planning | Agents propose milestones and bounded Tasks, with dependencies, ownership, inputs, acceptance criteria, and limits. | An approved, versioned delivery baseline and eligible work. |
| 4. Execution | The Scheduler dispatches eligible, authorized Runs for recorded Assignments. Workers and Runner Adapters use the selected Agent Profiles and runtimes to produce artifacts and validation evidence. | A submission, an internal question, or a recorded execution failure. |
| 5. Assessment and integration | Arrange independent review and required verification, resolve findings, and perform authorized integration as the Task contract requires. Record acceptance only after its applicable gates pass. | Accepted Task Deliverables; overall code delivery additionally requires fresh validation of the exact combined revision. |
| 6. Outcome acceptance | Required results are checked together against the Initiative's agreed outcome. | A completed Initiative, or specific remaining work. |

The loop also applies to a feature, defect, migration, or investigation in an existing project. The amount of planning scales to the change; a small task need not create every planning role or milestone.

Establish shared contracts first, then deliver small usable slices across data, domain, business logic, workers, and presentation as needed. Work that can proceed against stable contracts may run in parallel. Human review after the initial baseline focuses on decisions outside the approved intent or authority.

## Questions and human escalation

1. An agent records the precise ambiguity, the evidence inspected, options, and its recommendation, linked to affected work.
2. The affected work waits and releases execution capacity; independent work can continue.
3. The Orchestrator Agent resolves the question within delegated authority and the governing baseline, or routes it to a suitable internal role.
4. If human authority or clarification is needed, only the Orchestrator Agent initiates a human escalation through the Coordinator.
5. The authorized answer is recorded, affected specifications are revised as required, and prerequisites are rechecked before execution resumes.

Several Tasks may depend on the same Decision. Resolution makes affected work eligible for re-evaluation; it does not by itself prove that the required artifacts or approvals exist.

## Waiting and recovery

The defaults distinguish waiting, recoverable execution problems, changed allocation, and stopping. The [focused diagram](diagrams/waiting-and-recovery.md) shows the routing; unresolved judgment returns to the Orchestrator.

| Action | Default |
| --- | --- |
| Wait | Persist the unmet condition and progress without an idle model session. Meaningful external or internal changes trigger reassessment; independent eligible work can continue. |
| Retry | Retry only recoverable, authorized work within remaining limits, using the same Task and a new Run. Reconcile unknown launches or external effects before repeating operations. |
| Reassign | Record a new allocation to an eligible Agent under the same Task. Preserve prior results and history, retire superseded execution ownership, and establish exclusive ownership for the new attempt. |
| Stop | Stop affected execution or further starts when authority, recovery, or limits do not permit continuation. Preserve work and the reason; route unresolved Decisions through the Orchestrator without claiming acceptance. |

The Coordinator enforces the applicable policy and the Scheduler dispatches only currently eligible work. Recovery preserves evidence and cumulative limits; superseded execution cannot advance authoritative state. Affected capacity remains unavailable until cleanup or effective containment is established. Stopping an attempt or further starts does not itself cancel the logical Task or establish acceptance. If the Orchestrator cannot run, expose the required authorized action without idle model calls or bypassing limits. Existing review, acceptance, and escalation gates still apply.

## Human controls and scope changes

Apply each authorized control to an explicit scope of work; Request-scoped controls follow validated delivery links within the existing hierarchy. These defaults are summarized in the [focused diagram](diagrams/human-controls.md).

| Control | Effect |
| --- | --- |
| Pause | Immediately hold new starts and wind down affected active Runs under supervision, preserving progress. Do not leave their processes frozen indefinitely. |
| Resume | An explicit request lifts only the selected hold, preserving broader holds, cancellation, and remaining limits. Recheck current readiness, authority, and execution conditions before a new Run, preserving the original Run record. Cancelled work requires new authorization to continue. |
| Cancel | End the selected work and stop affected Runs under supervision. Preserve completed effects and progress; cancellation establishes neither success nor automatic undo. |
| Reprioritize | Change the order of eligible work without changing permissions, dependencies, or budgets. Do not automatically preempt active work. |
| Take over | Hold affected automation, retire old execution ownership, and clean up or contain execution before exclusive human work. Record human changes; explicit return to automation requires fresh checks. |
| Change scope | Record authorized baseline updates, identify affected work, and reassess its readiness, acceptance, and evidence. Unrelated authorized work can continue. |

Authorized human controls reach the Coordinator directly without requiring an Orchestrator Run. It validates authority and scope, persists holds and cancellation decisions across restarts, and distinguishes a recorded control from observed stopping, cleanup, or containment. The Orchestrator handles unresolved judgment and required escalation when eligible; an unavailable Orchestrator does not delay authorized controls. Scope changes within existing delegation need no automatic additional human approval. Exact commands, transitions, and enforcement details remain follow-up specifications.

Changed goals follow the linked-Request rule above. Authorized updates to governing scope preserve prior baselines and evidence while reassessing their applicability to affected work. Human-produced changes remain subject to the normal review and acceptance gates.

## Context continuity and shared work

Before each Run, supply shared operating rules, the selected Role instructions, the Assignment, relevant accepted requirements, specifications and Decisions, applicable policies, acceptance criteria, and required prerequisite outputs at identified revisions. Routine assembly follows the approved Task/context policy without another Orchestrator Run. The Orchestrator proposes context and boundaries needing judgment; the Coordinator validates references, authority, and readiness and pins the inputs. Agents assess sufficiency and report conflicts; execution resolves authorized sources.

Durable Artifacts and recorded handoffs retain produced progress, including unaccepted work, findings, evidence, limitations, and unresolved questions across new Runs, retries, and reassignment. Summaries identify source revisions and freshness; they guide access to governing material rather than replacing it or proving success. Review context follows independence policy rather than automatically inheriting an author's conversation. The [focused diagram](diagrams/context-and-shared-work.md) shows this model.

- Missing or changed governing inputs trigger reassessment of affected work. Do not silently switch to the latest baseline or rewrite an earlier Run's configuration, context, or evidence; unrelated authorized work can continue.
- Parallel Tasks can proceed when their accepted prerequisites and stable contracts permit it. The dependency graph governs execution order; a parent relationship alone creates no prerequisite.
- Parallel Tasks may edit the same paths in isolated mutable workspaces within explicit change boundaries. Coordinate conflicts, shared contracts, test state, and integration targets; authoring can overlap while conflicting integration operations remain serialized.
- Keep outputs versioned and distinguish produced material from accepted results. When an output or Decision resolution satisfies a governed dependency, its required acceptance and applicable revision must be recorded; a closed issue or summary is insufficient.

## Agent onboarding

Prepare an Agent through versioned definitions and separately authorized access. Its stable identity remains distinct from its Role, Profile, execution Worker, individual Runs, and any Gitea user. [Pilot and Agent setup](pilot-and-agent-setup.md) owns the selected setup and forge-account policy.

| Step | Preparation |
| --- | --- |
| 1. Define responsibilities and configuration | Select or define the Role instructions, shared rules, and reusable Profile suitable for the intended work and governing permissions and limits. |
| 2. Register the Agent | Establish a stable logical identity with an exact Profile revision binding. Retain any permitted overrides in its versioned definition. |
| 3. Arrange forge access | Map each Agent acting in Gitea to its own stable account and approved permissions, separate from the Coordination account. Other Agents need no forge account. Definitions retain secret references; credential values stay in the authorized secret mechanism. |
| 4. Validate and publish | Review and validate the Registry definitions and their references, then publish a retrievable Git revision for configuration resolution. |
| 5. Qualify and enable selection | Record qualification of the execution combination for its supported scope and enable the Agent through the authorized configuration process. Assignments and dispatch still require current readiness, authority, and execution capacity and limits. |

Publication, qualification, administrative enablement, and permission to perform particular work are separate determinations. Publishing a definition establishes none of the others by itself. Changes produce new reviewed Registry revisions and apply through authorized selection; they do not rewrite existing Run configuration or history. The [Agent Registry discussion](agent-registry.md) covers the proposed organization and first registered Agents.

## Closure rules

| Record | Completion rule |
| --- | --- |
| Documentation or planning Task | Its own versioned artifact is independently accepted. |
| Implementation Task | Its own acceptance contract is satisfied; a reviewed-patch Task may finish before integration when integration belongs to a separate Task. Overall code delivery requires validation of the exact integrated revision. |
| Decision | An authorized answer is recorded and its effects on affected work are identified. |
| Run | The bounded attempt has a recorded outcome; this does not establish Task completion. |
| Milestone | Its required scope meets the checkpoint's acceptance conditions. |
| Initiative | Required delivery is complete and aggregate outcome acceptance passes. |

A completed architecture Task stays complete while implementation Tasks continue under the same Initiative. Dependencies express that those Tasks require the architecture output. Delegation and routing are audit events unless they create a distinct deliverable or Decision.

A closed queue or a collection of closed tickets is insufficient evidence that the outcome works. Exact states and their transition policies remain subject to [D-04](decisions.md#decision-register).
