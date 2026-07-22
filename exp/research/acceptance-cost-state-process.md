# Acceptance-cost state process — a post-loop decision lens

- **Research date:** July 20, 2026
- **Status:** unpromoted synthesis; not a question, loop contract, result, or promotion decision
- **Read with:** [Envelope](../../README.md), [Q1](../q1-trusted-agent-code/QUESTION.md), [Q1/L1](../q1-trusted-agent-code/l1-contract-reproduction/LOOP.md), and [harness compositional generalization](harness-compositional-generalization.md)

## What this is

This note is a compact model for interpreting Q1/L1 after its findings are recorded and deciding what question the next human-approved loop should answer.

It does not choose or authorize Q1/L2. Its purpose is to prevent one run from being mistaken for a distribution, a state diagram from being mistaken for a statistical model, or harness-training results from being mistaken for inference pricing evidence.

## Core model

An acceptance contract defines the terminal conditions for work. A configured agent traverses candidate generation, verification, remediation, review, and failure states until it reaches accepted completion or another terminal disposition. Every transition consumes resources.

Envelope should price the traversal, not a model call:

\[
F_{A,c}(b)
=
P(\text{accepted before abandonment with total cost} \le b
\mid A,c),
\]

where `A` is the versioned acceptance contract and `c` is the sealed model, harness, tools, authority, environment, evaluator, retry, and stopping configuration.

Set cost-to-acceptance to `+∞` when acceptance never occurs. Then `F` preserves failure mass instead of reporting only the cost of successful runs. Mean cost is secondary and may be misleading or undefined.

Acceptance is a predicate over an augmented state:

\[
\operatorname{Accept}(artifact, evidence, evaluator, contract, review).
\]

A plausible artifact without admissible evidence is not yet in an accepting state. Historical settlement may remain final for its versioned run even when later drift invalidates the qualification used for future decisions.

## Objects Envelope needs

| Object | Meaning |
|---|---|
| Contract `A` | Accepting predicate, constraints, evidence, evaluator, and review requirements |
| Configuration `c` | Exact effective model, harness policy, tools, authority, environment, budgets, and stopping rules |
| History `h` | Append-only execution and evidence events observed so far |
| State `φ(h)` | A derived projection of history sufficient for a declared decision |
| Harness policy `π` | Chooses observations, actions, information retention, verification, remediation, and stopping |
| Transition kernel | Distribution of next state and disposition under `A`, `c`, and `π` |
| Resource vector `r` | Tokens, compute, wall time, tools, infrastructure, and human attention consumed by a transition |
| Valuation `v` | Versioned price schedule that maps resources to money or another selected cost measure |

Keep the event history canonical and derive state from it. A premature fixed state schema will either discard evidence or grow special cases as new failure paths appear.

Record resources before dollars. This separates unchanged behavior under a new tariff from a real change in execution.

## Harness implication

A harness is part of the transition policy, not a label attached to a model. It controls:

- what the model observes;
- which actions are available;
- what information persists;
- when and how verification occurs;
- how failures are classified and remediated;
- when execution stops.

Changing the harness can therefore change reachable states, transition probabilities, and transition costs while the model remains fixed. Qualification belongs to the complete configuration.

The RLM paper’s trajectory equivalence is not enough for Envelope. Two tasks may produce the same root-model tokens while hidden sub-call counts, failure rates, verification needs, or costs differ materially.

Envelope needs **predictive comparability** instead:

> Under a named contract and configuration, two starting tasks or intermediate histories are comparable when their prospective distributions over terminal disposition, remaining cost, time, remediation, and admissible evidence are equal within declared tolerances.

This is approximate, empirical, configuration-relative, and valid only for a stated interval. In state-machine terms, the partition must be approximately **lumpable**: histories placed in one macro-state must have sufficiently similar next-state and cost distributions.

Harness-induced trajectory similarity may help propose a partition. Only acceptance-and-cost behavior can qualify it.

## The real state question

The useful question is not whether AI work is Markov. Any process becomes Markov if its state contains the entire history.

The question is:

> What is the smallest observable state that makes remaining acceptance probability and cost conditionally independent of earlier history, within an approved error tolerance?

Likely candidates include:

- current artifact and evidence identities;
- failed contract obligations and failure class;
- attempt count and remediation already tried;
- remaining budget and time;
- harness context state;
- model, provider, environment, and authority snapshots.

Variable transition duration or cost can justify a semi-Markov model. It does not remove history dependence. If earlier paths still predict outcomes after conditioning on current state, Envelope needs a richer state, a higher-order model, or an explicit history model.

Complexity must earn its place through better prospective calibration. The direct empirical run-level distribution remains primary; a transition model is secondary until it predicts held-out runs well enough to justify its assumptions and instrumentation.

## Cost and premium

Per-token pricing is a resource tariff, not task pricing. Tokens may be consumed during generation, diagnosis, remediation, verification, and orchestration. Envelope adds every relevant resource across the path and preserves uncertainty about paths not observed or not accepted.

For each transition, record a resource vector before applying a price schedule:

\[
r_e = (\text{input tokens},\text{output tokens},\text{compute},\text{wall time},
\text{tools},\text{infrastructure},\text{human time}).
\]

Verification and remediation costs can be reported as ledger categories. A **premium** is a causal contrast between declared configurations or assurance regimes, not merely the sum of everything labeled “after generation.” A harness can spend more before its first candidate and less on remediation; both belong in total cost-to-acceptance.

## Drift

