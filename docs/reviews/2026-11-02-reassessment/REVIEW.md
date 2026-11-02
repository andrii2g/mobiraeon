# Independent full review of the FR-01–FR-05 repair

Date: 2026-11-02 (Europe/Kiev). Candidate: `submissions/repair-fr-01-fr-05/final-02`.

**Changes required: one residual P2 and one new P2.** FR-01, FR-03, FR-04 and FR-05 are resolved within the reviewed scope. FR-02's partial-effect/progress repair works, but its audit-availability metadata remains inaccurate. The new regression verifier can also hide a failed standalone signal subcheck. Designated repair acceptance remains pending.

This is a separate review. The [original findings](../2026-11-02/REVIEW.md), [original validation](../2026-11-02/VALIDATION.md), developer handoffs, earlier attempts and historical Increment acceptance records remain preserved. No implementation changes, project staging, commit or push were performed.

## Exact source and scope

The submitted archive contains **139 files**, independently verified entry by entry, with SHA-256:

```text
56dc16b8a08cc3bb36c4eb067250bd97a1de61a98f825e756920b2fb1bd79bc6
```

Its manifest SHA-256 is `5b3381e0bfcc2dc7a5232bb80105b2f290892ece6458eb6b13ee2b13baa1929f`; `deleted_paths=[]`. Git base/starting revision is `7a386fe69c6e2c5bb7ee32d17ecdb2773e0f2491`. The active checkout matched every candidate file before review-document changes; there was no implementation drift.

The independently extracted original baseline is the 128-file archive `91e6a9ef1ffbf5b897ca7e56bf9eac87f5e7307a74c357904986bce94ce87aed`. The combined candidate differs by 18 modified files and 11 additions; those additions include the three supplied review/brief documents as well as eight new repair test/tool files. The project/lock/runtime pins, migrations 0001–0004, Coordinator authority/receipt implementation, Access/API/catalog/transaction boundaries, fixed fixture build assets and initial catalog remain unchanged.

This review assesses the captured `docs/implementation-instructions.md` in the [reviewed source archive](../../../submissions/repair-fr-01-fr-05/final-02/source.zip), maintained execution/Registry/Coordination contracts, changed implementation, regression harness, documentation and exact submitted evidence. Unchanged boundaries were checked for interactions with the repair. It does not start Increment 5 or qualify ordinary Agents or production deployment.

## Findings requiring repair

### FR-02-R1 — P2: preserve the child's actual audit availability

Location: [bootstrap.py](../../../src/mobiraeon/bootstrap.py), line 83; aggregate propagation at lines 47–49. Related existing service semantics: [catalog.py](../../../src/mobiraeon/catalog.py), `_attempt_audit()` at lines 136–150.

The preparation wrapper currently maps an absent child `result.data` to `audit_status="unavailable"`. However, normal failed Registry operations return no business data after successfully recording their failure audit. `_attempt_audit()` adds explicit unavailable metadata when audit writing fails; missing business data does not establish such a failure.

A fresh real protected installation with one complete instruction followed by an incomplete instruction reproduced the mismatch without mocking RegistryService or audit storage. The first publication and second draft committed. The second `registry.validate` returned `known_failure/incomplete_definition`, and a matching `registry_audit` row existed for that exact child invocation. Both the failed progress step and top preparation result nevertheless reported audit unavailability.

The mutation outcome and retained publications were correctly reported; no missing audit record or authorization bypass was demonstrated. The residual defect is false audit-outage metadata, violating FR-02's explicit requirement to retain truthful child audit availability and potentially sending callers into unnecessary audit-outage handling.

Required correction: preserve the child's established audit semantics, including successful failure-audit recording when business data is absent. Retain explicit genuine audit unavailability. Add a real normal-failure/audit-success control beside the existing outage case, asserting the child invocation's actual audit row, step metadata and aggregate status.

Evidence: [assessment](../../../submissions/independent-full-review-fr01-fr05-20261102-01/bootstrap-config-audit/assessment.md), [real CLI/audit mismatch](../../../submissions/independent-full-review-fr01-fr05-20261102-01/bootstrap-config-audit/real-failure-audit-status.json).

### FR-06 — P2: propagate a failed standalone signal check to verifier failure

Location: [verify_fr_repairs.py](../../../tools/verify_fr_repairs.py), line 102, after the standalone probe at line 88; CLI exit at line 133. The [wheel verifier](../../../tools/verify_wheel.py) trusts this outer repair result.

The harness executes pytest and a separate `foundation_signal_verification.exercise()`, but computes its overall result only from pytest's exit code. Therefore a standalone signal probe can report failure while the enclosing result says `passed` and the command exits 0.

A bounded controlled aggregation probe called the actual unmodified `main()` with completed child results. With an injected successful pytest result containing 60 case records and one failed standalone nested-signal case, `main()` returned 0 and emitted `passed`. A failed-pytest/passing-signals control returned 1/failed; an all-pass control returned 0/passed. The probe changes only trusted test inputs to the aggregator; it does not claim that a real application signal check failed.

