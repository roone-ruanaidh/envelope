# Envelope

Envelope is an open, local-first system for buying AI work by outcome instead of by token.
It begins when desired work is expressed as an executable acceptance contract, then assesses feasibility, resolves an evidence-backed computation-and-verification plan with projected cost and uncertainty, and settles the realized computation against the contract.

Broad outcome intent is not automatically an acceptance contract. Envelope must never silently invent, weaken, or claim measurability for one. A condition remains unresolved until its settlement rule and required evidence are explicit.

## Economic object

Per-token pricing measures an input, not the price of a realized output.
Envelope makes as many relevant variables as possible legible before computation is purchased—models or weights, hardware, data, context, tools, authority, policies, turns, budgets, verification, and human attention—then checks that the computation purchased is the computation received.
That includes the negative space: actions, access, and scope that were not purchased must not be exercised.

The unit of account is an **accepted completion under a declared local contract**, not a token, model call, or nominally successful run.
Its accounting boundary includes generation, failed attempts, infrastructure, verification, controls, telemetry, review, remediation, and cleanup. Unresolved uncertainty remains visible rather than being priced by default, and different cost bearers are not silently collapsed into one scalar.

```text
declared order
  → kernel-checked receipt
  → accumulated comparable settlements
  → evidence-backed task-class pricing
```

The desired output remains partly unknown.
The mathematical kernel's role is to stabilize what `accepted` means across runs—not to turn empirical evidence, human judgment, or assumptions into proof.

## System direction

Envelope's target is an open economic control plane for probabilistic computation.
Given an operational acceptance contract, reliability target, hard constraints, and accounting boundary, it should return an evidence-backed feasible frontier, an admissible plan, or a structured infeasibility result.
Realized evidence settles to `Accepted`, `Rejected`, or `Inconclusive`.

The architectural default is local-first and open until measured infrastructure requirements make centralization necessary rather than convenient.
The organization or individual should own its contracts, data, prompts, tools, identities, execution history, costs, and qualification evidence.

The provisional language boundary is:

- **Lean** for the normative mathematical and epistemic kernel: admissibility, constraint preservation, proof boundaries, and settlement properties that can actually be proven;
- **Rust** for the stateful systems layer: orchestration, execution, adapters, evidence collection, storage, concurrency, identity, and deployment;
- **Python** as an early SDK and research interface because of its AI ecosystem and ergonomics, not as a settled trusted-core dependency.

Shared implementation enters `src/` only after its supporting evidence earns promotion. Research is the product-building process.

## Experiments

The [`exp/`](exp/) tree holds candidates, approved experiments, and their evidence. Repository co-location is not promotion.

[`E1`](exp/e1/) measures the cost of moving one agent-produced lease service from declared completion to accepted completion under a frozen contract and settlement procedure. Its human-authored contract, sealed behavioral evaluator, defective-implementation bank, review gate, isolated authoring environment, and decomposed cost ledger form the first vertical slice of the method.

GitHub issues hold lifecycle state, priority, and sequence. Structured manifests and result records hold machine-readable state and evidence. Experiment READMEs describe only the durable question, method, boundaries, and reproduction interface.

## Governance

- A **candidate** is preserved, unsequenced, and unnumbered.
- An **experiment** has an approved question, method, evidence plan, stopping rule, and `eN` identifier.
- A **completed** experiment has its declared settlement and report; completion is not promotion.
- A **promoted** artifact has been explicitly adopted into Envelope after review of its evidence.

Every experiment passes three gates: charter, settlement, and promotion. Accepted, rejected, and inconclusive are valid settlements. An experiment may contain stages, runs, and arms without creating new experiments. Keep one active experiment unless another is explicitly approved.

Artifacts leave `exp/` for `src/` only through an explicit promotion decision.

## Repository

```text
AGENTS.md                              working agreement
exp/eN/                               experiments and evidence
exp/candidates/                       preserved, unsequenced candidates
docs/FOUNDATIONS_RESEARCH_2026-07-10.md  dated research record
src/                                  promoted implementation only
docs/                                 durable research and ADRs
```

Prefer contracts, configuration, code, and tests for exact behavior; structured artifacts for state and evidence; and GitHub issues for planning. Add prose only when it records durable context that cannot live more precisely in one of those places.
