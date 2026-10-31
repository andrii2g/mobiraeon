# Möbiræon documentation

The product requirements and D-01 through D-12 form the design baseline. The high-level architecture and workflow cover delivery, recovery, human controls, scope changes, context continuity, and Agent onboarding. The Registry is a forge-independent Python module within Möbiræon, with its own authenticated, versioned API and SQLite persistence. [Forge identities](agent-registry.md#forge-identities) and [first-Agent preparation](agent-registry.md#first-agent-preparation) define account mappings, the five-Agent catalog, and administrator-led bootstrap. The [implementation plan](implementation-plan.md#remaining-specifications) tracks unfinished contracts and verification gates, including selection of a bounded end-to-end validation scenario under D-12.

## Reading order

| Document | Owns |
| --- | --- |
| [Product goals and scope](../README.md) | Product purpose, supported work, engineering coverage, and delivery authority |
| [Definitions](definitions.md) | Canonical terminology and relationships |
| [Requirements](requirements.md) | Approved requirements, Agent configuration contract, and acceptance scenarios |
| [High-level architecture](architecture.md) | System boundary, five logical parts, Coordination responsibilities, persistence ownership, and main exchanges |
| [Workflow](workflow.md) | Delivery, recovery, human controls, context/shared work, and Agent onboarding |
| [Mermaid diagrams](diagrams/README.md) | High-level system and focused workflow views, with agreement markers |
| [Decision register](decisions.md) | Confirmed decisions, remaining details, and their consequences |
| [Implementation plan](implementation-plan.md) | Remaining specifications, readiness gates, implementation work, and verification evidence |
| [Agent Registry](agent-registry.md) | Registry ownership, API, logical collections, revision boundaries, forge identities, first Agents, and bootstrap |
| [Infrastructure](infrastructure.md) | Gitea/PostgreSQL Compose setup in WSL, local configuration, verification, and backup/restore procedures |

## Agreement and change rules

- **Confirmed** means the user explicitly requested or agreed to the requirement or decision. It does not mean implemented or tested.
- **Proposed** means a recommendation prepared for discussion.
- **Open** means a choice or detail remains unresolved.
- Record implementation and verification evidence separately from agreement status.
- Keep each definition in the definitions document, each requirement in the requirements document, and each unresolved choice in the decision register. Other documents link to those owners.
- Give a change to an agreed requirement or specification a new revision and identify affected tasks before execution continues.

## Current boundaries

The initial design uses Python, one active Coordinator/Scheduler service, one Linux control host with supervised isolated container Workers, local Gitea, and SQLite on local persistent disk. Registry and coordination data share the application and storage with separate logical ownership. The Registry API publishes immutable revision IDs; Git is optional import/export. These boundaries follow D-05 through D-07 and D-11.

The requested execution paths are Codex CLI, Claude Code CLI, and an Ollama-backed coding harness, qualifying one primary path first under D-08. Operating limits, delegated authority, and bounded end-to-end validation follow D-09, D-10, and D-12. The [implementation plan](implementation-plan.md#remaining-specifications) records unfinished contracts and settings; its [qualification and live-pilot gates](implementation-plan.md#gates-before-qualification-or-live-pilot-execution) and [verification requirements](implementation-plan.md#verification-and-evidence) separate remaining preparation from established evidence.

This checkout contains documentation and Gitea infrastructure/bootstrap scripts. The Registry, Coordinator/Scheduler, and Worker runtime remain to be implemented and qualified. Recorded Gitea setup checks and remaining operational verification are covered by the [infrastructure guide](infrastructure.md#verification-before-relying-on-the-instance).
