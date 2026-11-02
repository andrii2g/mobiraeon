# Independent repaired-repository validation

Date: 2026-11-02 (Europe/Kiev). Review: [independent full review](REVIEW.md).

## Snapshot and preservation

Candidate `repair-fr-01-fr-05/final-02` has 139 files, archive SHA-256 `56dc16b8a08cc3bb36c4eb067250bd97a1de61a98f825e756920b2fb1bd79bc6`, manifest SHA-256 `5b3381e0bfcc2dc7a5232bb80105b2f290892ece6458eb6b13ee2b13baa1929f`, and no declared deletions. Every zip entry's path/hash/length and the active starting checkout were verified. Starting Git revision remains `7a386fe69c6e2c5bb7ee32d17ecdb2773e0f2491`.

[Starting state/delta](../../../submissions/independent-full-review-fr01-fr05-20261102-01/starting-state.json) binds the current uncommitted source. The [prior evidence inventory](../../../submissions/independent-full-review-fr01-fr05-20261102-01/prior-evidence-inventory.json) records **59,300 readable existing evidence files** before verification and four inaccessible historical directories. The [final preservation comparison](../../../submissions/independent-full-review-fr01-fr05-20261102-01/preservation-verification.json) verified all 59,300 readable files unchanged. No ACL/ownership changes or attempts to remove those directories were made; unreadable contents cannot be claimed byte-verified. All 138 candidate files outside the documentation catalog remained unchanged. Only the new review documents and catalog navigation were added; Git HEAD and staging remain unchanged.

## Fresh material checks

| Check | Current independent result |
| --- | --- |
| Windows full matrix | 14 commands, all exit 0; source unchanged afterward. |
| Windows full pytest | 331 passed in 117.10 seconds. |
| Windows repair source / clean installed wheel | 60 / 40 passing cases; standalone signal observations separately inspected. |
| Linux full pytest | 329 passed, 1 skipped in 222.51 seconds. |
| Linux full matrix / source and installed Docker | 14 commands, all exit 0; source unchanged. Both Docker suites passed 76 records including seven retained Increment 4 repair cases. |
| Linux repair source / clean installed wheel | 60 / 40 passing cases; nine installed execution signal cases passed. |
| Identical baseline comparison | Each platform: 30 expected failures and 30 passing controls across 60 cases. |

Raw independent records: [Windows platform](../../../submissions/independent-full-review-fr01-fr05-20261102-01/windows-verification.json), [Linux platform](../../../submissions/independent-full-review-fr01-fr05-20261102-01/linux-verification.json), [Windows baseline](../../../submissions/independent-full-review-fr01-fr05-20261102-01/baseline-windows.json), [Linux baseline](../../../submissions/independent-full-review-fr01-fr05-20261102-01/baseline-linux.json), [Linux launcher](../../../submissions/independent-full-review-fr01-fr05-20261102-01/run-linux.sh).

Collected results: [platform summary](../../../submissions/independent-full-review-fr01-fr05-20261102-01/verification-summary.json), [identical regression comparison and standalone signal checks](../../../submissions/independent-full-review-fr01-fr05-20261102-01/regression-comparison.json), [source Docker](../../../submissions/independent-full-review-fr01-fr05-20261102-01/execution-source.json), [installed Docker](../../../submissions/independent-full-review-fr01-fr05-20261102-01/execution-installed.json), [final Linux source/runtime state](../../../submissions/independent-full-review-fr01-fr05-20261102-01/linux-final-state.json).

The two platforms use fresh native extractions of the same archive and existing locked tool caches. Installed checks run outside the checkout beneath `100%valid`, with actual module paths and source import isolation recorded. No provider credentials or new owner-selected values are needed or used.

Existing image `sha256:0a8b7aa53e80af9edebaa8ea21803b9b70ee9325a16751c7dd6a1465c8a5f8f8` and Engine `0fc089f8-7374-43a4-a1aa-7381a79669e6` are reused after unchanged fixture-input verification. There is no image pull/rebuild/publication, daemon replacement or Gitea infrastructure change.

## Focused independent controls and findings

- FR-01: six additional real-store completion edge controls pass; FR-03: three additional signal/external-stop/restoration controls pass.
- FR-02/FR-04: thirteen extra controls pass (three late bootstrap-error/response-loss paths, eight invalid deferred URL-port cases and two valid URL controls). A separate real-store diagnostic reproduces FR-02-R1's false audit-unavailability report.
- FR-05: two additional isolated Git/capture edge cases pass. Submitted evidence audit checks 129 indexed artifacts, both wheels' 37 source-backed members and before/after import/test identity.
- FR-06: controlled aggregation calls the actual verifier `main()` in three combinations. Passing pytest plus a failed standalone signal check incorrectly returns 0/passed; failure and all-pass controls behave as documented. This is not an actual runtime signal failure.

Diagnostic passes that assert a defect mean the defect was reproduced, not repaired. Source/installed signal reports are examined independently because the new outer verifier result has the aggregation defect described in FR-06. The actual recorded signal checks pass.

## Documentation and limitations

The documentation audit verified 223 fragments. Final Markdown fence, local file-link and whitespace checks, platform/source bindings and preservation results are recorded in the [validation summary](../../../submissions/independent-full-review-fr01-fr05-20261102-01/validation-summary.json). The [artifact index](../../../submissions/independent-full-review-fr01-fr05-20261102-01/artifact-index.json) binds the new review records and evidence. New review records/navigation are the only project edits. Implementation code, original full-review Markdown, briefs and all submitted source/evidence remain unchanged; no project staging, commit or push was performed.

Expected Windows Worker unavailability and native console/readiness context limits remain explicit. Linux/WSL is development evidence, not production Linux qualification. No real Agent is enabled, no provider/model or live forge call is made, and no distributed storage, hostile OS, power-loss/disaster recovery, dependency-vulnerability or latest-release compatibility audit is claimed. Repair acceptance and Increment 5 implementation remain pending.
