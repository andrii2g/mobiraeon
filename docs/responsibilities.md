# Responsibilities

Möbiræon separates accountability, execution configuration, and authority. Roles define responsibilities; Agent Profiles configure execution; governing policies and execution configuration establish permissions, limits, and delegated authority.

## Roles and accountability

| Role | Accountability |
| --- | --- |
| **Human owner** | Establishes goals, constraints, and acceptance expectations; approves the initial baseline and delegation policy; participates in clarification and resolves escalated Decisions within their authority. |
| **Orchestrator Agent** | Reasons about intake, plans, Assignments, and Decisions; coordinates specialist contributions, proposes authorized coordination actions, and initiates human escalation when required. |
| **Architect and planner** | Researches alternatives and proposes architecture, boundaries, contracts, bounded Tasks, and dependencies; records tradeoffs, assumptions, and consequences. |
| **Technical writer** | Maintains specifications, acceptance criteria, component descriptions, and source-linked summaries; identifies ambiguity and the documentation impact of changes. |
| **Developer** | Implements assigned changes, relevant tests, and documentation; commits and pushes through permitted repository operations; reports results, limitations, and unresolved questions. |
| **Reviewer** | Independently assesses exact submitted revisions against applicable requirements, accepted Decisions, contracts, and review rules; records findings and review outcomes. |
| **Verifier or QA** | Produces verification evidence for identified revisions and environments; exercises relevant edge cases, failure conditions, and integrated behavior; reports failures and limitations. |
| **Decision resolver** | Investigates unresolved questions using accepted context, specialists, research, or experiments; evaluates evidence and alternatives and recommends resolution or escalation to the Orchestrator Agent. |

## Coordination and execution components

| Component | Accountability |
| --- | --- |
| **Coordinator** | Maintains authoritative workflow state and enforces permissions, prerequisites, ownership, limits, progression rules, and acceptance gates. Records acceptance when the required authority and evidence establish it. |
| **Scheduler** | Deterministically dispatches eligible, authorized Runs within configured capacity and limits. Tasks awaiting prerequisites or Decisions consume no active execution slot. |
| **Worker** | Provides execution capacity under configured isolation and resource controls; reports availability and execution health. |
| **Runner Adapter** | Invokes the configured runtime through a transport, delivers inputs, captures outputs, supervises the process lifecycle, and normalizes outcomes within execution and tool policies. |

These are logical responsibilities and may share a service or process. Agent identity, Profile configuration, Worker capacity, and Run execution remain distinct concepts, as defined in the [definitions](definitions.md).

## Role and Profile assignments

Role assignments and Agent Profiles are configured independently. A Role may use multiple qualified Profiles, and a Profile may serve multiple Roles where its instruction bindings, capabilities, and governing policy permit.

Each Run records its assigned responsibilities, applicable instruction revisions, Agent identity, Profile revision, and effective configuration. Profiles specify the runtime, transport, provider, model, supported reasoning settings and options, tools, context policy, and execution limits through the Agent configuration contract.

Role descriptions and shared operating rules provide the instructions for each Assignment. Reusing a Profile or changing a Role label preserves the applicable permission boundaries and review-independence requirements.

## Coordination and decision authority

The Orchestrator Agent plans and routes work through authorized Coordinator operations. The Coordinator validates proposed actions against current state, policy, and evidence; the Scheduler dispatches work within those controls. Model output supplies proposals or evidence for evaluation, not permission to bypass controls.

Agents act within the governing baseline, delegation policy, and execution permissions. They record unresolved questions as Decision requests with evidence, attempted resolution, recommendations, affected work, and required authority. The Decision resolver investigates and recommends an outcome; any authority to accept that outcome comes from policy.

Only the Orchestrator Agent initiates or assigns agent-generated requests for human decisions or intervention, through authorized Coordinator operations. Ordinary human review and intervention follow project policy.

Accepted Decisions identify their authority, applicable baseline, affected revisions, and required follow-up actions. Dependent work resumes after the accepted resolution, required artifact updates, and prerequisite conditions are recorded and satisfied.

## Recovery and human controls

The Coordinator records and enforces durable waiting conditions, recovery decisions, and authorized human controls. The Scheduler respects them when dispatching; execution supervises wind-down and cleanup or containment. The Orchestrator handles unresolved judgment when eligible. Authorized human controls do not require an Orchestrator Run. Takeover retires prior automation ownership before exclusive human work, and return to automation requires current checks. Human-produced changes remain subject to normal review and acceptance.

See [waiting and recovery](workflow.md#waiting-and-recovery) and [human controls and scope changes](workflow.md#human-controls-and-scope-changes) for their effects and boundaries.

## Review, acceptance, and integration

Independent review uses a separate Assignment and Run under the configured independence policy. Changing the author’s Role or Profile alone does not establish independence. The same model may perform authoring and review when the policy’s independence conditions are satisfied.

Review and verification provide assessments and evidence. Acceptance requires the designated authority and applicable gates; policy may explicitly grant acceptance authority to an eligible reviewer.

The [initial defaults](workflow.md#initial-defaults) assign routine routing to the Coordinator under approved rules and ordinary Task acceptance to an explicitly delegated, eligible independent reviewer. The Orchestrator handles unresolved judgment or exceptions; the Scheduler dispatches the resulting authorized Runs.

For [Initiative outcome acceptance](workflow.md#initiative-outcome-acceptance), the Orchestrator coordinates the overall assessment and any missing work. An eligible independent Reviewer requires explicit Initiative-level delegation to accept the outcome; Task-level authority does not extend automatically. The Coordinator enforces and records the determination.

For [Request closure and follow-up](workflow.md#request-closure-and-follow-up), the Coordinator applies the approved closure rule to accepted delivery and Request-specific criteria. The Orchestrator classifies later reports and proposes appropriate repair, new scope, or a Decision. Existing acceptance does not silently grant broader Request-level judgment.

Integration uses the assigned workflow and authorized repository identity. Ordinary implementation Task contracts include integration and fresh combined-revision validation. A Task may finish with an accepted reviewed patch when its contract explicitly assigns integration separately. Overall code delivery requires the prescribed review evidence and fresh validation of the exact combined revision. The [decision register](decisions.md) defines the governing delivery and authority boundaries.
