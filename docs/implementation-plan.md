# Planning and validation sequence

This proposed execution sequence builds on D-01 through D-12 and the approved requirements. Complete the remaining detailed contracts and pilot specifications identified in the [readiness review](implementation-readiness-review.md). Existing sample code is an experimental reference, not a selected production foundation.

## Remaining high-level discussions

The main architecture and normal delivery path are established. Discuss the remaining responsibilities and outcomes below without reopening the selected technologies, topology, terminology, or Agent configuration model. The agenda does not establish new defaults.

| Topic | Remaining discussion |
| --- | --- |
| Agent onboarding and Gitea identities | Discuss [Registry hosting and forge-account mappings](pilot-and-agent-setup.md#registry-and-gitea-identities), then the [Agent preparation workflow](workflow.md#proposed-agent-onboarding). Preserve the established Git Registry and configuration contract. |
| Concrete demonstration pilot | Discuss the [proposed repository, feature, and outcome](pilot-and-agent-setup.md#demonstration-pilot) within D-12, then select the concrete baseline, outcome acceptor, and demonstration coverage. |

Detailed specifications and qualification follow these discussions. Exact lifecycle transitions, concrete authority and independence rules, component contracts, persistence/recovery mechanisms, enforcement controls, operating values, and tested versions belong to the later work tracked in the [readiness review](implementation-readiness-review.md).

## Design stages and remaining specifications

| Stage | Established baseline and remaining work | Main decisions |
| --- | --- | --- |
| 1. Purpose and vocabulary | System boundary, hierarchy, Role/component names, and naming conventions are established. Keep later specifications consistent with their owning documents. | D-01, D-02, D-03 |
| 2. Requirements and lifecycles | Requirements, Task readiness, and the high-level delivery loop are established. Specify exact lifecycle transitions, actor permissions, and recovery rules after resolving the remaining high-level responsibilities. | D-04, D-09, D-10 |
| 3. Registry and execution contract | Agent/Profile fields, Git Registry persistence, execution boundaries, and staged qualification are established. Specify publication and override rules and concrete runtime/runner contracts. | D-05, D-06, D-08 |
| 4. Architecture specifications | Specify adapter contracts, packaging, versions, persistence/recovery, and enforcement within the confirmed Gitea, Python/SQLite, and Linux/container baseline. | D-07, D-11 |
| 5. First live validation | Specify one bounded end-to-end scenario, budgets, observable checks, and stopping conditions. | D-09, D-12 |

Agreement updates the [decision register](decisions.md) and the relevant owning documents. It does not automatically authorize repository renaming, infrastructure provisioning, paid runs, or production deployment.

## Validation candidates after agreement

- **Forge adapter qualification:** qualify Gitea first against the versioned, forge-neutral contract and its declared capabilities, traceable mappings, and authority boundary. Project migration and cross-forge synchronization remain separately scoped.
- **CLI capability checks:** establish supported noninteractive behavior, options, tool boundaries, output contracts, and cancellation for each requested runtime family.
- **One controlled delivery slice:** prepare a specification, execute one small change, handle one clarification, review independently, integrate, and verify the combined result.
- **Recovery checks:** interrupt a run, repeat an event, change a profile revision, and confirm that results remain attributable and ownership remains valid.
- **Model/profile comparison:** compare accepted outcomes, rework, elapsed time, spend when measurable, and necessary human decisions.
- **Operating readiness:** assess persistence, isolation, secrets, observability, stop controls, and integration credentials for the selected environment.

These are candidate validation activities. Their implementations, order, and release scope depend on the approved requirements. Do not infer broad autonomy from a passing demonstration.

## Existing sample

The earlier experimental sample is historical context. Its prototype reference is not present in this checkout. Its data model, states, storage, and framework do not constrain the confirmed target design.
