# Möbiræon workflow lab

This repository rehearses human intake and linked work items in local Gitea. The proposed repository name is **`mobiraeon-workflow-lab`**, with private visibility and `main` as its default branch.

This is a setup rehearsal. No Coordinator, polling integration, Scheduler, Worker, or Agent runtime is implemented or activated by these files. It is not the selected D-12 feature pilot, an application repository, or the Agent Registry.

## Prepare the repository

1. Create the private repository in the local Gitea instance under the intended human owner or organization. Enable issues.
2. Place this README and the entire `.gitea/` directory at the repository root and commit them on its default branch. Preserve the hidden directory name.
3. Create the three repository labels below before trying the templates. Their names are proposed conventions for this rehearsal, not finalized adapter contracts.
4. Open **New Issue** and confirm the Request, Initiative, and Task choices appear. Check their wording and automatic kind labels in the installed Gitea version.
5. Rehearse one human-authored Request, a linked Initiative, and a bounded Task. Use ordinary issue links to preserve their origin and scope. Record the observed result and any gaps; do not describe this as automated workflow qualification.

| Label | Meaning |
| --- | --- |
| `kind/request` | A desired outcome submitted for intake or clarification. |
| `kind/initiative` | A delivery outcome within a Project, delivered through linked Tasks. |
| `kind/task` | A bounded contribution proposed for validation and assignment. |

No workflow-status labels are supplied. Exact lifecycle states and their transition rules remain design work.

## Use the templates

- **Request** is the normal human entry point. Describe the outcome and constraints; unanswered questions are expected.
- **Initiative** preserves the delivery outcome and links its originating Request and Tasks. A Request may contribute to an existing Initiative rather than requiring a new one.
- **Task** describes bounded work within an Initiative. A human-created Task remains a candidate until its contract, context, authority, and prerequisites are validated.

Keep the Request and its discussion. Creating an Initiative or decomposing work does not replace the Request or create nested Task trees. Scope links and execution prerequisites are recorded separately.

These Markdown templates collect information; they do not enforce completeness or validate approvals. Labels and issue closure do not establish readiness, delegated authority, acceptance, or permission to execute. In the target system those determinations belong to the Coordinator under the governing policies and evidence rules. During this rehearsal all tracking is manual. Do not put credential values in issues or attachments.

The formats follow [Gitea's issue-template documentation](https://docs.gitea.com/usage/issues-prs/issue-pull-request-templates/). Verify template rendering and label behavior against the local installation. The authoritative product definitions, requirements, decisions, and workflow remain in the Möbiræon documentation repository.
