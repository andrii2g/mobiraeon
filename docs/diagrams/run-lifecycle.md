# Run launch and result reporting

**[A] Agreed high-level design.** This shared lifecycle applies to every Agent stage, including Orchestrator reasoning, authoring, independent review, verification, and Agent-performed integration. It does not define exact states or API messages. The [workflow](../workflow.md#run-launch-and-result-reporting) owns the rules.

```mermaid
---
config:
  flowchart:
    wrappingWidth: 280
---
flowchart TB
    ASSIGN["Recorded Assignment"] --> CHECK["Coordinator rechecks readiness,<br/>authority, ownership and execution limits"]
    CHECK --> PERMIT{"Start permitted?"}
    PERMIT -->|No| WAIT["Record reason and wait<br/>or route required action"]
    PERMIT -->|Yes| RECORD["Coordinator durably records Run,<br/>ownership and pinned configuration"]
    RECORD --> DISPATCH["Scheduler dispatches<br/>the recorded Run"]
    DISPATCH --> EXEC["Worker / Runner Adapter<br/>starts and supervises bounded execution"]
    EXEC --> REPORT["Agent report and Artifact revisions<br/>plus separate supervisor observations"]
    REPORT --> VALIDATE["Coordinator authenticates submission<br/>and checks ownership and evidence"]
    VALIDATE --> CURRENT{"Current, authorized<br/>execution?"}
    CURRENT -->|No| STALE["Retain audit evidence;<br/>reject authoritative updates"]
    CURRENT -->|Yes| OUTCOME["Record validated outcome:<br/>produced, blocked, failed,<br/>cancelled or unknown"]
    OUTCOME --> NEXT["Continue assessment, waiting<br/>or bounded recovery as applicable"]
    REPORT -.-> CLEANUP["Return capacity only after<br/>cleanup or effective containment"]

    classDef agreed fill:#e8f3ee,stroke:#28644d,color:#12372a;
    classDef boundary fill:#eef2ff,stroke:#5261a3,color:#20294f;
    class CHECK,PERMIT,WAIT,RECORD,DISPATCH,EXEC,REPORT,VALIDATE,CURRENT,STALE,OUTCOME,CLEANUP agreed;
    class ASSIGN,NEXT boundary;
```

The Agent receives shared rules, Role instructions, the Assignment, permitted context, and an output contract. Trusted execution controls enforce permissions and limits outside the prompt. Reports identify work, exact revisions, checks and environments, limitations, and unresolved questions; a successful exit or a completion claim does not establish acceptance.

| Recorded outcome | Continuation |
| --- | --- |
| Produced work or assessment evidence | Continue with [assessment and rework](assessment-and-rework.md); assessment reports contribute evidence rather than automatically starting another review of themselves. |
| Blocked work | Preserve progress and the unmet condition. Use an eligible Orchestrator Assignment when interpretation or a Decision is needed; waiting needs no active model. |
| Failed attempt | Follow bounded recovery while preserving Task identity, evidence, and cumulative limits. A changed configuration requires a new authorized Run. |
| Unknown or interrupted outcome | Reconcile launches and external effects before repeating an operation. A missing acknowledgement does not establish success or permission to retry blindly. |
| Cancellation | Record the authorized stop, retained work, and uncertain effects. |

Capacity cleanup is independent of acceptance. Duplicate dispatches and reports must converge without duplicate launches or accepted work. Follow-up Agent work returns through [assignment and selection](assignment-and-selection.md) and this same lifecycle.

Previous: [assignment and selection](assignment-and-selection.md). Next: [assessment and rework](assessment-and-rework.md). Return to the [diagram guide](README.md).
