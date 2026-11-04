# Increment 5 final replay repair and closure

**I5-FR-R1 is closed. No material finding remains within the agreed Increment 5 scope.** Implementation, independent technical review and affected verification are complete. This records technical completion; it does not record human acceptance, deployment or Agent enablement.

The [original full review](../2026-11-04-increment-5-full/REVIEW.md) and every earlier review/report retain their original text and conclusions. This separate reassessment records the subsequent repair.

## Repair and causal regression

The transaction wrapper now retains the controlled body error only after verified rollback. The operation boundary honors its recorded non-success outcome only for Forge-owned bindings, using the same validated path as ordinary replay. Acquiring a writer, losing transaction ownership, failing rollback or failing commit retains the previous conservative behavior. Generic reason mappings, authorization, schema and provider behavior are unchanged.

The new disk-backed test interleaves two genuine matching configuration requests after the first outer replay read closes. A real SQLite `BEGIN IMMEDIATE`/`SQLITE_BUSY` failure records an `unavailable/storage_failed` attempt before the delayed writer continues. The [baseline run](evidence/red-results.json) fails at the original `known_failure` mismatch; its current-authorization control passes. The repaired run passes both cases.

Assertions cover ordinary, writer-side and subsequent replay; unchanged connection/revision/request/receipt records; delayed audit outcome/reason; no HTTP traffic; revoked current authority; and conflicting changed inputs. Sixteen additional controls cover every retained non-success outcome, invalid/success labels, ownership restrictions, real DDL rollback, and commit/rollback uncertainty. See the [four-file repair diff](evidence/repair-normalized.patch).

## Verification and decision

| Check | Recorded result |
| --- | --- |
| New regressions and boundary controls | 18 passed |
| Complete native Linux suite | 747 passed, 1 expected skip |
| Complete Windows suite | 745 passed, 4 expected skips |
| Locked lint / format / build | Passed on both platforms |
| Clean noneditable installed wheel | 218 Forge, operation and persistence tests passed |
| Source and installed runtime-only Forge scenarios | Both passed, 10 checks each |
| Packaged source | All 55 member paths and byte hashes match on both builds |
| Independent repair reassessment | No material finding; all closure gates verified |

The [validation record](VALIDATION.md) links actual exits, source identities, environment checks, failed setup evidence and preservation receipts. The [independent final assessment](evidence/independent-final-assessment.json) binds its decision to the repaired files and actual reports. No further implementation repair is required for the known Increment 5 findings.

## Exact source and retained qualification

The checked repair is the 204-file archive `4a6f85d5cbd4c59ef39f5e0523342081a3f01497fd062685a341fb9eb09c9ed0`, based on unchanged HEAD `7fff312282c66ac8dfe616fde0b4230b31e133b2`. It changes two product files and two test files. All 53 other packaged inputs remain unchanged. Current status/navigation and this closure record follow qualification and are separately preserved; they are not claimed to be in that earlier archive.

Existing final-11 live Gitea, Worker and fixed certification evidence keeps its original source attribution. Those unchanged mechanisms were assessed for carry-forward under the plan's affected-check rule; they were not rerun or relabelled as executions against this repair archive. The new source/installed runtime checks use production transport over a loopback fixture and do not claim a fresh real-provider qualification.

The original review's O1/O2 robustness observations remain preserved and nonblocking for the pinned UTF-8/LF Linux producer. Existing cooperative-edit, local storage and fixture limits remain. All five actual Agents remain disabled/unqualified; ordinary Runners, production PostgreSQL/deployment and native Windows Worker remain outside the qualified scope.

All prior evidence remains preserved. No commit or push occurred.
