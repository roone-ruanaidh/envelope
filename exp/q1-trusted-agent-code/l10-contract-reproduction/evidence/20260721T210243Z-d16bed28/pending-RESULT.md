# Q1/L10 result — contract reproduction

## Observed evidence

- Run: `20260721T210243Z-d16bed28`
- Executable contract commit: `c35cdb399eef7b891f82c9dc3791f918497754c1`
- Candidate attempts completed: 1
- Evidence: [`evidence/20260721T210243Z-d16bed28`](evidence/20260721T210243Z-d16bed28)
- Separate cost and latency ledger: [`evidence/20260721T210243Z-d16bed28/accounting.json`](evidence/20260721T210243Z-d16bed28/accounting.json)

Final non-human gates:

    "unavailable"

## Disposition

**Inconclusive.**

Reason:

    "export candidate attempt 1 exited 1"

## Deviations and unknowns

See `evidence/20260721T210243Z-d16bed28/unavailable.json`. Missing required evidence is not recorded as zero and forces `Inconclusive`; explicitly unavailable cost observations remain unknown.

## Effect on Q1

Q1 gains the recorded cost and failure evidence, but no valid cost-to-accepted-completion observation. It does not authorize a next loop.

## Possible next loops

None authorized. The terminal evidence returns to human review for a broad next-step decision.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
