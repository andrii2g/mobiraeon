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
| [11. Agent setup and Gitea](agent-setup-and-gitea.md) | Agent onboarding and stable forge-identity relationship |
| [12. Registry API and persistence](registry-organization.md) | Forge-independent Python/SQLite Registry and configuration ownership |
| [13. First-Agent preparation](first-agent-preparation.md) | Reviewed inputs, the persistent disabled catalog, preparation evidence, and later onboarding handoff |
| [14. Registry authoring and publication](registry-publication.md) | Editable drafts, exact-content review, immutable publication, and later changes |
| [15. Registry administrator access](registry-access.md) | First-owner bootstrap, shared API/CLI permission checks, revocation, and owner-controlled recovery |
| [16. Registry controls and overrides](registry-controls.md) | Current selection and enablement, reviewed ceiling reductions, and separate execution gates |

## Agreement legend

- **[A] Agreed:** an explicitly accepted high-level step or a rule already established by the approved requirements and decisions.
- All current views describe the design baseline. Green nodes show processing and retained records; indigo nodes distinguish participants or context without implying an unconfirmed step.
- Arrows show logical relationships or handoffs. They do not define API messages, transactional boundaries, exact lifecycle state names, or a mandatory total ordering of concurrent work. Polling, independent work, and supervised execution can overlap under the governing controls.

Read the system view first, then use the focused workflow views as needed. Links at each boundary connect the parts without duplicating the shared Run lifecycle or drawing long feedback arrows across the whole delivery process. Delivery review, verification, reasoning, and repair performed by Agents use ordinary bounded Runs; subsequent work re-enters the relevant view. Registry authoring and review follow the authorized administrator path.

The [architecture](../architecture.md), [workflow](../workflow.md), [requirements](../requirements.md), and [decision register](../decisions.md) govern the meaning of each view, including review, authority, and exact-revision evidence requirements.

