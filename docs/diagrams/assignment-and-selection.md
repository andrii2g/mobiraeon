# Assignment and Agent selection

**Snapshot: 2026-10-31. [A] Agreed high-level behavior.** This view follows [Agent assignment and selection](../workflow.md#agent-assignment-and-selection). It separates Task readiness, configuration eligibility, and Run dispatch without defining exact state names or selection contracts. Agreement does not mean implemented or verified.

```mermaid
---
config:
  flowchart:
    wrappingWidth: 280
---
flowchart TB
    Ready["Ready Task or workflow stage"] --> Role["Identify required responsibility / Role<br/>from the Task or approved workflow"]
    Role --> Candidates["Resolve enabled registered Agents<br/>and each exact referenced Profile"]
    Candidates --> Eligible{"Any eligible<br/>configurations?"}
    Eligible -->|No eligible configuration| Missing["Record missing eligibility;<br/>await an authorized resolution"]
    Missing -. Judgment needed and eligible Orchestrator available .-> Orchestrator
    Missing -. Configuration or authority changes .-> Candidates
    Eligible -->|Eligible candidates| Default{"Selection resolved by an approved<br/>rule or Orchestrator proposal?"}
    Default -->|Yes| Preference["Apply the preference or proposal<br/>among eligible candidates only"]
    Default -->|No| Orchestrator[["Bounded Orchestrator Assignment / Run<br/>proposes a suitable selection"]]
    Orchestrator -->|Proposal requires validation| Candidates
    Preference --> Assignment["Coordinator validates and records<br/>the authorized Assignment"]
    Assignment --> Dispatch{"Run start conditions<br/>still satisfied?"}
    Dispatch -->|Yes| Run[["Scheduler dispatches recorded work<br/>through the shared Run lifecycle"]]
    Dispatch -->|Capacity temporarily unavailable| Capacity["Assignment waits for capacity;<br/>no model call merely to wait"]
    Capacity -. Capacity changes .-> Dispatch
    Dispatch -->|Other condition changed| Reassess["Coordinator reassesses the affected<br/>Task, selection or authorization"]

    classDef default fill:#e8f3ee,stroke:#28644d,color:#12372a;
```

Eligibility covers the Role, capabilities, qualified execution scope, permissions, limits, and review independence. Each selected registered Agent revision retains its exact `profileRef`; its Profile's `roleRef` and instruction bindings must cover the responsibility. The Scheduler does not attach an arbitrary Profile or model, and Role text grants no permissions. Authorized changes follow the versioned Registry process.

Missing Agent eligibility and temporary lack of capacity do not alone remove Task readiness. Loss of required inputs or governing authority does trigger [readiness reassessment](intake-and-readiness.md). An unresolved choice is visible even when no eligible Orchestrator can run; it never authorizes an unqualified fallback. Ordinary approved selections require no additional reasoning Run.

The Assignment records the authorized allocation and governing references; it does not start execution. Run start rechecks readiness, authority, ownership, qualified configuration, capacity, and limits through the [shared Run lifecycle](run-lifecycle.md), including the immutable configuration record. Review uses a separate Assignment and Run under the independence policy; a different Agent name, Role, Profile, or model alone is insufficient.

Previous view: [Intake and readiness](intake-and-readiness.md). After execution: [Assessment and rework](assessment-and-rework.md).
