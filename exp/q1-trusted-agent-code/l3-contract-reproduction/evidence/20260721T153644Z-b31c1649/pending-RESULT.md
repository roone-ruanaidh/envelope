# Q1/L3 result — contract reproduction

## Observed evidence

- Run: `20260721T153644Z-b31c1649`
- Executable contract commit: `aad8f60c1a129bfa1ab909ce0ef89912a7ffd8b2`
- Candidate attempts completed: 0
- Evidence: [`evidence/20260721T153644Z-b31c1649`](evidence/20260721T153644Z-b31c1649)
- Separate cost and latency ledger: [`evidence/20260721T153644Z-b31c1649/accounting.json`](evidence/20260721T153644Z-b31c1649/accounting.json)

Final non-human gates:

    "unavailable"

## Disposition

**Inconclusive.**

Reason:

    "provision and probe candidate VM exited 1"

## Deviations and unknowns

See `evidence/20260721T153644Z-b31c1649/unavailable.json`. Missing required evidence is not recorded as zero and forces `Inconclusive`; explicitly unavailable cost observations remain unknown.

## Effect on Q1

Q1 gains the recorded cost and failure evidence, but no valid cost-to-accepted-completion observation. It does not authorize a next loop.

## Possible next loops

None authorized. The terminal evidence returns to human review for a broad next-step decision.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
