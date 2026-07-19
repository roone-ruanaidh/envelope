# Contract-to-harness pricing — candidate architecture and experiment

- **Candidate date:** July 15, 2026
- **Disposition:** candidate — experimental framing, unpromoted, and unsequenced
- **Source study:** [Codex and Grok Build: anatomy of two Rust coding-agent harnesses](qualified-harnesses/README.md)

## Objective

Define and test the smallest useful connection among:

1. a task contract and its acceptance obligations;
2. the Lean layer that verifies what can genuinely be proved;
3. the Rust harness components selected to pursue and evidence those obligations;
4. the compiled harness configuration actually executed; and
5. the probability distribution of cost required to reach accepted completion.

The initial product objective is **comparison and cost visibility**, not automatic optimization. Envelope should help a person compare configurations they are considering, understand where cost is certain or uncertain, see where cost is likely to be incurred, and choose among qualified options with greater confidence.

Envelope does not set a price, optimize a margin, or initially decide which configuration a person must use. A later feature may recommend or automatically route to a cost-effective configuration for a novel task, but that is downstream of the more foundational ability to produce honest, comparable estimates for user-selected choices.

## Central experimentation question

> What is the smallest compositional interface between a contract obligation, the controller component chosen to address it, the evidence it must produce, and the cost transition it induces?

The operational test is:

> Can that interface support honest comparison of user-selected compiled harness configurations for cost-to-accepted-completion, without hiding uncertainty or requiring an automatic optimizer?

This is the candidate's primary research question. The object being tested is not a universal harness implementation. It is the interface that connects contract semantics, harness composition, admissible evidence, and observed cost.

## Starting position

A task begins as broad human intent. That intent is not itself a proof object and may contain ambiguity, preference, judgment, and claims that cannot be closed computationally. The task layer produces a versioned contract that narrows the intent into explicit acceptance criteria, constraints, assumptions, and unresolved uncertainty.

The contract then drives two related processes:

1. determine the basis on which each acceptance obligation could be established; and
2. determine what harness capabilities and evidence would be required to pursue it.

The harness should not be selected first and retrofitted to the contract. The contract should determine the required sensors, actuators, authority, evidence, and controller behavior. Model, harness, tools, context, infrastructure, and verification are configuration choices made relative to those requirements.

```text
broad intent
→ versioned task contract
→ acceptance obligations and uncertainty
→ proof and evidence requirements
→ feasible harness components
→ compiled harness configurations
→ execution evidence and incurred cost
→ acceptance reconciliation
→ comparative cost-to-accept distributions
```

## Three distinct claim bases

The architecture must not collapse formal proof, empirical observation, and statistical belief into one notion of truth.

### Formally provable

Lean owns statements that can be represented as explicit propositions and checked from admissible premises. It can verify contract consistency, implications among criteria, proof-carrying acceptance conditions, and whether a formally represented settlement rule follows.

Lean does not make an external measurement true merely because Rust serialized it correctly. Where a theorem depends on an observed premise, Lean may verify the logical consequence of that premise while the evidence system separately identifies the measurement and its trust basis.

### Empirically verifiable

Rust owns execution and observational evidence:

- a named test suite passed on an identified target;
- an artifact has a particular digest;
- a command exited with a recorded result;
- a sandbox control was requested and observed as applied;
- a tool changed a declared set of files;
- a provider returned a request receipt;
- a reviewer or external evaluator returned a signed decision.

These are evidence-backed claims about an execution instance. They are not timeless proofs about every possible execution.

### Statistical, judgmental, or unresolved

Some obligations remain probabilistic or partly inaccessible:

- semantic quality outside a formal specification;
- absence of all regressions;
- provider-internal custody or routing that is not exposed;
- whether a generated design is tasteful or appropriate;
- whether observed task performance transfers to a novel task;
- whether a human reviewer would accept a borderline result.

These should remain explicit statistical qualifications, human-review requirements, or unresolved claims. They must not be silently upgraded to proof or averaged out of the price estimate.

