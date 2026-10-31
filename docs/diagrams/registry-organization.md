# Agent Registry organization

**[P] Repository organization proposal.** Amber nodes show the proposed catalog areas. Publication and Coordination retain the boundaries established by [D-05](../decisions.md#d-05-registry). See the [Registry discussion](../agent-registry.md) for the proposed first Agents.

```mermaid
---
config:
  flowchart:
    wrappingWidth: 250
---
flowchart TB
    INSTRUCTIONS["Shared and Role instructions"] --> PROFILES["Reusable Profiles<br/>with Role and instruction bindings"]
    SUPPORT["Policies and capability definitions"] --> PROFILES
    PROFILES --> AGENTS["Stable registered Agents<br/>with exact Profile bindings"]
    AGENTS --> PROJECTS["Project selection and policy references<br/>Agent-to-Gitea bindings"]
    PROFILES --> PUBLISH["Reviewed and validated<br/>exact Registry publication"]
    PROJECTS --> PUBLISH
    PUBLISH --> COORD["Coordination resolves Run configuration<br/>and checks qualification and authority"]

    classDef proposed fill:#fff3d6,stroke:#a66b12,color:#513807;
    classDef agreed fill:#e8f3ee,stroke:#28644d,color:#12372a;
    class INSTRUCTIONS,SUPPORT,PROFILES,AGENTS,PROJECTS proposed;
    class PUBLISH,COORD agreed;
```

The publication includes all referenced definitions and uses the validation contracts in the proposed `schemas/` area. Project bindings select reusable definitions; they do not grant permissions beyond governing authority.

Live work, qualification references, and immutable per-Run records belong to Coordination; substantial evidence belongs to Artifacts, and credential values to the secret-management mechanism. Continue with [Agent setup and Gitea](agent-setup-and-gitea.md) or return to the [diagram guide](README.md).
