# Q1/L11 result — contract reproduction

## Observed evidence

- Run: `20260721T213105Z-93108211`
- Executable contract commit: `cac2946b0915feab99b87ce5a273b169aec5bf1b`
- Authentication, evaluator validation, candidate provisioning, boundary validation, candidate export, transfer integrity, and clean dependency bootstrap passed.
- Luna produced a reproducible two-file candidate: a 982-line `service.py` and six-line `Makefile`; it declared `['.venv/bin/python', 'service.py']` complete.
- Luna first found four typing errors, fixed them, then recorded six clean typechecks. Its action trace also records passing local behavior and concurrency/edge checks. These are agent-run checks, not trusted acceptance evidence.
- Luna emitted four completion-shaped messages before its final declaration. The harness's last-message rule prevented premature settlement; the behavior remains a model output-discipline finding.
- The trusted typing gate did not evaluate the candidate. Bubblewrap could not traverse the evaluator's mode-`0700` attempt directory: `Can't find source path .../attempt-1/candidate: Permission denied`.
- No behavior attempt or remediation ran. Final non-human acceptance gates are unavailable.
- Luna invocation: `833.293666` seconds. Reported usage: `4,044,907` input tokens (`3,915,852` cached), `57,093` output tokens, and `27,029` reasoning-output tokens. Monetary charge was unavailable.
- Evidence: [`evidence/20260721T213105Z-93108211`](evidence/20260721T213105Z-93108211)
- Candidate source: [`evidence/20260721T213105Z-93108211/candidate/attempt-1/source`](evidence/20260721T213105Z-93108211/candidate/attempt-1/source)
- Cost and latency ledger: [`evidence/20260721T213105Z-93108211/accounting.json`](evidence/20260721T213105Z-93108211/accounting.json)

## Disposition

**Inconclusive.** The harness failed before trusted candidate evaluation. This is not a candidate rejection.

## Deviations and unknowns

The evaluator attempt directory was created mode `0700`, while the isolated command intentionally runs as UID `65534`. The directory therefore blocked Bubblewrap from resolving the read-only candidate bind. Preflight missed the mismatch because its fixture parent was mode `0755`.

Post-run source review found no concrete contract defect. The sharpest unverified risks are manual ASGI body replay, synchronous SQLite work inside async routes, and no retained candidate tests. Candidate typing, behavior, remediation response, and human source attestation remain unknown. Missing observations remain unknown rather than zero; see [`unavailable.json`](evidence/20260721T213105Z-93108211/unavailable.json).

## Effect on Q1

Q1/L11 establishes that Luna can build, locally test, clean, declare, export, and transfer a concrete candidate under the frozen workload. It does not establish candidate correctness or cost to accepted completion because no trusted candidate gate ran.

## Possible next loops

Create evaluator attempt directories with the existing traversable-but-unlistable mode `0711`, add a production-shaped isolation regression, then rerun the frozen model, workload, budgets, gates, and human boundary. This is a mechanical harness correction, not authorization for another loop or a change to acceptance.

## Promotion candidate

None. Loop success and promotion remain human-gated.