A provisional shared representation might distinguish:

```text
Formal(proof reference)
Observed(evidence predicate)
Statistical(qualification reference)
Human(review policy and result)
Unresolved(reason and consequence)
```

The stable semantics of this representation must be earned experimentally before promotion into a shared IR.

## Lean, Rust, and pricing

The three layers have different responsibilities.

### Lean: acceptance logic

Lean answers:

> Given these typed and admissible premises, does the contract's acceptance conclusion follow?

Lean should own:

- formally represented acceptance conditions;
- proof verification;
- logical composition of criteria;
- admissibility and implication rules;
- proof-carrying transformations of contracts;
- settlement rules that can be stated formally.

It should not own natural-language intent interpretation, empirical execution, or probabilistic performance estimation.

### Rust: controller realization and evidence

Rust answers:

> Which exact configuration ran, what authority did it have, what occurred, and what evidence was produced for each contract premise?

Rust should own:

- compiled harness configuration;
- model/provider adapters;
- prompt and context construction;
- tools, permissions, and execution;
- infrastructure and sandbox enforcement;
- retries, scheduling, cancellation, and resource limits;
- append-only evidence and artifact custody;
- requested-versus-applied enforcement receipts;
- run-level cost and usage observations.

### Pricing: comparative cost visibility

Pricing answers:

> For this contract and this selected configuration, what distribution of cost is supported for reaching accepted completion, what contributes to it, and how uncertain is the estimate?

The initial pricing layer should estimate and compare, not choose or route. Its output should make visible:

- costs known before execution;
- variable costs expected during execution;
- remediation and verification costs that appear only on some trajectories;
- costs already incurred during a live task;
- remaining estimated cost to acceptance;
- evidence gaps and uncertainty that weaken the estimate;
- dimensions on which two configurations are not fairly comparable.

Uncertainty should appear as a distribution or explicit unknown, not as an unexplained markup.

The handoff is:

```text
Lean:
  If these premises hold, the contract is accepted.

Rust:
  Here is identified evidence and uncertainty for each premise,
  produced by this exact compiled harness on this exact target.

Pricing:
  Here is the observed and estimated cost distribution for producing
  enough admissible premises to reach acceptance with this configuration.
```

## Control-system interpretation

The model is the central stochastic plant. The harness is the controller built around it to pursue a contract reference under authority, budget, and evidence constraints.

| Control-system concept | Envelope concept |
|---|---|
| Reference | Task contract and acceptance threshold |
| Plant | Model interacting with the task environment |
| Controller | Compiled harness policy |
| Actuators | Model calls, tools, infrastructure, and human escalation |
| Sensors | Proof checkers, tests, evaluators, evidence collectors, and reviewers |
| State estimate | Context projection plus execution journal |
| Control law | Prompting, tool routing, scheduling, retries, model routing, and completion policy |
| Constraints | Contract, authority, sandbox, custody, infrastructure, and budget |
| Disturbances | Model stochasticity, provider drift, environment variation, and failures |
| Terminal condition | Reconciled accepted completion or declared inability to close the contract |
| Control cost | Inference, tools, infrastructure, verification, remediation, review, and cleanup |

This metaphor explains why harness configuration affects cost-to-accept. It does not require Envelope to implement an optimal controller. The initial system can expose several qualified controller realizations and their comparative distributions, leaving the choice to the user.

## Harness components versus compiled harnesses

The Codex and Grok Build study suggests two distinct catalogs.

### Component catalog

Components are reusable controller parts with explicit contracts:

- model and provider adapter;
- prompt program;
- tool profile;
- context policy;
- scheduler and concurrency policy;
- completion policy;
- retry and recovery policy;
- execution and sandbox backend;
- infrastructure profile;
- evidence collector;
- evaluator or proof adapter;
- human-review policy.

Each component should eventually identify:

