# Review-first cleanup and preservation

The full review decision was recorded before cleanup. It requests one P2 replay repair; cleanup did not change implementation code or claim that the finding was resolved.

The external archive is `C:\Users\andrey\Documents\Mobiraeon-Recovery\full-review-cleanup-20261104-01`. An exact copy of all 191 original reviewed source files, plus the original ZIP/manifest, was hash-verified there before cleanup.

## Completed cleanup

- Moved `submissions/`, `artifacts/`, `dist/`, root pytest/Ruff caches, the obsolete Windows-mounted Linux toolchain, mixed/regression environments and six one-off `.tools` scripts out of the checkout: 14 explicit allowlisted roots in total.
- Retired 12 obsolete Increment 5 implementation, completion, repair and status/recovery documents only after verifying their original archived copies.
- Updated maintained README/catalog/plan/forge-contract navigation. Added the lasting [verification guide](../../verification.md) and [archive catalog](../../evidence-archive.md).
- Retained maintained source, regression tests, verification/control modules, domain-Agent roles, bootstrap/examples, infrastructure, `.git`, the active Windows virtual environment and its Python/uv/cache dependencies. No production data, credentials, service or Agent configuration was altered.

All moves used verified absolute paths on the same volume. Destination paths were absent; nothing was overwritten. No old ACL was changed. Original historical review and acceptance document bytes remain unchanged. Active navigation opens their archived mirrored originals so their original relative evidence links remain usable.

## Integrity results and limits

Default and owner contexts inventoried and then rechecked the relocated trees. Their union verified **87,363 distinct readable files, 4,230,367,527 bytes**, with **zero hash mismatches**. All 14 root directory/file identities remained unchanged. All 191 original source copies still match; all 55 packaged source files and the other retained non-documentation inputs remain unchanged in the checkout.

There were **1,198 pre-existing access-error paths common to both inventory contexts**. Their inaccessible contents are not claimed byte-verified. They were preserved by relocating their whole roots without ACL changes, with unchanged root identities. This is separate from the smaller final-11 qualification's historical cache-access count.

[Compact verification](evidence/cleanup-verification.json) records the exact path allowlist, retired documents, preserved source, Git state and full-manifest hashes. Complete before/after manifests and move receipts are retained under the archive's `.preservation/cleanup-working/`; their original pre-move copies are also retained in `.preservation/`.

The only edits to existing maintained source files are documentation: root README, documentation catalog, implementation plan and forge-contract introduction/navigation. The 12 retired briefs are preserved externally. New review records and verification/archive guides are additional documentation. The source ZIP remains the original pre-cleanup snapshot and is not presented as containing these later documentation changes.

HEAD and empty staging remain unchanged. No commit, push, deployment, human acceptance or product fix occurred. The separate earlier full recovery backup and final-11 completion backup were not overwritten.

The [post-cleanup build](evidence/cleanup-build.json) passes with all 55 packaged source files unchanged and all 111 maintained source/test/tool/bootstrap/example inputs in the source distribution. Retired briefs and generated work trees are absent from that distribution. [Final validation](evidence/final-validation.json) records documentation-link, source and Git checks. Large raw inventories remain external; the compact source-manifest derivative retains every original source entry and points to the untouched full manifest.
