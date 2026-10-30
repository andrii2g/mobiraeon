# Definitions

Möbiræon uses the following terms consistently across its documentation, work tracking, and agent assignments.

| Term | Definition |
| --- | --- |
| **Request** | A desired outcome submitted by a human or an authorized integration, such as a new project, feature, or repair. |
| **Project** | The product context containing goals, repositories, constraints, accepted decisions, and related requests. |
| **Task** | A bounded assignment describing an objective, inputs, dependencies, expected deliverables, and acceptance criteria. |
| **Deliverable** | A result evaluated against acceptance criteria, such as an architecture decision, specification, or implementation change. |
| **Artifact** | A versioned representation of a result or evidence, including documents, schemas, commits, and verification reports. |
| **Milestone** | A group of deliverables representing a meaningful delivery objective or checkpoint. |
| **Parent relationship** | Scope membership identifying the larger request or deliverable to which a work item contributes. |
| **Dependency** | A prerequisite requiring a specified accepted output or decision before dependent work proceeds. |
| **Role** | A defined responsibility and authority, such as architect, developer, or reviewer. |
| **Agent profile** | The execution configuration for a role, including provider, model, reasoning setting, tools, context access, and limits. |
| **Agent run** | One execution attempt against an assignment. A role is served by separate runs as work becomes eligible. |
| **Orchestrator** | The logical authority responsible for coordinating work, enforcing progression rules, routing decisions, and managing human escalation. |
| **Decision request** | A recorded ambiguity, conflict, or missing decision that prevents correct progress within the current assignment. |
| **Human escalation** | An orchestrator-created request for a human decision or intervention when available evidence or delegated authority is insufficient. |
| **Baseline** | The accepted versions of requirements, relevant specifications, contracts, and decisions governing a request or assignment. |
| **Ready** | Work has sufficient inputs, satisfied prerequisites, authority, and acceptance criteria to begin. |
| **Blocked** | Work requires an external input, prerequisite, or decision before it continues correctly. |
| **Failed attempt** | An execution that did not achieve its assigned result. The work item's recovery or terminal outcome is determined by its governing policy. |
| **Done** | The work item's required deliverable has been accepted using its applicable evidence and authority rules. |
| **Autonomy policy** | The permitted decisions, actions, limits, and escalation conditions for a project, request, or role. |

## Relationships between terms

A request expresses the desired outcome. Work items divide the work into bounded assignments. Deliverables are the results assessed for acceptance, and artifacts record those results and their evidence.

A parent relationship identifies scope membership. A dependency identifies an execution prerequisite. The two relationships serve separate purposes.

A role defines responsibility and authority. An agent profile defines execution configuration. An agent run is one attempt to perform the assigned work.

Blocked work awaits an external condition. A failed attempt records an unsuccessful execution. Done records accepted delivery under the applicable policy.