- version and artifact digest;
- required and provided capabilities;
- typed input/output contract;
- authority introduced;
- evidence produced;
- compatibility constraints;
- known failure modes;
- observed cost behavior;
- operational design domain;
- qualification status and validity interval.

Component qualification is reusable evidence. It is not a claim that every arbitrary composition is qualified.

### Compiled harness catalog

A compiled harness is a complete controller realization assembled for a declared contract or contract class:

```text
model and route
+ effective prompt
+ advertised and executable tools
+ context and compaction policy
+ scheduling and result-ordering policy
+ completion and recovery policy
+ permissions and applied sandbox
+ infrastructure target
+ evidence profile
+ run limits
```

Compilation should resolve compatibility, reject missing requirements, freeze effective configuration, and produce a digestible identity. Each inference may derive an immutable step snapshot, but the compiled harness is the broader reusable catalog object.

A qualified compiled harness should publish:

- the contract classes for which evidence exists;
- exact component identities;
- execution-platform identity;
- acceptance, cost, time, and remediation distributions;
- evidence quality and custody properties;
- known failure modes and incomparable dimensions;
- observation period, validity, and drift signals;
- downloadable Rust artifact and configuration where applicable.

This is the “pre-made harness” offered to someone who does not want to perform their own qualification and pricing work.

## What Codex and Grok Build contributed

The repositories are evidence about useful component boundaries, not finished Envelope harness kits.

### Codex patterns

Codex contributes:

- an immutable per-inference `StepContext` binding advertised capability to execution state;
- a narrow Responses-oriented transport surface;
- explicit model capability metadata;
- separation between advertised and executable tools;
- deterministic model-visible result ordering despite concurrent work;
- incremental prompt/context updates designed for stable prefixes;
- command approval and sandbox orchestration;
- history normalization and reconstruction checkpoints.

These suggest reusable snapshot, model, tool-planning, scheduling, context, and execution components.

### Grok Build patterns

Grok Build contributes:

- canonical conversation types spanning three wire protocols;
- typed tool arguments and outputs with generated JSON Schema;
- prompt construction from reusable context and templates;
- explicit sequential preflight before concurrent tool execution;
- reusable context pruning and compaction traits;
- classified retry and recovery policies;
- completion requirements and structured-output recovery;
- reuse of the session machinery for child harnesses;
- long-lived terminal and local/remote workspace abstractions.

These suggest reusable protocol, prompt, typed-tool, completion, recovery, context, and execution components.

### Negative findings that shape Envelope

Neither repository provides the complete modular evidence system Envelope requires:

- neither has a complete crash-safe evidence journal spanning every request, decision, side effect, enforcement control, and cost;
- not every effect passes through one typed authority and execution gateway;
- configured policy can differ from observed enforcement;
- OS and remote-execution behavior materially change the harness target;
- side-effecting retries can replay partially completed work;
- component interactions are substantial;
- product composition roots obscure which behavior belongs to the reusable kernel;
- some Grok tool implementations share lineage with Codex or OpenCode, so similarity is not independent validation.

The study therefore supports extracting candidate interfaces and testing them. It does not justify copying either architecture wholesale or promoting a universal component schema immediately.

## Comparison, not initial optimization

The first product should answer a comparative question selected by the user:

```text
For contract T, compare compiled configurations A, B, and C.
```

For each configuration, the interface should expose:

| Output | Meaning |
|---|---|
| Qualification applicability | Whether evidence supports using this estimate for the declared task/contract class |
| Cost-to-accept distribution | Probable total cost, including verification and remediation |
| Acceptance probability | Observed probability of reaching the declared threshold within the run policy |
| Cost attribution | Inference, tools, infrastructure, verification, remediation, review, and cleanup |
| Time distribution | Expected and tail completion times where supported |
| Evidence coverage | Which contract obligations are formally, empirically, statistically, or humanly covered |
| Uncertainty | Sampling error, transfer limits, hidden provider state, drift, and unresolved criteria |
| Incomparability | Dimensions on which configurations do not support a fair ranking |
| Current incurred cost | What has already been spent during an active execution |
| Estimated remaining cost | Conditional estimate from the current execution state to acceptance |

