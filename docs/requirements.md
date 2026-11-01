# Möbiræon requirements

This document defines the approved product requirements and Agent configuration contract for Möbiræon. The agreed interpretations below form part of this baseline.

Requirement IDs remain stable. Changes to the baseline require the applicable approval or delegated authority and must identify affected work. Implementation, qualification, and verification evidence are tracked separately; an approved requirement is not a claim that the capability has been implemented or verified.

The baseline is technology-neutral. Release scope, implementation technologies, forge mappings, deployment topology, and environment-specific operating values are established through the decisions and policies required by S-05, S-06, and N-07.

## Purpose and scope

| ID | Requirement |
| --- | --- |
| S-01 | Coordinate AI agents to deliver a new project, feature, or other bounded software change with infrequent human involvement after planning. |
| S-02 | Cover requirements, specifications, research, architecture, data, domain, business logic, workers, presentation, implementation, and testing as the change requires. |
| S-03 | Start with a brief prepared by the human, clarify it with a capable model, and discuss and approve the brief and initial specification with the human. |
| S-04 | Allow different agent roles to use different providers, models, reasoning settings, and other execution options. |
| S-05 | Define the scope baseline for the first live release, including the first complete end-to-end use case, supported operating environments, inclusions, exclusions, and acceptance criteria. Obtain human approval unless an existing human-approved delegation policy explicitly authorizes the scope decision. Record the approval or the applicable delegation and its rationale. |
| S-06 | Review alternatives against the approved requirements and release scope, and establish the implementation stack, persistence technology, coordination infrastructure, and forge. Record the choices, rationale, tradeoffs, and constraints. Obtain human approval of this technology baseline unless an existing human-approved delegation policy explicitly authorizes the decision. Record the approval or the applicable delegation and its rationale. |

## Agent and execution terminology

Terminology, roles, hierarchy, and states are described in [definitions](definitions.md). A registered Agent uses a versioned Profile; a Worker hosts execution and a Runner Adapter invokes the chosen runtime. Related architecture and lifecycle decisions are maintained in the [decision register](decisions.md).

## Functional requirements

### Configuration and execution

| ID | Requirement |
| --- | --- |
| F-01 | Provide a stored collection of configured agents that can be assigned distinct responsibilities and execution settings. |
| F-02 | Support the requested CLI execution choices: Codex CLI, Claude Code, and an Ollama-based path. |
| F-03 | Represent runtime integration, runner transport, provider, and model as separate configuration properties. Declare and validate compatibility constraints. Resolve provider and model selections from explicit configuration or declared profile defaults. Selecting a runtime or CLI must not silently override those selections. |
| F-04 | Execute Runs noninteractively through a defined contract covering input delivery, output and artifact capture, timeouts, cancellation, termination, and machine-readable outcomes. Requests for interactive input must produce a controlled failure or recorded internal decision request without leaving execution waiting for terminal input. |
| F-05 | Execute Ollama-based implementation Runs through an explicitly configured coding-tool harness providing policy-controlled repository access, file editing, command execution, and capture of tool actions and results. A model response alone is not evidence that implementation actions occurred or that implementation is complete. |
| F-06 | Before dispatch, validate the resolved Run configuration against the versioned capability definitions applicable to the selected runtime, provider, and model. Reject unsupported or unrecognized reasoning settings, options, and combinations. Any permitted fallback must be explicitly authorized, validated, and recorded; silent substitution or coercion is prohibited. |
| F-07 | Maintain a persistent Agent Registry containing registered Agent identities, stable profile identifiers, and immutable, retrievable profile revisions. Store credentials through the configured secret-management mechanism. Profiles, task descriptions, configuration exports, and audit records must contain secret references rather than secret values. |
| F-08 | Before dispatch, bind each Run to an immutable configuration record containing the Agent identity and Profile revision, runtime identity and version, runner transport, provider and account reference, model identifier, reasoning settings and other options, tool policy, limits, and context revisions. Record requested and effective settings separately, including resolved defaults. Append observable execution identities and deviations to the Run’s execution history without modifying the bound configuration. Explicitly identify unavailable or unverified information. |
| F-09 | Maintain an evidence-backed support matrix covering installed runtime versions, runner transports, operating environments, provider/account references, models, reasoning settings, and required noninteractive capabilities. Mark a combination as supported for its declared capability scope only after its defined acceptance checks pass. Record the tested configuration, evidence, and limitations; reassess qualification when relevant components or configuration change. Ordinary Runs require qualified combinations; explicitly authorized qualification Runs may test unvalidated combinations. |

