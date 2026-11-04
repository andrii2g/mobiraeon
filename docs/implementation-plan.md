# Implementation plan

This is the single checklist for remaining specifications, implementation preparation, and verification under the approved [requirements](requirements.md) and [decisions](decisions.md). Design agreement, provisioning, implementation, execution qualification, and delivery acceptance remain separate records.

## Current position

Increments 1–4 are implemented, independently reviewed, and accepted by the human owner within their recorded scopes below. The application includes the foundation, authenticated persistent Agent Registry with its disabled initial test catalog, [minimum local simulated Coordination workflow](#increment-3-coordination-and-scheduling), and [supervised fixture execution](#increment-4-supervised-execution) through one local Linux Docker Worker. Increment 4's I4-R1–R3 findings, including residual I4-R2, are resolved. Its completed implementation brief is retired; the maintained [execution contracts](execution-contracts.md) and [application guide](../README.md#supervised-fixture-execution-increment-4) describe the delivered interface.

The [repository repair pass](#repository-repairs-after-increment-4) is implemented, independently reassessed, and accepted by the human owner. FR-01–FR-05, residual FR-02-R1 and FR-06 are resolved within the reviewed scope. The [acceptance record](reviews/2026-11-02-repairs-acceptance.md) identifies the exact repaired snapshot and preserved review chain. Completed repair instructions are retired from active documentation; their original text and all prior evidence remain preserved.

[Increment 5](#increment-5-forge-integration-gitea-first) has an agreed high-level scope, [connection authority/configuration](#connection-authority-and-configuration), [field ownership](#field-ownership-and-publication), and [linking/conflict rules](#linking-and-synchronization-conflicts): one existing local Task explicitly linked to one existing Gitea Task issue in one configured repository, with manually triggered synchronization and a Coordinator-authored status/evidence comment. Its forge-neutral boundary follows D-07, with Gitea as the first adapter. The named [forge operations, Project-scoped permissions, local CLI and persistence ownership](#operation-and-persistence-contracts), [synchronization defaults and recovery](#synchronization-limits-and-recovery), and [demonstration](#demonstration-and-completion-evidence) are also agreed. The maintained [forge contracts](forge-contracts.md) define the wire/API bindings, configuration ranges and persistence constraints. The bounded bridge has completed implementation, [full independent review](reviews/2026-11-04-increment-5-full/REVIEW.md), and [verified closure of its last P2 finding](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md). Technical verification is complete with no remaining material finding. Designated acceptance remains pending. Broader Coordination, ordinary Agent execution, additional forge integration and execution qualification remain unfinished. All five actual Registry Agents remain disabled and unqualified.

The [architecture](architecture.md), [workflow](workflow.md), [forge-account policy](agent-registry.md#forge-identities), and [first-Agent preparation](agent-registry.md#first-agent-preparation) remain the design baseline. The concrete repository and feature for end-to-end validation will be selected under D-12. Existing Gitea setup checks and operational gaps remain in the [infrastructure guide](infrastructure.md#verification-before-relying-on-the-instance).

## Implementation increments

Use the following work breakdown to turn the agreed components into bounded implementation Tasks. Build subsequent increments on the accepted foundation and Registry interfaces, completing their applicable contracts and checks. Detailed execution choices and operating values remain in the checklist below.

| Increment | Position | Deliverable | Completion evidence |
| --- | --- | --- | --- |
| 1. Shared contracts and application foundation | Accepted | Python application, minimum shared contracts, configuration/diagnostics, SQLite migrations and transactions, and controlled operation boundaries. | Independent reassessment resolved R1–R5; Windows and Linux/WSL checks passed; the human owner accepted the identified snapshot with recorded limitations. |
| 2. Agent Registry and bootstrap | Accepted | SQLite-backed Registry API/CLI, immutable publication and reference resolution, protected administrator setup, and the disabled initial test Agent catalog. | Independent reassessment resolved I2-R1/I2-R2; Windows and Linux/WSL checks passed; the human owner accepted the identified repaired snapshot with its execution-readiness limitations. |
| 3. Minimum Coordination workflow | Accepted | One locally supplied Request/Initiative/Task, authorized Assignment and simulated Run, result, independent assessment and explicit Task acceptance, with persistent status/history and basic duplicate protection. | Independent reassessment resolved I3-R1; Windows and Linux/WSL checks passed; the human owner accepted the identified repaired snapshot within its local simulation and storage limits. |
| 4. Supervised execution | Accepted | One supervised fixture Run at a time in one local isolated Linux/container Worker, with bounded input/output, stopping, cleanup and persistent Coordination reporting. | Independent reassessments resolved I4-R1–R3, including residual I4-R2; Windows and Linux/WSL checks passed, including real source/installed Docker suites; the human owner accepted the exact repaired snapshot within its fixture limits. |
| 5. Forge integration (Gitea first) | Implementation, review and technical verification complete; designated acceptance pending | One existing local Task linked to one existing Gitea Task issue in one configured repository, manual synchronization, persistent mapping and one Coordinator-authored status/evidence comment through a forge-neutral adapter contract. | Repeated synchronization and restart preserve the mapping without duplicate work or updates; publication follows the agreed ownership/conflict and recovery rules within configured budgets. The [maintained forge contracts](forge-contracts.md) fixes interfaces, persistence constraints, ranges and required verification. |
| 6. Primary execution integration and qualification | Planned | Integrate and qualify the first actual Runner Adapter for one concrete runtime/provider/model/environment combination, declared capability scope, and independently configured review. Preserve the separate runtime/transport/provider/model configuration and extension boundary for the other requested paths. | Authorized qualification checks pass with versioned configuration, operating limits, evidence, and limitations; only qualified scope becomes eligible for ordinary work. Codex CLI, Claude Code CLI and the Ollama-based coding path require separate qualification. |
| 7. End-to-end delivery validation | Planned | One bounded change in a prepared existing repository selected through the D-12 validation contract. | The complete delivery, acceptance, waiting, recovery, duplicate, and stale-result scenarios pass for identified revisions. |

## Increment 1: shared contracts and application foundation

**Accepted by the human owner.** Acceptance covers Tasks 1–6 of the independently reviewed, repaired 77-file foundation snapshot with archive SHA-256:

```text
9a53a51b85cdd3cff39e11d04f451ee94811b40b144d7ca87a2b465fc4051d3b
```

R1–R5 are resolved. Independent verification reproduced 116 passing tests on Windows 11 and 115 on Ubuntu 24.04/WSL2, plus locked dependency checks, lint, formatting, builds, clean installed-wheel checks beneath a percent-containing path, and the recorded native interruption checks. The count difference is a Windows-only SIGBREAK unit case.

| Task | Accepted result |
| --- | --- |
| 1. Minimum shared contracts | Stable identities and exact revision references, configuration-reference consistency, operation/result contracts, and evidence/acceptance separation. |
| 2. Python application | Installable package, console/module entry points, application composition, foreground lifecycle, and truthful capability reporting. |
| 3. SQLite persistence | Explicit initialization/opening/upgrades, packaged immutable migration chain, store identity/revision guards, shared transactions, bounded contention, and truthful failure boundaries. |
| 4. Configuration and diagnostics | One immutable configuration resolution path, strict source validation and precedence, source-relative paths, safe JSON diagnostics, and controlled terminal reporting. |
| 5. Operation boundaries | Explicit owner routing, trusted caller context, current permission checks requiring a valid boolean grant, safe attribution, and distinct success/refusal/failure/uncertainty outcomes. |
| 6. Combined verification and assessment | Integrated checks and captured source/evidence, independent reassessment of repairs, and human acceptance of the foundation scope. |

Acceptance retains the recorded limits:

- Windows native signal checks passed through the recorded uv launcher. Direct interpreter execution in a restricted tool context timed out on SIGINT; restoring Ctrl+C processing in the isolated controller passed both signals. Evidence is launcher/context-qualified.
- Readiness precedes signal-handler registration, and the verifier waits 0.2 seconds before sending a signal. The checks cover steady-state interruption rather than the exact readiness boundary or every terminal's manual keyboard delivery.
- Windows and Linux/WSL foundation evidence does not qualify a production Linux host, full authentication, disaster recovery, or later Registry, Coordination, Worker, model, or forge capabilities.

The original and repaired source archives, manifests, handoffs, and independent review remain locally retained under the ignored `submissions/increment-1/` tree (now relocated intact through the [evidence archive](evidence-archive.md)). Documentation finalization records this acceptance and retires the completed assignment brief; it does not rewrite those captured snapshots or claim that the updated documentation still has their original file hashes.

The [D-11 technical baseline](decisions.md#d-11-implementation-technology-and-topology), [foundation setup and configuration guide](../README.md#application-foundation-increment-1), [storage/authorization boundaries](../README.md#storage-and-authorization-boundaries), and [application operation contract](../README.md#application-operation-contract) govern subsequent work. The old implementation instructions are no longer an active assignment; their exact text remains in the reviewed source archives.

## Increment 2: Agent Registry and bootstrap

**Accepted by the human owner.** Acceptance covers Tasks 1–6 of the independently reassessed, repaired 102-file Registry snapshot with archive SHA-256:

```text
013654178835b0194d0f2641eff63f8653029664839a588f48f697fbe21502b1
```

I2-R1 and I2-R2 are resolved. Independent verification reproduced 156 passing tests on Windows 11 and 155 on Ubuntu 24.04/WSL2, plus locked dependency checks, lint, formatting, builds, installed-wheel checks beneath a percent-containing path, TLS trust/hostname rejection, and source/installed foundation/API interruption checks. The same 14 repair regressions produced nine failures against the original reviewed source and all passed against the repaired source.

| Task | Accepted result |
| --- | --- |
| 1. Define Registry contracts | Strict operation targets/inputs/read results, exact revisions, mutable versions, invocation-local trusted identity, authoring/review/publication, control and override bounds, and truthful input/effect outcomes. |
| 2. Implement Registry persistence | Forward migration with catalog/access ownership, immutable publication/dependency/history records, current controls, stale-edit protection, and per-operation mutation/audit transactions. |
| 3. Implement controlled catalog operations | Authorized authoring, validation, exact-candidate review/publication, retrieval/history, explicit selection, reduced ceilings, unavailable enablement and usable disablement. |
| 4. Provide API and CLI administration | Protected owner setup/recovery, revocable credentials/grants, coordinated delivery/registration/cleanup, authenticated API/CLI, direct TLS, caller isolation and bounded lifecycle handling. |
| 5. Prepare the initial catalog | Five complete initial test Agent/Profile pairs and dependencies, approved logical account/credential references, exact selections, disabled state, restart persistence and repeat/resume/conflict evidence. |
| 6. Verify and independently assess the Registry | Source-bound developer verification, preserved original review, independent reassessment of both repairs, and human acceptance of this bounded result. |

Acceptance retains these limits:

- All five Agents remain disabled, unqualified and without administrative grants. Approved [initial test settings](initial-agent-configuration.md) and internal references are complete catalog configuration; external credentials, connectivity and runtime enforcement remain unprovisioned or unverified.
- Authorized enablement remains unavailable without mutation; disablement is usable. Registry acceptance grants no execution, provider calls or delivery-acceptance authority.
- Credential lifecycle exclusion is verified for cooperating application processes on tested local Windows/POSIX stores. Network-filesystem/distributed locking, hostile OS interference, power-loss durability and disaster recovery are not qualified. The persistent lock sidecar must not be manually removed.
- Windows signal evidence covers the exercised native console context. Linux/WSL evidence does not qualify a production Linux/container deployment; live disconnect and hung-handler scenarios retain their recorded limits.
- Coordination, scheduling, Workers/Runner Adapters, forge integration, execution qualification and end-to-end delivery remain later increments. Optional Registry Git import/export remains separately scoped.

The original and repaired source archives, manifests, handoffs, original review and separate reassessment remain locally preserved under ignored `submissions/increment-2/` (now relocated intact through the [evidence archive](evidence-archive.md)). The acceptance record identifies this exact repaired snapshot; documentation finalization does not rewrite captured evidence or claim that the updated documentation retains the snapshot's original hashes.

The [Registry design](agent-registry.md), [operation contracts](registry-contracts.md), [initial configuration](initial-agent-configuration.md), and [application guide](../README.md#agent-registry-increment-2) govern ongoing use. The completed implementation assignment is retired from active documentation; its original text remains in the reviewed archives. Subsequent increments build on these accepted interfaces without implicitly enabling the initial Agents or introducing live execution.

## Increment 3: Coordination and scheduling

**Accepted by the human owner.** Acceptance covers Tasks 1–6 of the independently reassessed, repaired 111-file minimum Coordination snapshot with archive SHA-256:

```text
5a32ddb559c590ab77bb5b817cf99ea66687341eac5c388af436b72acb04b21f
```

I3-R1 is resolved. Independent verification reproduced 207 passing tests on Windows 11 and 206 on Ubuntu 24.04/WSL2, locked dependency checks, lint, formatting, builds, installed-wheel checks beneath a percent-containing path, Registry/TLS checks, source/installed foundation/API interruption checks and the simulated workflow. The same 19 regression cases produced six expected failures and 13 passes against the original reviewed source, then all passed against the repaired source. The platform count difference remains the Windows-only SIGBREAK case.

| Task | Accepted result |
| --- | --- |
| 1. Minimum contracts and workflow authority | Strict local actions and explicit scoped grants, trusted invocation-local callers, current authorization and separate workflow/Registry authority. Synthetic author/assessor identities exist only in isolated composition. |
| 2. Persistent work and history | Forward migration 0003, retained Project/Request/Initiative/Task context, separate immutable stage facts, exact configuration/artifact references, transactional history and stable receipts. |
| 3. Narrow workflow progression | Supplied bounded work through submitted evidence, independent exact-submission assessment and explicit Task acceptance. Run completion cannot accept the Task or its parent outcome. |
| 4. Explicit allocation and simulated dispatch | One explicit fixture allocation, current authority/reference/ownership checks and durable reservation before the isolated simulated effect. Ordinary Agent execution remains unavailable. |
| 5. Restart and duplicate safety | Persistent inspection, replay/conflict protection, stale/non-owner refusal and uncertainty fences. I3-R1 binds resolving receipts to the original operation, with conservative legacy-history handling. |
| 6. Combined verification and handoff | Source-bound developer verification, preserved original review, independent regression comparison/reassessment and human acceptance of this bounded result. |

Acceptance retains these limits:

- One local supplied Request/Initiative/Task scenario, CLI actions/status and an isolated scripted simulator. Preserve `Project → Initiative → Task`; the Request is a separate origin link. No live Orchestrator, Coordination HTTP surface or background service is delivered.
- Synthetic assessment/Task acceptance demonstrates application policy mechanics; it is distinct from independent review and acceptance of this increment. The Request stays open and the Initiative stays unaccepted.
- All five initial Registry Agents remain disabled and unqualified. No Worker, provider/model, forge or repository-integration capability is qualified or enabled. Ordinary tokens still represent one installation human; two tokens cannot establish reviewer independence.
- Uncertain outcomes remain fenced unless exact retained evidence establishes the original recorded operation. Legacy replay history without sufficient provenance can remain conservatively unresolved. There is no automatic retry, reassignment or general reconciliation workflow.
- If both commit acknowledgement and separate uncertainty-history recording fail, audit availability is explicitly unavailable; missing records cannot authorize retry. Retained local storage and deliberate inspection remain necessary. Power loss, hostile OS interference and disaster recovery are not qualified.
- Native interruption evidence retains its console/readiness-timing limits; Linux/WSL is not production Linux qualification. Broader [Coordination capabilities](#deferred-coordination-capabilities), supervised execution and later roadmap work remain deferred.

The original archive/review, repaired submission under `submissions/increment-3/repair-i3-r1/`, and separate independent reassessment remain locally preserved under ignored `submissions/increment-3/` (now relocated intact through the [evidence archive](evidence-archive.md)). This acceptance identifies the exact repaired snapshot; documentation finalization does not rewrite evidence or claim that updated documentation retains the snapshot's original hashes.

The [Coordination contracts](coordination-contracts.md) and [application guide](../README.md#local-coordination-increment-3) own the maintained interface and operation details. The completed developer brief is retired from active documentation; its exact text remains in the reviewed archives. Select the next small delivery boundary before preparing another implementation assignment.

## Increment 4: supervised execution

**Accepted by the human owner.** Acceptance covers Tasks 1–5 of the independently reassessed, repaired 129-file supervised fixture snapshot with archive SHA-256:

```text
15ab37802b6b523a01475a356b4c4830799959ee71914c56f317bb6d386b1517
```

I4-R1 and I4-R3 were resolved in the first independent reassessment; the separate residual-I4-R2 reassessment resolves the nested-signal defect with no new material findings. Independent verification reproduced 271 passing tests on Windows and 269 passing tests plus one skip on Ubuntu 24.04/WSL2. Both platform runners completed all 13 commands successfully, covering locked dependencies, lint, formatting, builds, clean installed wheels beneath a percent-containing path, Registry/TLS, Coordination and native interruption checks.

The real Linux Docker source and installed suites each passed 76 driver records, including seven repair cases. Separate source/installed signal probes passed all nine cases on each platform. The same probe reproduced all four nested-signal deadlocks on the prior baseline; the repair required actual depth-two delivery, both handler returns, pending intent and handler restoration. Spaced real CLI signal cases separately verified stop intent and descendant/container retirement. These results establish the tested fixture scope, not ordinary Agent or production qualification.

| Task | Accepted result |
| --- | --- |
| 1. Execution handoff | Authenticated run/status/stop actions, current scoped authority, exact Task/Assignment/attempt ownership and immutable inputs/settings before launch. |
| 2. Worker and fixture Runner Adapter | One local Linux Docker Worker and packaged deterministic fixture/build assets, non-root isolation, bounded resources/storage/output, no external fixture network or credentials, and pinned image/Engine provenance. |
| 3. Supervision and stopping | Separate startup/execution deadlines, bounded stop/escalation, ordinary and nested interruption handling, independent lifetime guard, fenced cleanup and capacity retention until verified retirement. |
| 4. Persistent reporting | Short reservation/history transactions, exclusive fenced external actuation, duplicate/stale protection, authoritative capture state and sealed artifact provenance, including pinned assessment allowances. |
| 5. Combined verification and handoff | Source-bound developer evidence, preserved original reviews, independent before/after regressions and reassessments, and human acceptance of this bounded result. |

Acceptance retains these limits:

- One predefined fixture Run at a time in the tested local Linux Docker environment. All five actual Registry Agents remain disabled and unqualified. No provider/model, forge, arbitrary command/image, remote/multiple Worker or background scheduler capability is enabled.
- Startup and execution defaults are 100 seconds each, with 5 seconds graceful stopping and 10 seconds forced cleanup/verification. Resource defaults remain 1 CPU, 256 MiB RAM/no swap, 32 processes/threads, 64 KiB input/result each, 256 KiB combined capture and 32 MiB writable scratch. Effective supported values are configured, validated and pinned per Run; later edits apply to future Runs.
- Status is read-only after supervisor loss. Authorized stop may take fenced cleanup control of the existing attempt; it cannot relaunch or resume it. Unknown effects or unverified cleanup keep capacity held. Automatic retries remain zero; broader recovery and human controls remain deferred.
- Capture errors or incomplete writers cannot establish valid successful output. Existing artifacts retain their pinned assessment allowances after configuration changes. Stale or untrusted reports cannot advance Coordination.
- Synthetic independent assessment and explicit Task acceptance demonstrate the application flow. The Request stays open and the Initiative stays unaccepted; these demonstrations do not establish independent acceptance of other work.
- Native Windows Worker execution is explicitly unavailable. Windows interruption evidence retains its exercised console/context limits, and Linux/WSL does not qualify production deployment, hostile interference, power-loss durability or disaster recovery.

The original submission/review, `repair-i4-r1-r3/final-01`, `repair-i4-r2-nested-signal/final-01`, and separate independent reassessments remain preserved under ignored `submissions/increment-4/` (now relocated intact through the [evidence archive](evidence-archive.md)). The final independent report is `submissions/increment-4/independent-reassessment-i4-r2-20261102-01/reassessment.md`. This acceptance identifies the exact repaired snapshot; documentation finalization does not rewrite historical evidence or claim that updated documentation retains its original hashes.

The [execution contracts](execution-contracts.md), [Coordination contracts](coordination-contracts.md), and [application guide](../README.md#supervised-fixture-execution-increment-4) own the maintained behavior and operating instructions. The completed implementation brief is retired from active documentation; its exact text remains in the reviewed source archives.

## Repository repairs after Increment 4

**Accepted by the human owner.** Acceptance covers the independently reassessed 143-file `submissions/repair-fr02-r1-fr06/final-01` snapshot with archive SHA-256:

```text
b36f8afa6eb0bc212d2ce87e37727b8daed25f8210443a4daa86c2e0eed72464
```

Its manifest SHA-256 is `9b39407591171d71b9e933fa0755d95db389586f9863ed88c37ef8ccaad04ef4`; declared deletions are empty. The [acceptance record](reviews/2026-11-02-repairs-acceptance.md) connects this snapshot to the original findings, separate reassessments and retained evidence. This is a repair of the accepted foundation and fixture scope, not a new increment or broader execution qualification.

| Finding | Accepted repair |
| --- | --- |
| FR-01 | Successful execution requires authoritative terminal-zero completion, valid complete capture and verified cleanup; attachment loss or cleanup cannot manufacture success. |
| FR-02 and FR-02-R1 | Bootstrap retains effect-aware partial progress and receipts, with truthful recorded/unavailable child audit metadata and aggregate status. |
| FR-03 | Foundation signal callbacks record lock-free stop intent; synchronized shutdown occurs in normal control flow. |
| FR-04 | Invalid API configuration stays inside safe validation with narrow source/setting attribution. |
| FR-05 | Source capture records combined checkout deletions explicitly, and verification checks both present files and declared absence. |
| FR-06 | A failed required standalone signal probe fails the repair verifier and propagates through wheel/platform verification while retaining child evidence. |

The [first repair reassessment](reviews/2026-11-02-reassessment/REVIEW.md) resolved FR-01, FR-03, FR-04 and FR-05 and identified residual FR-02-R1 and new FR-06. The [final reassessment](reviews/2026-11-02-fr02-r1-fr06-reassessment/REVIEW.md) resolved FR-02-R1 and FR-06 with no additional actionable finding. Independent reproduction passed all 14 commands on each platform: 338 Windows tests and 336 Linux/WSL tests plus one skip, locked checks, lint/formatting, builds, source and clean installed-wheel verification, Registry/TLS, Coordination and interruption checks. The same final regression assertions reproduced four baseline failures and 63 passing controls per platform, then passed all 67 source and 42 installed application cases. Real Linux source/installed Worker suites each passed 76 records, including seven retained Increment 4 repair cases.

Acceptance retains the existing fixture, authority, storage and platform limits. All five actual Registry Agents remain disabled and unqualified; no ordinary Agent, provider/model, forge or production Linux capability is qualified by these repairs. Automatic recovery/resumption, hostile interference, power-loss durability and disaster recovery remain outside the tested scope. The controlled FR-06 failures verify aggregation; actual signal observations passed.

Original reviews, handoffs, frozen source archives and raw evidence remain preserved. Completed repair briefs are retired from active documentation, with their exact text retained in the reviewed archives. Acceptance and documentation finalization do not rewrite historical results or claim that the updated documentation retains the accepted archive's original hashes. Increment 5's agreed high-level scope follows below.

## Increment 5: forge integration (Gitea first)

Implementation now exists under the maintained [forge contracts](forge-contracts.md). Developer verification and exact-source evidence are retained in the [evidence archive](evidence-archive.md). The [final repair reassessment](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md) closes the last P2 replay finding with regression, source/installed and both platform checks. Implementation and technical verification are complete; designated acceptance remains pending. Earlier agreed planning below retains its scope.

Start with a minimum bridge between one configured Gitea repository and the accepted local Coordination flow. A human explicitly links one existing local Task to one existing Gitea Task issue. A manually triggered synchronization observes that linked issue and publishes a narrow Coordinator-owned status/evidence comment. Repeating synchronization or restarting preserves the same durable mapping without duplicate work or external updates. This high-level scope, connection/authority defaults, field ownership, linking/conflict policy, cooperative managed-comment editing with its accepted race, logical operation/persistence contracts, synchronization defaults/recovery and demonstration are agreed. The [maintained forge contracts](forge-contracts.md) fixes the concrete contracts and required evidence for implementation.

Keep the Coordinator authoritative for workflow state, permissions and acceptance. Gitea is the human-facing work surface; a label or issue closure alone cannot authorize allocation, execution or acceptance. Reuse existing local run/status/stop operations under their own grants. Linking or synchronization does not automatically start a Run or enable an Agent. The existing local Task supplies its recorded work contract and context; this slice does not create a local Task from issue content.

| Task | High-level result |
| --- | --- |
| 1. Define the minimum forge boundary | A small forge-neutral adapter contract with explicit capabilities, stable external references, normalized observations/publication outcomes, the agreed field ownership and current authority. Implement Gitea first for the link between one existing local Task and one existing Task issue. |
| 2. Configure one project connection | Explicit repository/project binding and a least-privilege Coordination transport account, using protected local credential references. Agent/Profile definitions remain forge-independent; individual Agent forge accounts are deferred. |
| 3. Link and observe existing work | An explicit human action establishes the durable Task/issue mapping. A manually triggered synchronization validates the linked issue and records its observed revision. Missing or conflicting input stays blocked; repeat/restart preserves the same mapping without creating Tasks. |
| 4. Publish controlled progress | Maintain the agreed Coordinator-authored status/evidence comment from recorded local facts. Retain an outbound operation identity and reconcile uncertain delivery before retry; preserve human-owned content and refuse unauthorized progression. |
| 5. Verify the bridge | Verify the shared adapter contract and Gitea implementation, including explicit linking, observation, authorized publication, human-content preservation, repeat/restart without duplicate work or updates, and lost-acknowledgement handling against isolated test data. Include installed-package checks and retained accepted regressions. |

### Forge adapter boundary

Follow the existing [D-07](decisions.md#d-07-forge-integration-and-initial-platform) separation: shared synchronization owns mapping, field ownership, duplicate protection and reconciliation under Coordinator authority. An in-process provider adapter translates issue/comment operations, authentication mechanics, native references and revision observations, pagination and API responses. Provider-specific payloads do not become Coordinator work contracts or workflow decisions.

Keep the initial contract limited to reading the linked external issue, locating/reading its managed comment, and creating/updating that comment. Use stable external references scoped by the forge connection/instance and external project/repository; titles, URLs and issue numbers alone are insufficient identity. Adapters declare their capabilities and report conflicts, unavailable access, refusal, unsupported behavior and uncertain effects truthfully. The shared layer must not infer a successful publication or weaken ownership rules when a provider cannot establish the required guarantees.

Implement and verify Gitea first. Future GitLab or other adapters use the same boundary and applicable contract checks, with their own connection bindings and qualification. The Agent Registry and authoritative local work remain independent of the forge. Moving an existing linked Project to another forge additionally requires explicit mapping/history and pending-publication migration; it is not a provider-setting change and remains outside this increment.

### Runtime independence

Forge Adapters and Runner Adapters are separate extension points. The requested execution paths remain Codex CLI, Claude Code CLI and an Ollama-based coding harness under [F-02 through F-09](requirements.md#functional-requirements) and [D-08](decisions.md#d-08-initial-profiles). Other execution integrations can use the same Runner Adapter boundary after their contracts and capabilities are defined and verified. Profiles configure runtime, transport, provider and model separately; each Run pins its resolved configuration.

The forge bridge publishes normalized local Task/Run facts independently of which qualified Runner Adapter produced the result. Ollama-based implementation work requires a coding-tool harness providing repository access, edits, command execution and evidence under F-05. The delivered Worker currently runs only the fixed fixture; actual CLI Runner Adapter integration and qualification begin with one primary path in Increment 6, followed by the remaining integrations. Increment 5 does not enable ordinary Agent execution.

### Connection authority and configuration

| Area | Initial approach |
| --- | --- |
| Human authority | Use the existing authenticated human identity, with explicit Project permissions for configuring the connection, linking, synchronizing and approving comment repairs. Registry administration or forge access alone grants no workflow authority. |
| Forge access | Use one dedicated Coordination account to read the selected issue and maintain its managed comment. Möbiræon enforces the agreed publication boundaries even when native forge permissions are broader. |
| Connection configuration | Keep provider, instance, repository identity, account binding and credential reference in Project integration configuration, separate from reusable Agent Profiles. |
| Credentials | Keep credential values in protected storage; configuration contains references. |
| Availability | Check current connection access when operating. Forge unavailability blocks affected publication while local workflow remains usable. |

Credential rotation preserves the connection's identity and existing mappings. Changing the provider or repository requires explicit handling of those mappings; a settings edit cannot silently retarget an existing link. The [maintained forge contracts](forge-contracts.md) defines configuration fields, protected token import and current-access checks.

### Field ownership and publication

| Content | Owner | Synchronization behavior |
| --- | --- | --- |
| Issue title and description | Human | Preserve human edits. The recorded local Task contract continues to govern work. |
| Discussion comments | Their authors | Preserve discussion. Comments are not workflow commands in this increment. |
| Labels, milestones and issue assignees | Human | Preserve them. An issue assignee does not establish an Agent Assignment. |
| Issue open/closed state | Human | Observe changes. Local cancellation, acceptance or resumption still requires an authorized Coordination action. |
| Local Task/Run state and evidence records | Coordinator, under existing authority rules | Publish recorded facts without inferring workflow decisions from issue edits. Acceptance remains subject to the existing designated authority and assessment gates. |
| Published status/evidence comment | Coordinator | Maintain one clearly identified Coordinator-authored comment under the cooperative editing rule below. |

The managed comment contains the local Task reference, current workflow state, latest relevant result and evidence links. Update it when those published facts change; unchanged synchronization does not create another comment or duplicate an update. This is a projection of local records, not a second authoritative workflow store.

Use cooperative editing for the managed comment. Before each update, read it and compare its identity, author and content with the recorded expected observation. A detected external edit or deletion is a publication conflict requiring explicit resolution; hold publication rather than overwriting the observed edit or recreating the comment. Ordinary human discussion uses separate comments. Before manually editing the managed comment, humans must ensure synchronization is idle and no publication remains unresolved.

Gitea's standard API cannot atomically bind an update to the Coordinator's preceding read. A human edit arriving between that read and the server's update-time load can still be overwritten. This remaining race is explicitly accepted for Increment 5; atomic protection is not a completion claim. The checks above and explicit resolution of detected conflicts remain required. The high-level resolution rules below preserve the existing Task-control authority; the [maintained forge contracts](forge-contracts.md) defines the exact checks and operation contracts.

### Linking and synchronization conflicts

An authorized human selects the exact existing local Task and external issue through the configured Project connection. The Coordinator validates their identities, access and existing mappings, then records a durable one-to-one association. Repeating the same pairing reuses it. Linking only establishes the relationship; the next manual synchronization publishes the managed comment, and local workflow progression continues through its existing authorized operations.

| Situation | Handling |
| --- | --- |
| Either endpoint is linked differently | Retain the existing mapping and require explicit resolution. Do not automatically rebind or merge work. |
| External edit of the managed comment is detected | Hold affected publication. An authorized human may approve refreshing it from current local facts under the cooperative editing rule. |
| Deletion of the managed comment is established | Hold affected publication. An authorized human may approve one replacement, preserving the mapping and publication history. |
| Issue or access is unavailable | Preserve the link and report the problem. Ambiguous absence does not establish deletion. |
| Information became stale | Read again and recompute the intended update before publishing. |
| A write may have succeeded before timing out | Establish its outcome before another write. Insufficient evidence leaves publication unresolved; repeat/restart must not duplicate the comment or update. |

Ordinary edits to human-owned fields remain observations. Publication problems hold the affected synchronization; Task and Run control continue through existing authorized operations. These rules apply through the shared forge boundary, including future providers.

### Operation and persistence contracts

| Operation | Responsibility |
| --- | --- |
| `forge.connection.configure` | Create or revise the Project's versioned forge binding and protected credential reference. |
| `forge.connection.read` | Inspect the connection configuration and its revision. |
| `forge.link` | Establish the exact existing Task/issue relationship. |
| `forge.status` | Inspect the mapping, last confirmed publication and any conflict or unresolved delivery. |
| `forge.sync` | Perform one bounded synchronization cycle. Report published, unchanged, blocked or unresolved facts truthfully. |
| `forge.resolve` | Explicitly authorize refreshing an externally edited comment or replacing a confirmed deletion under the existing link. |

These operation names, Project-scoped per-operation permissions and initial local CLI surface are agreed. Reuse the existing request envelope and result conventions. Operations reading or publishing Task facts additionally require the existing Task-read authority. Forge permissions grant no Task progression or acceptance authority. Exact targets and input/result fields are defined in the [forge contracts](forge-contracts.md#ownership-and-authority).

Each operation checks current authority. Mutations use expected local versions and stable request identities: an exact repeat returns its recorded result after current authorization, while conflicting reuse fails. Task acceptance continues through its existing separate operation. `forge.resolve` cannot clear an uncertain write merely to permit another attempt; that outcome must be reconciled first.

Preserve the [architecture's ownership split](architecture.md#main-parts): the Registry owns versioned Project connection configuration, account bindings and credential references. Coordination owns Task/issue mappings, observations, publication intentions, receipts and history. The Forge Adapter owns provider-specific HTTP operations and delivery observations. Shared SQLite storage does not merge those responsibilities.

Retain the following logical records in the existing SQLite application:

- Registry-owned versioned connection bindings.
- Task/issue mappings, managed-comment references and relevant observations.
- Last confirmed published content and its local Task revision.
- Pending publication intentions, outcomes, replay receipts and attributable history.

Synchronization versions remain separate from Task workflow versions. Publication follows three steps: durably record the exact intended update locally, perform the forge operation outside the SQLite transaction, then record its confirmed outcome locally. No SQLite transaction stays open across the remote request.

An interruption between these steps leaves an unresolved publication to reconcile before another write. Only one active or unresolved publication is allowed per link, preventing concurrent synchronization from creating duplicate comments. Retain the intention and history across restart; remote and local outcomes must remain truthful when either acknowledgement is missing.

### Synchronization limits and recovery

| Limit | Initial behavior |
| --- | --- |
| Scope | One cycle handles the linked Task/issue pair. |
| Publication | At most one managed-comment write attempt per cycle. |
| Concurrency | One active cycle per link; concurrent requests report its existing state. |
| Timing | Configurable overall deadline and individual request timeouts. |
| Reading | Configurable request, pagination and response-size bounds. Reconciliation consumes the same budget. |
| Output | A bounded status summary with evidence references. |
| Retries | No automatic write retries or background continuation. |

Use these configurable defaults:

| Budget | Default |
| --- | --- |
| Whole synchronization cycle | 100 seconds |
| Individual request | 10 seconds, capped by remaining cycle time |
| Total HTTP requests | 20 |
| Comment-list pages | 5 |
| Response size / total data read | 1 MiB / 5 MiB |
| Managed comment size | 16 KiB UTF-8 |

Connection checks, reconciliation and rereads share these budgets. Reserve time within the cycle for recording its outcome. An incomplete search cannot establish that a comment is absent. Supported ranges, complete-request deadlines, finalization reserve and practical timing limits are defined in the [forge limits and token contracts](forge-contracts.md#configuration-and-protected-tokens). A cycle may inspect and reconcile an existing unresolved intention; it cannot create another publication while the earlier one remains unresolved.

- Before a write, report a known unattempted outcome when that fact can be established. A later manual cycle may try again.
- After a write may have started, timeout, interruption or lost acknowledgement leaves the publication unresolved. Reconcile its outcome before another write.
- Restart retains mappings, intentions and history and publishes nothing by itself. The next manual cycle inspects and reconciles unfinished work under current authority.
- When reading reaches a limit, incomplete observations cannot prove that a comment is missing. Stop affected publication and report what remains unknown.
- Refresh/replacement approval applies to the observed conflict. Recheck current authority and circumstances before acting; changed circumstances require fresh resolution.

An unresolved publication does not expire because time passed or its process ended. Publication holds affect synchronization without automatically changing Task or Run state.

### Demonstration and completion evidence

Use one existing local fixture Task and one prepared Gitea Task issue under the configured Project connection:

1. Link the existing pair and publish its status comment.
2. Advance the Task using the accepted fixture flow, then update that same comment from the new recorded facts.
3. Demonstrate repeat/restart without duplicates, preservation of human-owned content, and recovery from lost acknowledgement or a detected edit/deletion of the managed comment under the cooperative editing rule. Record the accepted concurrent-edit limitation rather than claiming atomic protection.

The expected result is a durable link and controlled status/evidence publication with retained history. Fixture progression does not enable real Agent execution or establish independent acceptance of other work. The [verification guide](verification.md) defines isolated test data, actual-provider qualification, checks and source-bound evidence.

### Implementation and review record

The one-off developer briefs are retired from active documentation and preserved in the [evidence archive](evidence-archive.md). Maintained [forge contracts](forge-contracts.md), the [application guide](../README.md#manual-forge-bridge-increment-5) and [verification guide](verification.md) own the implemented interfaces and operating boundaries.

The final-11 qualification passed its recorded platform, runtime, provider and Worker checks. The subsequent [full repository review](reviews/2026-11-04-increment-5-full/REVIEW.md) reproduced one P2 concurrent configuration-replay classification defect. The [final repair reassessment](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md) closes it against a separately frozen repaired source, with 18 new controls, both complete platform suites and clean installed-wheel checks. No material finding remains within the agreed Increment 5 scope. Earlier live qualification retains its original archive attribution; no new human acceptance is recorded.

## Deferred Coordination capabilities

These behaviors remain agreed product direction, but are **not Increment 3 completion requirements**. Select bounded later increments as the next useful capability becomes necessary. The remaining roadmap numbers 5–7 are retained; the placement of additional Coordination increments will be selected during later planning.

| Later capability | Deferred behavior and governing reference |
| --- | --- |
| Multi-Task delivery | Dependencies, accepted prerequisites, Decision waits, automated review/rework and changed-context reassessment under the [workflow](workflow.md#intake-and-task-readiness). |
| Scheduling across work | Work-class preferences, permitted alternatives, priority with stable equal-priority ordering, capacity and cumulative-limit scheduling under [Assignment and selection](workflow.md#agent-assignment-and-selection). |
| Human controls and scope changes | Pause/resume/cancel/reprioritize/takeover and baseline-change effects under [human controls](workflow.md#human-controls-and-scope-changes). |
| Advanced recovery | Retries, reassignment, ownership expiry/supersession, uncertain-effect continuation and cleanup/containment before capacity reuse under [waiting and recovery](workflow.md#waiting-and-recovery). |
| Overall outcome and closure | Initiative outcome acceptance and Request closure independently of Run/Task completion under [Initiative acceptance](workflow.md#initiative-outcome-acceptance) and [Request closure](workflow.md#request-closure-and-follow-up). |
| Live integration | Forge synchronization, ordinary Agent execution, primary qualification and end-to-end delivery beyond the accepted supervised fixture. |

Later increments must implement and verify the safeguards their capabilities rely on before use. Extending the accepted fixture to ordinary Agent execution must retain applicable stopping, ownership and cleanup controls. Deferral does not weaken authority, independence, isolation or qualification requirements. Exact transitions, grants, schemas, commands and operating values are decided for the capability being implemented.

## Remaining specifications

The accepted foundation, Registry, local simulated workflow and supervised fixture contracts are implemented within their recorded scopes. The rows below cover broader capabilities; they do not reopen completed Increments 1–4. Complete each applicable contract before implementing its dependent capability. Independent work can proceed when its own inputs are sufficient.

| Area | Unfinished specification | Governing baseline |
| --- | --- | --- |
| Lifecycles and assignments | Transitions beyond the accepted one-Task simulated/fixture flow: multi-Task/dependency and Decision progression, Initiative/Request outcomes, rework, reassignment, human controls and recovery. Preserve Task identity and exact evidence when extending the current contracts. | D-03, D-04; F-12, F-19, F-20, F-22 |
| Authority and independence | Production service/Agent identities and broader delegated workflow authority, baseline approval, review eligibility, human intervention and Orchestrator-only escalation. Extend current local scoped grants and exact-evidence gates without inferring execution authority from Registry administration. | D-08, D-10; S-03, F-18, F-20, F-25 |
| Coordinator state and recovery | Beyond the bounded [Increment 4 contracts](execution-contracts.md), specify general ownership expiry/supersession, reassignment and deliberate recovery. Preserve durable records, operation identities, transactional history, uncertainty fences and safe capacity reuse. | D-04, D-11; F-22, F-23; N-02, N-05 |
| Coordination access to the Registry | Least-privilege service access for live dispatch, exact published configuration/current controls and qualification/enablement integration. Preserve the accepted Registry interfaces and local scoped-read behavior; isolated fixture resolution does not qualify ordinary execution. | D-05, D-11; F-07 through F-09, F-15; N-04, N-05 |
| Runner and configuration contracts | Extend the fixed fixture contract to actual Agent runtimes: inputs/machine-readable outcomes, Artifact references, cancellation/errors, compatibility validation, explicit overrides and requested/effective configuration under the approved fields. Bind immutable per-Run settings and context. | D-05, D-08; F-03 through F-09 |
| Enforcement boundary | Beyond the no-network/no-credential fixture, specify threat assumptions and trusted enforcement for Agent processes, workspaces, network, resources, repository operations, Coordinator actions and secrets, including subprocess activity and revoked access. Retain demonstrable cleanup/containment criteria. | D-06, D-10; N-02 through N-04 |
| Forge contract | Supported operations/events, capability declarations, per-field authority, stable mappings, actor authentication, external edit/close/reopen behavior, duplicate handling, reconciliation, and conflict treatment. Keep project forge bindings separate from reusable Agent/Profile definitions. | D-07; F-16, F-18, F-22, F-24 |
| Artifacts, context, and integration | Beyond supplied local text artifacts: durable external publication/resolution, context assembly and freshness, dependency evidence, shared-target coordination, exact combined-result validation and retention/deletion. Preserve current immutable references and acceptance applicability checks. | D-05, D-11; F-13 through F-15, F-21, F-27; N-05 |

## Gates before qualification or live pilot execution

Apply each gate to the relevant activity. Qualification and live execution require their configured authority, operating values, and verified controls; design approval alone does not establish readiness to run.

| Area | What remains to be specified | Completion evidence |
| --- | --- | --- |
| End-to-end scenario and release coverage | Select a prepared existing repository, baseline revision, and bounded feature. Specify its outcome criteria, inclusions/exclusions, feature and system checks, permitted operations, and outcome acceptor. Declare release coverage and deferred execution integrations against F-02. | Approved, versioned validation contract traceable to D-12 and S-05; no broader support claim than the qualified scope. |
| Primary execution path | Record the concrete runtime/harness, provider/account reference, model, reasoning/options, versions, tools, and independently configured review for the primary qualification path. Identify included capability scope and deferred integrations. | Versioned capability definitions, authorized qualification configuration, and passing support-matrix checks for the declared scope. Applicable authority precedes privileged or paid checks; ordinary Runs require qualification. |
| Operating profile | Numeric budgets, allocation estimates, concurrency, deadlines, retry/failure thresholds, ownership conditions, cleanup criteria, retention/deletion, recovery objectives, and treatment of measured, estimated, or unavailable usage/cost. | Approved values and executed checks demonstrating enforcement, cleanup, and recovery for the tested environment. |
| Deployment and recovery | API hosting, deployment packaging and service identities under D-11; recorded application, host, container, forge, runtime, and enforcement versions; migrations, startup/shutdown, persistence, backups, restoration, and operator controls. | A reproducible environment and tested restoration of coordination state together with Artifacts and referenced Registry revisions; linked observations for blocked, uncertain, and failed work. |

## Verification and evidence

The [acceptance scenarios](requirements.md#acceptance-scenarios) and requirement-specific checks define observable completion. Verification includes:

- **Registry and bootstrap:** protected first-owner setup, persistent access initialization, consistent API/CLI authorization including protected reads, revocation, last-administrator protection, audited recovery that keeps bootstrap closed, validation/publication, immutable references, exact Agent/Profile bindings, and separate qualification and enablement. Optional imports cannot bypass publication controls.
- **Registry controls and resolution:** explicit selected revisions and persistent current enablement, historical-value bypass prevention, reviewed ceiling-reduction overrides, rejection of unsupported or conflicting changes, and the defined response when required qualification/authority evidence is unavailable. Registry checks do not implement Coordination dispatch or qualification.
- **Unavailable enablement:** unauthorized refusal, authorized unavailable/no-mutation behavior through API and CLI, preserved disabled state after restart, authorized disablement, no forced/manual/automatic enablement, and isolation of positive qualification doubles from production and bootstrap evidence.
- **Registry operations and persistence:** validated targets/inputs and safe results, stale-edit/review protection, mutation/audit commit integrity, separate unsuccessful-attempt audit including unavailable storage, referenced-history preservation, per-operation preparation progress, and reconciliation before replay after uncertain effects.
- **Forge adapter:** qualify Gitea against the versioned forge-neutral contract, declared capabilities, traceable mappings, actor authentication, and authority boundary. Project migration and cross-forge synchronization remain separately scoped.
- **Runner capabilities:** establish supported noninteractive behavior, options, tool boundaries, output contracts, cancellation, and cleanup for the declared execution combinations. One qualified path does not establish support for every requested runtime family.
- **Controlled delivery:** exercise intake and clarification, specification and baseline approval, bounded implementation, independent review, authorized integration, fresh validation of the exact combined revision, and outcome acceptance under D-12.
- **Recovery and continuity:** exercise waiting and continuation, interruption recovery, duplicate reconciliation, stale-owner rejection, configuration/context revision changes, and coherent restoration of Registry revisions, coordination records, and retained Artifacts.
- **Operating controls:** verify configured budgets and concurrency, isolation, secret protection, status and required human action, stop controls, and integration credentials for the selected environment.

Each check records the tested software, configuration and policy revisions, environment, method, observed result, and limitations. Distinguish performed checks from planned checks and supplied evidence. A passing demonstration establishes only its evidenced scope; missing inputs or inconsistent references block affected work rather than establishing success.

Identify the exact combined source assessed. A commit may identify it; for uncommitted work, retain the base revision and a source snapshot or patch covering relevant tracked and untracked files, with a manifest or hashes to verify contents. Independent review and verification assess that same source. Later changes require affected checks and reassessment. Keep local execution evidence with its submission or review record rather than adding standing status documents to the design baseline; local `submissions/` output is ignored by Git.

## Maintaining the plan

Record completion against the governing specification and verification evidence. Changes to the design baseline follow its designated decision authority and update the [decision register](decisions.md) and relevant owning documents. Implementation and qualification Tasks retain their applicable permissions, limits, and acceptance requirements.
