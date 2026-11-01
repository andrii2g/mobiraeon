# Registry enablement before Coordination qualification

**[A] Disabled preparation and unavailable enablement.** This view applies the [enablement boundary](../agent-registry.md#enablement-before-coordination-qualification) to Increment 2. It describes logical outcomes without defining exact commands, reason codes, or qualification records.

```mermaid
---
config:
  flowchart:
    wrappingWidth: 270
---
flowchart TB
    REQUEST["Enable or disable operation<br/>Explicit Agent target and trusted caller"] --> AUTH{"Currently authorized?"}
    AUTH -->|No| REFUSE["Refuse the operation<br/>No unauthorized control change"]
    AUTH -->|Yes| CONTROL{"Requested control"}
    CONTROL -->|Enable| QUALIFY["Coordination qualification-check boundary<br/>Unavailable in Increment 2 production"]
    QUALIFY --> UNAVAILABLE["Return unavailable<br/>Current enablement remains unchanged"]
    CONTROL -->|Disable| DISABLE["Commit disabled control<br/>and required audit record"]

    classDef agreed fill:#e8f3ee,stroke:#28644d,color:#12372a;
    classDef boundary fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class AUTH,REFUSE,CONTROL,QUALIFY,UNAVAILABLE,DISABLE agreed;
    class REQUEST boundary;
```

Enablement remains a recognized operation. An authorized request returns an explicit unavailable outcome while qualification cannot be checked, with no change to current enablement. Authorized disablement remains available independently of qualification. Publishing and selecting disabled Agent revisions continue through their ordinary validation and authority checks.

Coordination owns the future qualification check. Increment 2 does not create qualification records or accept an administrator-supplied qualified assertion. No pending-enable state, forced-enable flag, or additional approval queue is introduced. All five initially prepared Agents remain disabled.

When qualification becomes available, an administrator must explicitly request enablement and pass fresh checks against the exact selected configuration; availability does not enable anything automatically. Selecting another configuration cannot carry qualification forward automatically.

A stored or recovered enabled flag does not prove present execution eligibility. Report administrative state separately from qualification availability and preserve history. Positive qualification test doubles remain isolated from production composition and bootstrap evidence.

Continue with [current controls and overrides](registry-controls.md), [first-Agent preparation](first-agent-preparation.md), or the [diagram guide](README.md).
