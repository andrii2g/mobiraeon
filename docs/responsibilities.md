# Responsibilities

Möbiræon separates logical responsibilities from agent execution configurations. Roles define accountability and authority; agent profiles define how those roles execute their assignments.

## Roles and accountability

| Role | Accountability |
| --- | --- |
| **Human owner** | Establishes goals, constraints, authority, and acceptance expectations; participates in clarification and early review; resolves escalated product decisions. |
| **Orchestrator** | Tracks progression, selects eligible work, coordinates assignments, routes blockers, enforces limits, and creates requests requiring human decisions or intervention. |
| **Architect and planner** | Researches alternatives, describes boundaries and contracts, evaluates tradeoffs, and proposes bounded work and dependencies. |
| **Technical writer** | Maintains specifications, acceptance criteria, component descriptions, and project summaries linked to authoritative artifacts. |
| **Developer** | Implements assigned changes and relevant tests; documents outcomes, limitations, and unresolved questions. |
| **Reviewer** | Independently assesses deliverables against applicable requirements, accepted decisions, and review rules. |
| **Verifier or QA** | Establishes verification evidence, assesses relevant edge cases, and checks integrated behavior. |
| **Decision resolver** | Investigates questions using accepted context, appropriate specialists, research, or experiments; recommends resolutions or escalation to the orchestrator. |

## Role and profile assignments

Role assignments and agent profiles are configured independently. Profile assignments support multiple roles within one profile and multiple profiles for a role. The governing policy determines the permitted assignments and the independence required for assessment.

Each profile specifies its AI provider, model, supported reasoning settings, tools, context access, and execution limits. Role names, profile counts, and model choices are configurable.

## Coordination and decision authority

The orchestrator coordinates the progression of work and uses specialist agents for judgments within their responsibilities. Work eligibility, permissions, and acceptance are enforced through explicit rules and recorded evidence. A model's success statement alone does not establish that a rule has been satisfied.

Agents exercise the authority granted by the governing autonomy policy and baseline. They record unresolved questions as decision requests and provide the available evidence and recommended resolution.

The decision resolver investigates those requests and recommends a resolution or escalation. Only the orchestrator creates requests requiring human decisions or intervention.

The human owner resolves escalated decisions within their authority. Accepted decisions are recorded and made available to the affected work.
