# Q1/L8 result — contract reproduction

## Observed evidence

- Run: `20260721T204010Z-87c2d9c9`
- Executable contract commit: `9846c7c3a9bfa5f958a54243d278fb5570a8f3e5`
- API authentication preflight: HTTP `200`
- Candidate Codex login: passed
- Agent invocation: reached OpenAI, then failed before generation because the
  completion schema's root `oneOf` is unsupported
- Candidate attempts completed: 0
- Evidence: [`evidence/20260721T204010Z-87c2d9c9`](evidence/20260721T204010Z-87c2d9c9)
- Separate cost and latency ledger: [`evidence/20260721T204010Z-87c2d9c9/accounting.json`](evidence/20260721T204010Z-87c2d9c9/accounting.json)

Final non-human gates:

    "unavailable"

## Disposition

**Inconclusive.**

Reason:

    "invalid_json_schema: root oneOf is not permitted"

## Deviations and unknowns

The run exercised neither candidate implementation nor the masked-fingerprint
sanitizer: no provider fingerprint appeared. Before run state existed, recovery
also found that macOS Keychain's interactive password prompt truncated the
long-form API key; execution began only after the clipboard and stored value
matched byte-for-byte. That prerequisite diagnostic is outside the indexed run
evidence.

See `evidence/20260721T204010Z-87c2d9c9/unavailable.json`. Missing required
evidence is not recorded as zero and forces `Inconclusive`; explicitly
unavailable cost observations remain unknown.

## Effect on Q1

Q1/L8 resolves its credential unknown: the supplied bearer and candidate login
worked. It exposes a harness compatibility error before Luna could act, so Q1
still has no valid cost-to-accepted-completion observation.

## Possible next loops

Mechanically express the unchanged completion declaration in the OpenAI
Structured Outputs subset, then rerun. This result does not itself authorize
that loop.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
