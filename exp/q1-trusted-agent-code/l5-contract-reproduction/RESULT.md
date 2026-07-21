# Q1/L5 result — contract reproduction

## Observed evidence

- Run: `20260721T173838Z-aef45487`
- Executable contract commit: `30e9d15716f45e48fad6f3635587e925ccf56161`
- Candidate attempts completed: 0
- Evidence: [`evidence/20260721T173838Z-aef45487`](evidence/20260721T173838Z-aef45487)
- Separate cost and latency ledger: [`evidence/20260721T173838Z-aef45487/accounting.json`](evidence/20260721T173838Z-aef45487/accounting.json)

Final non-human gates:

    "unavailable"

## Disposition

**Inconclusive.**

Reason:

    "verify dispatch mechanics in evaluator VM exited 2"

## Deviations and unknowns

See `evidence/20260721T173838Z-aef45487/unavailable.json`. Missing required evidence is not recorded as zero and forces `Inconclusive`; explicitly unavailable cost observations remain unknown.

## Effect on Q1

Q1 gains the recorded cost and failure evidence, but no valid cost-to-accepted-completion observation. It does not authorize a next loop.

## Possible next loops

None authorized. The terminal evidence returns to human review for a broad next-step decision.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
