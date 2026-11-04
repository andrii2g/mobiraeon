# Replay repair validation and preservation

The repaired source is frozen in the [204-file manifest](evidence/repair-source-manifest.json). The [pre-repair manifest](evidence/baseline-manifest.json) preserves the original dirty state and source hashes. Both ZIPs, controllers, raw outputs and the original unnormalized diff remain in `C:\Users\andrey\Documents\Mobiraeon-Recovery\increment-5-replay-repair-20261104-01`. No previous archive was overwritten.

## Actual checks

- [Baseline regression](evidence/red-results.json): pytest exit 1, exactly one causal failure and one passing authority control. The [outer observer](evidence/red-outer.json) exits 0 because this expected failure was verified. Its production code is identical to the preserved pre-repair baseline; the causal test matches the final test.
- [Native repair checks](evidence/green-results.json): all 14 commands exit 0, including 18 new cases, the 747-test full suite, lint/format/build, locked runtime/test installation, both runtime Forge modes and 218 installed affected tests. [Actual native owner exit](evidence/native-outer.json): 0.
- [Windows full suite](evidence/windows-results.json): 745 passed, four expected skips, actual exit 0. [Windows lint/format/build](evidence/windows-checks.json): all exit 0; all 55 wheel members match the manifest. Frozen source hashes match before and after both platform runs.
- [Source Forge runtime](evidence/source-forge.json) and [installed Forge runtime](evidence/installed-forge.json): each passes all 10 checks. Runtime-only installed identity is observed before adding test dependencies; pytest, Ruff and cryptography are absent then. Imports resolve into the noneditable installed environment, outside the source checkout, with no source `PYTHONPATH`.

Linux source, Python executable/base/stdlib, uv, cache, temporary state, controllers and reports resolve to ext4 under `/home/andrey/work/mobiraeon-increment-5-20261104-01/replay-repair-20261104-01` or its established native toolchain parent. Initial inputs are staged before execution; completed exports are byte-identical. No old native source or report directory was reused for output.

One [Windows setup attempt](evidence/windows-setup-attempt01.json) stopped before pytest because hardening its newly created root was refused. Its script/result remain preserved; the empty root was removed nonrecursively. The successful run used a fresh protected child of the existing qualified owner root, without changing any old ACL. No repaired-source test failure was retried, timeout increased or return value forced. [New Ruff cache relocation](evidence/windows-working-cleanup.json) keeps generated output outside the checkout.

## Independent assessment and completion scope

The [source assessment](evidence/independent-source-assessment.json) precedes final gate completion and retains its pending status. The separate [final assessment](evidence/independent-final-assessment.json) verifies completed raw reports and exact repaired-file hashes. The assessor authored neither the product repair nor its tests. The current technical completion decision follows this final assessment; historical results are not rewritten.

The [baseline/scope comparison](evidence/baseline-and-scope.json) verifies all 22 original full-review indexed files unchanged and records the 53 unchanged packaged inputs. Previously qualified live Gitea/Worker paths and controls are unchanged; their original final-11 evidence remains valid within its original attribution and limits. This is an incremental repair closure under the implementation plan's affected-check requirement, not a new full live-provider/Worker qualification claim.

After checks, only maintained status/navigation and new closure documentation are updated. [Final integrity verification](evidence/final-integrity.json) records the final allowlist, preserved original review bytes, unchanged tested product/test hashes, source/doc archive identities, link validation and Git state. `evidence-index.json` seals this new review. No commit, push, deployment, production state change or human acceptance is recorded.
