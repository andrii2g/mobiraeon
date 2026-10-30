# Definitions

Möbiræon uses the following terms consistently across its documentation, work tracking, configuration, and Agent assignments.

| Term | Definition |
| --- | --- |
| **Request** | A desired outcome submitted by a human or an authorized integration, such as a new project, feature, or repair. |
| **Project** | The product context containing goals, repositories, constraints, accepted Decisions, and related Requests and Initiatives. |
| **Initiative** | An intended outcome within a Project, delivered through bounded Tasks. |
| **Task** | A bounded unit of work defining its objective, scope, inputs, dependencies, Deliverables, and acceptance criteria. |
| **Assignment** | An authorized allocation of a Task or workflow stage to an Agent. An Assignment may involve multiple Runs. |
| **Decision** | A record of a question or choice, its governing context and authority, and its resolution when available. |
| **Decision request** | A recorded ambiguity, conflict, or unresolved choice requiring resolution for affected work to proceed correctly. |
| **Human escalation** | An agent-generated request for human decision or intervention, initiated by the Orchestrator Agent through authorized Coordinator operations when internal resolution or delegated authority is insufficient. |
| **Deliverable** | A result evaluated against acceptance criteria, such as a specification, architecture design, or implementation change. |
| **Artifact** | A versioned representation of a result or evidence, such as a document, schema, commit, or verification report. An Artifact may exist before its acceptance. |
| **Acceptance** | A recorded determination by the designated authority that an identified Deliverable revision or outcome satisfies its applicable criteria and evidence requirements. |
| **Milestone** | A grouping of delivery targets representing a meaningful objective or checkpoint. |
| **Parent relationship** | A scope-membership link identifying the containing context, such as a Task’s Initiative. |
| **Dependency** | A prerequisite identifying a required Deliverable or Decision, applicable revision constraints, and acceptance conditions before dependent work proceeds. |
| **Role** | Defined responsibilities, such as architecture, development, or review. A Role name or description grants no permissions; governing policy establishes authority. |
| **Agent** | A logical AI actor with a stable registered identity. |
| **Agent Profile** | Reusable, versioned configuration defining how an Agent executes assigned work. |
| **Agent Registry** | The persistent, versioned catalog of registered Agents and Agent Profiles, separate from live execution state. |
| **Worker** | Execution capacity available to host supervised Runs. |
| **Runner Adapter** | A component that invokes a configured runtime through a transport, supervises its lifecycle, and normalizes execution outcomes. |
| **Run** | One bounded execution attempt under an Assignment, pinned to its configuration and context revisions. |
| **Coordinator** | The component enforcing authority, authoritative workflow state, progression rules, and acceptance gates. |
| **Scheduler** | The component deterministically dispatching eligible, authorized work within configured capacity and limits. |
| **Orchestrator Agent** | The Agent that reasons about intake, plans, Assignments, and Decisions, proposing actions through authorized Coordinator operations. |
| **Baseline** | The accepted versions of requirements, specifications, contracts, Decisions, and policies governing a Request or Assignment. |
| **Ready** | Work has resolvable governing context, sufficient inputs, satisfied prerequisites, defined Deliverables and acceptance criteria, and required authority to begin. |
| **Blocked** | Affected work requires an external input, prerequisite, or Decision before it can continue correctly. |
| **Failed attempt** | A Run recorded with a failure outcome under governing policy. Failure is distinct from blocking or cancellation and does not itself determine the Task’s final outcome. |
| **Done** | The required outcome or Deliverable has been accepted under its applicable authority and evidence rules. |
| **Autonomy policy** | An approved, versioned policy defining delegated decisions, permitted actions, limits, and escalation conditions within governing permissions. |

## Relationships between terms

A Request expresses a desired outcome within a Project. Initiatives organize outcomes, and Tasks divide the work into bounded units. Deliverables are assessed for acceptance; Artifacts represent those results and their evidence. Submission or review of an Artifact can precede Task acceptance.

A Parent relationship identifies scope membership. A Dependency identifies an execution prerequisite. Dependencies form an acyclic graph and are satisfied by the required accepted results and revisions. Closing a related record alone does not satisfy a prerequisite.

A Role defines responsibility, an Agent supplies a stable identity, and an Agent Profile supplies execution configuration. Assignments allocate work; Workers provide execution capacity; Runner Adapters invoke configured runtimes through transports; Runs record individual attempts. Runtime, transport, provider, and model identities remain distinct.

The Coordinator enforces state and authority, the Scheduler dispatches eligible work, and the Orchestrator Agent reasons about plans and Decisions. These are logical responsibilities that may share a service or process. The [decision register](decisions.md) defines the initial implementation topology.

Independent review supplies an assessment. Acceptance additionally requires the designated authority and required evidence. Policy may explicitly assign assessment and acceptance authority to the same eligible reviewer. Human escalation is distinct from ordinary human review, which follows project policy.

## Hierarchy and lifecycle principles

The scope hierarchy is **Project → Initiative → Task**. Milestones group delivery targets independently of execution dependencies. Initial decomposition creates linked Tasks within the Initiative, preserving traceability to their origin rather than creating nested Task trees.

Task, Run, and Decision lifecycles are modeled separately, with acceptance recorded independently of execution status. Review and verification normally use Assignments and Runs within a Task’s workflow; distinct Deliverables may justify separate Tasks. Retries, rework, and reassignment preserve the logical Task identity.

A completed Run supplies a result for assessment. A reviewed-patch Task may be accepted before a separately assigned integration Task when its contract permits this. Overall code delivery requires validation of the exact combined revision. Initiative acceptance follows its overall outcome and acceptance criteria.

Ready work may await execution capacity. Blocked work awaits an external condition, and a failed attempt follows the applicable recovery policy. Done describes accepted delivery. Workflow specifications define the concrete state names, transitions, and recovery behavior.