### Planning and task coordination

| ID | Requirement |
| --- | --- |
| F-10 | Enable the Orchestrator Agent to classify intake, select suitable Agent Profiles, and coordinate research, documentation, architecture, milestones, Task assignments, implementation, and verification through authorized operations. |
| F-11 | Make assigned Tasks and their linked governing context discoverable to eligible Agents. Allow Agents to execute Ready, authorized Tasks, submit versioned deliverables, and record the validation actually performed, including its results and limitations. |
| F-27 | Provide project, milestone, and Task summaries alongside detailed Task descriptions covering scope, inputs, dependencies, deliverables, and acceptance criteria. Apply a defined summary format and refresh policy. Identify each summary’s source revisions and freshness so outdated summaries cannot be mistaken for current governing context. |
| F-26 | Allow implementation Agents to test, commit, and push their Task changes through authorized repository operations. Record the submitted revisions and associated validation evidence. Commit or push success alone does not establish Task acceptance or delivery completion. |
| F-12 | Represent Initiative ownership and parent-child scope separately from execution dependencies. Accept and close a planning Task when its own deliverables and acceptance criteria are satisfied; keep the Initiative open until its overall outcome is accepted. A parent link alone does not establish an execution prerequisite. |
| F-13 | Represent execution dependencies as a validated acyclic Task graph. Each dependency identifies the required deliverable or Decision, acceptance conditions, and applicable version constraints. Record the accepted artifact revision or Decision resolution that satisfies it. A closed Task or forge item alone does not satisfy a prerequisite. Reject dependency changes that introduce cycles. |
| F-14 | Mark an implementation Task Ready only when its scope, deliverables, acceptance criteria, accepted prerequisites, and governing versioned context are available, resolvable, and consistent. A summary supports navigation and does not replace the governing sources. |
| F-15 | Reassess affected Tasks and Runs when governing requirements, contracts, dependencies, or accepted artifact revisions change. Record whether readiness, approvals, and validation remain applicable, and require necessary updates before affected work continues. Preserve each Run’s original baseline, context, and evidence for audit. |
| F-16 | Define and maintain explicit mappings and stable links among Initiatives, milestones, internal Tasks, Decisions, Runs, and external forge items. Specify authoritative state, synchronization, and conflict handling for each mapped entity. Runs, retries, and execution events must not require individual forge tickets. |
| F-25 | Separate Coordinator enforcement of authority and workflow state, deterministic Scheduler dispatch, and Orchestrator Agent reasoning. Validate proposed actions against current state and policy before execution. Dispatch only eligible, authorized Runs within configured limits. Model output alone must not grant permissions or change authoritative state. |

### Decisions, acceptance, and recovery

| ID | Requirement |
| --- | --- |
| F-17 | Allow Agents to submit internal decision requests identifying the question, evidence, attempted resolution, affected work, and required authority. Enable the Orchestrator Agent to resolve each request within its authority or route it internally. Preserve the original Task and its progress, and coordinate continuation once its prerequisites are satisfied. |
| F-18 | Permit only the Orchestrator Agent to initiate or assign agent-generated requests for human decisions or intervention. Other Agent roles route escalation through it. Enforce this restriction through policy and access controls while preserving normal human review under project policy. |
| F-19 | Record each Decision’s question, evidence, resolution, approving authority, applicable policy, affected baseline and revisions, and required follow-up actions. Persist waiting state and release active execution capacity. Resume dependent work only after the accepted resolution and required artifact changes are recorded and its prerequisites are satisfied. |
| F-20 | Require independent review of the exact submitted artifact revisions against their acceptance criteria. Conduct Agent review in a separate Run under the configured independence policy; changing roles or profiles alone does not establish independence. Record acceptance only when the designated authority and required review and verification evidence establish it. |
| F-21 | Require integration into the designated delivery target and fresh validation of the exact combined revision before code delivery is accepted. Serialize conflicting integration operations and reassess evidence affected by intervening changes. Individual Tasks remain subject to their own acceptance contracts. |
| F-22 | Use recoverable, exclusive Task execution ownership, stable operation identities, and bounded retries. Reject authoritative state changes and acceptance of results from expired or superseded ownership. Make side-effecting operations retry-safe through idempotency, deduplication, or reconciliation; check uncertain outcomes before retrying. Preserve Task identity across retries and reassignments. |
| F-23 | Maintain durable, attributable audit history linking Tasks and Runs to dispatch, state transitions, effective configurations, Decisions and authority, artifact revisions, results, validation evidence, recovery actions, and policy enforcement outcomes. Record usage and cost when available, distinguishing measured, estimated, and unavailable values. |
| F-24 | Persist waiting conditions, activate Agents for actionable work, and reconcile authoritative state after missed events or interruptions. Event monitoring and reconciliation must not invoke a model merely to check whether work or an answer is available. |

