# Human controls and scope changes

**[A] High-level human controls.** Authorized human instructions reach the Coordinator directly. The [workflow](../workflow.md#human-controls-and-scope-changes) describes pause, resume, cancellation, reprioritization, takeover, and scope changes.

```mermaid
---
config:
  flowchart:
    wrappingWidth: 280
---
flowchart TB
    HUMAN["Authorized human instruction"] --> COORD["Coordinator validates the instruction<br/>and its affected scope"]
    COORD --> APPLY["Apply the control and record<br/>affected work and retained progress"]
    APPLY --> CONTINUE{"Continuation authorized<br/>and no applicable hold?"}
    CONTINUE -->|Yes| CHECK["Recheck readiness and authority;<br/>dispatch eligible work within limits"]
    CONTINUE -->|No| HOLD["Affected work remains held or stopped;<br/>record the required next action"]

    classDef agreed fill:#e8f3ee,stroke:#28644d,color:#12372a;
    classDef boundary fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class COORD,APPLY,CONTINUE,CHECK,HOLD agreed;
    class HUMAN boundary;
```

Pause holds new starts and winds down affected Runs under supervision. Resume lifts only the selected hold and rechecks current conditions. Cancellation ends selected work without implying acceptance or undoing existing effects. Reprioritization changes eligible pending order without automatic preemption.

Takeover holds affected automation, retires prior execution ownership, and cleans up or contains its processes before exclusive human work. Human-produced changes remain subject to normal evidence and acceptance rules. Returning to automation is explicit and requires current checks through a new Run when execution is needed.

Controls persist across restart and apply to explicit scope; Request-level controls use validated delivery links. A narrower resume does not override broader holds or cancellation. Cancelled work requires new authorization to continue. Authorized scope changes update governing context and trigger reassessment of affected work and evidence; independent work may continue.

Recording a control request is distinct from establishing that active execution has stopped. Cleanup or effective containment still governs capacity reuse. These responsibilities do not select exact states, timing, or control mechanisms.

Related: [waiting and recovery](waiting-and-recovery.md). Return to the [diagram guide](README.md).
