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

These collections describe ownership, not physical tables, package names, or exact API resources. Keep reusable definitions in one catalog. A Project selects eligible definitions and binds its integrations without duplicating Agents or silently broadening governing permissions or limits. Physical schemas and concrete validation contracts follow the [agreed control and override rules](#current-controls).

Registry persistence is the authoritative publication source. Git may supply reviewed import inputs or receive exports through the same validation process; it is not a second independently editable Registry. A separate Gitea Registry repository is unnecessary. Structured configuration and Markdown instruction content remain supported without making Git commits their identity.

Versioned project bindings preserve internal Agent identities and historical forge attribution. Account provisioning and forge qualification remain separate preparation activities under the [forge identity rules](#forge-identities). Project migration and cross-forge synchronization remain separately scoped under [D-07](decisions.md#d-07-forge-integration-and-initial-platform).

## Administrator access and bootstrap authority

Start with one explicitly designated human owner as administrator. Administrative identities and grants belong to trusted application access controls, separate from publishable Agent definitions, Role text, and forge accounts. Publishing configuration cannot create administrative authority.

| Area | Behavior |
| --- | --- |
| First-owner bootstrap | An explicit, protected local setup action establishes the first administrator while administrative access is uninitialized. No running Orchestrator or Agent is required. |
| Bootstrap boundary | Access initialization survives restart. Clearing the Agent catalog cannot reopen bootstrap; repeated setup cannot add administrators, replace the owner, or reset established access. |
| Ordinary administration | API and CLI establish trusted caller identity and enforce the same current permissions on every protected operation, including reads. The foundation's local OS operator grants and test policies do not automatically grant Registry administration. |
| Permission boundaries | Catalog management and granting administrative access are distinct permissions; initially the owner may hold both. Registry administration does not automatically grant execution or delivery-acceptance authority. |
| Automation | Agents receive no Registry administration in Increment 2. Later Coordination access uses its own trusted service identity with only the access needed to resolve published definitions and current eligibility. |
| Revocation and recovery | Revocation blocks subsequent protected operations. Protect against accidental loss of the last usable administrator and provide explicit owner-controlled recovery while keeping first-time bootstrap closed. |

Retain attributable audit records for bootstrap, access changes, recovery, and catalog operations, including their outcomes. Credential values stay outside Agent definitions and logs. Authentication technology, concrete grant contracts, credential storage, and the recovery procedure remain implementation details. The [access and bootstrap diagram](diagrams/registry-access.md) shows the authority boundary.

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

## Current controls

Keep the selected published Agent revision and present administrative enablement distinct from immutable publication history. These current decisions are authorized, auditable, and persistent; historical values cannot establish current permission.

| Control | Behavior |
| --- | --- |
| Selected revision | Explicitly choose a published Agent revision for future work. Publishing another revision does not automatically select or enable it. |
| Enablement | Current disablement prevents new selection and dispatch. Historical enabled values cannot bypass it; enablement alone does not authorize execution. |
| Execution gates | Coordination checks current authority, qualification, readiness, holds, capacity, and remaining budgets. Registry eligibility satisfies only one condition. |
| Active Runs | Ordinary configuration changes affect future selections. Existing Runs retain their pinned configuration; revocations and stop controls follow the established enforcement and recovery rules. |

Disabling an Agent and stopping active work remain separate authorized controls. Immutable Run records preserve history without preserving revoked permission. The [controls and overrides diagram](diagrams/registry-controls.md) shows the Registry boundary and later Coordination checks.

## Permitted overrides

Initially, an Agent may override only explicitly declared execution ceilings by lowering them, such as duration, retries, tokens, cost, or applicable concurrency. Each override is explicit, validated, reviewed, and retained in the Agent revision. It cannot expand governing permissions or limits, reset consumed budgets, or introduce a silent substitution.

Changes to Role, instructions, runtime, transport, provider/account, model, reasoning, execution options, or governing policies and contracts use a new reviewed Profile revision. Unknown override fields, conflicting references, and unsupported combinations are rejected.

Resolve configuration against every applicable constraint: numeric ceilings must remain within all governing ceilings, permissions must satisfy all governing policies, and incompatible execution choices require correction. No automatic merge may conceal a conflict. For example, a declared lower Agent token ceiling may be permitted, while changing its model requires a reviewed Profile change.

A permitted override still needs applicable qualification. Registry validation checks the definition; Coordination checks whether the resolved configuration may execute. The [configuration contract](requirements.md#agent-configuration-contract) governs the fields and retained requested/effective settings; concrete supported override fields and validation rules remain implementation contracts.

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

## Bootstrap inputs and preparation evidence

An established, authorized administrator prepares the initial catalog from one reviewed set of inputs through the normal [authoring and publication path](#authoring-and-publication).

| Input | Required content |
| --- | --- |
| Agent catalog | The five [agreed identities](#initial-agent-catalog) mapped to Role-specific Profiles, all initially disabled and carrying no administrative grants. |
| Instructions | Snapshots of the [shared operating rules](roles/_shared/OPERATING_RULES.md) and applicable [Role instructions](roles/README.md), with their source version and provenance. |
| Candidate Profiles | Complete required runtime, transport, provider/account references, model, reasoning, options, and limits for one primary execution path. Preserve [D-08's selection intent](decisions.md#d-08-initial-profiles) and independent review configuration. |
| Governing definitions | Exact published references for capabilities, tool and authority policies, context/output contracts, and any permitted fallback. Reuse suitable definitions across Profiles. |
| Preparation authority | The established administrator's applicable review and publication permissions. Credential values remain outside catalog content. |

Reusable instruction snapshots are bootstrap inputs; project-specific Assignments and resolved Run context arrive later. Exact models, limits, connection references, and governing definitions still require selection. Required missing values keep affected definitions in draft. Test fixtures establish Registry mechanics separately from the complete candidate catalog.

Preparation evidence demonstrates:

- **Exact retrieval:** all five published Agent/Profile revisions, their exact dependencies, current disabled state, instruction provenance, and attributable review/publication records are retrievable.
- **Persistence:** restart preserves the publications, bindings, and current controls.
- **Repeatability:** repeating or resuming preparation creates no duplicate identities or silent overwrites. Conflicting inputs require explicit reconciliation and reviewed changes.
- **Controlled failures:** representative missing-reference, invalid-setting, unauthorized or stale-change, and failed-publication cases produce truthful outcomes. A failed publication leaves no partial published result for that operation.

Retain a concise generated preparation record with Increment 2's submission evidence, identifying application and input versions, performed checks, results, and limitations. Preparation completes with a reviewed, published, persistent five-Agent catalog, all disabled. Runtime qualification, enablement, execution, project/forge bindings, and external account provisioning follow their later contracts.

## First-Agent preparation

Apply the [onboarding model](workflow.md#agent-onboarding) through the following initial setup sequence. Concrete runtime/model values, numeric limits, exact lifecycle states, and API endpoints remain specifications.

The [bootstrap inputs and evidence](#bootstrap-inputs-and-preparation-evidence) define Increment 2's disabled-catalog completion point. The sequence below also includes later integration and execution preparation; those stages retain their applicable increment boundaries.

| Stage | Preparation |
| --- | --- |
| Bootstrap | Establish the first human administrator through the protected [access bootstrap](#administrator-access-and-bootstrap-authority), then use authorized Registry operations, initially through a CLI. Creating the first Orchestrator does not require an already running Orchestrator or an Agent Run. |
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
