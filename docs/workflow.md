# Workflow summary

**Status: Proposed summary except for confirmed requirements and decisions.** D-02 confirms Agent/component terminology, D-03 confirms the hierarchy, and D-04 confirms lifecycle separation and review/rework principles. Exact state names and transitions remain to be agreed. See [definitions](definitions.md) and the approved [requirements](requirements.md).

## Delivery loop

| Stage | Main activity | Outcome |
| --- | --- | --- |
| 1. Intake | Human supplies a goal, initial requirements, ideas, constraints, and exclusions. | A classified Request linked to a Project and delivery scope. |
| 2. Clarification | Orchestrator Agent coordinates requirements analysis, research, architecture, and writing. It consolidates unresolved questions for the human. | A reviewed brief and initial specification approved by the human. |
| 3. Planning | Agents propose milestones and bounded Tasks, with dependencies, ownership, inputs, acceptance criteria, and limits. | An approved, versioned delivery baseline and eligible work. |
| 4. Execution | Scheduler assigns ready work. Workers use the selected agent profiles and CLI runtimes to produce artifacts and validation evidence. | A submission, an internal question, or a recorded execution failure. |
| 5. Review and integration | An independent reviewer checks the submission. Accepted changes are integrated and verified against the current shared baseline. | Accepted documentation or integrated, validated code. |
| 6. Outcome acceptance | Required results are checked together against the Initiative's agreed outcome. | A completed Initiative, or specific remaining work. |

The loop also applies to a feature, defect, migration, or investigation in an existing project. The amount of planning scales to the change; a small task need not create every planning role or milestone.

Establish shared contracts first, then deliver small usable slices across data, domain, business logic, workers, and presentation as needed. Work that can proceed against stable contracts may run in parallel. Human review after the initial baseline focuses on decisions outside the approved intent or authority.

## Questions and human escalation

1. An agent records the precise ambiguity, the evidence inspected, options, and its recommendation, linked to affected work.
2. The Task becomes Blocked and releases execution capacity.
3. The Orchestrator Agent resolves the question within approved requirements or routes it to a suitable internal role.
4. If human authority or clarification is needed, only the Orchestrator Agent initiates a human escalation through the Coordinator.
5. The authorized answer is recorded, affected specifications are revised as required, and prerequisites are rechecked before execution resumes.

Several Tasks may depend on the same Decision. Resolution makes affected work eligible for re-evaluation; it does not by itself prove that the required artifacts or approvals exist.

## Waiting and recovery

Events and periodic reconciliation wake the Scheduler when useful work is possible. Waiting does not require an active model session. Failed or expired Runs follow bounded recovery policy; exhausted recovery produces a visible blocker and a Decision for the Orchestrator Agent.

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
