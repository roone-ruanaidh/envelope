# Q1/L2 result — contract reproduction

## Observed evidence

- Run: `20260721T071826Z-10ec801b`
- Executable contract commit: `d7292b3f737c25cf00a92f570b85d6f3bc7e4c2b`
- Candidate attempts completed: 0
- Evidence: [`evidence/20260721T071826Z-10ec801b`](evidence/20260721T071826Z-10ec801b)
- Separate cost and latency ledger: [`evidence/20260721T071826Z-10ec801b/accounting.json`](evidence/20260721T071826Z-10ec801b/accounting.json)

Final non-human gates:

    "unavailable"

## Disposition

**Inconclusive.**

Reason:

    "provision and probe candidate VM exited 1"

## Deviations and unknowns

See `evidence/20260721T071826Z-10ec801b/unavailable.json`. Missing required evidence is not recorded as zero and forces `Inconclusive`; explicitly unavailable cost observations remain unknown.

## Effect on Q1

Q1 gains the recorded cost and failure evidence, but no valid cost-to-accepted-completion observation. It does not authorize a next loop.

## Possible next loops

None authorized. The terminal evidence returns to human review for a broad next-step decision.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
