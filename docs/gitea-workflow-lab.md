# Gitea workflow lab

Created and verified on **2026-10-31** through the installed Gitea server CLI and HTTP API. This is a manual setup rehearsal for the agreed intake conventions. Coordinator, Scheduler, Worker execution, and automatic workflow progression remain unimplemented by this setup.

## Live repository

| Item | Observed value |
| --- | --- |
| Repository | [andrey/mobiraeon-workflow-lab](http://localhost:3001/andrey/mobiraeon-workflow-lab) |
| Access | Private, under the existing `andrey` account |
| Default branch | `main` |
| Gitea version | `28.2.0`, read from the authenticated API |
| Repository ID | `2` |
| Template commit | `3453d82076f474eff9b02b14ddfb19010aab71c4` |

The reachable address for this session is `http://localhost:3001/`, supplied by the human owner. This does not change the Compose defaults or establish Worker-container connectivity. The existing test repository was not modified.

## Published starter

The [starter repository files](../infra/gitea/bootstrap/repository/README.md) contain a README and three Markdown templates in `.gitea/ISSUE_TEMPLATE`: Request, Initiative, and Task. The [label manifest](../infra/gitea/bootstrap/labels.json) supplies three individual API label payloads:

| Label | Purpose |
| --- | --- |
| `kind/request` | Desired outcome for intake or clarification |
| `kind/initiative` | Overall delivery outcome within a Project |
| `kind/task` | Bounded work candidate requiring validation before assignment |

The labels are exclusive within their `kind` scope. No lifecycle-status labels, Agent identities, repository collaborators, or model settings were configured. These concrete label names are lab conventions; the general forge contract still needs its detailed specification. Labels and issue closure do not establish readiness, permission, or acceptance.

## Linked rehearsal items

- [Request #1](http://localhost:3001/andrey/mobiraeon-workflow-lab/issues/1): try human Request intake.
- [Initiative #2](http://localhost:3001/andrey/mobiraeon-workflow-lab/issues/2): verify linked intake and delivery records; references Request #1.
- [Task #3](http://localhost:3001/andrey/mobiraeon-workflow-lab/issues/3): inspect the templates; references Initiative #2 and Request #1.

All three are open, explicitly identified as Codex-created setup samples at the owner's direction. They establish no Task readiness, Assignment, Run, baseline approval, or Deliverable acceptance. This lab is separate from selecting the executable feature pilot in D-12 or publishing an Agent Registry.

## Operations and verification

The setup used the existing container's `gitea admin user` command to identify the account and generate a temporary scoped token. No password was retrieved or changed, and token values were kept in process memory. Gitea 28.2.0's repository-creation route requires both user-write and repository-write scopes; the first attempt without user-write returned 403 before creating a repository, and its token was revoked. The successful setup used user, repository, and issue write scopes and revoked that token afterward as well. Authentication rejection was checked after each revocation.

The successful API sequence was repository creation through `POST /user/repos`, label creation through `POST /repos/{owner}/{repo}/labels`, one commit of the four starter files through `POST /repos/{owner}/{repo}/contents`, and creation of the three sample issues. File bytes were read back and matched to the local sources. The repository remained private on `main`.

Gitea's [issue-template API](https://docs.gitea.com/api/operations/repo-get-issue-templates/) recognized all three template names, file paths, contents, and expected kind labels. API readback verified each sample's open state, label, and origin links. The samples' labels were supplied explicitly through the API; automatic label application when submitting the browser form and visual form rendering were not tested.

The next manual check is to open [New Issue](http://localhost:3001/andrey/mobiraeon-workflow-lab/issues/new/choose), inspect the three choices, and try a Request submission. Automated polling, authenticated human approvals, Coordinator mappings, and execution still require their own implementation and qualification.
