# Verification and local evidence

The [forge](forge-contracts.md), [execution](execution-contracts.md), Registry and Coordination contracts define supported behavior. The [full review](reviews/2026-11-04-increment-5-full/REVIEW.md) and [final repair reassessment](reviews/2026-11-04-increment-5-replay-repair/REVIEW.md) record the findings and verified closure. Developer verification, independent review and human acceptance remain separate.

## Exact source and repeatable checks

Record the base revision, dirty tracked/untracked source and a manifest or source archive before checking an uncommitted implementation. Use locked dependencies. Run required checks against that exact source and a noneditable installed wheel outside the checkout, with no source `PYTHONPATH`. Record real command exits and raw subresults; an aggregate must fail when a required child fails. Preserve failed attempts with their original meaning. Choose a fresh output directory rather than overwriting a reviewed snapshot.

The application guide retains commands for tests, lint, formatting, builds, installed-wheel verification, foreground interruption handling and disposable Worker/Gitea checks. `submissions/`, `artifacts/`, caches and build output are generated local work, not maintained source. Historical runs are located through the [archive catalog](evidence-archive.md).

The complete `verify_wheel.py`, `verify_foundation.py` and `verify_platform.py` tools include the current Linux Worker suites. On Linux, first prepare the approved fixture image using a verified local Docker Engine and pass its immutable ID with `--fixture-image-id IMAGE_ID`; native Windows checks instead retain explicit Worker-unavailable results. The `verify_foundation.py --increment` option selects the evidence location rather than an older subset of checks. Default `verify_forge.py` loopback mode needs no Docker or real Gitea; `--real-gitea` deliberately requests separate live-provider qualification.

## Native Linux execution chain

For Linux timing and live fixture qualification, place source, uv, Python executable **and base/standard library**, virtual environments, dependency cache, temporary files, controllers, manifests and active reports on the native Linux filesystem. A `/tmp` virtual environment can still resolve its Python into a Windows-mounted directory; verify actual resolved paths and filesystem types. Do not infer native placement from the working-directory name. Stage inputs before checks and copy completed reports back byte-identically.

The recorded final-11 context is `/home/andrey/work/mobiraeon-increment-5-20261104-01` on ext4. Its same-version CPython toolchain and cache are Linux-local. This identifies a tested environment; it is not a production deployment contract or proof of the historical signal timeout's cause.

On Windows, keep private test installations and temporary candidates outside Git. Protected historical files can be readable in different default/owner tokens. Verify each using the appropriate read context; preserve inaccessible limitations rather than changing old ACLs to force a check to pass.

## Signal-progress and failure evidence

The signal verifier accepts at most **64 nested JSON containers including the root object**. Its quote/escape-aware incremental scanner rejects the 65th before JSON decoding, including without a final newline. The existing 262144-character line/raw-prefix bounds remain. This local progress policy does not change application request, forge or stored Task JSON contracts.

Parser errors preserve the original failure/context/site and stop further parsing while healthy bounded raw collection continues. Physical read, decode and retention failures have separate attribution. Known exits and independent finalizers remain observable; later cleanup cannot replace the original error. Maintained regressions cover moderate nesting boundaries, a small parser fault and actual parent/durable propagation. Historical extreme-input evidence is preserved, not the supported input specification.

The installed execution-signal exercise retains nine cases, its four-second communicate allowance and three-second post-kill safety bound. Additive monotonic anchors locate launch/import/communicate/completion observations without changing success predicates or adding retries. A child completion record alone does not prove process exit and EOF. Minimal signal handlers only record pending intent; synchronized work remains in normal flow.

## Docker and completion evidence

Use a verified immutable direct Docker-client executable, exact Engine identity/destination and prepared image/build-input identity. The last recorded context used `/snap/docker/3618/bin/docker` at SHA256 `32d535f940cf658c82216a31b3440ab65f7cabf554b0e06d563f32846c163f05`. `QUALIFIED_DOCKER_EXECUTABLE` in examples means a freshly verified path; a dispatcher such as `/snap/bin/docker` has a different startup path and is not interchangeable evidence. Revalidate identities after environment changes.

The `mobiraeon.execution_fixture` build/prepare helper discovers `docker` through `PATH`; it has no `--docker-executable` argument. Prepend the verified direct client's parent directory to the Linux `PATH` and confirm that `command -v docker` resolves to the exact qualified executable before building or preparing. Retain that environment when running the full Worker verifiers. The real-Gitea verifier separately accepts `--docker-executable` explicitly.

Keep one real Worker foreground suite at a time. Preserve original startup/execution/grace/cleanup and resource bounds. Completion inspection, parsing, identity checks and predicate admission consume one original absolute monotonic cutoff. Exhausted, late or genuinely missing completion remains unknown. Cleanup state cannot supply earlier business completion or authorize a Coordination result.

UTC is for correlation. Preserve actual Engine timestamp anomalies, but do not subtract UTC lifetimes to manufacture a monotonic allowance. Final-11 retained two reversed UTC pairs; their exact cause remains unknown, while all original monotonic admission predicates passed. Detailed observations remain in the archived qualification.

Real Gitea qualification requires inspected genuine published-loopback use throughout both source/installed scenarios, exact readiness/API checks and verified owned cleanup. A private-container fallback may provide diagnostics but remains incomplete/nonzero qualification. The named `127.0.0.2` fixture route does not repair or qualify the historical `127.0.0.1` route.

Retain all maintained verifier/control modules and tests, including files with historical `final07`–`final10` names: ordinary tools and installed-wheel checks import them. No check here enables the five real Agents, ordinary Runners, production PostgreSQL/deployment or native Windows Worker execution.
