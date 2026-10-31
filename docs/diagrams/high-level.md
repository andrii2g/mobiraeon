# High-level system diagram

**Snapshot: 2026-10-31.** All five logical parts and the responsibility boundaries in this view are agreed. [A] means agreed design, not implemented or qualified. The [architecture](../architecture.md) owns the component descriptions; the [diagram guide](README.md) explains versioning and status markers.

```mermaid
flowchart LR
    HUMAN(["Human owner"])

    subgraph INTERFACE["1. Human interface [A]"]
        GITEA["Gitea<br/>Human input and status"]
    end

    subgraph COORDINATION["2. Coordination [A]"]
        SYNC["Forge Synchronization<br/>Poll and publish"]
        COORD["Coordinator<br/>State, authority and gates"]
        SCHED["Scheduler<br/>Eligible Run dispatch"]
        STATE[("Coordination state<br/>SQLite")]
        SYNC --> COORD
        COORD --> SCHED
        COORD <--> STATE
        COORD --> SYNC
    end

    subgraph EXECUTION["3. Agent execution [A]"]
        RUNNER["Workers / Runner Adapters<br/>Controlled execution"]
        AGENTS["Orchestrator / specialists<br/>Reasoning and work"]
        RUNNER <--> AGENTS
    end

    subgraph REGISTRY["4. Agent Registry [A]"]
        PROFILES[("Agents and Profiles<br/>Git-published revisions")]
    end

    subgraph CONTENT["5. Artifacts and context [A]"]
        ARTIFACTS[("Versioned sources,<br/>Deliverables and evidence")]
    end

    HUMAN <--> GITEA
    GITEA <--> SYNC
    PROFILES -->|Pinned configuration| COORD
    SCHED -->|Authorized Run| RUNNER
    RUNNER -->|Reports and observed facts| COORD
    RUNNER <-->|Permitted content access| ARTIFACTS
    COORD <-->|Revisions and evidence| ARTIFACTS

    classDef agreed fill:#e8f3ee,stroke:#28644d,color:#12372a,stroke-width:1.5px;
    classDef human fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class GITEA,SYNC,COORD,SCHED,STATE,RUNNER,AGENTS,PROFILES,ARTIFACTS agreed;
    class HUMAN human;
```

The Coordinator is the authority for workflow changes; Agent proposals, forge observations, and process exits are inputs to its controls. Workers submit results through that boundary. The Registry retains configuration, Coordination retains operational records and acceptance, and Artifacts/context retain the versioned material.

These are logical parts, not a requirement for five separate services. Credentials use a separately authorized secret mechanism, and execution uses the configured, qualified runtime/provider path. Detailed infrastructure and workflow progression are outside this view.

Continue with [intake and readiness](intake-and-readiness.md), or choose a focused view from the [diagram guide](README.md).
