# Q1/L6 result — contract reproduction

## Observed evidence

- Run: `20260721T175525Z-f7c72be4`
- Executable contract commit: `8c96fd15ab25d4de80b7208662b94b04b2df9210`
- Candidate attempts completed: 0
- Evidence: [`evidence/20260721T175525Z-f7c72be4`](evidence/20260721T175525Z-f7c72be4)
- Separate cost and latency ledger: [`evidence/20260721T175525Z-f7c72be4/accounting.json`](evidence/20260721T175525Z-f7c72be4/accounting.json)

Final non-human gates:

    "unavailable"

## Disposition

**Inconclusive.**

Reason:

    "inspect created candidate Lima configuration exited 125"

## Deviations and unknowns

See `evidence/20260721T175525Z-f7c72be4/unavailable.json`. Missing required evidence is not recorded as zero and forces `Inconclusive`; explicitly unavailable cost observations remain unknown.

## Effect on Q1

Q1 gains the recorded cost and failure evidence, but no valid cost-to-accepted-completion observation. It does not authorize a next loop.

## Possible next loops

None authorized. The terminal evidence returns to human review for a broad next-step decision.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
