# Full-review validation

The [review decision](evidence/review-decision.json) was recorded before cleanup. It identifies one reproduced P2 replay-classification defect; passing existing tests does not override that finding.

| Check | Actual result |
| --- | --- |
| Reviewed source | All 191 final-11 source entries matched the original manifest |
| Fresh native Linux suite | 729 passed, 1 expected skip; actual command exit 0 |
| Lint / formatting / build | Each actual command exit 0 |
| Fresh wheel | Exact 55 source-backed members and bytes verified |
| Replay concurrency probe | Actual controller exit 0; defect observed, `required_behavior=false` |
| Encoding / framing probes | Seven finite cases, actual controller exit 0; two nonblocking robustness observations |

[Fresh commands and full output](evidence/native-review-checks.json), [actual native owner record](evidence/native-review-outer.json), [compact source manifest](evidence/reviewed-source-manifest.json) and [starting state](evidence/starting-state.json) bind this review. The compact manifest retains all 191 source entries and identifies the unchanged original manifest in the external archive; its large nested starting-state inventory remains there. The Linux source, Python/base/stdlib, cache, temporary state and report/controller paths reside under `/home/andrey/work/mobiraeon-increment-5-20261104-01`; active review work did not use `/mnt/c` inputs after staging. Completed reports were exported byte-identically.

The existing final-11 qualification is preserved separately: [summary](evidence/prior-qualification-summary.json), [59-check raw audit](evidence/prior-qualification-audit.json) and [50-check repair closure](evidence/prior-repair-closure.json). Those records retain their original times, archive attribution and scopes. They cover 13/15/15 platform commands, both source/installed 76+30 Worker suites, all applicable repair controls, four production-runtime metadata observations, both 9-assertion/72-route Gitea modes and all 20 fixed Worker cases. This full review reproduced the broad Linux checks and targeted new cases; it did not rerun those live matrices/provider cases.

The replay probe's first two setup attempts refused temporary-directory ancestry before reaching the causal case. The third reached the writer lock but its controller expected the wrong reason spelling (`storage_failure` instead of actual `storage_failed`) before recording the comparison. All failed scripts/results remain in the archive. A distinct observer-only revision captured actual results before assertions and completed the paired reproduction. It did not change production code or force a return value. Temporary test stores/credentials were removed after export.

Two reversed Docker UTC timestamp pairs from earlier certification remain documented with unknown cause. Original monotonic deadline and pre-cleanup completion predicates passed; the earlier extra UTC-order audit assumption and its versioned correction remain preserved. No new clock adjustment or qualification retry was introduced here.

The source snapshot and original documentation were copied and hash-verified externally before cleanup. [Cleanup and archive verification](CLEANUP.md) records exact moved paths, preservation limitations, retained dependencies, documentation-only changes and final Git/source checks. Historical accepted records and reviews keep their original text; use the mirrored archived documents to follow their original relative evidence links after relocation.

Post-cleanup packaging passed. The wheel retains the same 55 source files, and the source distribution includes all 111 maintained source/test/tool/bootstrap/example inputs with no retired briefs or generated work trees. [Final checks](evidence/final-validation.json) verify the local documentation links, including 69 historical links in the unchanged archive mirror. The first cleanup validator incorrectly counted ZIP directory records as files; that failed reviewer attempt and the [correction](evidence/cleanup-validator-correction.json) are retained. No application or build failure occurred.
