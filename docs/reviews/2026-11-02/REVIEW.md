# Full repository review

Date: 2026-11-02 (Europe/Kiev). Reviewed commit: `7a386fe69c6e2c5bb7ee32d17ecdb2773e0f2491`.

**Five P2 findings require repair.** Existing suites pass their exercised cases, but focused probes expose additional failures in execution outcome reporting, bootstrap partial-progress reporting, foreground shutdown, configuration classification and source capture. No P0/P1 finding was established in this review.

This is a new review of the accepted repository. It preserves the historical Increment 1–4 acceptance records and original reviews. The repaired I4-R2 execution handler remains fixed; FR-03 concerns a different foreground-host handler. No implementation code, accepted evidence or Git history was changed. Increment 5 remains a proposal and has not been implemented.

## Scope and source binding

The review covers application configuration/lifecycle/transactions, Access and Registry/API/bootstrap, Coordination and its authority/evidence gates, supervised fixture execution, tests/build/capture tools, documentation/diagrams and static Gitea infrastructure configuration. Source inspection and bounded fault probes supplement fresh platform verification.

The clean starting checkout was captured as 128 files with archive SHA-256:

```text
91e6a9ef1ffbf5b897ca7e56bf9eac87f5e7307a74c357904986bce94ce87aed
```

The [validation record](VALIDATION.md) separates fresh checks, focused reproductions, corrected test invocation and unverified deployment/forge capabilities. Raw probes and platform results are local ignored artifacts; this report retains the essential triggers, observed results and repair criteria for review without those generated files.

## Findings

### FR-01 — P2: require terminal container evidence before reporting execution success

Location: [execution.py](../../../src/mobiraeon/execution.py), lines 632–639; related finalization at 664–695.

When the attached Docker CLI exits, supervision inspects the container and chooses `succeeded` solely from `State.ExitCode == 0`. It does not require the container to have stopped. Loss of the attachment can leave the container running with a default zero exit code. Cleanup may then stop/kill it and replace the runtime observation with exit 137, while the earlier `succeeded` outcome remains intact.

A real-SQLite probe supplied the exact valid summary, an exited attachment, a running container/default-zero observation and subsequently verified cleanup with terminal exit 137. The application returned `success`, sealed `artifact_valid=true`, and published a `succeeded` Coordination observation. Terminal-zero and terminal-nonzero controls produced their expected success/failure outcomes.

A separate real Docker probe on the recorded Engine/image confirmed the underlying state combination: killing only the attached CLI left the actual container running with `ExitCode=0` and an unset finish time; cleanup then observed exit 137 and verified retirement. That probe did not reproduce a naturally occurring valid-summary race. The application false-success path is independently demonstrated by the trusted transport-fault double. Attachment EOF alone cannot prove the fixture finished.

