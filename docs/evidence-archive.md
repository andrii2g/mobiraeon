# Historical evidence archive

Obsolete developer briefs, submission trees and raw review/build artifacts were retired from the checkout after the [2026-11-04 full review](reviews/2026-11-04-increment-5-full/REVIEW.md). Their original bytes and relative layout are preserved outside Git. Maintained source, tests/tools, domain-Agent roles, contracts, examples, infrastructure and current review records remain in the repository.

Archive root on this workstation:

```text
C:\Users\andrey\Documents\Mobiraeon-Recovery\full-review-cleanup-20261104-01
```

It mirrors the original 191-file reviewed source at its root, plus relocated `submissions/`, `artifacts/`, obsolete build/cache output and retired `.tools` baseline material. The original source ZIP and manifest are under `.preservation/`. [Cleanup verification](reviews/2026-11-04-increment-5-full/CLEANUP.md) records actual moved paths, integrity results and access limitations.

| Historical reference | Archived location beneath that root |
| --- | --- |
| `submissions/...` | `submissions/...`, unchanged relative layout |
| `artifacts/...` | `artifacts/...`, unchanged relative layout |
| Retired Increment 5 developer briefs/repair notes | Original `docs/...` paths |
| Original historical reviews/acceptance records | Original `docs/reviews/...` paths |
| Latest final-11 source/evidence | `submissions/increment-5/final-11/` |
| This full review's raw probes/checks | `artifacts/full-review-increment5-20261104-01/` |

Historical review and acceptance documents in the repository retain their original text, counts, decisions and evidence-relative URLs. Active documentation links to these versioned repository records. Their raw `submissions/` and `artifacts/` targets are outside the checkout: open the mirrored archived document to follow its original relative evidence links against the preserved tree. The two latest Increment 5 reviews also retain compact evidence in their repository `evidence/` directories.

The workstation paths in this catalog identify preserved local evidence; a fresh clone does not contain those external archives. Reading the maintained contracts and current review records does not require that drive layout. When transferring historical raw evidence to another workstation, preserve the archived relative tree and verify its saved manifests.

The earlier `increment-5-20261104-01` recovery backup and the separately verified `increment-5-final-11-20261104-01` source/completion backup remain unchanged alongside this archive. The latter includes a verified 462-member completion export. This cleanup archive preserves the broader historical workspace, not only final-11.

To recover old material, copy the required archived paths into a **new** directory and verify them against the saved manifests. Restore an exact old absolute layout only deliberately: historical virtual environments and reports contain original absolute paths and are not newly qualified portable installations. Do not overwrite current source or run obsolete instructions as active assignments.

The two sealed Increment 5 review directories have explicit Git `-text` attributes. Their evidence indexes must continue to match the original file bytes on every platform; do not regenerate them or normalize their line endings during documentation maintenance.

The historical full review recorded one P2 exact-replay classification defect. The [final repair reassessment](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md) closes it against a new frozen source. Its baseline, repaired source ZIP, raw controllers/results and preservation receipts are under `C:\Users\andrey\Documents\Mobiraeon-Recovery\increment-5-replay-repair-20261104-01`; neither earlier backup is overwritten. Technical closure does not record human acceptance, commit/push or deployment authorization.
