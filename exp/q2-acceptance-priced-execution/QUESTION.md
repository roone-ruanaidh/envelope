# Q2 — cost of controller-owned task execution

## Question

When the same model receives the same software task, tools, runtime, evaluator, and limits, does a Python harness that keeps task state outside the model pass the external evaluator more often, or reach a passing result with fewer total resources, than a conventional coding agent that uses its conversation as working memory?

## Decision this could change

Determine whether this execution model is worth retaining as the common substrate for later Envelope experiments, and which part of the design should be tested separately next.

## Boundary and non-claims

Q2 compares two complete harnesses on machine-graded Python issue-resolution tasks. Total resources include inference, exact computation, runtime, tools, wall time, and any human attention; unavailable prices remain unknown.

The evaluator is a production-shaped proxy for acceptance, not proof of human acceptance or production readiness. Q2 does not establish general agent superiority, attribute an outcome to one component, train a model, choose Rust boundaries, prove Lean invariants, or recover implementation cost.

## Load-bearing beliefs and unknowns

- **U1 — execution:** both harnesses can reach the same external evaluator through the measured runtime.
- **U2 — state ownership:** the treatment makes task state durable outside model context and admits model proposals and tool effects through deterministic control.
- **U3 — comparison:** the harness computation and memory model is the only intended difference between paired runs.
- **U4 — accounting:** accepted, rejected, and failed paths retain comparable resource and failure records.
- **U5 — task pressure:** the tasks exercise enough navigation, diagnosis, editing, and verification to expose useful strengths and failures.

## Stop when

Stop when approved loops support a reproducible comparison of evaluator pass rate, failures, and total resources within this boundary, or show that the shared execution path cannot be qualified without becoming the research question. Preserve causal attribution and unavailable prices as unknown.
