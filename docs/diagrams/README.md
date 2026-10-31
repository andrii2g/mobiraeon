# Architecture and workflow diagrams

These Mermaid sources summarize the design discussed in the governing documents. They describe intended behavior, not implemented or qualified capabilities.

| View | Purpose |
| --- | --- |
| [High-level system](high-level.md) | The five agreed logical parts, their main exchanges, and information ownership |
| [1. Intake and readiness](intake-and-readiness.md) | Classify observed work, clarify when needed, and determine whether a Task is Ready |
| [2. Assignment and selection](assignment-and-selection.md) | Match a required responsibility to an eligible registered Agent/Profile and record the Assignment |
| [3. Run lifecycle](run-lifecycle.md) | Authorize and dispatch a bounded attempt, supervise it, and record its outcome |
| [4. Assessment and rework](assessment-and-rework.md) | High-level assessment model and initial defaults |
| [5. Integration and validation](integration-and-validation.md) | High-level view of combining reviewed work and validating the whole result |
| [6. Initiative outcome acceptance](initiative-acceptance.md) | Whole-outcome assessment, acceptance authority, and remaining-work handoff |
| [7. Request closure and follow-up](request-closure-and-follow-up.md) | Fulfillment and handling of later defects or changed goals |
| [8. Waiting and recovery](waiting-and-recovery.md) | Choices among waiting, retry, reassignment, and stopping |
| [9. Human controls](human-controls.md) | Human intervention and scope changes |
| [10. Context and shared work](context-and-shared-work.md) | Context handoff and coordination of parallel Tasks |
| [11. Agent setup and Gitea](agent-setup-and-gitea.md) | Proposed onboarding and forge-identity relationship |

## Agreement legend

- **[A] Agreed:** an explicitly accepted high-level step or a rule already established by the approved requirements and decisions.
- **[P] Proposed:** routing or behavior prepared for the current discussion and awaiting agreement. Proposed nodes use an amber background as well as the text marker in the view's introduction.
- Arrows show logical relationships or handoffs. They do not define API messages, transactional boundaries, exact lifecycle state names, or a mandatory total ordering of concurrent work. Polling, independent work, and supervised execution can overlap under the governing controls.

Read the system view first, then use the focused workflow views as needed. Links at each boundary connect the parts without duplicating the shared Run lifecycle or drawing long feedback arrows across the whole delivery process. Review, verification, reasoning, and repair are all ordinary bounded Agent Runs; subsequent work re-enters the relevant view.

The [architecture](../architecture.md), [workflow](../workflow.md), [requirements](../requirements.md), and [decision register](../decisions.md) govern the meaning of each view, including review, authority, and exact-revision evidence requirements.

