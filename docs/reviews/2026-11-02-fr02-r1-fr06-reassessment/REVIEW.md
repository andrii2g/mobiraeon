# Independent reassessment of FR-02-R1 and FR-06

Date: 2026-11-02 (Europe/Kiev). Candidate: `submissions/repair-fr02-r1-fr06/final-01`.

**FR-02-R1 and FR-06 are resolved. No additional actionable finding was established.** Fresh Windows and Linux verification each passed all 14 required commands, including clean installed artifacts and real Linux source/installed Worker suites. Designated repair acceptance remains pending.

This separate reassessment follows the captured `docs/repair-instructions-fr02-r1-fr06.md` in the [reviewed source archive](../../../submissions/repair-fr02-r1-fr06/final-01/source.zip) and preserves the [original full review](../2026-11-02/REVIEW.md), [first repair reassessment](../2026-11-02-reassessment/REVIEW.md), submitted handoffs and all prior evidence. No implementation, staging, commit or push was changed by this review.

## Exact source and reviewed scope

The latest frozen archive contains **143 files**, independently checked entry by entry against its manifest. Its SHA-256 is:

```text
b36f8afa6eb0bc212d2ce87e37727b8daed25f8210443a4daa86c2e0eed72464
```

Manifest SHA-256: `9b39407591171d71b9e933fa0755d95db389586f9863ed88c37ef8ccaad04ef4`. Declared deletions: `[]`. Starting Git revision: `7a386fe69c6e2c5bb7ee32d17ecdb2773e0f2491`. The active checkout matched every captured file before review-document additions.

The separately verified defective baseline is the **139-file** `repair-fr-01-fr-05/final-02`, archive SHA-256 `56dc16b8a08cc3bb36c4eb067250bd97a1de61a98f825e756920b2fb1bd79bc6`. It is the baseline for these two findings, distinct from the earlier 128-file full-review archive.

The repair changes bootstrap audit metadata, the repair verifier, their tests and the maintained Registry contract. Other baseline-to-final differences are the previously supplied review/navigation/brief additions. Locks/runtime pins, migrations 0001–0004, catalog/Access/Coordination transactions and authority, both signal handlers, fixed fixture assets, disabled Agent catalog and earlier application repairs remain unchanged.

## Findings and dispositions

| Finding | Independent disposition | Evidence |
| --- | --- | --- |
| FR-02-R1 | Resolved | Real failure-audit success reports recorded metadata; genuine audit-write failure remains unavailable. Partial mutations, attribution and receipts remain truthful. |
| FR-06 | Resolved | A required standalone probe failure now fails the aggregate and CLI; existing wheel/platform guards propagate it with failed details retained. |

No new actionable finding was established within this reassessment. Passing developer checks alone was not used as the finding disposition.

### FR-02-R1: truthful child audit availability

At [bootstrap.py](../../../src/mobiraeon/bootstrap.py), lines 83–86, `(result.data or BusinessData()).audit_status` uses the established recorded default when a failed Registry operation has no business data. The unchanged `RegistryService._attempt_audit()` leaves such a result unchanged after a successful failure-audit transaction and explicitly adds unavailable metadata on an audit-write failure. The existing any-step stopped-result aggregate preserves actual outages.

The two new real protected CLI/SQLite cases prove the distinction without replacing Registry service results. A complete first instruction remains published; an incomplete second instruction retains its draft and stops with `known_failure/incomplete_definition`. Normal failure matches the exact validate invocation, actor and target to the actual audit row and reports `recorded`/`operations_recorded`. The targeted genuine audit-write fault proves that row absent and preserves `unavailable` at both levels. The installed application selection includes both cases.

Two additional independent real-store controls pass: an incomplete first definition with no earlier publication, and an earlier genuine history-audit outage followed by a later validation failure whose audit succeeds. The latter proves the aggregate retains an earlier outage even when the last failed step is recorded. No generic boundary, outcome, orchestration audit, transaction or resumption change was introduced.

Evidence: [focused assessment](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/bootstrap-audit/assessment.md), [additional controls](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/bootstrap-audit/additional-controls-03.json).

### FR-06: required probe failures reach the enclosing result

At [verify_fr_repairs.py](../../../tools/verify_fr_repairs.py), lines 105–107, pass now requires pytest exit zero and a passing standalone probe. Actual `main()` derives its nonzero command result from this aggregate. The raw `exit_code` continues to mean the pytest child status, while individual cases, stdout/stderr and full foundation signal records remain available. Thus raw pytest zero alongside an aggregate failure is truthful when the separate probe failed.

The unchanged wheel guard rejects a failed repair aggregate before emitting successful wheel JSON. The unchanged platform runner retains the failed command/report and returns nonzero. The five regression cases exercise actual production aggregation/CLI and both wrapper boundaries using completed controlled child observations, rather than testing an isolated Boolean helper.

An additional independent probe exercised five pytest/probe combinations in both source-tool and application-only selection modes. All **10 repaired controls pass**. The unchanged baseline falsely passes failed and unavailable probe results with successful pytest in both modes, reproducing four false passes. The five submitted FR-06 cases were also independently rerun directly and passed. These injections verify result aggregation; they do not claim an actual application signal failure.

Evidence: [focused assessment](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/tooling-audit/assessment.md), [independent controlled results](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/tooling-audit/aggregation-controls.json).

## Verification and evidence assessment

The same final 67-case assertions independently reproduce **four baseline failures and 63 passing controls on each platform**: normal recorded-audit metadata, failed-probe aggregation, wheel rejection and platform propagation fail on the old implementation. Baseline application/tool imports are bound to the old extraction; repaired implementation modules were not substituted into it.

All **93 submitted indexed artifacts** were independently checked by hash/length. Both retained submitted wheels have **37 source-backed members** matching the candidate. Identical before/after test bytes, distinct baseline/source/site-packages imports, actual audit rows and raw controlled aggregation excerpts agree with the submitted handoff. Actual standalone foundation signal records were checked independently and kept separate from injected failures.

Fresh Windows verification completed 14 commands, all exit 0, with **338 pytest passes in 145.74 seconds**, 67 source and 42 clean-installed application repair cases. Fresh Linux verification also completed 14 commands, all exit 0, with **336 pytest passes plus one skip in 221.45 seconds**, 67 source and 42 clean-installed application repair cases. Both matrices verified captured source unchanged afterward.

The Linux source and installed Worker suites each passed 76 records, including seven retained Increment 4 repair cases. Nine separate installed execution signal cases passed on each platform. Every actual standalone foundation signal result was independently inspected and passed. Final checks verified all 143 candidate and 139 baseline source entries and found no remaining fixture containers on the verified Engine.

See [validation](VALIDATION.md) for source binding, commands, raw results, preservation, environment attempts and limitations.

## Acceptance boundary

This independent reassessment is complete. Designated repair acceptance remains a separate human decision. Historical Increment 1–4 acceptance scopes remain unchanged. No actual Agent was enabled or qualified by this work; Increment 5, live provider/forge behavior and production Linux qualification are outside this review.