The interface may show trade-off frontiers and sortable choices. It should not initially compute an opaque optimum or automatically purchase a route on the user's behalf.

An optimizer could later consume the same comparison model:

```text
given contract, constraints, and preferences
→ select a configuration or adaptive policy
→ execute automatically
```

That is a possible product feature, not a prerequisite for comparative pricing. Deferring it simplifies the initial mathematics and keeps Envelope centered on visibility, qualification, and informed choice.

## Pricing object

The priced object is the trajectory to accepted completion under a selected compiled configuration, not a token and not merely one attempt.

```text
total cost to accepted completion
  = model inference
  + tools and infrastructure
  + proof and empirical verification
  + retries and remediation
  + human review or escalation
  + failed-attempt and cleanup cost
```

For task contract `T` and selected compiled harness `H`, the initial target is a conditional estimate such as:

```text
P(total cost, elapsed time, acceptance outcome
  | contract T, compiled harness H, target identity, evidence profile)
```

Envelope presents this conditional distribution and its assumptions. It does not initially solve:

```text
argmin H expected_cost(T, H)
```

The latter may become a recommendation or automatic-ordering feature after the underlying estimates are calibrated and users can inspect why configurations differ.

## Component effects are not automatically additive

Modularity supports reuse, but it does not make cost contributions independent.

Important interactions include:

```text
model × prompt
model × tool schema
model × context policy
tool profile × sandbox
retry policy × side effects
completion policy × evaluator quality
OS × execution backend
```

A better context policy may reduce retries. A new tool may reduce inference cost while increasing authorization and verification cost. Parallel execution may lower median time while increasing conflict and remediation risk.

Therefore:

- component qualification supplies reusable priors and compatibility evidence;
- compiled-harness qualification measures the assembled behavior;
- comparisons must preserve material interaction terms;
- a component's observed marginal effect must be scoped to the configurations in which it was measured.

This is still simpler than automatic optimization. The initial system needs defensible conditional comparisons, not a globally optimal policy over every possible configuration.

## Three project layers

### 1. Reusable methodology

The methodology allows others to construct and price their own configurations. It should define:

- contract and claim-basis semantics;
- proof/evidence/human/unknown separation;
- component and compiled-harness identity;
- evidence and custody requirements;
- qualification experiment design;
- cost boundaries and attribution;
- comparability and incomparability;
- uncertainty, calibration, validity, and drift.

### 2. Qualified harness catalog

The catalog provides choices users can trust without repeating the entire methodology:

- qualified reusable components;
- precompiled task-specific harnesses;
- applicability and compatibility information;
- downloadable Rust artifacts and configurations;
- evidence profiles;
- comparative cost-to-accept observations;
- validity windows and drift warnings.

The component catalog supports builders. The compiled-harness catalog supports users who want a ready-made controller.

### 3. Budgetable ordering

The initial ordering layer should make selection and execution legible:

```text
declare or select a task contract
→ select configurations to compare
→ inspect cost, uncertainty, evidence, and trade-offs
→ choose a configuration
→ execute through an SDK or interface
→ observe incurred cost and evidence
→ reconcile accepted completion
```

Ordering initially means making qualified choices executable and budgetable. It does not require automatic configuration optimization.

## Candidate experimental program

The central interface should be tested with ordinary experiment artifacts before any shared IR is promoted.

### Phase 1 — obligation partition

Choose one bounded task contract and classify every acceptance obligation as formal, observed, statistical, human, or unresolved. Record disagreements and criteria that cannot be represented without changing their meaning.

### Phase 2 — component requirements

For each obligation, declare:

- the controller capability intended to address it;
- the evidence required to evaluate it;
- the authority and infrastructure required;
- the costs that should be observed;
- the uncertainty that remains after evidence collection.

