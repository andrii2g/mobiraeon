# First-Agent preparation

**[A] Inputs, disabled catalog, and preparation evidence.** This view shows the bounded Increment 2 result and its handoff to later onboarding without defining exact states or API commands. See the [bootstrap inputs and preparation evidence](../agent-registry.md#bootstrap-inputs-and-preparation-evidence) and the broader [first-Agent preparation](../agent-registry.md#first-agent-preparation).

```mermaid
---
config:
  flowchart:
    wrappingWidth: 270
---
flowchart TB
    ADMIN["Established human administrator<br/>Current review and publication grants"] --> INPUTS["Reviewed bootstrap candidate specification<br/>Actual Profile values, exact references and instruction versions"]
    INPUTS --> CREATE["Prepare the five named Agents disabled<br/>Bind Role-specific Profile revisions"]
    CREATE --> PUBLISH["Validate and review exact candidates<br/>Publish immutable Registry revisions"]
    PUBLISH --> EVIDENCE["Verify exact retrieval, restart and repeatability<br/>Check controlled failures and retain preparation evidence"]
    EVIDENCE --> PREPARED["Prepared catalog<br/>Five published, persistent Agents, all disabled"]
    PREPARED -.-> LATER["Later onboarding<br/>Project bindings, qualification and controlled enablement"]

    classDef agreed fill:#e8f3ee,stroke:#28644d,color:#12372a;
    classDef boundary fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class INPUTS,CREATE,PUBLISH,EVIDENCE,PREPARED agreed;
    class ADMIN,LATER boundary;
```

First-owner setup applies only while administrative access is uninitialized; catalog preparation uses established administration. The [administrator access view](registry-access.md) covers current permissions and owner-controlled recovery. No running Orchestrator or Agent Run is required. The focused [authoring and publication view](registry-publication.md) governs drafts and exact-content review; the same authorized human may perform these administrative actions where policy permits.

The [bootstrap candidate specification](../agent-registry.md#bootstrap-candidate-specification) contains runtime/transport/provider/model/reasoning/options, nonsecret connection definitions and credential references, applicable numeric limits, and identified instruction content/source versions for one primary path. The accepted [initial test configuration](../initial-agent-configuration.md) supplies complete values and internal logical references without requiring provisioned external credentials. Exact governing instruction, capability, policy, context, output, and applicable fallback references remain required. Preserve strong planning Profiles, medium routine implementation, independent review, and dedicated verification intent. Missing schema fields keep affected definitions in draft; configuration completeness does not establish execution readiness.

Evidence retains the five Agent/Profile revisions, dependencies, current disabled state, instruction provenance, and attributable review records. Restart preserves them; repeat or resumed preparation creates no duplicates or silent overwrites. Conflicts require explicit reconciliation. Missing references, invalid settings, unauthorized or stale changes, and failed publication produce truthful outcomes with no partial published result for the failed publication. Keep a concise generated preparation record alongside Increment 2 submission evidence, identifying application and input versions, performed checks, results, and limitations.

The prepared catalog completes Increment 2's bootstrap outcome. The [enablement boundary](registry-enablement.md) returns unavailable while Coordination qualification cannot be checked, leaving current enablement unchanged; authorized disablement remains available. Project integration, runtime qualification, successful enablement, and execution follow their applicable later gates. Authorized qualification checks cannot override disablement or revoked access.

The [implementation plan](../implementation-plan.md#increment-2-agent-registry-and-bootstrap) records Increment 2 acceptance and its verification limits. The [operation contracts](../registry-contracts.md) retain the current behavior. Original instructions, reviews and source-bound evidence remain preserved through the [evidence archive](../evidence-archive.md); qualification and execution follow later gates.

Continue with the agreed [Agent setup](agent-setup-and-gitea.md), [operations and persistence](registry-operations.md), or the [diagram guide](README.md).
