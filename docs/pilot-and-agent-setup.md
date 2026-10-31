# Pilot and Agent setup

The repository names, feature, account policy, and onboarding sequence below are proposals. Registry persistence and the prepared-repository pilot boundary follow [D-05](decisions.md#d-05-registry) and [D-12](decisions.md#d-12-first-live-validation-and-release-scope).

## Demonstration pilot

| Repository | Purpose |
| --- | --- |
| Existing `andrey/mobiraeon-workflow-lab` | Manual issue-template and label rehearsal, as recorded in the [lab guide](gitea-workflow-lab.md). |
| Proposed `andrey/mobiraeon-agent-registry` | Private Registry hosted in Gitea, containing versioned configuration and instructions. |
| Proposed `andrey/mobiraeon-demo` | Prepared task-list application used for the automated feature pilot. |

Prepare and review a working task-list application baseline before starting the automated pilot. Repository creation and application scaffolding are preparation; the pilot changes an existing identified baseline. The application technology remains a separate choice from Möbiræon's Python coordination service.

Proposed human Request: **Export the currently displayed tasks as CSV.** The observable outcome is a downloadable file representing that list with its agreed columns and correctly preserved values. The exact columns and examples belong to the pilot contract.

Demonstrate the full path from Request and baseline approval through implementation, independent review, authorized integration, combined-result validation, and outcome acceptance. Also demonstrate Decision waiting, interrupted-Run recovery, duplicate observation handling, and stale-result rejection required by D-12. Repository setup alone does not demonstrate these capabilities.

## Registry and Gitea identities

Store registered Agent definitions and reusable Profiles as JSON, and standing instructions as Markdown, in the dedicated Git Registry. Publish reviewed, validated revisions identified by exact commits. Coordination retains live work state, qualification references, and immutable per-Run configuration records; Artifacts retain substantial evidence, and credential values remain in the secret-management mechanism.

Propose one stable Gitea automation account for each registered Agent that acts in the forge, plus a separate Coordination service account. Accounts attach to stable Agent identities rather than Roles, Profile revisions, Workers, or individual Runs. An Agent performing no forge operations need not acquire an account merely to execute.

Project integration configuration binds an Agent to the relevant Gitea instance/account and permitted operations. Profiles remain reusable execution configuration. This is distinct from model-provider accounts; exact binding fields and catalog layout remain later specifications.

The Coordination account publishes coordination updates; Agent-attributed submissions and reviews use their explicitly mapped principals through authorized operations. Account provisioning is an administrative setup activity. Neither account creation nor an account's repository access grants workflow authority or establishes review independence. Trusted execution and forge operations remain subject to Coordinator controls, including authenticated actor and Run attribution; do not rely on a commit author name as proof of the acting principal.

Gitea supplies [repository and team permissions](https://docs.gitea.com/usage/access-control/permissions/), [API-token permissions](https://docs.gitea.com/development/api-usage/), and [protected-branch controls](https://docs.gitea.com/usage/access-control/protected-branches/). Use the applicable capabilities alongside Möbiræon's controls and qualify the actual permitted operations on the installed instance. Secret values stay outside Registry files and model-visible context; retain references in the appropriate configuration.

## Preparation order

1. Select the pilot repository, bounded feature, expected outcome, and applicable acceptance delegation.
2. Prepare the application baseline and publish the initial Role/Profile and Agent definitions, starting from the existing [Role catalog](roles/README.md).
3. Establish the selected forge identities, project bindings, repository permissions, and secret references through authorized administration.
4. Validate publication and qualify the selected execution path; enable the eligible configurations and apply the approved operating limits.
5. Start the bounded pilot through the normal Assignment and Run workflow.

Begin with Git-based editing and review; a future configuration editor follows the same validation and publication path. See the [Agent onboarding proposal](workflow.md#proposed-agent-onboarding) and its [diagram](diagrams/agent-setup-and-gitea.md). These steps do not select JSON schemas, concrete credentials, runtime versions, or UI implementation.
