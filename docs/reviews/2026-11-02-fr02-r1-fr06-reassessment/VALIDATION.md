# Independent FR-02-R1 / FR-06 validation

Date: 2026-11-02 (Europe/Kiev). Findings: [reassessment](REVIEW.md).

## Snapshot and commands

Candidate: `submissions/repair-fr02-r1-fr06/final-01`, 143 files, archive SHA-256 `b36f8afa6eb0bc212d2ce87e37727b8daed25f8210443a4daa86c2e0eed72464`, manifest SHA-256 `9b39407591171d71b9e933fa0755d95db389586f9863ed88c37ef8ccaad04ef4`, no declared deletions. [Starting state](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/starting-state.json) records Git revision/status, source hashes, empty staging and the exact baseline delta. Every captured entry and active starting checkout file was checked.

Windows and Linux each use a fresh native extraction of this same archive and an isolated locked environment. All new evidence is under `submissions/independent-reassessment-fr02-r1-fr06-20261102-01/`; prior directories are inputs only. Platform launchers: [Windows](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/run-windows.py), [Linux](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/run-linux.sh). They run the captured `tools/verify_platform.py` with the original candidate manifest and a new external report path.

The shared runner covers locked sync, full pytest, Ruff checks/formatting, build, source repair regressions, clean installed wheel, Registry/TLS, Coordination, source/installed native interruptions and Worker verification. Installed application checks run outside the checkout beneath `100%valid`, without application-source `PYTHONPATH`. The fixture image argument is passed through the wheel boundary.

## Fresh results

| Check | Independent result |
| --- | --- |
| Windows full matrix | 14 commands, all exit 0; captured source unchanged. |
| Windows full pytest | 338 passed in 145.74 seconds. |
| Windows source / installed application regressions | 67 / 42 passing cases. |
| Linux full pytest | 336 passed, one skip in 221.45 seconds. |
| Linux full matrix | 14 commands, all exit 0; captured source unchanged. |
| Linux source / installed application regressions | 67 / 42 passing cases. |
| Linux source / installed Worker suites | 76 passing records each, including seven retained Increment 4 repair cases in each suite. |
| Installed execution signal cases | Nine pass on each platform; actual standalone foundation observations also independently inspected and pass. |
| Identical baseline regressions | Each platform: four expected failures and 63 passing controls. |
| Additional FR-02-R1 controls | Two independent real-store cases pass. |
| Additional FR-06 controls | Ten repaired combinations pass; four old false passes reproduced. Five supplied production aggregation/wrapper cases additionally pass. |

Raw platform reports: [Windows](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/windows-verification.json), [Linux](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/linux-verification.json). Fresh unchanged-baseline records: [Windows](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/baseline-windows.json), [Linux](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/baseline-linux.json). The baseline launcher intentionally expects verifier exit 1 from the four reproduced failures; launcher success does not classify those baseline tests as passing.

Collected results: [platform/source bindings](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/verification-summary.json), [identical regression comparison and independently checked signals](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/regression-comparison.json), [source Worker](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/execution-source.json), [installed Worker](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/execution-installed.json). Fresh retained build hashes and both wheels' 37 source-backed members are checked against the candidate in the [final validation summary](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/validation-summary.json). The [artifact index](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/artifact-index.json) binds these new review records and evidence.

Focused reviews: [bootstrap audit](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/bootstrap-audit/assessment.md), [tooling audit](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/tooling-audit/assessment.md), [submitted evidence/source audit](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/evidence-audit/assessment.md).

Actual signal observations are inspected independently of outer aggregate status. Controlled failed observations in FR-06 prove failure propagation and remain explicitly labelled as injected observations. No actual signal failure is inferred from them.

## Preservation and environment attempts

The [combined preservation comparison](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/preservation-verification.json) verifies **67,466 distinct prior files unchanged** across two read contexts. The restricted inventory covered 67,406 files; the native inventory covered 67,392. Their shared file hashes agree, and complementary access covers the historical directories inaccessible in either single context. No directory was inaccessible in both inventory contexts; no ACL or ownership changes were made. Both comparisons also verify every starting source file unchanged, along with Git HEAD, staging and hooks.

The initial Windows launcher was denied execution of cached uv by the restricted sandbox before verification started. Its [stderr](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/windows-launch.stderr) is preserved; the authorized native rerun succeeded. No failed verification was relabelled as a pass. Linux/WSL checks use the authorized native context and existing tool caches.

Earlier bootstrap control attempts are preserved in the focused audit directory: an inherited inaccessible pytest-cache path and an independent assertion spelling error were corrected in a new `_03` harness/output. The [focused assessment](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/bootstrap-audit/assessment.md) explains those attempts. No application changes were made to accommodate the independent tests.

Existing image `sha256:0a8b7aa53e80af9edebaa8ea21803b9b70ee9325a16751c7dd6a1465c8a5f8f8` and Engine `0fc089f8-7374-43a4-a1aa-7381a79669e6` were checked with unchanged fixture asset hashes before Worker execution. No image rebuild/pull, daemon replacement, Gitea change, provider call or Agent enablement occurred. [Final Linux state](../../../submissions/independent-reassessment-fr02-r1-fr06-20261102-01/linux-final-state.json) verifies both 143/139-file source extractions, the same Engine, fixture build-input label and no remaining fixture containers. Final source, Git and documentation checks are included in the validation summary.

## Limits

This is a focused repair reassessment against the follow-up brief, not a new production security/dependency or live-pilot qualification. Native Windows Worker execution remains explicitly unavailable; actual Worker enforcement is checked under Linux/WSL. WSL does not establish production Linux qualification. Historical acceptance records retain their scope. Designated repair acceptance and Increment 5 implementation remain pending. Implementation and all prior reviews/evidence remain unchanged; this review creates only new review documents and evidence, with no staging, commit or push.