Drift is not one condition. Separate what changed:

| Drift class | Change |
|---|---|
| Behavioral | Next-state or terminal-disposition probabilities |
| Efficiency | Resources consumed by a transition |
| Price | Valuation of unchanged resource use |
| Population | Distribution of starting tasks or states |
| Contract | Acceptance or evidence requirements |
| Observation | Instrumentation or failure classification |

Milestone 5 becomes tractable only when contract and effective configuration identities are sealed. A stable product or model name is insufficient. Managed-provider state that cannot be sealed remains an explicit uncontrolled variable, not part of a “fixed” configuration claim.

Transition signals may detect change before terminal outcomes, but they are sparse and classifier-dependent. Accepted yield and acceptance-by-cost remain the authoritative drift consequences.

## Language boundary

### Lean

Lean proves that declared, admissible premises satisfy transition guards, acceptance, or settlement rules. It does not prove that an external event occurred because Rust serialized it.

### Rust

Rust executes transitions and owns sealed configuration identity, append-only evidence, resource accounting, authority enforcement, and state projection from events.

### Python

Python supports contract-authoring ergonomics, experiments, estimators, calibration, drift analysis, and distribution inspection. Convenience does not make it the authority for acceptance semantics.

## What Q1/L1 can establish

Q1/L1 is deliberately one configuration-specific observation. It can establish whether Envelope can:

- preserve one admissible traversal from invocation through settlement;
- separate agent, VM, evaluator, trusted-machine, wall, and human observations;
- distinguish candidate failure from infrastructure or evidence failure;
- expose one bounded remediation transition if the initial candidate fails admissibly;
- keep evaluator material outside the candidate’s authority;
- preserve unknown and right-censored costs instead of inventing totals.

Q1/L1 cannot estimate:

- transition probabilities;
- a reusable cost-to-acceptance distribution;
- path dependence;
- a comparable-work class;
- harness treatment effects;
- qualification half-life or drift.

Lima isolation does not remove identity and access from the model. It fixes or exposes them so one run’s boundary is more reproducible. VM provisioning, synchronization, teardown, and failures remain transitions with costs.

## Reading Q1/L1 after completion

Read Q1's [`FINDINGS.md`](../q1-trusted-agent-code/FINDINGS.md) in this order:

1. **Admissibility:** Was the disposition supported, or did infrastructure/evidence failure make the run inconclusive?
2. **Path:** Which declared and unexpected transitions actually occurred?
3. **Cost:** Which resource intervals were observed, unknown, or right-censored?
4. **Remediation:** Did it occur, and did failure history appear relevant to its cost or outcome?
5. **Boundary:** Which state variables did isolation fix, expose, or fail to control?
6. **Decision:** What single unresolved claim now blocks the next useful inference?

Do not choose Q1/L2 from the terminal disposition alone. An accepted run with incomplete cost evidence may teach less about Envelope than an inconclusive run that precisely locates a broken measurement boundary.

## Choosing the next loop

| Q1/L1 evidence | What remains unknown | Candidate next move |
|---|---|---|
| Acceptance meaning, evaluator validity, or human-review rule fails | The target itself is not validly settled | Return to human review of Q1 or the contract. Do not price or repeat it. |
| Infrastructure or evidence fails at a precise boundary | Whether the traversal can be measured reproducibly | Define the smallest loop that tests that boundary. Do not broaden to harness comparison. |
| Terminal run is valid but material cost fields remain unknown | Whether repeated runs would produce trustworthy cost evidence | Test accounting and reproducibility under the same contract/configuration. |
| Terminal run and cost trace are valid | Run-to-run disposition and cost variability | Prefer a repeated-trial Q1/L2 under the same contract/configuration. |
| Later repeated trials show history predicts remaining outcome or cost | Current state omits a load-bearing variable | Test the smallest augmented state against a simpler attempt-level model. |
| Later repeated trials are stable under a simple state | Whether a harness changes accepted yield or cost | Compare flat append-context and decomposition harnesses under the same contract, model, evaluator, and budget. |

The likely Q1/L2 after a valid Q1/L1 is therefore **repeated-trial qualification of the baseline**, not immediate harness comparison. One run cannot supply the counterfactual or variance needed to interpret a harness effect.

Do not choose a repetition count before Q1/L1 reveals per-run cost and failure shape. The human should approve the smallest sample and stopping rule capable of changing the next decision.

## Candidate Q1/L2 question

If Q1/L1 produces a valid, sufficiently complete traversal, the next question could be:

> Under the same acceptance contract and declared configuration, what empirical distribution of terminal disposition and observed cost is supported across independent runs?

That loop would unlock a decision between:

- treating the baseline as repeatable enough for a later harness comparison;
- running a separate state-sufficiency loop because history appears predictive;
- improving accounting or execution qualification before further pricing work;
- stopping because the attainable sample cannot support a distributional claim.

Its output should be the empirical acceptance-by-cost distribution with explicit failure mass. State-model comparison belongs in a later loop unless Q1/L2 predeclares it as the single targeted unknown and has enough held-out runs to score it.

## Stop claims

Until evidence earns them, do not claim that:

- Q1/L1 estimates a probability distribution;
- AI work is memoryless;
- a token-similar trajectory defines comparable work;
- isolation eliminates environment dependence;
- verification/remediation ledger categories equal a causal premium;
- a harness changes cost-to-acceptance.

The state process is already useful as execution semantics. It should become Envelope’s statistical model only if it improves prospective decisions over direct repeated-run evidence.