All actual submitted and freshly inspected signal results pass. This finding does **not** invalidate those observed passes or reopen the repaired signal handler. It is a new verification-tool defect: a future independently failed subcheck can be hidden by the enclosing source/wheel report.

Required correction: aggregate pytest and standalone signal results consistently into the reported result and CLI exit. Test failed-probe/passing-pytest, failed-pytest/passing-probe and all-pass combinations, including the wheel verification boundary. Preserve subcheck details rather than dropping failed evidence.

Evidence: [tooling assessment](../../../submissions/independent-full-review-fr01-fr05-20261102-01/tools-evidence-audit/assessment.md), [actual main and three controls](../../../submissions/independent-full-review-fr01-fr05-20261102-01/tools-evidence-audit/result-aggregation-v2.json). The earlier one-case aggregation probe is preserved separately.

## Original finding dispositions

| Finding | Independent disposition | Evidence and limits |
| --- | --- | --- |
| FR-01 | Resolved | Pre-cleanup terminal completion and attachment status are separate from cleanup state. Success requires terminal-zero execution, valid complete capture, verified cleanup and existing stop/generation gates. Seven supplied cases pass; six additional real-store controls cover missing/zero finish time, missing Running, boolean exit code, established nonzero failure and normal success. Cleanup-zero cannot create success. |
| FR-02 | Partially resolved | Reference preflight, per-operation/partial-definition progress, retained receipts and CLI effect classification work. Extra late generic error and mutating-response-loss controls agree with real database state. FR-02-R1 above remains. |
| FR-03 | Resolved | The foundation callback only assigns pending intent. Both handlers return under actual nested delivery; external stop, exceptional restoration, fresh scopes and native interruptions are retained. Three additional scope/stop/restoration controls pass. This remains separate from the already fixed execution signal handler. |
| FR-04 | Resolved | URL/deferred-port and numeric failures safely report invalid configuration with narrow source/setting attribution. Eight extra invalid URL-port cases across file/environment and two valid URL controls pass, in addition to supplied CLI/resolver regressions. |
| FR-05 | Resolved | Present files and sorted deletions remain distinct; HEAD/index/present checkout, legacy manifests, read-error handling, fresh extraction and stale-file rejection are covered. Two additional real Git cases pass: staged deletion followed by a working replacement, and an index-only added file subsequently removed. Only disposable fixtures receive fixture commits. |

Extra audit evidence: [execution controls](../../../submissions/independent-full-review-fr01-fr05-20261102-01/execution-audit/assessment.md), [bootstrap/configuration controls](../../../submissions/independent-full-review-fr01-fr05-20261102-01/bootstrap-config-audit/assessment.md), [capture/evidence controls](../../../submissions/independent-full-review-fr01-fr05-20261102-01/tools-evidence-audit/assessment.md).

## Verification and evidence assessment

On each platform, the identical 60-case expectations independently produced **30 expected baseline failures and 30 passing controls**. Group failures were FR-01: 3, FR-02: 10, FR-03: 4, FR-04: 8 and FR-05: 5. The actual baseline imports were checked; the candidate/external harness did not substitute repaired application code for the baseline.

The submitted evidence audit independently verified all 129 indexed artifacts and both retained wheels' 37 source-backed members against the captured source. Test hashes and actual baseline/source/site-packages imports agree across the submitted before/after and installed reports. Every actual standalone signal record was checked separately rather than trusting the defective outer aggregation. No discrepancy in those reported passes was established.

Fresh Windows reproduction completed **14 commands, all exit 0**, with **331 pytest passes in 117.10 seconds**, 60 source repair cases and 40 installed application repair cases. Fresh Linux reproduction also completed **14 commands, all exit 0**, with **329 pytest passes plus one skip in 222.51 seconds**, 60 source repair cases and 40 installed application repair cases. Both platform matrices left the captured source unchanged.

The fresh Linux source and installed Docker suites each passed 76 records, including seven retained Increment 4 repair cases. Nine separate installed execution signal cases passed. Actual standalone foundation signal records were checked independently of the faulty aggregate result and all passed. Final checks verified the 139-file candidate and 128-file baseline extractions and found no remaining fixture containers.

See [validation](VALIDATION.md) for exact commands, platform results, preservation and scope limits. Passing existing suites does not resolve the two independent findings above.

## Recommendation

Repair FR-02-R1 and FR-06 in a small follow-up, add their controls, rerun affected and required source/installed checks, and submit a new frozen candidate for independent reassessment. Keep the original reviews/evidence unchanged. No broader architecture change or Increment 5 implementation is required to fix these issues.

Historical Increment 1–4 acceptances retain their recorded meaning. This repair's designated acceptance remains pending. All five actual Registry Agents remain disabled/unqualified, and the high-level Increment 5 proposal remains unimplemented.
