# Initial Agent configuration

This is the approved initial test configuration delivered in [accepted Increment 2](implementation-plan.md#increment-2-agent-registry-and-bootstrap). The five Agents remain disabled and have no administrator grants. Publication authorizes no execution, provider calls, connectivity claim or qualification. The original proposal and verification evidence remain with the local Increment 2 submission.

## Shared settings

The explicit, nonsecret input is [bootstrap/initial-test.json](../bootstrap/initial-test.json). Preparation resolves its symbolic references to actual immutable publication IDs through normal create, validate, review and publish operations. Role/shared-rule content is captured from Git revision `bb3af7869b6d3d47c92fcd5ad1376e2c66801141` with source paths and SHA-256 hashes. Editing current documentation cannot silently change those publications.

Use Codex CLI **0.165.0-alpha.1.2**, OpenAI provider, **gpt-6.1-sol**, and noninteractive `codex exec` stdin/JSON transport. The intended execution host remains an isolated Linux container Worker. The accepted Worker currently executes only the fixed fixture; no live CLI Runner Adapter is implemented. No fallback is configured. JSON output, ephemeral sessions, ignore-user-config and explicit sandbox selection are declared. Policies forbid ambient plugins, MCP, hooks, delegation, bypass flags and unrelated authority. Future external isolation must enforce network and filesystem constraints; CLI options do not prove enforcement.

Exact Linux candidate: [official x86_64 musl release artifact](https://github.com/openai/codex/releases/download/rust-v0.165.0-alpha.1.2/codex-x86_64-unknown-linux-musl.tar.gz), SHA-256 `1146f2d5c66d1258d1fb7139bfe7852bdb07fab8ec5515941a6f4c4259508366`. Version/help observations are developer metadata checks, not Linux execution qualification. The locally observed Windows binary is separate evidence.

The [model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol) documents low, medium, high, xhigh and max effort. The [Codex model guide](https://learn.chatgpt.com/docs/models) distinguishes Ultra delegation from single-agent Max. Max is the approved actual initial Orchestrator/Planner setting; Ultra remains future requirements intent. No provider call verifies runtime acceptance or model availability.

Connection endpoint: `https://api.openai.com/v1`. Account reference **openai-primary-account-v1** and credential reference **openai-primary-credential-v1** are approved application-owned logical identifiers. They are not external OpenAI identifiers or existing credentials. External mapping, provisioning, resolution, connectivity and qualification are **unprovisioned/unverified** execution-readiness dependencies. They do not prevent this disabled catalog being complete and published. No secret manager or provider credentials are created. Later binding changes require explicit versioned revisions.

Shared context policy admits explicit reviewed task inputs only, with no secrets or ambient unrelated context. Output requires concise evidence, exact source references, observed outcomes and limitations. Authority policy grants no administration, execution, enablement, deployment, forge or real-account authority. Catalog grants are distinct from execution policies. The configured aggregate execution ceiling is one, requiring later scheduler enforcement.

## Five independent Profiles

| Agent | Effort | Seconds | Retries | Tokens | Cost micro-USD | Concurrency | Tool policy |
|---|---|---:|---:|---:|---:|---:|---|
| orchestrator-01 | max | 1200 | 0 | 30000 | 5000000 | 1 | Read/plan, read-only sandbox |
| planner-01 | max | 1200 | 0 | 30000 | 5000000 | 1 | Read/plan, read-only sandbox |
| developer-01 | medium | 1800 | 0 | 40000 | 5000000 | 1 | Authorized task workspace writes/checks |
| reviewer-01 | high | 1200 | 0 | 30000 | 3000000 | 1 | Disposable verification workspace writes/checks |
| verifier-01 | high | 1200 | 0 | 30000 | 3000000 | 1 | Dedicated behavioral verification in disposable workspace |

Reviewer and Verifier preserve the assessed source and may create temporary verification artifacts. Each has its own Role snapshot and Profile revision. Limits are configured ceilings, **runtime enforcement unverified**: seconds mean wall duration; retries are additional attempts (zero means none); tokens mean total input/output budget; micro-USD means millionths of one USD ($5/$3); concurrency is simultaneous executions per Agent. Token accounting, cost estimation, process termination, retry handling and aggregate concurrency enforcement require later measurable runtime contracts. No limit is claimed enforced by this Registry.

## Administration and reconfiguration

One protected, authorized human owner may author, review and publish through separate audited actions. Setup requires an explicit self-review-policy choice and explicit grants; Agents receive none. Deployment TLS endpoint/CA and installation principal remain deployment settings and do not block catalog preparation.

Increment 2 delivered publication of this initial test catalog and dependencies, exact current administrative selections, restart persistence, disabled state, and repeat/resume evidence without duplicate publication. Future reconfiguration uses normal edits and new reviewed publications. Updating this reference does not mutate existing published configurations.

Real credential binding, runtime qualification and execution readiness remain later work under their applicable contracts.
