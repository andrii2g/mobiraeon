# Agent setup and Gitea integration

**[A] High-level Agent setup.** The [setup model](../pilot-and-agent-setup.md#registry-and-gitea-identities) defines stable forge-account bindings; the [workflow](../workflow.md#agent-onboarding) describes preparation. Registry organization and the first Agent catalog remain a [separate proposal](../agent-registry.md).

```mermaid
---
config:
  flowchart:
    wrappingWidth: 280
---
flowchart TB
    PROFILE["Role instructions<br/>and reusable Profile"] --> AGENT["Stable registered Agent<br/>with exact Profile binding"]
    AGENT --> PUBLISH["Reviewed and validated<br/>Registry publication"]
    PUBLISH --> ELIGIBLE["Coordinator checks configuration,<br/>qualified scope and project authority"]
    FORGE["Each Agent acting in Gitea has a stable account<br/>Project binding and approved permissions"] --> ELIGIBLE
    QUALIFIED["Qualified execution path"] --> ELIGIBLE
    ELIGIBLE --> RUN["Eligible authorized Assignment<br/>and bounded Run"]

    classDef agreed fill:#e8f3ee,stroke:#28644d,color:#12372a;
    classDef boundary fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class AGENT,PUBLISH,ELIGIBLE,RUN agreed;
    class PROFILE,FORGE,QUALIFIED boundary;
```

Registry publication retains configuration; Coordination retains operational state and per-Run records. The Coordination service uses a separate Gitea account. Forge identities and model-provider identities are distinct. Account access complements workflow permission and independence checks rather than replacing them.

Where a forge account is required, bind it through project integration configuration with secret references. Credential values remain in the authorized secret mechanism. New configuration revisions affect later validated selections and do not rewrite existing Runs.

This view shows preparation relationships rather than mandating a separate service, account for every Role or Run, or a particular provisioning mechanism. Continue with the [pilot setup](../pilot-and-agent-setup.md#demonstration-pilot). Return to the [diagram guide](README.md).
