# Möbiræon documentation

The product requirements and D-01 through D-12 form the design baseline. The high-level architecture and workflow cover delivery, recovery, human controls, scope changes, context continuity, and Agent onboarding. The [pilot repository names, CSV-export feature, Gitea identity policy, and setup sequence](pilot-and-agent-setup.md) are selected design choices. [Registry organization and the first Agents](agent-registry.md) remain proposed; the [remaining agenda](implementation-plan.md#remaining-high-level-discussions) separates these discussions from later specifications. Complete the remaining contracts and operational specifications before implementing the affected capabilities or activating the pilot.

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
| [Planning sequence](implementation-plan.md) | Remaining high-level discussions, later specifications, and design validation order |
| [Pilot and Agent setup](pilot-and-agent-setup.md) | Selected pilot repository names and CSV feature, Registry hosting, Gitea identity mappings, and setup order |
| [Agent Registry](agent-registry.md) | Proposed Registry organization, first registered Agents, and configuration boundaries |
| [Implementation readiness review](implementation-readiness-review.md) | Remaining contracts, operational details, and recommended discussion order |
| [Infrastructure](infrastructure.md) | Gitea/PostgreSQL Compose setup in WSL, local configuration, verification, and backup/restore procedures |
| [Gitea workflow lab](gitea-workflow-lab.md) | Created private rehearsal repository, starter templates and labels, linked samples, and API verification evidence |

The earlier experimental sample is historical context; its technology choices and state names do not establish the target design. Its prototype reference is not present in this checkout.

## Agreement and change rules

- **Confirmed** means the user explicitly requested or agreed to the requirement or decision. It does not mean implemented or tested.
- **Proposed** means a recommendation prepared for discussion.
- **Open** means a choice or detail remains unresolved.
- Record implementation and verification evidence separately from agreement status.
- Keep each definition in the definitions document, each requirement in the requirements document, and each unresolved choice in the decision register. Other documents link to those owners.
- Give a change to an agreed requirement or specification a new revision and identify affected tasks before execution continues.

## Current boundaries

CLI execution through Codex CLI, Claude Code CLI, and Ollama is a requested capability. Agent configuration and a persistent agent collection are required. The system and repository names Möbiræon and `mobiraeon` are confirmed; D-02 terminology, D-03 hierarchy, D-04 lifecycle principles, and D-05 Registry publication are confirmed; detailed state names and transitions remain under review. Gitea is confirmed as the initial local forge through the versioned, forge-neutral adapter contract in [D-07](decisions.md#d-07-forge-integration-and-initial-platform). D-11 confirms Python, one active Coordinator/Scheduler service, supervised isolated runner processes, and SQLite on local persistent disk. D-06 confirms one Linux control host with locally attached, isolated container Workers. D-08 confirms profile-selection intent and staged qualification. D-09 confirms operating-policy principles, D-10 confirms delegated authority, and D-12 confirms the bounded feature pilot. Concrete lifecycle/adapter contracts, framework and versions, isolation controls, numeric operating values, the delegation matrix, the executable pilot specification, and qualification evidence still require completion.

The current source sample has not been changed to implement the revised definitions. No agent runtime, provider, or forge is activated by these documents.
