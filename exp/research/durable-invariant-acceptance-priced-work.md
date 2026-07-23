# Durable invariant: acceptance-priced semantic computation

- **Research date:** July 23, 2026
- **Status:** unpromoted synthesis; not a question, loop contract, result, or design
- **Read with:** [Envelope](../../README.md), [acceptance-cost state process](acceptance-cost-state-process.md), [recursive language model control](recursive-language-model-control.md), [Python REPL as working memory](python-repl-semantic-coprocessor.md), and the [semantic computer sketch](semantic-computer.html)

## Finding

The durable pattern across Envelope's intent, Recursive Language Models, and the related memory and control research is:

> Do not let task state, authority, accounting, and acceptance collapse into the model's opaque trajectory.

The system's governed and priced unit is therefore not a token, model turn, tool call, or final output. It is an **admitted state transition toward a versioned acceptance contract**.

```text
contracted state
  -> reserve budget and authority
  -> execute one bounded operation
  -> seal its artifact, observation, or receipt
  -> admit the event
  -> deterministically derive the next state
  -> Accepted | Rejected | Inconclusive | another legal transition
```

The bounded operation may be:

- **exact computation**, producing an artifact;
- **semantic computation**, producing a model observation; or
- **an external effect**, producing a receipt and new external observation.

The executors may change. The transition envelope should not.

## The four separations

### State leaves the model

The authoritative task state is the journal plus immutable artifacts. RAM, REPL bindings, summaries, indexes, and model context are derived working views.

The context window is a bounded semantic cache. It contains the instruction and evidence projection needed for one model operation. It is not the task workspace, event history, or source of truth. Larger tasks should normally create more cache loads, not one proportionally larger model trajectory.

### Authority leaves model output

A model response is data. It may propose a plan, semantic judgment, or effect intent. It does not grant itself permission, reserve resources, mutate the world, or accept its own work.

Read tools are sensors. Mutating tools are actuators. Both sit behind typed interfaces; effects require controller admission, idempotency, and reconciliation.

### Accounting leaves post-hoc token totals

Resources are reserved before dispatch and settled from evidence afterward. Record the resource vector before applying a price schedule:

```text
tokens / model compute / exact compute / storage / tools /
infrastructure / wall time / verification / human attention
```

Post-hoc token counting is useful telemetry but cannot prevent parallel overspend or explain the cost of failure, remediation, review, and cleanup.

### Acceptance leaves model self-report

A candidate artifact is not accepted completion. Acceptance is a predicate over the artifact, evidence, evaluator, contract, and any required human review.

The model may contribute semantic evidence. It cannot establish that the evidence is admissible, that an external event occurred, or that the contract is satisfied merely by saying so.

## The transition envelope

A provisional work unit has this shape:

```text
WorkEnvelope = {
  contract_ref,
  current_state_ref,
  operation_id,
  input_handles,
  output_type,
  authority,
  reservation,
  evidence_rule,
  failure_policy,
  stopping_rule,
  configuration_identity
}
```

Execution returns one or more typed records:

```text
ArtifactRef       exact or externally acquired value
ObservationRef    sealed semantic result, not automatically true
ReceiptRef        evidence of an attempted or completed external effect
```

The reconciler—not the executor—determines whether the result is admissible and which transition follows.

This envelope recurses. A programmatic sub-agent receives a smaller contract, explicit input views, output schema, child budget, deadline, and allowed child operations. It does not inherit the parent's heap, credentials, unbounded recursion, or authority. Nested work remains attributable to the parent reservation and acceptance path.

## Task shape is derived

Envelope should not start with a universal workflow or a desired number of steps.

The task contract supplies obligations. Available structured data supplies exact dependencies. Genuine semantic unknowns become model operations. Required external changes become effect intents. Evidence requirements create verification and reconciliation nodes.

This produces:

- a minimum contract skeleton;
- bounded fan-out from input scale;
- optional, validated frontier expansion for unresolved topology;
- predeclared failure and repair transitions; and
- terminal acceptance, rejection, or inconclusive states.

Step count and cost are outputs of this shape and its realized failures. Adaptation is allowed only when a candidate expansion is typed, reservable, authorized, and consumes finite potential.

## Price to acceptance

Per-token price is a tariff on one resource. It is not the price of agentic work.

For contract `A` and sealed configuration `c`, Envelope's economic object is:

\[
F_{A,c}(b)
=
P(\text{accepted before abandonment with total path cost} \le b
\mid A,c).
\]

The configuration includes the effective model, inference engine, context policy, controller, tools, authority, environment, evaluator, retry policy, and stopping rule.

