# Agent setup and Gitea integration

**[P] High-level onboarding and forge-identity proposal.** Git-based Registry persistence is already established. The [setup discussion](../pilot-and-agent-setup.md#registry-and-gitea-identities) proposes account bindings; the [workflow](../workflow.md#proposed-agent-onboarding) describes preparation.

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
    FORGE["Applicable Agent-to-Gitea binding<br/>and project permissions"] --> ELIGIBLE
    QUALIFIED["Qualified execution path"] --> ELIGIBLE
    ELIGIBLE --> RUN["Eligible authorized Assignment<br/>and bounded Run"]

    classDef proposed fill:#fff3d6,stroke:#a66b12,color:#513807;
    classDef boundary fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class AGENT,PUBLISH,ELIGIBLE,RUN proposed;
    class PROFILE,FORGE,QUALIFIED boundary;
```

Registry publication retains configuration; Coordination retains operational state and per-Run records. Forge identities and model-provider identities are distinct. Account access complements workflow permission and independence checks rather than replacing them.

Where a forge account is required, bind it through project integration configuration with secret references. Credential values remain in the authorized secret mechanism. New configuration revisions affect later validated selections and do not rewrite existing Runs.

This view shows preparation relationships rather than mandating a separate service, account for every Role or Run, or a particular provisioning mechanism. Continue with the [pilot proposal](../pilot-and-agent-setup.md#demonstration-pilot). Return to the [diagram guide](README.md).
