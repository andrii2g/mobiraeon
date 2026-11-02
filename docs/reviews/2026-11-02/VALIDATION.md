# Full review validation

Reviewed commit: `7a386fe69c6e2c5bb7ee32d17ecdb2773e0f2491`; source archive SHA-256 `91e6a9ef1ffbf5b897ca7e56bf9eac87f5e7307a74c357904986bce94ce87aed`, 128 files. The starting checkout was clean. Source was captured before adding these review documents; generated environments/probes are excluded and no implementation file is edited.

## Fresh material checks

- Windows: all 13 platform commands passed; full pytest **271 passed in 87.42 seconds**; locked sync, Ruff check/format, build, clean installed wheel, Registry/TLS, Coordination, portable execution/signals and native foundation/API interruption checks passed. Native Linux Worker execution is explicitly unavailable on Windows.
- Linux/WSL: full pytest **269 passed, 1 skipped in 166.65 seconds**; locked sync, Ruff check/format, build, Registry/TLS, Coordination and native interruption checks passed.
- The first Linux invocation omitted the required fixture image argument. Its clean-wheel and source Worker commands stopped with `prepared fixture image ID required for Linux verification`. Those initial nonzero results are retained and are not product findings. Both affected commands passed with the corrected image argument: the clean installed-wheel check in 525.90 seconds and source Worker check in 406.12 seconds. Both real Worker suites passed 76 driver records including seven repair cases each; the installed wheel separately passed all nine signal cases. Together with the initial 11 successful commands, all 13 required Linux checks passed. Both source trees remained unchanged after checks.

Raw records: [Windows platform report](../../../submissions/full-review-20261102-01/windows-verification.json), [initial Linux platform report](../../../submissions/full-review-20261102-01/linux-verification.json), [corrected Linux fixture checks](../../../submissions/full-review-20261102-01/linux-fixture-checks.json), [source manifest](../../../submissions/full-review-20261102-01/source-manifest.json),
[installed Worker detail](../../../submissions/full-review-20261102-01/execution-installed.json) and
[source Worker detail](../../../submissions/full-review-20261102-01/execution-source.json).

The fixed image is `sha256:0a8b7aa53e80af9edebaa8ea21803b9b70ee9325a16751c7dd6a1465c8a5f8f8`, Engine `0fc089f8-7374-43a4-a1aa-7381a79669e6`. Existing images/runtime were reused; there was no pull, rebuild, publication or infrastructure upgrade.

## Independent focused reproductions

| Finding | Method and observed result |
| --- | --- |
| FR-01 | Real SQLite/Access/Coordination with a trusted Worker transport-fault double seals successful output despite final exit 137. Three controls distinguish terminal-zero, terminal-nonzero and running/default-zero behavior. A separate real Docker probe confirms attach-client loss leaves the container running/default-zero and retires only its own container. |
| FR-02 | Fresh protected temporary store outside checkout; CLI preparation commits one publication before a late missing reference returns invalid input and no progress metadata. No credential values were recorded. |
| FR-03 | Bounded actual-handler subprocess probes on Windows and Linux; four nested signal combinations per platform deadlock, controls pass, every child is killed/reaped. |
| FR-04 | Direct configuration resolver plus real CLI subprocesses; three malformed configurations report uncertainty before any database creation, while an ordinary invalid-input control is correctly classified. |
| FR-05 | Exact capture tool in a small isolated Git fixture; unstaged deletion fails with a partial archive/no manifest, restored-file control passes. Only the fixture receives a synthetic initialization commit. |

Diagnostic test passes mean the observed defect was reproduced; they are not repair verification. Initial protected-store/sandbox-refused execution-probe attempts are retained alongside the final successful diagnostic runs and do not establish findings themselves.

## Documentation, preservation and limits

The initial documentation audit passed 51 Markdown files and 221 local fragment links, including infrastructure/bootstrap material. Including the new review documents, the cross-audit passed 53 Markdown files and 223 local fragment links. Final file-link, whitespace, source and preserved-evidence checks are recorded in the [validation summary](../../../artifacts/full-review-20261102-01/validation-summary.json) and [artifact hash index](../../../artifacts/full-review-20261102-01/artifact-index.json). The integrity check verified all 27,619 files in the prior evidence inventory and all 57 indexed files from the final Increment 4 reassessment remain byte-identical. All 128 captured files remain unchanged except the documentation catalog navigation; implementation code, tests and tools match the reviewed source. No Run-owned fixture container remains after verification.

Existing Increment submissions/reviews/acceptance records are preserved. The review adds only its durable Markdown records/navigation; raw captures, probes, logs and environments remain in ignored `submissions/full-review-20261102-01/` and `artifacts/full-review-20261102-01/`. No project commit or push is authorized or performed for this review.

Linux/WSL is the exercised development environment, not production Linux qualification. No real Agent was enabled, no provider/model or live Gitea operation was performed, and no production deployment, network-filesystem/distributed locking, power-loss/disaster recovery, hostile OS defense, external dependency-vulnerability audit or latest-release compatibility was qualified. Static Compose/bootstrap inspection does not establish live forge health. Existing test success does not cover the new failure cases identified in the review.
