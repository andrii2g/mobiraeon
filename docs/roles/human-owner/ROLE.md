# Human owner

## Role identity

**Role ID:** `human-owner`  
**Role type:** Human reference

## Purpose

Provide product intent and accountable decisions. Establish the boundaries within which agents operate and resolve decisions requiring human judgment or authority.

This description documents the human participant's responsibilities. It is not an executable AI agent role and does not authorize an agent to impersonate the owner or supply a human approval.

## Required inputs

- Use the [Shared operating rules](../_shared/OPERATING_RULES.md) as the common collaboration reference.
- Review the product goals, requested outcome, relevant requirements, and known constraints.
- Review proposed baselines, acceptance expectations, autonomy rules, and any decision requests requiring human input.
- Obtain the evidence and alternatives needed to make the relevant decision.

## Startup checks

1. Identify the intended users, problem, desired result, and explicit non-goals.
2. Identify the human decision authorities and the project policies governing agent actions.
3. Establish what evidence demonstrates successful delivery and which decisions require human acceptance.
4. Distinguish approved requirements from suggestions, assumptions, and matters still awaiting a decision.

## Responsibilities

- Supply an initial brief describing intent, requirements, constraints, and priorities.
- Participate in clarification and early review, correcting interpretations that do not match the intended outcome.
- Establish or accept the scope, delivery expectations, and autonomy policy within the owner's authority.
- Define the boundaries for independent engineering decisions, resource consumption, and externally consequential actions.
- Review escalated product questions, competing requirements, scope changes, and exceptions that agents lack authority to resolve.
- Make explicit decisions using the available evidence, consequences, and alternatives.
- Identify the affected scope when approving a change and distinguish it from unrelated requirements.
- Review progress and outcomes using the agreed acceptance policy. Exercise available pause, cancellation, reprioritization, or takeover controls when appropriate.

## Required outputs

Provide the initial brief, accepted requirements or other baselines, recorded policy decisions, and answers to human-directed requests.

For each decision, state the affected request or task, the selected outcome, relevant conditions, and any changes to scope or authority. Supply enough rationale to prevent the same ambiguity from recurring. Record any required follow-up or another designated decision authority.

## Authority and boundaries

Decide only within the human owner's actual authority. Route matters requiring another authorized person through the project's established decision process.

Allow agents to resolve details already covered by delegated authority. A human answer changes only the scope and conditions explicitly addressed by that answer. Silence and elapsed time do not establish acceptance.

## Completion and handoff

Provide the decision through the agreed project channel so it is recorded and available to the orchestrator and affected tasks. Identify remaining conditions or evidence required before dependent work proceeds.

Human participation in a decision is complete when its outcome and authority are recorded. The overall request remains governed by its separate delivery and acceptance criteria.
