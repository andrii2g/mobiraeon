# Increment 2 implementation brief: Agent Registry and bootstrap

Implement the six Tasks in the [implementation plan](implementation-plan.md#increment-2-agent-registry-and-bootstrap). Deliver an authenticated, persistent Registry through API and CLI, with reviewed immutable publications and repeatable preparation of the five initial Agents, all disabled. This brief assigns implementation; it does not establish verification, independent review, or designated acceptance.

## Governing baseline and boundaries

Read the [Registry design](agent-registry.md), [Agent configuration contract](requirements.md#agent-configuration-contract), [D-05](decisions.md#d-05-registry), [D-11](decisions.md#d-11-implementation-technology-and-topology), [Role catalog](roles/README.md), and [foundation guide](../README.md#application-foundation-increment-1). Those owners govern terminology, fields, authority, publication, and runtime intent. Apply their agreed rules together; identify contradictions rather than silently selecting a weaker rule.

Preserve the accepted Increment 1 foundation and unrelated working changes. Record the starting revision/status. Retain CPython 3.14.10, `src/mobiraeon`, uv/uv_build, SQLAlchemy Core, sqlite3, Alembic, pytest, and Ruff. Add tested FastAPI/Uvicorn versions, retain the complete `uv.lock` resolution, and let FastAPI select compatible Starlette. Domain contracts remain independent of storage types.

Do not implement Coordination workflows, scheduling, Assignments/Runs, qualification execution or records, Workers, Runner Adapters, model/provider calls, Gitea operations/accounts, project integration, deployment, production recovery qualification, or optional Git synchronization/import/export. Local temporary verification servers and synthetic credentials are verification facilities, not live integrations.

## Task 1: Define concrete contracts

Document and review concrete contracts before implementing dependent behavior. Routine table names, endpoint names, module layout, loaders, and examples may be developer proposals within this baseline. Do not silently invent owner account references, governing permissions, budgets, or execution preferences. Request missing consequential inputs while continuing independent work.

The current boundary accepts only empty inputs and exact revision targets, returns no business payload, and composes a fixed local caller. Extend these intentionally for:

- Stable identities, draft targets, exact publications, current controls, access targets, and creation against an intended identity/collection.
- Strict operation-specific inputs and safe typed read/business results, created/observed references, and mutable versions. Keep immutable publication IDs distinct from edit versions; never resolve exact references as latest content.
- Expected-version checks inside protected updates, review/publication, and control changes; uniqueness for creation. Stale edits and incompatible references require reconciliation, not automatic merging.
- Trusted immutable context per invocation/request, established by authenticated adapters. Request fields cannot supply identity or authority, and shared services cannot retain another request's caller.
- The existing six outcomes, precise reasons, and consistent HTTP/CLI mappings. Preserve success, invalid input, refusal, unavailable capability, known failure, and uncertain effects. Safe results exclude raw credentials and verification material.
- Declared override fields, units, types, and bounds. Only ceiling reductions are permitted; other Profile settings require reviewed Profile revisions. Define zero/unspecified semantics per field and reject unknown, coercive, conflicting, or unsupported values.

Specify token format/verification/lifetimes, action/target grants, installation-owner proof, protected delivery/durability, recovery, last-administrator protection, certificate/trust configuration, readiness/drain limits, retry/reconciliation behavior, and audit-outage reporting. Make security and effect boundaries explicit rather than relying on framework defaults. These concrete contracts require applicable review; they do not reopen the agreed architecture.

## Task 2: Implement owned persistence

Use the existing application/database with separate logical ownership. Represent stable identities, versioned drafts, exact-candidate reviews, immutable publications/dependencies, versioned current controls, access records, and audit. Enforce uniqueness, expected versions, and valid published references. Incomplete drafts may be saved; publication requires complete consistent definitions.

Add forward migrations to the existing linear chain. Preserve explicit initialize/upgrade versus ordinary existing-store validation, transaction ownership, foreign keys, bounded contention, and truthful effect boundaries. Each logical mutation and required audit record commit together; recheck applicable caller authority (current credential validity/grants or protected local ownership proof), versions, review applicability, and references inside that boundary, including after lock acquisition. No transaction spans human review or external/file delivery work.

If required audit cannot commit, the mutation cannot succeed. Verified rollback is known failure; otherwise retain uncertainty. Refused/failed attempts need separate audit handling, with honest unavailable-storage reporting. Preparation commits per operation: earlier completed publications survive a later failure. Reconcile exact revisions, control versions, and correlated audit records before replay; current state alone may not establish an earlier outcome.

Provide no hard deletion of published revisions, required dependencies, review provenance, or audit history in this increment. Authorized draft discard preserves required history. Raw credential files have a separate lifecycle; deliberate cleanup follows established registration/revocation status while nonsecret identifiers and revocation history remain.

## Task 3: Implement controlled Registry operations

Implement authoring, validation, exact-candidate review/publication, protected retrieval/history, explicit current selection, enable/disable, and declared ceiling-reduction overrides through the shared operation boundary. Keep catalog and access administration permissions distinct. Review records bind exact candidate content/dependencies; edits require renewed review. Published content cannot be overwritten or silently cascade into dependent Agent bindings. Restoring earlier settings creates a new reviewed revision.

Publication selects or enables nothing automatically. Current disablement blocks selection for ordinary work, while administrative revision selection remains available. The production qualification-check boundary reports unavailable: authorized enable requests return unavailable without changing enablement; unauthorized requests are refused. Authorized disablement remains usable independently and commits with its required audit. No forced/pending/automatic enablement, manual qualification assertion, or production positive test double is allowed. Stored enabled flags cannot prove eligibility.

Example contracts must cover create/edit/review/publish/retrieve/select; a permitted lower ceiling; forbidden model/policy overrides; unavailable enablement; authorized disablement; stale edits; changed reviewed content; revoked access; required-audit failure; uncertain commit; and resumable preparation. Reads repeat under current authorization. Do not promise universal mutation replay or treat invocation IDs as retry guarantees.

## Task 4: Provide secure API and CLI administration

Implement one stable human administrator identity with individually revocable personal tokens, verification hashes/nonsecret metadata in access-owned records, and current expiry/revocation/grant checks. Provisioning establishes a trusted OS owner and protected private state. Setup/recovery verify the actual principal and resource protections, using appropriate Linux permissions or Windows ACLs. A username argument, loopback connection, or foundation OS-operator grant is insufficient.

First-owner setup and recovery are protected local CLI operations requiring no HTTP server or Agent. Initialization survives catalog changes/restarts; recovery preserves initialized status/history. Refuse changes knowingly removing the last usable administrative access without an established replacement/recovery path.

For credential issuance, generate a credential/nonsecret identifier, securely create and durably save a new owner-protected destination, then register its verifier, access changes, and required audit in a database transaction. First-owner setup also closes bootstrap there. Delivery failure cannot activate the credential. After uncertain registration, retain the protected file and reconcile rather than blindly issuing another credential or repeating setup. Rotation saves the replacement before registration/revocation. Do not claim filesystem/database atomicity. Raw credentials never enter command arguments, ordinary configuration values, exports, results, or logs.

Expose authenticated versioned FastAPI/OpenAPI administration through one Uvicorn process inside the existing application, initially loopback-bound. Use direct TLS with operator-provisioned certificate/key files and explicit client CA/endpoint verification. Broader exposure and trust changes require their applicable explicit configuration; no verification-disabled fallback or automatic global trust changes.

Extend the single strict configuration resolver and pass resolved settings programmatically. API and local CLI use the same operations, credential checks, and grants; local administration needs no HTTP server. Keep synchronous database operations connection/transaction-owned within one execution context. Distinguish listener readiness, administrative availability, and execution eligibility. Before owner setup, protected administration stays locked; unavailable qualification does not block catalog administration. Report listener readiness only after successful initialization/binding. Use one lifecycle/signal owner, withdraw readiness, stop admission, drain within the configured deadline, and close once before terminal success. HTTP cancellation/disconnection does not establish database rollback.

## Task 5: Prepare the reviewed five-Agent catalog

Prepare `orchestrator-01`, `planner-01`, `developer-01`, `reviewer-01`, and `verifier-01`, each disabled and without administrative grants. Preserve strong Orchestrator/Planner reasoning, medium routine Developer reasoning, independently configured review, and dedicated behavioral/combined-result verification intent.

Use one reviewed input set with actual candidate runtime/transport/provider/model settings for one primary execution path; Role-specific reasoning/options; versioned nonsecret connections/credential references; exact instruction/capability/tool/authority/context/output and applicable fallback references; applicable duration/retry/token/cost/concurrency ceilings; and captured instruction content/source versions. Absence of an applicable fallback means no substitution. Registry publication establishes no live connectivity or qualification.

These actual execution/account/policy/budget values are not yet selected. Identify them early, propose a complete nonsecret candidate set, and obtain the applicable owner/delegated decisions before publication. Do not manufacture values or publish placeholders. Missing required inputs keep affected definitions in draft; fixtures prove mechanics but cannot complete Task 5. Continue independent implementation/checks while inputs are pending and report the exact publication blocker honestly.

Prepare through ordinary operations. Restart preserves exact publications, dependencies, provenance, bindings, and disabled state. Repeat/resume creates no duplicates or silent overwrites; conflicting inputs require explicit reconciliation. Installed usage must consume explicit packaged or supplied inputs rather than implicitly reading the checkout.

## Task 6: Verify and hand off the combined result

Retain meaningful foundation regressions, including R1–R5 effect/authorization/cleanup/path/lock boundaries. Add contract-driven checks using real temporary disk databases and synthetic, runtime-generated credentials. Required coverage includes:

- Forward upgrades, restart, constraints, contention/concurrency, stale edits/reviews, mutation/audit failures, uncertain effects, and safe reconciliation.
- Protected setup/delivery/recovery, revocation/expiry/grants, last-administrator protection, failed/uncertain registration, and OS resource protections on every platform claimed supported.
- API/CLI parity, protected reads, TLS trust/endpoint failures, concurrent caller isolation, redaction, configuration precedence, listener/admin readiness, graceful shutdown and cancellation uncertainty.
- Exact immutable retrieval, overrides, current selection, unavailable enablement/no mutation, usable disablement, disabled-state restart, and repeat/resume of the reviewed five-Agent inputs when available.

Run and retain results for:

```text
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
uv run --locked python tools/verify_wheel.py
```

Adapt installed-wheel/native interruption verification to prove both entry paths, packaged migrations, explicit bootstrap inputs, actual capabilities, TLS/lifecycle behavior, and operation outside the checkout without `PYTHONPATH`. Preserve percent-containing installation coverage and environment-qualified interruption observations. Do not weaken checks merely to pass or claim an unsupported platform from another environment's results.

Existing capture/foundation tools write to Increment 1 and wheel checks expect its unavailable capabilities. Adapt/parameterize them for ignored `submissions/increment-2/`, preserving all Increment 1 archives/evidence. Capture the exact combined source: base revision plus relevant tracked/untracked files, archive, manifest/hashes, inputs/provenance, dependency/environment versions, commands, raw results, failures, and limitations. Exclude credential/TLS private material and generated evidence from source capture. Changes after capture require affected checks and recapture.

Deliver an increment-specific handoff identifying each Task's result, remaining blockers, check outcomes, and reproduction instructions. Independent review must assess that same source and reproduce material checks. Developer verification, independent review, and designated acceptance remain separate; do not self-certify independent acceptance. Task 5 is complete only with the real reviewed catalog, and Increment 2 is complete only when all required evidence and designated acceptance establish it.
