# Envelope

Envelope is an open, local-first system for pricing AI work by outcome instead of by token.

It begins when desired work is expressed as an executable acceptance contract, then assesses feasibility, resolves an evidence-backed computation-and-verification plan with projected cost and uncertainty, and settles the realized computation against the contract.

Broad outcome intent is not automatically an acceptance contract. Envelope must never silently invent, weaken, or claim measurability for one. 
A condition remains unresolved until its settlement rule and required evidence are explicit.

## Economics

Per-token pricing measures an input, not the price of a realized output.

Envelope makes as many relevant variables as possible legible before computation is purchased—models or weights, hardware, data, context, tools, authority, policies, turns, budgets, verification, and human attention—then checks that the computation purchased is the computation received.

That includes the negative space: actions, access, and scope that were not purchased must not be exercised.

The unit of account is an **accepted completion under a declared local contract**, not a token, model call, or nominally successful run.

Its accounting boundary includes generation, failed attempts, infrastructure, verification, controls, telemetry, review, remediation, and cleanup. 
Unresolved uncertainty remains visible rather than being priced by default, and different cost bearers are not silently collapsed into one scalar.

```text
declared order
  → kernel-checked receipt
  → accumulated comparable settlements
  → evidence-backed task-class pricing
```

The desired output remains partly unknown.
The mathematical kernel's role is to stabilize what `accepted` means across runs—not to turn empirical evidence, human judgment, or assumptions into proof.

## Direction

Envelope's current target is an open economic control plane for probabilistic computation.
Given an operational acceptance contract, reliability target, hard constraints, and accounting boundary, it should return an evidence-backed feasible frontier, an admissible plan, or a structured infeasibility result.
Realized evidence settles to `Accepted`, `Rejected`, or `Inconclusive`.

The architectural default is local-first and open until measured infrastructure requirements make centralization necessary rather than convenient.
The organization or individual should own its contracts, data, prompts, tools, identities, execution history, costs, and qualification evidence.

The provisional language boundary is:

- **Lean** for the normative mathematical and epistemic kernel: admissibility, constraint preservation, proof boundaries, and settlement properties that can actually be proven;
- **Rust** for the stateful systems layer: orchestration, execution, adapters, evidence collection, storage, concurrency, identity, and deployment;
- **Python** as an early SDK and research interface because of its AI ecosystem and ergonomics, not as a settled trusted-core dependency.

## Experiments

Envelope is built through experimentation.
The [`exp/`](exp/) directory holds candidates, active experiments, and their evidence.

Artifacts leave `exp/` for `src/` **only** through an explicit promotion decision.

### Work

- **Candidate:** preserved, unsequenced, and unnumbered.
- **Experiment:** approved question, method, evidence plan, and stopping rule. An `eN` identifier is assigned at approval.
- **Completed:** the declared settlement and report exist. Completion is not promotion.
- **Promoted:** the user has reviewed the evidence and explicitly adopted an artifact into Envelope.

An experiment may contain stages, runs, and arms; these do not create new experiments. Keep one active experiment unless the user explicitly approves another.

### Gates

1. **Charter:** approve the experiment and assign its `eN` identifier.
2. **Settlement:** apply the declared rule; accepted, rejected, and inconclusive are valid results.
3. **Promotion:** promote, extend, retire, or return the result for more evidence.

### Tracking and ownership

GitHub issues are the work registry. Candidate issues imply neither priority nor sequence.

Within the Envelope repository, `exp/` owns candidates, experiments, evidence, and promotion reviews. 
Promoted artifacts move to the narrowest appropriate repository surface.

Documentation is primarily captured in READMEs, `src/` and `tests/` code, and `exp/` subdirectories. `docs/` is intentionally limited to durable research and necessary ADRs.

## Repository

```text
AGENTS.md                              working agreement
docs/                                 durable research and ADRs
exp/eN/                               experiments and evidence
exp/candidates/                       preserved, unsequenced candidates
src/                                  promoted implementation only
```