### Phase 3 — compiled configurations

Assemble a small set of configurations that differ in controlled ways. Examples include:

- same model and tools, different context policy;
- same harness components, different model;
- same model, different tool authority;
- same logical configuration on macOS and Linux as explicitly different target classes;
- simple completion rule versus evaluator-backed completion.

The user-selected comparison framing should remain primary. The experiment need not choose a winner automatically.

### Phase 4 — repeated execution and reconciliation

For every run, preserve:

- compiled harness identity;
- contract and obligation identities;
- formal proof results;
- empirical and human evidence;
- unresolved claims;
- model, tool, infrastructure, verification, remediation, and cleanup cost;
- acceptance result and time;
- requested and applied enforcement.

### Phase 5 — comparison and transfer

Evaluate whether:

- configurations can be compared under a declared profile;
- cost attribution is consistent enough to be useful;
- uncertainty is legible before purchase time;
- component effects transfer across nearby compiled harnesses;
- material interactions can be identified rather than hidden;
- the same interface supports both self-priced configurations and catalog harnesses.

## Success criteria

The candidate survives if the experiment demonstrates that:

1. contract obligations can be partitioned without conflating proof, observation, statistics, and judgment;
2. a small component interface can connect obligations to required capabilities and evidence;
3. compiled harnesses can be deeply identified and reproduced;
4. cost-to-accept distributions can be compared for user-selected configurations under explicit assumptions;
5. certain, uncertain, incurred, and remaining cost can be distinguished;
6. component evidence is reusable within a declared domain without pretending compositions are additive;
7. the same underlying records can support methodology users, catalog users, and ordering users.

## Falsifiers and walls

Re-derive the design rather than patching around any of these outcomes:

- contract obligations cannot be partitioned without destroying their intended meaning;
- Lean premises require empirical facts whose trust basis cannot be represented honestly;
- component boundaries change radically across every task;
- assembled-harness interactions make component qualification non-transferable even to adjacent configurations;
- cost categories cannot be measured consistently enough for meaningful comparison;
- the interface encourages users to interpret weak or incomparable evidence as a total ranking;
- incurred and remaining costs cannot be reconciled against the original estimate;
- compiled identity cannot capture the behavior-changing configuration surface;
- the methodology and catalog require incompatible records.

A falsifier may imply experiment-specific qualified sets rather than a universal component catalog. That is an acceptable outcome.

## Non-goals for the initial candidate

- Automatically choose the cheapest configuration.
- Optimize provider margin or set market prices.
- Route every novel task without direct evidence.
- Formalize all broad human intent in Lean.
- Treat empirical evidence as formal proof.
- Build a universal provider or harness abstraction before experiments establish stable semantics.
- Assume component cost contributions are independent.
- Collapse macOS, Linux, remote, or managed execution into one harness identity.
- Promote the candidate into `src/` before repeated experiments justify it.

## Long-term extension

If the comparative methodology becomes calibrated, the same records may eventually support:

- recommendations based on user preferences and constraints;
- automated selection among qualified configurations;
- adaptive fallback policies;
- real-time estimates for novel tasks using nearby contract/configuration evidence;
- an orderable SDK that can execute a selected or recommended configuration.

Those extensions should consume an inspectable comparison model. They should not replace it. The foundational product remains increased awareness before purchase time: what a selected inference configuration is likely to cost to reach accepted completion, why, where uncertainty remains, and what evidence supports the estimate.

## Next artifact if resumed

The next artifact should be an experiment-local **contract–component–evidence–cost interface sketch** containing only the types needed to run the candidate experiment:

```text
TaskContract
AcceptanceObligation
ClaimBasis
HarnessRequirement
HarnessComponent
CompiledHarness
ExecutionEvidence
AcceptanceReconciliation
CostObservation
ConfigurationComparison
```

It should be tested against one bounded contract and several controlled compiled harness configurations. It should not be promoted as the Envelope object model until the experiment shows which semantics remain stable.
