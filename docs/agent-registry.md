# Agent Registry and first Agents

The Agent Registry is a **Python module in the `mobiraeon` repository and application**, with its own authenticated, versioned API and **SQLite persistence**. It is independent of Gitea and follows [D-05](decisions.md#d-05-registry), [D-11](decisions.md#d-11-implementation-technology-and-topology), and the approved [configuration contract](requirements.md#agent-configuration-contract). The initial catalog and preparation sequence below define the first Agents and their administrator-led setup.

The application foundation is accepted; Registry business operations remain the next implementation increment. The [Increment 2 plan](implementation-plan.md#increment-2-agent-registry-and-bootstrap) records its agreed scope and six Tasks; detailed contracts remain under discussion. The ownership and onboarding rules below remain the governing baseline.

## Registry ownership and interface

Initially the Registry shares Möbiræon's Python application and local SQLite database with Coordination, retaining ownership of its tables and configuration operations. Its API manages creation, editing, validation, review/publication, enablement, retrieval, and versioned export/import. Describe the authenticated, versioned HTTP interface with OpenAPI; the administrator's CLI uses the same authorized application operations. Detailed endpoint contracts and schemas remain specifications.

| Logical collection | Purpose |
| --- | --- |
| Agents | Stable internal identities, exact Profile revision bindings, administrative enablement, and permitted overrides. |
| Profiles | Reusable execution configuration with Role, instruction, runtime, capability, policy, and limit references. |
| Instructions, policies, and capability definitions | Versioned responsibility text, shared rules, constraints, declared execution capabilities, and qualification requirements. |
| Revisions and publications | Immutable published configurations, exact dependency references, review/change provenance, and audit history. |
| Project integration bindings | Project selection and policy references, plus external forge account and repository mappings separate from Agent and Profile identity. |

These collections describe ownership, not physical tables, package names, or exact API resources. Keep reusable definitions in one catalog. A Project selects eligible definitions and binds its integrations without duplicating Agents or silently broadening governing permissions or limits. Schema design and override precedence remain later specifications.

Registry persistence is the authoritative publication source. Git may supply reviewed import inputs or receive exports through the same validation process; it is not a second independently editable Registry. A separate Gitea Registry repository is unnecessary. Structured configuration and Markdown instruction content remain supported without making Git commits their identity.

Versioned project bindings preserve internal Agent identities and historical forge attribution. Account provisioning and forge qualification remain separate preparation activities under the [forge identity rules](#forge-identities). Project migration and cross-forge synchronization remain separately scoped under [D-07](decisions.md#d-07-forge-integration-and-initial-platform).

## Authoring and publication

Agents, Profiles, instructions, policies, and capability definitions follow the same high-level authoring path. Publication establishes reviewed configuration; execution qualification and current eligibility remain separate.

| Activity | Behavior |
| --- | --- |
| Draft | An authorized administrator creates or edits a candidate definition. Incomplete drafts may be saved, but cannot be selected for work. |
| Validate | Check completeness, declared compatibility, exact references, and governing restrictions. Configuration validity does not establish runtime qualification. |
| Review | Assess the exact candidate, its dependencies, and the change reason. Retain the reviewer's identity and applicable authority with the reviewed content and references. |
| Publish | Publish the reviewed candidate as an immutable, retrievable revision with consistent, valid published dependencies. Check that review and authority still apply; a failed publication leaves no partial published result. |
| Change | Start a new draft from published content. Further candidate edits require renewed review; published history remains intact. |

For initial administrator-led setup, the same authorized human may author, review, and publish where governing policy permits. Record the actions distinctly. A separate reviewer is required when policy calls for one; Role text alone does not grant review or publication authority. Reject stale concurrent edits rather than overwriting another change or publishing content different from what was reviewed.

Publication does not cascade changes to dependent definitions. A new Profile revision leaves Agents bound to their existing exact Profile revisions. Moving an Agent to a different Profile is an explicit, reviewed configuration change for later authorized selection; publication does not enable the Agent, establish qualification, or rewrite existing Runs. Current disablement, revoked access, and governing restrictions still apply to historical definitions.

Returning to earlier settings creates a new reviewed revision, potentially reusing earlier published dependencies after current checks. Preserve history and reassess qualification where the change requires it. The [authoring and publication diagram](diagrams/registry-publication.md) summarizes this model without defining exact states or API operations.

## Forge identities

Use one stable Gitea automation account for each registered Agent that acts in the forge, plus a separate Coordination service account. Accounts attach to Agent identities rather than Roles, Profile revisions, Workers, or individual Runs. An Agent performing no forge operations need not acquire a forge account merely to execute.

Versioned project integration configuration binds each Agent to the relevant forge instance, account, repositories, and permitted operations. These bindings remain separate from reusable Profiles and model-provider accounts. Exact binding fields and physical schemas belong to the implementation contracts.

The Coordination account publishes coordination updates; Agent-attributed submissions and reviews use their mapped principals through authorized operations. Account provisioning is an administrative activity. Repository access alone grants no workflow authority or review independence. Trusted operations enforce authenticated actor and Run attribution; a commit author name is insufficient proof of the acting principal.

Use applicable Gitea [repository and team permissions](https://docs.gitea.com/usage/access-control/permissions/), [API-token permissions](https://docs.gitea.com/development/api-usage/), and [protected-branch controls](https://docs.gitea.com/usage/access-control/protected-branches/) alongside Möbiræon's controls, qualifying the actual operations on the installed instance. Configuration, exports, and Run records retain secret references; credential values remain outside the Registry and model-visible context.

## Revision and execution boundaries

- Published revisions and their exact references remain immutable and retrievable under the [authoring and publication rules](#authoring-and-publication). Changes preserve prior publications and their review provenance.
- An Agent revision references an exact Profile revision. Before dispatch, Coordination resolves all governing references and retains an immutable effective configuration snapshot; later publication cannot rewrite that Run.
- Publication, qualification, enablement, and execution authorization are separate. The Coordinator checks current enablement and authority, so historical snapshots cannot bypass disablement or revoked access. Existing Runs follow the established human-control and recovery rules.
- Registry administration requires applicable authority and records changes with provenance. Agents cannot grant themselves broader permissions or limits by editing configuration.
- Backups, restoration, and versioned export/import preserve identities, published definitions, references, and history alongside Coordination records and retained Artifacts. Database or service migration must preserve revision meaning and be verified.

The Registry retains declared configuration and secret references. Coordination retains qualification references, availability, Assignments, Runs, usage, and acceptance. Artifacts retain substantial qualification and delivery evidence. Credential values remain in the secret-management mechanism, outside Registry content and exports. The [Registry diagram](diagrams/registry-organization.md) shows the ownership and API boundary.

## Initial Agent catalog

Start with five stable logical Agents, each bound to a Role-specific Profile. Use the names below for the initial Agents; internal identities, external account names, and model choices remain distinct.

| Agent | Role | Initial purpose |
| --- | --- | --- |
| `orchestrator-01` | Orchestrator | Interpret Requests, coordinate plans and Assignments, resolve routing questions, and initiate required human escalation. |
| `planner-01` | Architect and planner | Define the bounded feature, contracts, acceptance expectations, and Task dependencies. |
| `developer-01` | Developer | Implement the assigned change and relevant tests and documentation. |
| `reviewer-01` | Reviewer | Independently assess submitted revisions; exercise acceptance authority only when explicitly delegated. |
| `verifier-01` | Verifier or QA | Produce required behavioral and combined-result verification evidence. |

The Coordination service account is separate from the Agent catalog, and the human owner is never configured as an autonomous Agent.

Five registered Agents do not require five concurrent processes or a Run for every Role on every Task. In particular, separate Verifier/QA Runs follow the contract and policy; ordinary tool-based checks still produce evidence without requiring another reasoning Run.

## First-Agent preparation

Apply the [onboarding model](workflow.md#agent-onboarding) through the following initial setup sequence. Concrete runtime/model values, numeric limits, exact lifecycle states, and API endpoints remain specifications.

| Stage | Preparation |
| --- | --- |
| Bootstrap | An authorized human administrator uses the Registry interface, initially through a CLI. Creating the first Orchestrator does not require an already running Orchestrator or an Agent Run. |
| Seed instructions | Import snapshots of the finalized [Role catalog](roles/README.md) and shared rules as authoring inputs, retaining their source provenance. Validate, review, and publish instruction revisions through the same publication path; live file changes cannot silently change Run inputs. |
| Prepare Profiles | Start with explicit Role-specific Profiles targeting one primary execution path to qualify first. Reuse suitable capability and policy definitions. Configure runtime/provider/model references, reasoning intent, tools, output/context contracts, and limits under the existing configuration contract. |
| Create Agents | Create each stable identity disabled for ordinary selection. Bind it to an exact Profile revision and retain any permitted explicit overrides; assign no work during creation. |
| Bind the Project | Bind the selected Agent definitions and governing policies, then arrange external account access and versioned integration bindings. Each Agent acting in Gitea uses its own stable mapped account; credentials remain separate. |
| Publish and qualify | Review and validate the definitions and dependencies, then publish exact retrievable Registry revisions. Authorized qualification checks evaluate the candidate execution configuration/environment independently of ordinary Agent selection; they do not dispatch the disabled Agent or override disablement or revoked access. |
| Enable selection | An authorized administrator enables each Agent whose intended configuration is qualified for its intended work. A configured intake rule identifies the initial Orchestrator; every ordinary Assignment and Run still passes current Coordinator and Scheduler checks. |

Several Profiles may share the same runtime, provider, and model where suitable. Preserve [D-08](decisions.md#d-08-initial-profiles): strong reasoning for planning and consequential Decisions, medium reasoning for routine implementation, and independently configured review.

A Profile is reusable only where its Role and instruction bindings, capabilities, and policy support the work. Sharing a runtime does not permit arbitrary Profile substitution. Independent review requires the separate Assignment, Run, provenance, and context controls already established in the workflow; a separate Gitea account alone is insufficient.

After initial setup, create, configure, and enable additional Agents through the same controlled Registry operations. Initial catalog changes are administrator-led; Agents do not create or enable other Agents.

Configuration changes produce reviewed revisions for later selections. Existing Runs retain their exact configuration and context. Detailed schemas, model/provider choices, runtime versions, numeric limits, account names, and validation commands remain the next design layer. The [first-Agent preparation diagram](diagrams/first-agent-preparation.md) summarizes the setup sequence.

Return to [Agent onboarding](workflow.md#agent-onboarding) or the [documentation guide](README.md).
