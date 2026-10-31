# Workflow summary

**Status:** The high-level Coordination loop, intake classification, and Task readiness below were agreed on **2026-10-31**, alongside the [Coordination operating model](architecture.md#initial-coordination-operating-model). Agent assignment and selection below are proposed for review. The delivery loop and further workflow detail remain proposed where they extend the confirmed requirements and decisions. D-02 confirms Agent/component terminology, D-03 confirms the hierarchy, and D-04 confirms lifecycle separation and review/rework principles. Exact state names and transitions remain to be agreed. See [definitions](definitions.md) and the approved [requirements](requirements.md).

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

## Proposed Agent assignment and selection

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

## Delivery loop

| Stage | Main activity | Outcome |
| --- | --- | --- |
| 1. Intake | Human supplies a goal, initial requirements, ideas, constraints, and exclusions. | A classified Request linked to a Project and delivery scope. |
| 2. Clarification | Orchestrator Agent coordinates requirements analysis, research, architecture, and writing. It consolidates unresolved questions for the human. | A reviewed brief and initial specification approved by the human. |
| 3. Planning | Agents propose milestones and bounded Tasks, with dependencies, ownership, inputs, acceptance criteria, and limits. | An approved, versioned delivery baseline and eligible work. |
| 4. Execution | The Scheduler dispatches eligible, authorized Runs for recorded Assignments. Workers and Runner Adapters use the selected Agent Profiles and runtimes to produce artifacts and validation evidence. | A submission, an internal question, or a recorded execution failure. |
| 5. Review and integration | An independent reviewer checks the submission. Accepted changes are integrated and verified against the current shared baseline. | Accepted documentation or integrated, validated code. |
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

External observations, internal results, and periodic reconciliation reach Coordination. Validated changes make work eligible for Scheduler reassessment. Waiting does not require an active model session. Failed or expired Runs follow bounded recovery policy; exhausted recovery produces a visible blocker and a Decision for the Orchestrator Agent.

Retries and resumed runs preserve task identity, original evidence, configuration history, and existing change references. Duplicate events must converge without duplicate accepted work. Pause and cancellation stop further dispatch in the selected scope and handle active runs under an agreed policy.

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
