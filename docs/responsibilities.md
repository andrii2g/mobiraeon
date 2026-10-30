# Responsibilities

Möbiræon separates logical responsibilities from agent execution configurations. Roles define accountability; governing policies establish authority, and Agent Profiles define execution configuration. A role name or model output grants no permissions.

## Roles and accountability

| Role | Accountability |
| --- | --- |
| **Human owner** | Establishes goals, constraints, authority, and acceptance expectations; participates in clarification and early review; resolves escalated product decisions. |
| **Orchestrator Agent** | Reasons about intake, plans, assignments, and Decisions; proposes actions through authorized Coordinator operations and initiates human escalation within policy. |
| **Architect and planner** | Researches alternatives, describes boundaries and contracts, evaluates tradeoffs, and proposes bounded work and dependencies. |
| **Technical writer** | Maintains specifications, acceptance criteria, component descriptions, and project summaries linked to authoritative artifacts. |
| **Developer** | Implements assigned changes and relevant tests; documents outcomes, limitations, and unresolved questions. |
| **Reviewer** | Independently assesses deliverables against applicable requirements, accepted decisions, and review rules. |
| **Verifier or QA** | Establishes verification evidence, assesses relevant edge cases, and checks integrated behavior. |
| **Decision resolver** | Investigates questions using accepted context, appropriate specialists, research, or experiments; recommends resolutions or escalation to the Orchestrator Agent. |

## Coordination and execution components

| Component | Accountability |
| --- | --- |
| **Coordinator** | Enforces authority, authoritative workflow state, and progression and acceptance rules. Applies acceptance only when governing authority and evidence establish it. |
| **Scheduler** | Deterministically dispatches eligible, authorized work within configured capacity and limits. It does not use model output as permission to bypass controls. |
| **Worker** | Provides execution capacity for supervised Runs. Availability does not establish Task readiness or authority. |
| **Runner Adapter** | Invokes a configured runtime through a transport, supervises its lifecycle, and normalizes outcomes. It operates within configured execution and tool policies. |

These are logical responsibilities, not a requirement for separate services. An Agent is the logical actor, its Profile is execution configuration, and a Run is one bounded attempt; none is interchangeable with Worker capacity.

## Role and profile assignments

Role assignments and agent profiles are configured independently. Profile assignments support multiple roles within one profile and multiple profiles for a role. The governing policy determines the permitted assignments and the independence required for assessment.

Each profile specifies its AI provider, model, supported reasoning settings, tools, context access, and execution limits. Role names, profile counts, and model choices are configurable.

## Coordination and decision authority

The Orchestrator Agent reasons about progression and uses specialist Agents for judgments within their responsibilities. The Coordinator enforces workflow state, permissions, and acceptance through explicit rules and recorded evidence; the Scheduler dispatches eligible work within those controls. A model's success statement alone does not establish that a rule has been satisfied.

Agents exercise the authority granted by the governing autonomy policy and baseline. They record unresolved questions as decision requests and provide the available evidence and recommended resolution.

The decision resolver investigates those requests and recommends a resolution or escalation. Only the Orchestrator Agent initiates or assigns agent-generated requests for human decisions or intervention, through authorized Coordinator operations. Normal human review remains available under project policy.

The human owner resolves escalated decisions within their authority. Accepted decisions are recorded and made available to the affected work.