### Agreed interpretations

These interpretations form part of the agreed functional requirements.

| Requirement | Agreed interpretation |
| --- | --- |
| F-16 | The requirement establishes that a mapping exists. [D-07](decisions.md#d-07-forge-integration-and-initial-platform) selects the initial Gitea mapping; detailed adapter operations and qualification follow separately. |
| F-20 | A reviewer supplies an independent assessment. The reviewer may also hold acceptance authority when policy explicitly grants it. |
| F-21 | A Task may finish with a reviewed patch when its contract assigns integration to another Task. Overall code delivery remains incomplete until the combined result passes validation. |
| F-25 | Coordinator, Scheduler, and Orchestrator Agent are separate logical responsibilities; this does not require separate services. |
| F-24 | Ordinary API polling and scheduled reconciliation remain available. Idle model polling is excluded. |

## Agent configuration contract

The following field names, grouping, and configuration rules form the approved Agent configuration contract.

The persistent Agent Registry contains reusable Agent Profiles, registered Agents, and their revision history. Each registered Agent references a specific Profile revision. Any supported overrides are explicit, versioned, and included in configuration resolution.

Worker inventory, availability, Task ownership, scheduling, waiting conditions, Run state, results, and acceptance records remain separate from the Registry.

### Registry fields

| Field | Meaning | Related requirement |
| --- | --- | --- |
| `identity` | Stable identifier and display name. Registered Agent identity is distinct from reusable Profile identity. | F-01, F-07 |
| `revision` | Immutable configuration revision with change provenance and retrievable history. | F-07, F-08 |
| `enabled` | Current administrative eligibility for selection for new work. Historical values cannot bypass current disablement. Enablement does not establish authority, qualification, or Task readiness. | F-01, F-07, F-09, F-14 |
| `profileRef` | For a registered Agent, the exact reusable Profile revision it uses. | F-07, F-08 |
| `overrides` | Explicitly permitted changes to Profile defaults, retained in the registered Agent's revision. Overrides cannot expand governing permissions or limits. | F-07, F-08, F-25 |

Current selection explicitly identifies a published Agent revision for future work. Publication does not automatically select or enable it. Current selection and enablement are authorized, auditable, persistent controls distinct from immutable history; historical enabled values cannot establish current permission. See [current controls](agent-registry.md#current-controls).

Application operations distinguish stable-identity, draft, publication, current-control, and access targets. Mutable edit versions remain separate from immutable publication references; updates based on observed state carry expected versions checked within the protected transaction. Exact resolution never silently chooses latest content. Validated operation-specific inputs and safe read/business results retain the same logical outcomes across API and CLI; credential verification material is excluded. See [operation contracts](agent-registry.md#operation-contracts).

Initially, Agent overrides may only lower explicitly declared execution ceilings for duration, retries, tokens, cost, or applicable concurrency. Retain each validated, reviewed override in the Agent revision. Other execution, instruction, Role, and governing-policy changes use a new reviewed Profile revision. Overrides cannot reset consumed budgets or introduce silent substitutions. See [permitted overrides](agent-registry.md#permitted-overrides).

### Profile configuration

| Field | Meaning | Related requirement |
| --- | --- | --- |
| `roleRef` | Versioned role responsibilities and eligible Task classes. A role description grants no permissions. | S-04, F-10, F-25 |
| `instructionsRefs` | Versioned standing instructions, including shared operating rules and role instructions. | F-08, F-14 |
| `contextPolicyRef` | Rules for selecting and resolving governing Task context. Actual inputs and resolved context revisions are recorded per Run. | F-08, F-14, F-15 |
| `runtime` | Explicit execution application or coding-tool harness identity, required version constraints, and versioned capability-definition reference. | F-02, F-03, F-05, F-06 |
| `runnerTransportRef` | Invocation mechanism and permitted execution target or Worker pool. The selected Worker and execution location are recorded per Run. | F-03, F-04, F-08 |
| `provider` | Explicit model-service or local-inference identity, configured separately from the runtime and runner transport. | S-04, F-03 |
| `providerConnectionRef` | Provider endpoint and account configuration, referencing credentials through the secret-management mechanism. This is separate from the runner transport connection. | F-03, F-07, F-08 |
| `model` | Requested provider-native model identifier, preserved as requested. Any resolved or runtime-reported identity is recorded separately. | S-04, F-03, F-08 |
| `reasoning` | Requested integration-native reasoning configuration, or an explicit unspecified value. Support is determined by capability validation. | S-04, F-06 |
| `runtimeOptions` | Runtime-specific options validated against the selected integration and its capability definitions. | F-04, F-06 |
| `providerOptions` | Provider/model-specific generation options, such as supported context/output limits and sampling controls. Endpoint and credential configuration belongs in connection references. | S-04, F-06 |
| `capabilityRequirementsRef` | Required execution features and integration acceptance checks. Qualification evidence is maintained separately for the tested configuration and environment. | F-04, F-05, F-06, F-09 |
| `outputContractRef` | Versioned contract for machine-readable execution outcomes, deliverables, artifact references, and validation evidence. A reported outcome does not itself establish acceptance. | F-04, F-11, F-20, F-23 |
| `toolPolicyRef` | Approved policy governing tools, repository operations, workspace/network boundaries, and required approvals. | F-08, F-26, N-04 |
| `authorityPolicyRef` | Approved policy governing workflow actions, decision delegation, human escalation, review independence, and acceptance authority. | F-18, F-20, F-25 |
| `secretRefs` | References resolved by an authorized secret-management mechanism. Secret values are excluded from Registry records, Tasks, exports, and audit records. | F-07, N-04 |
| `limits` | Configured ceilings for duration, retries, tokens, measurable cost, and applicable concurrency. Effective limits also respect governing project and execution budgets. | F-08, F-22, N-01 |
| `fallbackPolicyRef` | Explicitly authorized alternatives, triggering conditions, and limits. Absence of an applicable policy means no substitution is permitted. | F-03, F-06, F-08 |

### Resolution and dispatch

All references must resolve to specific revisions before dispatch. Requested configuration is validated against the selected runtime, provider, model, capability definitions, and applicable qualification evidence.

Respect every applicable numeric ceiling and governing policy. Reject unknown overrides, conflicting references, and incompatible execution choices rather than concealing conflicts in an automatic merge. A permitted override still requires applicable qualification. Ordinary configuration changes affect future selections; existing Run records stay pinned, while current revocations and stop controls follow the established enforcement and recovery rules.

Unsupported or unrecognized settings and combinations are rejected. Runtime flags, option values, model aliases, and reasoning settings are interpreted through the selected integration; they are not assumed interchangeable.

Ollama-based implementation Runs require an explicitly configured coding-tool harness. Generated model text alone is not evidence that implementation actions occurred or that implementation is complete.

Enablement and a valid Profile do not authorize dispatch. The Coordinator enforces authority and workflow state; the deterministic Scheduler dispatches only ready, qualified, authorized work within applicable limits. The Orchestrator Agent proposes actions through those controls.

For Increment 2, the [qualification-check boundary](agent-registry.md#enablement-before-coordination-qualification) is unavailable in production. An authorized enable request reports unavailable without changing current enablement; unauthorized requests are refused. Authorized disablement remains independent of qualification availability. The Registry creates no qualification records or manual qualification bypass. Later enablement requires an explicit request and fresh checks of the exact selected configuration. Stored enabled values and isolated test doubles cannot establish production qualification.

### Per-Run configuration record

Before dispatch, each Run receives an immutable configuration record containing:

- Agent and Profile identities, revisions, and explicit overrides;
- resolved instruction, context, contract, and policy references;
- runtime/harness identity and version, runner transport, selected Worker, and execution environment;
- provider and account references;
- requested and effective model, reasoning, and option settings, including resolved defaults;
- effective tool permissions, limits, and applicable qualification evidence.

Unknown, provider-managed, or unverified information is identified explicitly. A requested alias is not presented as a verified underlying model revision.

Runtime-reported identities, configuration deviations, usage, and results are recorded as linked observations without rewriting the original configuration record.

A fallback that changes pinned configuration requires explicit authorization and validation, and starts a new Run linked to the same Task and previous attempt. It must not conceal a provider, model, reasoning, or runtime substitution.

Changes to governing configuration or context trigger the reassessment required by F-15. Historical Run records retain their original configuration, context, and evidence.

### Initial selection intent

The initial preferences are `gpt-6.1-sol` with Ultra for clarification, specification, and research, and a GPT-6-class model with Medium for implementation.

For the [initial test catalog](initial-agent-configuration.md) delivered in accepted Increment 2, Orchestrator/Planner use Max; Ultra remains future intent. Developer uses Medium and independently configured Reviewer/Verifier use High. Limits are configured ceilings with unverified runtime enforcement; unprovisioned internal connection/credential references are explicitly initial-test declarations, not live connectivity.

These labels preserve selection intent; they do not establish qualified provider-native combinations. D-08 confirms strong planning/reasoning Profiles, medium routine implementation Profiles, independent review configuration, and qualification of one primary execution path before the remaining requested integrations. Exact model identifiers, reasoning settings, runtime mappings, and account access still require the qualification evidence specified by F-09.

### Storage boundary

A persistent, versioned catalog is required. [D-05](decisions.md#d-05-registry) selects a forge-independent Python Registry module with an authenticated, versioned API and authoritative SQLite persistence. It initially shares the application and database with Coordination while retaining separate logical ownership. Published definitions have immutable, retrievable Registry revision IDs; exact configuration references and per-Run records preserve their provenance.

Registry administration follows authorized, validated, auditable operations and protects against conflicting concurrent edits. Publication, execution qualification, administrative enablement, and authorization for particular work remain separate. Git import/export is optional and does not create another authoritative store or a dependency on Gitea.

Credentials are resolved separately through the configured secret-management mechanism. Operational state and immutable per-Run configuration snapshots remain separate from published Registry definitions.

### Runtime documentation

Codex documents scripted execution and machine-readable results through [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode). Claude Code documents its agent loop in [programmatic execution](https://code.claude.com/docs/en/headless). Ollama documents [CLI inference](https://docs.ollama.com/cli), [tool calling](https://docs.ollama.com/capabilities/tool-calling), and [Claude Code integration](https://docs.ollama.com/integrations/claude-code). These establish candidate integration capabilities, not tested support in this system. Validate each installed runtime/backend combination before activation; reasoning and other controls are capability-specific, as illustrated by [Ollama thinking](https://docs.ollama.com/capabilities/thinking).

## Nonfunctional requirements

| ID | Requirement |
| --- | --- |
| N-01 | Enforce configured aggregate and per-Run budgets, concurrency limits, deadlines, retry limits, and repeated-failure thresholds. Account for active allocations before dispatch, and distinguish measured, estimated, and unavailable usage/cost. On exhaustion, preserve progress and stop affected execution or further dispatch, escalating as policy requires. Exhaustion cannot establish successful completion or acceptance. |
| N-02 | Supervise bounded startup, cancellation, execution deadlines, output limits, exit reporting, and cleanup of Run-owned descendant processes. Record output truncation and incomplete cleanup. Prevent abandoned or superseded processes from retaining valid ownership, and reject authoritative state changes or acceptance of results submitted under expired or superseded ownership. Do not return affected execution capacity to service until cleanup or effective containment is established. |
| N-03 | Isolate concurrent mutable workspaces and enforce assigned change boundaries. Preserve other Runs’ work and unrelated changes. Coordinate updates to shared mutable artifacts, test state, and integration targets; detect conflicting revisions and resolve them under integration policy rather than silently overwriting work. |
| N-04 | Enforce workflow, tool, filesystem, network, repository, credential, and resource permissions through trusted controls outside model prompts, including operations initiated by subprocesses. Repository content, retrieved material, comments, and model output cannot expand authority. Resolve secrets only for authorized operations and prevent their disclosure in model-visible context, captured outputs, logs, reports, and audit records. |
| N-05 | Recover durably recorded Tasks, Runs, dependencies, Decisions, configuration records, waiting conditions, ownership, and outcomes from authoritative state within approved recovery targets. Reconcile uncertain effects and safely recover or reassign ownership. Surface inconsistent state and block affected operations; never silently reset progress, infer success, or accept stale results. |
| N-06 | Expose execution and acceptance states separately, including ownership, waiting or blocking reasons, failures, required human action, and the next required step. Link status to the underlying Tasks, Runs, configurations, decisions, artifacts, and validation evidence. Include last-update times and identify stale or uncertain observations. |
| N-07 | Before live operation, establish an approved, versioned operating profile for each supported environment. Define numeric budgets and capacity limits, startup, execution, and cancellation deadlines, retry limits, repeated-failure thresholds, cleanup and containment criteria, recovery objectives, retention and deletion rules, deployment permissions, and the threat model. Specify measurement methods, enforcement boundaries, and acceptance checks, including the treatment of estimated or unavailable cost. |

## Acceptance scenarios

These scenarios define expected observable behavior and supplement requirement-specific checks. Verification results must identify the tested revision, environment, method, observed outcome, and evidence. The tested revision must identify the relevant software, configuration, and policy revisions for each scenario.

| Requirement | Observable acceptance scenario |
| --- | --- |
| **S-03** | An implementation Task lacking required approval of its governing brief or initial specification remains unready. Approval is recognized only from the designated authority or through applicable human-approved delegation. |
| **F-06** | Request an unsupported reasoning value for an ordinary Run with no applicable authorized fallback. Dispatch is rejected with a structured explanation identifying the incompatible setting; no model invocation occurs. |
| **F-08** | Start a Run using Profile revision P1, then publish P2 with a different model setting. The active Run retains P1 and its original configuration record. Selecting P2 for a later Run produces a separate configuration record. |
| **F-14** | Remove acceptance criteria or make a required specification revision unresolvable. The Task becomes unready, identifies the missing input, and cannot receive implementation dispatch. Restoring valid inputs allows readiness to be reassessed. |
| **F-18** | A Developer Agent attempts to create or assign a human escalation. The control layer denies the operation without creating an item. An authorized orchestrator operation creates the escalation with its decision context and audit record. |
| **F-20** | The author changes role or Profile and submits a purported independent review. Independence checks reject it. An eligible independent Run reviews revision A; that review does not automatically establish review or acceptance of revision B. Any reuse of evidence requires explicit reassessment under policy. |
| **F-21** | A Task with a reviewed-patch acceptance contract is accepted after its required review. Its separately assigned integration Task remains pending. Overall code delivery remains incomplete until the exact combined revision passes required validation. |
| **F-22, N-05** | Restart during execution, deliver duplicate assignment events, and recover an expired ownership claim. Only a valid owner can advance the Task. Authoritative state updates and acceptance of results from the former owner are rejected; Task identity, accepted outcomes, and audit history remain intact. |
| **F-22, N-05** | Interrupt execution after a forge item is created but before local acknowledgement is recorded. Recovery reconciles the uncertain operation and reuses the existing item rather than creating a duplicate. |
| **N-01** | Exercise configured concurrency, budget, and retry limits. Excess dispatch waits or is rejected; exhausted attempts stop with a recorded reason. Exhaustion itself never establishes successful completion or acceptance. |
| **N-02** | Exercise startup failure, a hanging process, excessive output, and a child process that ignores graceful cancellation. Each reaches its configured outcome. Truncation and incomplete cleanup are visible; uncontrolled execution prevents affected capacity from returning to service. |
| **N-03** | Two concurrent Runs edit the same source path in isolated workspaces. Neither alters the other’s files or unrelated changes. Conflicting integration attempts are coordinated under policy without silent overwrites. |
| **N-04** | Repository instructions request a prohibited operation or unauthorized secret access. The control layer denies access. An authorized credential-backed operation succeeds without exposing a seeded test secret in model context or captured records. |
| **N-05** | Introduce an inconsistent durable reference. Recovery identifies the inconsistency and blocks affected operations without resetting progress or manufacturing a successful outcome. |
| **N-06** | A completed Run is displayed separately from its Task awaiting review. A blocked Task identifies its unmet prerequisite, next required action, and whether human intervention is required. |
| **F-24, N-01** | Leave the system idle through multiple reconciliation cycles. No model calls occur merely to check for work. After a notification is missed, deterministic reconciliation discovers the actionable state. |
| **N-07** | Live-operation readiness remains blocked while required operating values, threat assumptions, permissions, or approvals are missing. Readiness is evaluated against the approved operating profile and its recorded verification evidence. |

Related documents: [definitions](definitions.md), [architecture](architecture.md), [workflow](workflow.md), and [decision register](decisions.md).