This framing has four consequences:

1. **Failure mass remains visible.** A failed or abandoned run consumed resources but did not produce accepted completion. Successful-run averages must not erase it.
2. **Verification is part of production cost.** Generation, checking, remediation, review, reconciliation, and cleanup lie on the same path.
3. **Harness changes are economic treatments.** They may change reachable states, acceptance probability, failure shape, and resource use even when the model is unchanged.
4. **The useful comparison is acceptance by budget.** "Configuration X reaches accepted completion more often by budget Y" is more informative than "model X costs Z per million tokens."

Record resources before dollars so behavior can be separated from later price changes. A new provider tariff changes valuation; it does not retroactively change the execution path.

## Determinism that is actually available

The model and external world remain stochastic. The attainable guarantees are narrower:

- deterministic control given the same state and admitted event;
- deterministic replay over the same sealed observations and receipts;
- canonical joins independent of completion order; and
- proved controller properties where a small formal model genuinely matches the claim.

Re-executing model or tool calls is a new trajectory. It is not replay.

Rust may own the durable operational membrane. Lean may prove selected invariants of a stable abstract machine. Python may remain the research workspace. Those assignments are replaceable; none is the invariant itself.

## Why this pattern appears durable

It survives changes in:

- model family, size, provider, or accelerator;
- Python REPL versus a typed plan runtime;
- fixed plans versus bounded adaptive frontiers;
- local versus remote inference;
- task domain and input scale; and
- exact implementation language.

It also creates one inspectable seam for memory, authority, evidence, failure, and cost. Removing any of those from the envelope pushes consequential state back into prompt prose or hidden runtime behavior.

## What Envelope is becoming

Envelope is less a better prompt harness than:

> A transactional operating system and economic runtime for stochastic semantic computation.

Its candidate stable substrate is:

1. a versioned task and acceptance contract;
2. durable state and evidence identities;
3. a deterministic transition kernel;
4. exact, semantic, and effect operation interfaces;
5. capability and reservation ledgers;
6. reconciliation and terminal dispositions;
7. replay over sealed external observations; and
8. configuration-relative acceptance-cost qualification.

The model is a semantic coprocessor inside that computer. Programmatic sub-agents are isolated semantic processes. Context is their disposable cache. Tools are I/O devices. The controller owns the task.

## Use cases refine the substrate

Each use case should solve useful work with the smallest available system while exposing where the substrate is missing, redundant, or wrong:

```text
useful task
  -> execution trace
  -> repeated operation or failed assumption
  -> candidate runtime primitive
  -> targeted experiment
  -> human promotion, simplification, or rejection
```

No run promotes its own pattern. A primitive earns promotion only after its semantics, failure behavior, resource claims, evidence, and value across more than one trajectory are clear enough to review.

This allows practical tools and the eventual computer to co-evolve without designing a universal agent architecture in advance.

## Critical unresolved questions

1. **Acceptance:** What evidence and judgment make a contract meaningful rather than merely machine-checkable?
2. **State sufficiency:** What smallest observable state predicts remaining acceptance probability and cost within an approved tolerance?
3. **Operator boundary:** What smallest exact/semantic/effect vocabulary covers useful task families without returning control to an opaque model loop?
4. **Projection policy:** How does the controller know that a bounded context view is sufficient for a semantic operation, and how is omission detected?
5. **Reservation:** How can hard global bounds remain honest when providers expose incomplete usage, cancellation, and billing information?
6. **Conformance:** How will a proved abstract transition kernel remain aligned with the operational implementation?

The operator boundary appears to be the next architectural question. The acceptance and state-sufficiency questions remain the deeper qualification questions.

## Stop claims

This synthesis does not establish that:

- agentic work is Markov under the current state representation;
- deterministic control makes model results deterministic or true;
- a context cache policy preserves all task-relevant information;
- typed output is admissible evidence;
- a successful candidate is accepted completion;
- a Rust runtime is crash-safe or least-authority merely because it is Rust;
- a Lean theorem proves production conformance or external truth;
- recurring operators should be promoted before cross-use-case evidence; or
- any proposed architecture lowers price to acceptance.

## Sources

- Zhang, Kraska, and Khattab, [*Recursive Language Models*](https://arxiv.org/abs/2512.24601), version 3, May 11, 2026.
- Zhang, [*Language model harnesses are compositional generalizers*](https://alexzhang13.github.io/blog/2026/harness/), 2026.
- Envelope's local research notes linked above.

The transition envelope and operating-system interpretation are architectural synthesis, not claims made directly by the cited sources.
