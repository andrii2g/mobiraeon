# Architecture and workflow diagrams

These Mermaid sources summarize the design discussed in the governing documents. They describe intended behavior, not implemented or qualified capabilities.

| View | Purpose |
| --- | --- |
| [High-level system](high-level.md) | The five agreed logical parts, their main exchanges, and information ownership |
| [1. Intake and readiness](intake-and-readiness.md) | Classify observed work, clarify when needed, and determine whether a Task is Ready |
| [2. Assignment and selection](assignment-and-selection.md) | Match a required responsibility to an eligible registered Agent/Profile and record the Assignment |
| [3. Run lifecycle](run-lifecycle.md) | Authorize and dispatch a bounded attempt, supervise it, and record its outcome |
| [4. Assessment and rework](assessment-and-rework.md) | Proposed routing for review, verification, correction, and authorized acceptance |

## Agreement legend

- **[A] Agreed:** an explicitly accepted high-level step or a rule already established by the approved requirements and decisions.
- **[P] Proposed:** routing or behavior prepared for the current discussion and awaiting agreement. Proposed assessment nodes use an amber background as well as the text marker in the view's introduction.
- Arrows show logical relationships or handoffs. They do not define API messages, transactional boundaries, exact lifecycle state names, or a mandatory total ordering of concurrent work. Polling, independent work, and supervised execution can overlap under the governing controls.

Read the system view first, then use the four focused workflow views as needed. Links at each boundary connect the parts without duplicating the shared Run lifecycle or drawing long feedback arrows across the whole delivery process. Review, verification, reasoning, and repair are all ordinary bounded Agent Runs; subsequent work re-enters the relevant view.

The [architecture](../architecture.md), [workflow](../workflow.md), [requirements](../requirements.md), and [decision register](../decisions.md) govern the meaning of each view. A proposed assessment route still has to satisfy the already agreed review, authority, and exact-revision evidence requirements.

## Keeping history

Keep the Mermaid source in these Markdown files so supported repository viewers render it and Git records readable text changes. Update the diagrams and their governing text in the same commit. Retain stable node identifiers where their meaning is unchanged, and change [P] to [A] only after agreement. Previous versions remain available through Git history; separate dated copies are unnecessary.

The current snapshot includes agreed Run launch/result reporting and the newly proposed assessment/rework route. It intentionally leaves exact states, policy values, and adapter contracts to their later specifications.
