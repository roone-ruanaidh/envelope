# Q1 — cost of trusted agent-produced code

## Question

What does it cost to move agent-produced code from declared completion to accepted completion?

## Decision this could change

Determine which verification, evidence, remediation, and human-review steps are load-bearing enough to retain in later Envelope work, and which add cost without changing acceptance.

## Boundary and non-claims

Q1 studies accepted completion for explicitly contracted code under declared execution and settlement procedures. It does not establish population reliability, production readiness, universal security, or correctness beyond a loop's contract.

## Load-bearing beliefs and unknowns

- **U1 — evaluator validity:** the evaluator must distinguish accepted behavior from realistic contract violations without enforcing undeclared semantics.
- **U2 — execution boundary:** the candidate must be isolated from sealed evaluation material while retaining the authority required to implement the contract.
- **U3 — remediation:** verification findings must be useful enough to guide correction without leaking sealed implementation details.
- **U4 — human judgment:** the work must localize which acceptance findings genuinely require human source review and discernment.
- **U5 — cost evidence:** agent usage, machine execution, human attention, remediation, and wall latency must remain separately observable, with missing values left unknown.

## Stop when

Stop when completed loops either support a reproducible account of cost-to-accepted-completion within their declared scope or show that the question is not decidable with the available evidence. Preserve any remaining human judgment or uncertainty explicitly.
