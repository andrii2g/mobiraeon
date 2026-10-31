# Workflow summary

**Status: Proposed high-level workflow except for confirmed requirements and decisions.** The five-part architecture and its main exchanges are agreed; the Coordination loop below is proposed alongside the [Coordination operating model](architecture.md#proposed-initial-operating-model). D-02 confirms Agent/component terminology, D-03 confirms the hierarchy, and D-04 confirms lifecycle separation and review/rework principles. Exact state names and transitions remain to be agreed. See [definitions](definitions.md) and the approved [requirements](requirements.md).

## Proposed Coordination loop

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
