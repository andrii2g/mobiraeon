# Möbiræon documentation

The [requirements](requirements.md) and [decisions](decisions.md) define the approved design. The [architecture](architecture.md), [workflow](workflow.md), [Agent Registry](agent-registry.md) and [Role catalog](roles/README.md) explain the logical parts, delivery flow and administrator-led preparation of the five initial Agents. Design agreement, implementation, qualification and human acceptance remain separate.

The [implementation plan](implementation-plan.md#current-position) records accepted Increments 1–4 and the technically complete Increment 5 manual Gitea bridge. The bridge links an existing local Task to an existing issue and manually publishes one Coordinator-owned status/evidence comment under the [forge contracts](forge-contracts.md). The [final repair reassessment](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md) closes the last material finding; designated human acceptance remains separate.

The maintained contracts and [verification guide](verification.md) describe available operations and tested limits. Ordinary Agent execution, the polling/scheduling service and end-to-end delivery qualification remain later work. All five actual Agents remain disabled and unqualified. Historical reviews and raw evidence are located through the [archive catalog](evidence-archive.md).

Increment 5 also uses the agreed [cooperative editing rule](implementation-plan.md#field-ownership-and-publication): check the managed comment before updates, hold detected conflicts, and require humans to avoid editing it during synchronization. The remaining read/update race is explicitly accepted; atomic protection is not claimed.

## Reading order

| Document | Owns |
| --- | --- |
| [Project overview and foundation guide](../README.md) | Product purpose, supported work, delivery authority, and current foundation setup/operation |
| [Definitions](definitions.md) | Canonical terminology and relationships |
| [Requirements](requirements.md) | Approved requirements, Agent configuration contract, and acceptance scenarios |
| [High-level architecture](architecture.md) | System boundary, five logical parts, Coordination responsibilities, persistence ownership, and main exchanges |
| [Workflow](workflow.md) | Delivery, recovery, human controls, context/shared work, and Agent onboarding |
| [Mermaid diagrams](diagrams/README.md) | High-level system and focused workflow views, with agreement markers |
| [Decision register](decisions.md) | Confirmed decisions, remaining details, and their consequences |
| [Implementation plan](implementation-plan.md) | Accepted increments, current planning, remaining specifications, and verification gates |
| [Documentation finalization](reviews/2026-11-04-documentation-finalization.md) | Current implementation boundaries, operating examples, portable navigation and preserved evidence |
| [Final Increment 5 repair reassessment](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md) | Last P2 closed; source/installed regressions and both platform suites pass; no remaining material finding |
| [Full repository review](reviews/2026-11-04-increment-5-full/REVIEW.md) | Original P2 finding, preserved nonblocking observations and validation |
| [Verification guide](verification.md) | Maintained platform, source-binding, signal and Docker qualification rules |
| [Evidence archive](evidence-archive.md) | Retired developer briefs, submissions and raw artifacts; verified restoration paths |
| [Forge bridge contracts](forge-contracts.md) | Implemented manual Gitea bridge, Project authority, tokens, budgets, recovery and cooperative-edit limits; designated human acceptance separate |
| [Full repository review](reviews/2026-11-02/REVIEW.md) | Historical findings against the accepted Increment 4 commit, focused reproductions and verification limits |
| [First repair reassessment](reviews/2026-11-02-reassessment/REVIEW.md) | Independent final-02 review, original finding dispositions, residual/new findings and verification evidence |
| [Final repair reassessment](reviews/2026-11-02-fr02-r1-fr06-reassessment/REVIEW.md) | Independent resolution of FR-02-R1 and FR-06 against the final frozen snapshot, with source/installed verification |
| [Repository repair acceptance](reviews/2026-11-02-repairs-acceptance.md) | Human acceptance of the completed repair pass, exact snapshot, retained limits and retired instructions |
| [Agent Registry](agent-registry.md) | Registry ownership, protected credential delivery, authentication/hosting, operations/persistence, publication, controls/overrides, and first-Agent preparation evidence |
| [Coordination contracts](coordination-contracts.md) | Implemented local simulated workflow, authority, exact evidence, duplicate/restart safeguards and exclusions |
| [Execution contracts](execution-contracts.md) | Accepted supervised fixture handoff, local authority, bounded Docker supervision, stopping/cleanup, artifacts and persistent reporting |
| [Registry operation contracts](registry-contracts.md) | Implemented operation, document, persistence, credential-lifecycle, hosting and failure contracts |
| [Initial Agent configuration](initial-agent-configuration.md) | Approved initial test settings, reusable policies, numeric ceilings and unprovisioned logical connection references |
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

Increment 1's Python application foundation is implemented, independently reviewed, and accepted within its [recorded scope and limitations](implementation-plan.md#increment-1-shared-contracts-and-application-foundation). The [root README](../README.md#application-foundation-increment-1) owns the current setup, configuration, storage, operation, and verification guide.

[Increment 2](implementation-plan.md#increment-2-agent-registry-and-bootstrap) is implemented, independently reviewed, and accepted by the human owner. Its authenticated Registry API/CLI and initial test catalog are available; all five Agents remain disabled and unqualified for execution.

[Increment 3](implementation-plan.md#increment-3-coordination-and-scheduling) is implemented, independently reassessed, and accepted by the human owner for the smaller Coordination slice: one supplied Request/Initiative/Task through a simulated attempt, independent assessment and explicit Task acceptance, with persistent status/history and duplicate/uncertainty safeguards. I3-R1 is resolved in the accepted repaired snapshot. Its [contracts](coordination-contracts.md) and [application guide](../README.md#local-coordination-increment-3) describe the available local operations and isolated scenario. Completed implementation assignments are retired from active documentation; their exact briefs and evidence remain in the reviewed archives.

[Increment 4](implementation-plan.md#increment-4-supervised-execution) is implemented, independently reassessed, and accepted by the human owner for one supervised fixture Run at a time in an isolated local Linux/container Worker. I4-R1–R3, including residual I4-R2, are resolved in the accepted repaired snapshot. The [application guide](../README.md#supervised-fixture-execution-increment-4) supplies preparation and run/status/stop commands; the completed implementation brief is retired, with its exact text preserved in the reviewed source archives. All five actual Registry Agents remain disabled and unqualified.

The [repository repair pass](reviews/2026-11-02-repairs-acceptance.md) is also accepted by the human owner. FR-01–FR-05, residual FR-02-R1 and FR-06 are resolved through the preserved review and reassessment chain. The completed repair briefs are retired from active documentation; their exact text remains in the captured source archives. This acceptance retains the existing fixture, authority and qualification limits.

Broader [Coordination capabilities](implementation-plan.md#deferred-coordination-capabilities), ordinary Agent execution, runtime/provider qualification and broader forge integration remain later work. Increment 5 has completed implementation, full review and [verified closure of its last material finding](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md); designated human acceptance remains separate. Retired implementation/repair briefs and raw evidence are preserved in the [archive](evidence-archive.md). Gitea is the first provider; later providers use the same adapter boundary. Recorded Gitea setup checks and remaining operational verification are covered by the [infrastructure guide](infrastructure.md#verification-before-relying-on-the-instance).
