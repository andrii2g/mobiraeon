# Full repository review after Increment 5

**Changes requested: one confirmed P2 finding.** The broad existing qualification passes, but a newly reproduced concurrent configuration replay returns the wrong public outcome class. No implementation fix was applied during this review. The earlier F10-R1 and Q3 repair evidence remains valid within its recorded scope.

Reviewed source: 191-file final-11 archive `e208e66b44e1e97678d0a4ca5ade6a2c50b90fc53b6dd9b589eb9757db4f4a1b`, based on Git HEAD `7fff312282c66ac8dfe616fde0b4230b31e133b2`. All original source hashes matched before documentation cleanup. The source and all old submissions are preserved in the [external evidence archive](../../evidence-archive.md). Later documentation retirement is a separate change; it does not claim the old archive includes the updated documentation.

## I5-FR-R1 — P2: writer-side replay loses the retained outcome

At [forge.py:378](../../../src/mobiraeon/forge.py#L378), `forge.connection.configure` checks replay again inside its writer transaction. If an identical request's failed-attempt audit becomes visible after the outer read but before writer acquisition, `_replay` raises `RecordedForgeFailure` containing the retained outcome. [Store.transaction](../../../src/mobiraeon/persistence/__init__.py#L147) wraps it as a rolled-back `TransactionFailure`, retaining only its reason. [OperationBoundary](../../../src/mobiraeon/operations.py#L121) therefore loses the outcome and maps `storage_failed` to `known_failure`. The outside-transaction replay path correctly retains `unavailable`.

The deterministic probe used actual `ForgeService`, `Store` and `OperationBoundary`, two matching authorized requests, a real SQLite `BEGIN IMMEDIATE`/`SQLITE_BUSY` failure and a scheduling barrier after the first replay read closed. It did not replace replay results, transaction conversion or public outcomes. The observed sequence was:

| Observation | Public outcome / reason |
| --- | --- |
| Matching request encountering the genuine writer lock | `unavailable` / `storage_failed` |
| Ordinary replay of that retained attempt | `unavailable` / `storage_failed` |
| Replay discovered inside the writer transaction | **`known_failure` / `storage_failed`** |
| Subsequent ordinary replay | `unavailable` / `storage_failed` |

Connection head/version and revisions remained unchanged; no request/receipt or HTTP write was created. An additional incorrect `known_failure` attempt was audited. The defect makes the public meaning of the same stable request timing-dependent, contrary to the [exact-replay contract](../../forge-contracts.md#ownership-and-authority). This is a supported local concurrency path, not a hypothetical provider failure.

Evidence: [raw paired reproduction](evidence/replay-probe.json), [actual process exit 0](evidence/replay-probe-outer.json). Probe exit 0 means the observation completed; `required_behavior=false` records the application defect. Earlier preparation failures are retained in the archive and are not classified as passing cases.

Repair guidance: preserve the typed retained outcome across confirmed rollback, or handle/re-raise `RecordedForgeFailure` after leaving the writer context without weakening rollback/commit uncertainty. Do not map every `storage_failed` reason to one outcome: the original recorded outcome must win. Add a regression for both ordinary replay and the outer-read-to-writer gap, with the same actor/target/inputs and a retained non-success outcome. Assert equal outcome/reason, unchanged business state and current authorization. Keep failed commit/rollback uncertainty conservative.

## Nonblocking robustness observations

**O1 — alternate encoded output.** Injected UTF-16LE/UTF-32LE summary bytes can pass `json.loads(raw)` at [execution.py:824](../../../src/mobiraeon/execution.py#L824), while decoding the ASCII-plus-NUL bytes as UTF-8 also succeeds. Execution can mark the artifact valid and publish a succeeded observation; subsequent submission rejects the NUL-containing content. Decode and parse the same strict UTF-8 text if this boundary is broadened. The approved immutable Linux fixture emits UTF-8, so no supported current public trigger was established.

**O2 — split CRLF.** At [signal_verification.py:143](../../../src/mobiraeon/signal_verification.py#L143), a `\r\n` pair split across reads parses `\r` as the record ending and then parses `\n` as an empty record, producing `JSONDecodeError`. Raw output and EOF remain retained. LF and unsplit CRLF controls pass. The current Linux producer emits LF, and native Windows Worker execution is unqualified. Handle CRLF framing across chunks before supporting such a producer.

These are low-priority robustness observations, not new Increment 5 qualification blockers. [Seven bounded probes](evidence/execution-probes.json) completed once, [actual exit 0](evidence/execution-probes-outer.json), using isolated temporary state and trusted Worker doubles. They do not claim real Docker/provider qualification.

## Scope and validation

Three independent source passes covered forge authority, credentials, transport, publication/reconciliation and migration constraints; execution ownership, stop/fencing, capture, cleanup, deadlines and diagnostics; and shared application/CLI/auth/persistence/packaging integration. No other material finding was confirmed. Accepted cooperative Gitea edit races and practical local persistence timing limits were not reclassified as defects.

A fresh native Linux reproduction passed **729 tests, one expected skip**, lint, formatting and build. The built wheel matches all **55 packaged source files**. Existing final-11 Windows/Linux matrices, source/installed Worker suites, both published-loopback Gitea modes and fixed 20-case certification were independently hash-bound and inspected; they were not relabelled as new executions. See [validation](VALIDATION.md).

This review does not grant human acceptance, enable actual Agents, qualify ordinary Runners, production PostgreSQL/deployment or native Windows Worker. All five actual Agents remain disabled/unqualified. No commit or push occurred. Cleanup retires obsolete briefs and relocates generated evidence; maintained code, tests, verification helpers, contracts, domain-Agent roles and operational infrastructure remain.
