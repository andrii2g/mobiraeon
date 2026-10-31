# Möbiræon Gitea issue templates

These starter files provide Request, Initiative, and Task issue-template examples for a Gitea repository. They can be adapted to the managed repository's approved forge configuration.

The files collect human input. Coordinator, polling, Scheduler, Worker, and Agent execution require their separate implementation and qualification.

## Prepare the repository

1. Select the intended Gitea repository and enable issues under its approved configuration.
2. Place the entire `.gitea/` directory at the repository root and commit it on the default branch. Preserve the hidden directory name and the repository's existing README.
3. Create the three example repository labels below before trying the templates. Their automated handling remains subject to the forge-adapter contract and qualification.
4. Open **New Issue** and confirm the Request, Initiative, and Task choices appear. Check their wording and automatic kind labels in the installed Gitea version.
5. Verify origin and scope links between a Request, its Initiative, and bounded Tasks. Record the observed behavior and any gaps; manual template checks do not qualify the automated workflow.

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

These Markdown templates collect information; they do not enforce completeness or validate approvals. Labels and issue closure do not establish readiness, delegated authority, acceptance, or permission to execute. In the target system those determinations belong to the Coordinator under the governing policies and evidence rules. Do not put credential values in issues or attachments.

The formats follow [Gitea's issue-template documentation](https://docs.gitea.com/usage/issues-prs/issue-pull-request-templates/). Verify template rendering and label behavior against the local installation. The authoritative product definitions, requirements, decisions, and workflow remain in the Möbiræon documentation repository.
