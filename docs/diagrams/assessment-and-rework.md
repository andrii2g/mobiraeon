# Assessment, acceptance, and rework

**Snapshot: 2026-10-31.** The routing in amber is **[P] proposed** for discussion. Independent review, designated acceptance authority, and revision-specific evidence are already required by the agreed baseline. This view describes responsibility and progression, not exact states or a mandatory sequence of review and verification. See the [workflow proposal](../workflow.md#proposed-review-verification-acceptance-and-rework).

```mermaid
---
config:
  flowchart:
    wrappingWidth: 280
---
flowchart TB
    RESULT["Recorded submission<br/>or new assessment evidence"] --> PLAN["Coordinator identifies missing assessment<br/>for the exact Deliverable revision"]
    PLAN --> MISSING{"Required assessment<br/>still missing?"}
    MISSING -->|Yes| ASSESS["Eligible review and/or verification<br/>Assignments through shared Run lifecycle"]
    ASSESS --> EVIDENCE["Record findings, checks,<br/>limitations and assessed revisions"]
    MISSING -->|No| GATE{"Required criteria met<br/>with current evidence?"}
    EVIDENCE --> GATE
    GATE -->|No| REASON{"What prevents acceptance?"}
    REASON -->|Required correction| REWORK["Author repairs within scope:<br/>same Task, another Run"]
    REASON -->|Missing or inconclusive evidence| CHECK["Arrange checks or investigation;<br/>keep acceptance pending"]
    REASON -->|Ambiguous or disputed expectation| DECISION["Orchestrator routes a Decision<br/>within delegated authority"]
    REWORK --> REASSESS["Reassess current revisions<br/>and affected evidence"]
    CHECK --> REASSESS
    DECISION --> REASSESS
    GATE -->|Yes| CONTRACT["Satisfy the Task's delivery contract,<br/>including integration when required"]
    CONTRACT -->|Delivery conditions satisfied| AUTHORITY["Accept only with designated authority<br/>and Coordinator-enforced gates;<br/>otherwise keep acceptance pending"]
    AUTHORITY -->|Task acceptance recorded| CONTINUE["Continue remaining Tasks and integration;<br/>assess the overall Initiative outcome"]

    classDef proposed fill:#fff3d6,stroke:#a66b12,color:#513807;
    classDef boundary fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class PLAN,MISSING,ASSESS,EVIDENCE,GATE,REASON,REWORK,CHECK,DECISION,REASSESS,CONTRACT,AUTHORITY proposed;
    class RESULT,CONTINUE boundary;
```

Each new submission or assessment result enters at the top. After correction, investigation, or a Decision, continue with current evidence through that same entry point. Every Agent Assignment uses the [shared Run lifecycle](run-lifecycle.md); the Coordinator does not perform model reasoning or execute checks itself.

Independent review assesses correctness, completeness, and conformance. Verification supplies check results and environment evidence; its timing and overlap follow the work contract. Separate Role names or models do not establish independence. A failed check is a finding about the work; a failed verifier execution follows Run recovery instead.

Acceptance remains pending while any required criterion, evidence, finding, or authority is unresolved. The Coordinator records the authorized determination and accepted revisions. An eligible reviewer can hold delegated acceptance authority; the model does not require an extra acceptance Run or fresh human approval for every Task. Only the Orchestrator initiates human escalation when resolution exceeds delegation. Changes to scope or governing contracts require the authorized Decision and artifact updates before affected work resumes.

| Delivery contract | What acceptance requires |
| --- | --- |
| Documentation or planning Task | Independent assessment and authorized acceptance of its own versioned Deliverable. |
| Reviewed-patch Task with separately assigned integration | Its own criteria may be accepted while the linked integration obligation continues. |
| Task requiring integrated code | Authorized integration and fresh validation of the exact combined revision before its acceptance. |
| Overall code delivery / Initiative | All required delivery obligations and overall outcome criteria, including applicable integrated validation. Accepted Tasks alone do not establish this. |

Conflicting target changes are serialized. Changes to a submission, governing input, or target revision require reassessment of affected evidence; reuse needs an explicit applicability determination. Rework retains Task identity, previous submissions, findings, and configuration history. Retry recovers execution; rework corrects assessed work. Neither exhaustion, silence, a closed issue, nor a merge establishes acceptance.

Previous: [Run lifecycle](run-lifecycle.md). Follow-up work returns to [assignment and selection](assignment-and-selection.md). Return to the [diagram guide](README.md).
