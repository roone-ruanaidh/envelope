# Q2/L1 — paired production-path canary

> **Question:** Can one frozen task traverse both harnesses and produce externally scored, comparable terminal records?

Q2/L1 qualifies one complete comparison path. It does not compare performance, isolate component effects, or authorize another loop.

## Intent

Build the smallest real Python harness that treats a task as a program submitted to a computation system:

- durable task state, authority, budget, and effects belong to the controller;
- model context is a disposable view of that state;
- the model performs bounded semantic work and proposes actions;
- deterministic code admits and executes tool effects; and
- the external evaluator decides task success.

This is an architectural intent, not an implementation recipe. The agent should derive the cleanest coherent design, reject unnecessary machinery, and stop rather than add patches, special cases, or parallel paths when the design does not fit.

## Decision and states

The initial state is `UnqualifiedComparison`: no treatment and baseline have traversed the same measured task path.

Legal measured transitions are:

```text
UnqualifiedComparison -> Running
Running -> QualifiedComparison | Failed | Inconclusive
```

A pass allows the human to consider a measured comparison loop. Terminal states do not reopen.

## Comparison boundary

The two arms must share the exact task, model and sampling, runtime and image, available tools and authority, external evaluator, and hard limits. Their intended difference is how computation and memory are organized.

Use one validated Python software-engineering task and an existing conventional coding harness from Prime Intellect's current production path. Choose them for evaluator integrity, runtime availability, and representative task pressure—not for an expected result.

The treatment must make its state ownership inspectable. File layout, libraries, types, operation vocabulary, context-selection policy, and internal control flow remain design decisions. Subagents, adaptive memory, Rust, Lean, and training are outside this loop unless the agent shows that the core boundary cannot be made real without one and the human changes the contract before execution.

## Ownership and clarification

Humans own this contract, the frozen comparison, changes to meaning, later-loop approval, acceptance interpretation, promotion, and publication. The agent owns technical design, implementation, exact execution, evidence, deterministic disposition, and the terminal findings draft.

Before writing the treatment, the agent must discuss with the human:

- its minimal computation and memory model;
- the proposed task, baseline, model, runtime, and shared limits;
- what the design deliberately omits; and
- any ambiguity that could change what the comparison means.

The human approves the frozen comparison. The agent should ask about consequential ambiguity, not delegate ordinary implementation judgment.

## Execution

After approval, freeze the comparison and treatment definition before inspecting the task contents. Build the treatment and only the local tests needed to show that state, context views, effects, and accounting obey its design.

Then start one measured record and execute one baseline attempt and one treatment attempt in fresh production runtimes. Each receives the same human-approved model-call, token, and wall-time limits. No benchmark tuning, retry, remediation, task substitution, or repair is allowed after `Running`.

Score both arms through the unchanged external evaluator, close proportional public-safe evidence, assign the disposition, update `FINDINGS.md`, and stop. The agent may create the terminal local commit; it never pushes.

## Evidence

Evidence is loop-scoped; synthesis accumulates in the question-level `FINDINGS.md`. Q2/L1 does not create `RESULT.md`.

Retain enough to reproduce and audit the claim:

- frozen contract, dependency, task, model, harness, runtime, authority, evaluator, and limit identities;
- treatment source, design record, and tests;
- ordered model, context-view, state-transition, tool-effect, candidate-diff, and evaluator records for both arms;
- separate inference, exact-compute, runtime, tool, wall-time, observed-price, and unavailable-price records; and
- deviations, attribution, disposition, and effect on Q2.

Credentials, auth state, sandbox images, secrets, and uncontrolled generated artifacts never enter Git.

## Disposition and stopping rule

| Disposition | Deterministic rule |
|---|---|
| `Pass` | Both arms produce a valid external score and complete comparable evidence, even if either task score is zero. |
| `Fail` | The frozen baseline path is valid and the treatment's implementation or state boundary is the attributable reason its terminal record cannot be produced. |
| `Inconclusive` | A shared task, model, provider, runtime, evaluator, accounting, or attribution failure prevents the comparison. |

The measured budget is one task and one attempt per arm under the frozen equal limits. A missing precondition stops before `Running` without disposition. Any measured limit breach or undefined branch is terminal. Diagnostics may explain the result but cannot repair or rerun Q2/L1.
