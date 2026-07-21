# Q1/L9 result — contract reproduction

## Observed evidence

- Run: `20260721T205408Z-36bfc6d1`
- Executable contract commit: `4b16fa7f695e3a2548eb7c0d1db6a775f5dee955`
- Candidate attempts completed: 0
- Authentication preflight: HTTP `200`
- Candidate login, provisioning, boundary, evaluator, and isolation checks passed
- Agent invocation reached OpenAI but stopped before inference: each `status` schema using `const` lacked the provider-required explicit `type`
- Agent invocation elapsed: `1.290235` seconds; token usage and monetary charge were unavailable
- Evidence: [`evidence/20260721T205408Z-36bfc6d1`](evidence/20260721T205408Z-36bfc6d1)
- Separate cost and latency ledger: [`evidence/20260721T205408Z-36bfc6d1/accounting.json`](evidence/20260721T205408Z-36bfc6d1/accounting.json)

Final non-human gates:

    "unavailable"

## Disposition

**Inconclusive.**

Reason:

    "OpenAI rejected the completion schema before generation because status lacked an explicit type"

## Deviations and unknowns

The root-object/nested-`anyOf` correction passed the prior failure point, but Luna produced no implementation or completion. Codex also emitted non-blocking warnings while enforcing disabled web search. See `evidence/20260721T205408Z-36bfc6d1/unavailable.json`; missing observations remain unknown rather than zero.

## Effect on Q1

Q1/L9 isolates the next schema compatibility defect but still provides no Luna action or cost-to-accepted-completion observation.

## Possible next loops

Under the standing human approval through Q1/L11, add the missing string types without changing either completion branch, verify the exact provider-compatible shape, and retry as Q1/L10.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
