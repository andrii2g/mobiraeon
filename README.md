# Möbiræon

**Möbiræon** is inspired by **Möbius**, representing continuity and interconnected workflows, and **æon**, a word of Greek origin evoking vast spans of time. The name reflects a continuous cycle of planning, building, verifying, and improving software through coordinated AI agents. The **ö** and **æ** preserve these references visually, while the repository uses the ASCII spelling `mobiraeon`.

Möbiræon is a platform for orchestrating and automating software development lifecycle activities through coordinated AI agents. It turns human intent into specifications, bounded assignments, and software changes assessed against explicit acceptance criteria.

## Purpose

Möbiræon reduces repeated human coordination while preserving control over product intent, delivery quality, and resource use. Specialized agents perform assigned work, resolve questions within their authority, and continue when required inputs or decisions become available.

The human owner supplies the initial brief, participates in clarification and early review, and resolves decisions outside the agents' authority. Human participation and agent autonomy follow the governing project policy.

## Product goals

- Coordinate multiple specialized agents working toward a shared project or change.
- Configure agent responsibilities, AI providers, models, reasoning settings, tools, and execution limits.
- Produce research, specifications, architecture descriptions, data contracts, implementation, tests, and supporting documentation.
- Organize bounded work, dependencies, milestones where useful, progress, and acceptance evidence.
- Support parallel work when prerequisites and shared boundaries permit it.
- Resolve answerable questions within delegated authority and route unresolved decisions through the orchestrator.
- Resume eligible work without repeated human prompting.
- Preserve continuity across waiting periods, interruptions, and subsequent requests.

## Supported work

The product scope covers:

- New projects.
- Features in existing projects.
- Bug fixes.
- Refactoring.
- Investigations and research.
- Documentation changes.

Each request type has activities and acceptance criteria appropriate to its intended outcome. Each release specifies the capabilities and request types it supports.

## Engineering coverage

Möbiræon coordinates work across:

- **Data and persistence:** database architecture, schemas, migrations, Redis structures, and data access contracts.
- **Domain:** constants, enumerations, models, DTOs, abstractions, and shared contracts.
- **Business logic:** data management, business rules, use cases, and application workflows.
- **Workers and integrations:** polling, consumers, network services, and background processing.
- **Presentation:** web, Blazor, mobile, desktop, console, and other user interfaces.

These areas define engineering coverage. Their execution order follows the dependencies and acceptance criteria of the work.

## Delivery boundaries and authority

The governing request and project policy define the delivery boundary and the evidence required for acceptance.

Production deployment, destructive changes to live data, and operation of delivered applications are controlled by their applicable authorization and acceptance policies. Authorization is established through the relevant policy or an explicit decision by the designated authority.

Only the orchestrator creates requests requiring human decisions or intervention. Agents submit unresolved questions for resolution within the system, and independent work continues while affected assignments wait for an answer.

## Documentation

See the [documentation index](docs/README.md) for requirements, architecture, workflow, and decisions.
