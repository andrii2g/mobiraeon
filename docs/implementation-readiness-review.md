# Implementation readiness review

Reviewed on **2026-10-31** against the approved requirements and confirmed D-01 through D-12. This is a documentation review, not implementation or runtime qualification evidence. Recommendations below are proposed; they do not amend confirmed requirements or grant operational permissions.

## Overall assessment

The decisions form a coherent pilot baseline: Project → Initiative → Task; separate execution and acceptance; a Git-versioned Registry; one Linux control host with isolated container Workers; local Gitea through an in-process forge-neutral adapter; Python with one active Coordinator/Scheduler service and SQLite; and a bounded feature pilot with delegated authority and explicit limits.

No direct contradiction was found among the confirmed decisions. Their principles are sufficient to begin detailed design. They do not yet specify enough operational behavior for independently implementing all components or starting unattended live execution.

Do not reopen the selected name, hierarchy, initial forge, language, or persistence choice merely because their detailed contracts are unfinished. Exact state names, policy schemas, enforcement mechanisms, release coverage, and executable acceptance checks remain distinct follow-up work.

## Clarifications before implementing the affected contracts

| Area | What remains to be specified | Recommended direction | Governing baseline |
| --- | --- | --- | --- |
| Lifecycles and assignments | Task, Run, Decision, Initiative, and acceptance states; transition guards and actors; pause/cancel/resume semantics; assignment identity and progression from implementation to review and integration. | Define separate transition tables. Distinguish Task ownership from Run/assignment identity and specify how exclusive ownership supports review and verification without accidental concurrent execution. Rework preserves Task identity. | D-03, D-04; F-12, F-19, F-20, F-22 |
| Authority and independence | Concrete actors and grants for approving specifications, resolving Decisions, accepting artifacts, integrating, or changing policy; reviewer eligibility and independence rules implementing the confirmed reviewer-acceptance default. | Produce a versioned actor/operation/target matrix. Use separate review Runs with explicit authorship/provenance checks and a defined context-isolation policy; a new identity, role, or Profile alone is insufficient. Include human approval authentication through the forge. | D-08, D-10; S-03, F-18, F-20, F-25 |
| Coordinator state and recovery | Entity identifiers, revisions, ownership generations, operation identities, transactional boundaries, dispatch durability, lease expiry, reassignment, and uncertain-effect reconciliation. | Specify a minimal domain model and command/result contracts before the SQLite schema. Couple state changes to durable pending operations; fence stale owners and reconcile external effects before retry. Define when cleaned or contained capacity is reusable. | D-04, D-11; F-22, F-23; N-02, N-05 |
| Runner and configuration contracts | Input/output envelopes, artifact and evidence references, cancellation and errors, supported overrides, publication validation, schema versions, and compatibility rules. | Build on the already approved configuration fields rather than redesigning them. Pin all references, reject unknown options, record requested/effective settings, and define explicit outcome categories without treating model claims as acceptance. | D-05, D-08; F-03 through F-09 |
| Enforcement boundary | Container runtime, mounts, process/resource controls, allowed network routes, secret mechanism, protected repository operations, and the channel for authorized Coordinator actions. | Specify a threat model and trusted enforcement path before enabling command execution. Explain how subprocesses and raw Git/forge requests are constrained, how credentials remain outside model-readable access, and how superseded execution loses privileged access. Prompt instructions and container placement alone do not meet N-04. | D-06, D-10; N-02 through N-04 |
| Forge contract | Supported operations/events, adapter capabilities, per-field authority, external edit/close/reopen behavior, actor authentication, event deduplication, reconciliation, and conflict handling. | Keep internal authority explicit. Treat forge actions as authenticated requests, not automatic acceptance. Define stable mappings and reconciliation for uncertain creates and updates; separate ordinary comments from authorized commands. | D-07; F-16, F-18, F-22, F-24 |
| Artifacts, context, and integration | Artifact identity and durable publication, baseline manifests, summary refresh, dependency satisfaction, evidence invalidation, integration serialization, and retention/deletion relationships. | Identify governing revisions explicitly. Define how artifacts become durable before acceptance, what happens if a referenced revision disappears, and when changes invalidate readiness/review. Validate the exact combined target revision and preserve required evidence across cleanup. | D-05, D-11; F-13 through F-15, F-21, F-27; N-05 |

