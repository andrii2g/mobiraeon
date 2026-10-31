# Waiting and recovery

**[P] High-level routing proposal.** Durable waiting, bounded recovery, preserved history, and exclusive ownership already follow the baseline. This view summarizes the next-action choices in the [workflow proposal](../workflow.md#proposed-waiting-and-recovery).

```mermaid
---
config:
  flowchart:
    wrappingWidth: 280
---
flowchart TB
    CHANGE["Changed condition<br/>or recorded Run outcome"] --> COORD["Coordinator applies policy,<br/>current authority and human controls"]
    COORD -->|Condition is missing| WAIT["Wait for input, prerequisite<br/>or eligible execution capacity"]
    COORD -->|Recovery is permitted| RETRY["Retry the bounded attempt<br/>under the same Task"]
    COORD -->|Allocation must change| REASSIGN["Reassign eligible execution<br/>under the same Task"]
    COORD -->|Stop is required| STOP["Stop affected automation;<br/>preserve progress and required next action"]

    classDef proposed fill:#fff3d6,stroke:#a66b12,color:#513807;
    classDef boundary fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class COORD,WAIT,RETRY,REASSIGN,STOP proposed;
    class CHANGE boundary;
```

Waiting uses no active model merely to monitor a condition. Capacity waiting does not itself remove Task readiness. Retry and reassignment preserve Task identity, earlier evidence, and cumulative limits; uncertain effects are reconciled before repeating operations.

Reassignment uses an eligible authorized allocation and preserves exclusive execution ownership. Affected capacity returns only after cleanup or effective containment. Durable human holds also constrain recovery; a restart or available Worker does not release a pause or cancellation.

Stopping an attempt or automatic dispatch does not establish Task cancellation or acceptance. The Orchestrator handles judgment when eligible; otherwise the required action remains visible without bypassing controls or limits.

Related: [Run lifecycle](run-lifecycle.md) and [human controls](human-controls.md). Return to the [diagram guide](README.md).