Impact: a transport interruption can become successful work evidence even though trusted final runtime evidence contradicts successful execution. This violates the [execution outcome and artifact contract](../../execution-contracts.md#fixture-output-and-coordinator-bridge).

Repair criteria:

- Derive success from established terminal container observations, independently of the attachment process ending.
- A default-zero running state or subsequent forced/nonzero termination cannot produce a valid successful artifact or successful Coordinator observation.
- Preserve established terminal-zero success with complete matching capture, and terminal-nonzero failure. Keep cleanup verification separate from execution outcome.

Evidence: [focused assessment](../../../artifacts/full-review-20261102-01/execution-audit/assessment.md), [application result](../../../artifacts/full-review-20261102-01/execution-audit/lost-attach-result.json), [real Docker state probe](../../../artifacts/full-review-20261102-01/execution-audit/real-attach-loss.json).

### FR-02 — P2: preserve bootstrap effects and progress on late orchestration errors

Location: [bootstrap.py](../../../src/mobiraeon/bootstrap.py), lines 27–32 and later direct `SafeError` paths; [administration.py](../../../src/mobiraeon/administration.py), lines 58–72; [cli.py](../../../src/mobiraeon/cli.py), lines 161–173.

Package-shape validation does not resolve all publication references before preparation begins. A complete first instruction followed by an Agent referring to a missing `published` Profile passes that preflight. The first instruction is created, reviewed and published. Resolving the second definition then raises a direct `SafeError`, bypassing the `PreparationStopped` wrapper and its completed receipts. The top-level CLI converts it to `invalid_input`.

The real protected-store reproduction returned exit 2, `invalid_input/reference_missing`, and `data=null`, while SQLite contained one committed entity, draft, review and publication. Other direct late conflict/unavailable paths have the same orchestration boundary; they need regression coverage rather than an assumption that every failure is pre-effect validation.

Impact: callers receive the documented no-execution input classification after actual catalog mutations, with no partial-progress result. The underlying immutable records/audit remain available; this is an effect-reporting defect, not a demonstrated authorization bypass or lost publication.

Repair criteria:

- Prevalidate dependencies where possible and provide an effect-aware boundary for every error after preparation starts.
- Retain completed receipts and the failed definition; distinguish known partial completion from genuinely uncertain child effects.
- Cover a late missing reference and late repeat/resume conflict, alongside the accepted no-effect structural preflight and commit-acknowledgement regressions.

Evidence: [focused assessment](../../../artifacts/full-review-20261102-01/registry-audit/assessment.md), [safe CLI/database result](../../../artifacts/full-review-20261102-01/registry-audit/late-bootstrap-error.json).

### FR-03 — P2: remove lock-taking work from the foundation host signal handler

Location: [cli.py](../../../src/mobiraeon/cli.py), lines 62–63; used by `start` with API hosting disabled at line 158.

`serve()` still calls `threading.Event.set()` directly from SIGINT/SIGTERM/SIGBREAK handling. A second signal can reenter while the first owns the Event's nonreentrant Condition lock. The nested callback waits on the main thread, preventing the first from returning and preventing foreground shutdown/finalization.

On both Windows and Linux, all four SIGINT/SIGTERM nested combinations reached depth two and timed out at the bounded four-second parent deadline without handler returns. All children were killed/reaped. Single-signal and spaced fresh-scope controls passed, including handler restoration. The probe delegates to the actual production callback and selects a legal asynchronous timing window without replacing the Event lock. It does not establish a natural occurrence rate or test repeated spaced signals within one running scope.

Impact: the implemented non-API foreground host can hang during ordinary interruption. This is separate from the lock-free `execution_signals()` repair and does not reopen its resolved finding.

Repair criteria: keep signal callbacks to minimal lock-free intent, move synchronized work to normal flow, and retain externally supplied stop-event behavior, SIGBREAK support, nested-delivery checks, bounded shutdown and restoration controls.

Evidence: [focused assessment](../../../artifacts/full-review-20261102-01/docs-audit/assessment.md), [Windows probe](../../../artifacts/full-review-20261102-01/docs-audit/cli-signals-windows.json), [Linux probe](../../../artifacts/full-review-20261102-01/docs-audit/cli-signals-linux.json).

### FR-04 — P2: classify malformed API configuration before effects

Location: [configuration.py](../../../src/mobiraeon/configuration.py), lines 73 and 85–88.

API URL parsing and numeric validation can raise ordinary exceptions outside the safe configuration boundary. `api.client_url="https://["` raises `ValueError`; a 401-digit integer for `api.port` or `api.startup_timeout_seconds` raises `OverflowError` from `math.isfinite()`. The CLI catches these as internal failures and emits exit 1, `uncertain_effects/internal_failure`.

All three cases were reproduced before application/store construction; no database was created. A normal invalid-port control correctly returned exit 2, `invalid_input/configuration_invalid`. The malformed URL is an ordinary input typo, so this finding does not rely solely on extreme integer inputs.

Impact: invalid configuration is incorrectly reported as uncertain execution, contrary to the [documented configuration and exit contract](../../../README.md#configuration), leaving callers with the wrong retry/inspection classification.

Repair criteria: normalize URL parser/hostname failures and numeric conversion/overflow to safe invalid-configuration results with source/setting attribution, without printing raw input. Preserve genuinely uncertain post-effect failures. Add direct-resolver and CLI regressions for the three cases and valid boundary controls.

Evidence: [probe source](../../../artifacts/full-review-20261102-01/foundation-audit/probe_config.py), [observed results](../../../artifacts/full-review-20261102-01/foundation-audit/config-results.json).

### FR-05 — P2: capture legitimate unstaged tracked-file deletions

Location: [capture_submission.py](../../../tools/capture_submission.py), lines 54–57.

The source-capture tool enumerates cached Git paths and unconditionally reads each path. An unstaged deletion remains in that list but is absent from the working tree. Capture raises `FileNotFoundError`, leaves a partial archive and produces no manifest. Staging the deletion happens to avoid the failure, although capture promises the combined checkout without Git mutation.

An isolated small Git fixture using the exact tool bytes reproduced the failure after deleting a tracked text file. Restoring that file made the same command capture successfully. The project checkout was untouched by this fixture.

Impact: normal deletions and renames can block exact-source handoff and independent review, or require an undocumented staging workaround.

Repair criteria: deliberately represent deleted tracked paths while archiving the present combined checkout; retain base/source identity and staged/unstaged/untracked coverage. Add deletion/rename controls and prevent incomplete output from being treated as a completed capture. Do not rewrite prior reviewed archives.

Evidence: [focused assessment](../../../artifacts/full-review-20261102-01/docs-audit/assessment.md), [failure and restored control](../../../artifacts/full-review-20261102-01/docs-audit/capture-deletion.json).

## Architecture, documentation and next increment

The current Python modules, shared local SQLite store and separate logical ownership remain coherent for the accepted single-host fixture boundary. This review established no additional authorization escalation, publication-immutability failure, last-administrator regression or defect in the repaired execution signal flag. This is scoped review evidence, not proof that those areas are defect-free.

Requirements/design, accepted fixture capabilities, disabled real Agents and future qualification are consistently distinguished. Diagram nodes describe the agreed broader design; their presence does not claim those capabilities are implemented. The Increment 5 proposal correctly leaves work mapping, field ownership, credentials and uncertain external delivery unresolved.

Repair these findings in a bounded follow-up before relying on newly published workflow outcomes. Prioritize FR-01's false success, FR-02's partial-effect classification and FR-03's shutdown deadlock; FR-04 and FR-05 can be repaired independently with narrow regressions. Preserve all original reviews and prepare a new exact-source handoff for independent reassessment.

For a small Increment 5, prefer linking one already supplied local Task to one managed Gitea issue first, with explicit synchronization and a narrow Coordinator-owned status projection. General Request parsing/import and automatic planning can be separately scoped. This is a recommendation for discussion, not a change to the approved design or a new implementation assignment.