## Clarifications before paid qualification or live pilot execution

| Area | What remains to be specified | Completion evidence |
| --- | --- | --- |
| Concrete pilot and release coverage | Repository/base revision, feature, inclusions/exclusions, feature and system acceptance checks, allowed branches/operations, and who accepts the outcome. Explicitly state whether the first release supports one execution path or all three requested runtime families; identify deferred work against F-02. The .NET example and endpoint remain candidates. | Approved, versioned pilot specification traceable to D-12 and S-05; no broader support claim than the qualified scope. |
| Primary execution path | Exact runtime/harness, provider/account reference, model, reasoning settings, versions, and independently configured review. Decide whether the Ollama path is included now; if so, name its coding-tool harness. | Versioned capability definitions, approved qualification configuration, and passing support-matrix checks for the declared scope. Approval for qualification must precede paid or privileged checks; ordinary Runs require qualification. |
| Operating profile | Numeric budgets, allocation estimates, concurrency, deadlines, retry/failure thresholds, ownership timing, cleanup criteria, retention/deletion, backup/restore objectives, and behavior when cost is unavailable. | Approved values and executable checks showing enforcement; measured recovery results rather than assumed targets. Previously suggested numbers are not approved by D-09. |
| Deployment and recovery | Exact Linux/Python/SQLite/container/Gitea versions, packaging, migrations, startup/shutdown, service identity, storage paths, backup destination, restore procedure, and operator stop/status controls. | A reproducible environment and tested restoration of coordination state together with artifacts and referenced Registry revisions; linked observations for blocked, uncertain, and failed work. |

## Documentation alignment found during review

- The documentation index still described technology selection as future work and treated operating policy, delegation, and release scope broadly as unresolved. Those descriptions have been aligned with confirmed D-09, D-10, D-11, and D-12; concrete policies and specifications remain unfinished.
- The planning sequence still invited comparison of implementation/hosting alternatives already settled in D-06 and D-11. It now distinguishes completing those choices from reopening them.
- The high-level architecture and workflow cover delivery, recovery, human controls, and context continuity. Agent onboarding, forge identities, and the concrete pilot remain under discussion. Detailed contracts and exact lifecycle names remain open. Logical component boundaries are not additional services.
- The architecture phrase requiring independent acceptance could imply that the reviewer cannot also accept. It has been aligned with F-20 and D-10: independent review is required; designated acceptance authority may belong to the reviewer under policy.

- Two existing links pointed to the absent historical `reference/prototype.md`. They have been replaced with an explicit availability note; no prototype content was reconstructed.

## Recommended discussion and implementation order

1. Agree lifecycle transitions, assignment/ownership semantics, and the authority/independence matrix together.
2. Specify Coordinator commands, persistence/recovery invariants, and Runner/configuration envelopes; derive storage and adapter schemas from these contracts.
3. Specify the enforcement boundary, forge synchronization, artifact/context handling, and integration rules before implementing their privileged paths.
4. Select the concrete pilot, primary execution configuration, operating values, and release coverage. Complete environment and qualification plans.
5. Implement and verify bounded slices, beginning with deterministic coordination and fake runners/adapters, then real container/forge/runtime qualification and the approved pilot.

Detailed design and offline implementation need not wait for every live numeric value or provider account to be chosen. Privileged execution, paid qualification, and live operation require their applicable approvals and controls. Not every design detail requires another human decision: follow the existing delegation policy where one applies; otherwise record the proposed decision for approval.

Related sources: [decisions](decisions.md), [requirements](requirements.md), [definitions](definitions.md), [responsibilities](responsibilities.md), [architecture](architecture.md), [workflow](workflow.md), and [planning sequence](implementation-plan.md).
