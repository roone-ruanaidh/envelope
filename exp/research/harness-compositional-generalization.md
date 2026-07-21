# Harness compositional generalization — implications for Envelope

- **Research date:** July 20, 2026
- **Status:** unpromoted research; no qualification or pricing claim
- **Primary source:** Alex L. Zhang and Omar Khattab, [“Language model harnesses are compositional generalizers”](https://alexzhang13.github.io/blog/2026/harness/), July 2026
- **Stable source snapshot:** [post source at `b076105`](https://github.com/alexzhang13/alexzhang13.github.io/blob/b076105332a2004c81afe108d5d417bbc1f1f333/_posts/2026-07-20-harness.md)
- **Envelope context:** [`README.md`](../../README.md)

The post is an early empirical argument about **RL training generalization** through one Recursive Language Model (RLM) harness. Envelope concerns the **inference-time distribution of total cost required to satisfy a fixed acceptance contract**. The connection is worth testing; the post does not establish it.

Numeric discipline: the source does not publish raw data or tabulated Figure 1 values. Values marked `≈` below are visual readings from the [summary plot](https://alexzhang13.github.io/assets/img/lm_compo/fig1b_length_strategy_generalization_lift.png), not reported exact estimates. The post-reported ratios and task ranges are stated as reported, including internal inconsistencies.

## 1. Core claims

### Central argument

The authors argue that a harness should be treated as a high-level inductive bias, not merely a tool adapter. A good harness decomposes an unfamiliar, complex environment state into observations that are familiar and simple enough for each underlying LM call. If structurally different tasks thereby induce nearly the same root-model trajectory, training on one can transfer across task length or domain.

This is partly demonstrated and partly mechanistic hypothesis:

| Status | Claim |
|---|---|
| **Demonstrated in the reported setting** | RL training of Qwen3-30B-A3B-Instruct-2507 as an RLM transfers better than training the same base Transformer directly on six length-shift and three cross-domain task pairs. |
| **Supported by proxy, not established** | RLM eval trajectories are lexically and length-wise closer to prior train trajectories than Transformer + YaRN trajectories. |
| **Hypothesized mechanism** | Context offloading and programmatic sub-calls induce task equivalence classes, keep individual calls locally in-distribution (LID), and therefore cause the transfer. There is no component ablation establishing this causal chain. |
| **Broader hypothesis** | Compositional generalization must largely live in the harness, and better harnesses will improve the coefficient on data scaling. The experiments do not establish necessity, universality, or production economics. |

### Finding 1 — short-task training transferred to longer tasks

The [length experiment](https://alexzhang13.github.io/assets/img/lm_compo/fig5_length_generalization_curves.png) used one model, six environments, 150 RL steps, batch size 64, four rollouts per sample, and evaluation every 10 steps. The RLM, a decomposition-nudged RLM variant, and a base Transformer with YaRN trained only on short splits; evaluation used longer held-out splits.

| Environment | Train → eval range as reported | Multiplier / qualification |
|---|---:|---|
| MRCRv2 | 64k → 2M tokens | 31.25× context. The prose says 2 needles → 8 needles; Figure 6 says 8 needles → 8 needles. |
| GraphWalks | <128k → >1M tokens | More than about 8×, but endpoints are not exact. |
| LongBench-Pro | 32k → 256k tokens | 8×. |
| OOLONG | 32k → 256k tokens | 8×. |
| OOLONG-Pairs | 8k → 32k input; 7k → 146k output | 4× input; about 20.9× output. This does not literally fit the blanket “8–32× longer in context length” description. |
| Ada-LEval | 8k → 128k tokens | 16×. |

Mean lift in Figure 1:

| Arm | Short-train mean Δ lift at step 150 | Long-eval mean Δ lift at step 150 | Eval peak |
|---|---:|---:|---:|
| RLM | ≈0.32 | ≈0.42 | ≈0.44 around step 140 |
| Transformer + YaRN | ≈0.15 | ≈0.04 | ≈0.05 |

The final-checkpoint eval-lift ratio is therefore about 10–11×, consistent with the post’s “roughly 10x” claim. The plotted final train lifts are not numerically the same: ≈0.32 versus ≈0.15. “With the same train lift” should not be imported as a literal equality without raw data or author clarification.

All six RLM long-eval curves improved from step 0; base-Transformer long-eval curves were generally flat even when short-train reward rose. On MRCRv2, GraphWalks, OOLONG, and OOLONG-Pairs, the trained Qwen RLM approached or exceeded the plotted GPT-5.5 RLM reference. The MRCRv2 Transformer baseline was omitted because even context extension could not fit 2M tokens.

Important boundary: the RLM did not reliably discover the transferable strategy unaided. On MRCRv2 it initially learned the short-only shortcut of delegating the whole task to one sub-call; a decomposition hint improved the result. The summary aggregation does not say clearly whether it uses the base or nudged RLM series.

### Finding 2 — training transferred across selected sibling domains

The [strategy experiment](https://alexzhang13.github.io/assets/img/lm_compo/fig6_strategy_generalization_curves.png) used three author-selected pairs with different surface token distributions but a claimed shared decomposition. Training ran for 500 steps and evaluation occurred every 20 steps.

| Train domain | Eval domain | Metric |
|---|---|---|
| OOLONG TREC coarse questions | OOLONG spam/ham questions, also 32k → 132k | avg@1 reward |
| OBLIQ writing author/style search | OBLIQ math proof-strategy search | nDCG@10 |
| OBLIQ Twitter stance search | OBLIQ WildChat latent-error search | nDCG@10 |

Mean lift in Figure 1:

| Arm | Source-train mean Δ lift at step 500 | Sibling-eval mean Δ lift at step 500 | Eval peak |
|---|---:|---:|---:|
| RLM | ≈0.30 | ≈0.19 | ≈0.25 |
| Transformer + YaRN | ≈0.47 | ≈0.07 | ≈0.08 |

The RLM’s final mean eval lift is about 2.5–3× the base arm, not 10×. The base arm learned the source tasks more, yet transferred less; some early base-arm OBLIQ improvement came from learning output format and then diminished. This is the strongest evidence that the observed effect is not merely long-context capacity. It remains conditional on three pairs selected because the authors believed they shared a strategy; there is no negative-control set of non-sibling domains.

### Finding 3 — eval trajectories were closer to prior train trajectories

At the best checkpoint, the authors compare each eval rollout with its nearest earlier train trajectory. The [analysis](https://alexzhang13.github.io/assets/img/lm_compo/fig7_trajectory_similarity.png) covers five of six length experiments—the MRCRv2 base arm is absent—and all three strategy experiments. It uses token-level normalized edit distance, word 3-gram containment, 3-gram Jaccard, weighted Jaccard, and a content-blind length ratio.

Across the eight reported panels, RLM similarity exceeds Transformer + YaRN on all five proxies. The exact labels printed for RLM span:

| Proxy | RLM similarity range across panels |
|---|---:|
| Token edit | 0.18–0.38 |
| 3-gram containment | 0.14–0.39 |
| 3-gram Jaccard | 0.07–0.24 |
| Weighted Jaccard | 0.41–0.66 |
| Length ratio | 0.82–0.96 |

This demonstrates greater surface and length similarity under these nearest-neighbor proxies. It does **not** demonstrate semantic equivalence, similar output distributions, LID, or equal task difficulty. Best-checkpoint selection and nearest-train matching also make this a favorable retrospective comparison.

### Finding 4 — the measured cost was higher

On similarly sized training tasks, RLM training took **1.5–3× longer** than direct Transformer training because each sample used multiple steps and waited on sub-calls. The post also says memory cost was higher but gives no memory number. It says training a simple ReAct agent for a 30B model on 8×H100 was difficult because of context bloat, but reports no controlled ReAct cost result.

This is **training runtime**, not inference cost per accepted task. The post does not report tokens, dollars, inference-time runtime, tool cost, retries, verification, remediation, tail latency, or cost-to-acceptance.

## 2. Formal objects

### Harness

An agent observes environment state `s`, chooses action `a`, and interacts with environment `E`. The post writes the harness as

\[
H : s \rightarrow a.
\]

`H` is the program between world and neural network. It encodes an arbitrarily large state into one or more LM observations `o` and determines the next action. This signature suppresses stochasticity, history, model parameters, multiple calls, and internal memory; it describes the interface, not a complete mathematical model.

**Class-tightening role:** rather than serialize all of `s` into one task-specific prefix, `H` can expose a shared decomposition procedure to the root model and route instance-specific data elsewhere. More different external states then yield similar root observations.

### Locally in-distribution (LID)

Even when the global state `s` is out-of-distribution, a harness is LID when **every individual LM call over the produced observation `o` is in-distribution with respect to that LM’s training data**.

This is a call-local property, not a claim that the whole trajectory or task is in-distribution. The post often analyzes the root context while assuming sub-agents receive small, individually in-distribution subtasks.

**Class-tightening role:** LID does not itself define the classes. It is the proposed reason that a class-preserving decomposition is learnable and reusable: each member becomes a sequence of familiar local calls.

**Formal gap:** the training distribution is normally unavailable, and the post uses benchmark competence as a proxy. LID is therefore not operationally decidable as defined.

### Harness-induced equivalence relation

The post introduces an “equivalence operator” `~_H` over a set `T`, described first as task states and later as trajectories. Informally,

\[
\tau_1 \sim_H \tau_2
\]

when harness `H` makes structurally similar tasks produce similar sets of observations—ideally token-for-token similar root trajectories. It writes the class of `τ′` as

\[
[\tau'] = \{\tau \in \mathcal{T} : \tau' \sim \tau\}.
\]

**Class-tightening role:** a better harness erases incidental domain, input, and length differences from the root trajectory, placing more tasks with the same useful decomposition into one class and reducing the root policy’s distinct learnable cases.

**Formal gap:** “similar” is not defined. The Appendix suggests `d(x, x′) < ε`, but thresholded distance is not generally transitive, so it need not be an equivalence relation. Reflexivity, symmetry, and transitivity are not proved. `T` also shifts between states, tasks, and trajectories.

### The “Hi/Q” quotient set

Figure 2’s caption literally calls the object **`Hi/Q`**, but neither `Hi` nor `Q` is defined. The body supplies the meaningful notation:

\[
\mathcal{T}/\!\sim_H,
\]

the quotient of task states or trajectories by the harness-induced relation. Each element is an equivalence class, so the root policy learns over classes rather than every surface-distinct task.

`Hi/Q` should therefore be treated as an undefined caption label—possibly a notation or rendering mistake—not a separate formal object. Envelope should cite `T / ~_H` and retain the source ambiguity.

### Context offloading

Instance-specific context is bound to a symbolic variable accessible from a REPL rather than inserted into the root LM’s prompt. Different inputs can therefore present the same initial root prompt and decomposition interface.

**Class-tightening role:** it removes input-token differences at the first root step.

**Limit:** tool, environment, or sub-agent outputs can still be appended later. The root history then becomes instance-specific and may leave LID over a long horizon.

### Programmatic sub-calling

Sub-agents and tools are functions inside the code REPL. Outputs can remain in variables and be passed directly to later functions or sub-calls without appearing in the root context. The root selectively inspects only what it needs.

**Class-tightening role:** it prevents intermediate task-specific data from progressively differentiating root trajectories after the first step. This is why the authors call it as important as initial offloading.

The footnote narrows the claim: the argument can recur inside each sub-agent, but recursion is **not necessary** for maintaining LID observations. Offloading and hidden intermediate state, not recursion by itself, are the operative design choices.

## 3. Mapping to Envelope

### a. `T / ~_H` as a candidate formalization of “comparable work”

**Connection.** It offers a relational definition: work is comparable *under a named harness* when the harness reduces it to the same decision-relevant trajectory shape. That is stronger than surface similarity and could help Envelope discover local task classes for which evidence transfers.

**Where it breaks.** Envelope’s comparability is about whether prior accepted-run evidence supports a cost distribution for a new contract/configuration. Root-trajectory equivalence omits variables that determine that inference:

- acceptance contract, evaluator, and evidence standard;
- model/provider, harness version, tools, authority, infrastructure, and time;
- number, content, failure rate, and cost of hidden sub-calls;
- verification, remediation, retries, human review, and stopping policy;
- task difficulty and acceptance probability inside a shared decomposition;
- temporal drift and sample-selection assumptions.

Two tasks can have identical root trajectories while one fans out 10 cheap sub-calls and the other 1,000 expensive or failure-prone calls. They are equivalent for root-policy learning and non-equivalent for Envelope pricing. Conversely, two root trajectories can differ while their cost-to-acceptance distributions are comparable.

The usable candidate is narrower:

> Harness-induced trajectory class may be one feature in an Envelope work-class qualification; it cannot define comparable work by itself.

### b. LID as a qualification criterion for a harness over a task class

**Connection.** A qualification could require evidence that every call role—root, worker, integrator, verifier—stays inside a measured operating envelope on the declared task class. That creates useful probes: per-role context length, instruction mix, tool-result volume, observed error rate, and trajectory novelty relative to the qualification corpus.

**Where it breaks.** LID as defined cannot be directly checked because the model’s training distribution is unavailable. Performance-as-LID is circular: success is used to declare the input in-distribution, then LID is used to explain success. It is also neither sufficient nor necessary for acceptance:

- individually familiar calls can decompose incorrectly, lose information, aggregate incorrectly, or violate the contract;
- an OOD call can still succeed and produce admissible evidence;
- similar prompts can yield different semantics or failure probabilities;
- qualification must cover the assembled configuration, acceptance behavior, cost, evidence, validity interval, and defeaters—not prompt familiarity alone.

For Envelope, **measured local operating-envelope conformity** is a candidate diagnostic and drift signal. “LID-qualified” would overstate what can be known.

### c. Context rot / OOD drift and milestone 5 drift detection

**Connection.** Both concern invalidating a prior behavioral claim when inputs move away from the distribution that supported it. Within a run, growing appended context changes the effective input distribution. Across runs, a model route, provider behavior, tool schema, environment, work mix, evaluator, or price can change. Per-role trajectory statistics could become milestone 5 canaries.

Candidate signals include context length and composition, tool-output fraction, compaction events, sub-call fan-out, failure/remediation rate, similarity to qualified trajectories, accepted yield, and cost quantiles.

**Where it breaks.** “Context rot” is within-trajectory degradation caused by accumulated context. Envelope milestone 5 drift is broader and longitudinal: the qualified target or work distribution changes over time. A stable short context can still sit behind a changed model alias; a long novel context can still pass its contract. Lexical trajectory distance is not behavioral drift, and behavioral drift is not necessarily context drift. Detection must be tied to acceptance and cost consequences, with false-alarm and missed-drift rates.

### d. 1.5–3× runtime versus ~10× lift as a price-performance frontier

**Connection.** The result motivates treating harness as an experimental treatment with both benefit and cost. Envelope should compare configurations on an acceptance-by-cost curve, not rank models independently of their harnesses.

**Where importing the numbers becomes overclaiming.** The post does **not** establish an Envelope price-performance point, much less a frontier:

1. **Stage:** it changes the harness during RL training; Envelope chooses a harness at inference.
2. **Outcome:** it measures benchmark reward lift; Envelope measures first accepted completion under a fixed contract.
3. **Cost:** it reports relative training wall time; Envelope needs inference, tools, infrastructure, verification, remediation, review, and cleanup cost.
4. **Object:** 1.5–3× is per similarly sized training task, not per accepted output.
5. **Denominator:** ~10× is a ratio of mean *delta lift from step 0*, not a 10× success probability, accepted yield, capability, or value.
6. **Scope:** ~10× applies to the six-task length aggregate; the three-task strategy aggregate is only about 2.5–3× at the final checkpoint.
7. **Absolute levels:** lift can be large while absolute acceptance remains unusable, or small from a strong baseline while acceptance is high.
8. **Distribution:** only mean curves are shown; no cost or acceptance variance, tails, censoring, confidence intervals, or repeated-seed analysis is reported.
9. **Starting points:** arms begin at different eval performance, making relative lift sensitive to baseline.
10. **Selection:** sibling domains were selected for shared strategy; no prospective work-class assignment or negative controls were tested.
11. **Feasibility asymmetry:** the 2M-token base baseline is omitted because it cannot run. That is important operational evidence, but it prevents a complete like-for-like aggregate.
12. **Resource accounting:** higher memory is unquantified; hardware utilization, sub-call tokens, concurrency, and dollar rates are absent.
13. **Retries and stopping:** the experiment has fixed RL checkpoints, not retry-until-accept trajectories or an inference budget.
14. **Acceptance premium:** there is no external acceptance contract, independent verifier, remediation loop, or human review.
15. **Amortization:** reduced training-data or rollout curation cost is a model-development benefit spread over future use, not the marginal cost of one inference task.
16. **Identity and drift:** one named Qwen model and a small benchmark set do not qualify other models, harness versions, providers, task classes, or future behavior.
17. **Causal attribution:** no ablation separates context offloading, programmatic state, recursion, prompting, and extra compute.
18. **Reproducibility:** the post provides figures and method summaries but no raw run records, seeds, uncertainty estimates, or complete cost ledger.

The defensible Envelope claim is only: **harness design may move both the outcome and cost distributions enough to deserve configuration-level qualification.** The reported multipliers cannot be reused as an inference-price ratio or expected “premium.”

## 4. Experiment candidate

### Question

On one fixed, machine-checkable Envelope acceptance contract and one frozen model, does a decomposition-style harness change the distribution of cost to first acceptance relative to a flat append-context agent?

This is a candidate only, not an approved question or learning loop.

### Smallest credible design

Use the existing small lease-service implementation contract, frozen repository snapshot, and external evaluator. Run **20 independent trials per arm**—40 total—interleaved to reduce time drift. If provider seeding is supported, pair trials by seed; otherwise randomize arm order and record provider nondeterminism.

This requires no RL, fine-tuning, or model-weight change. Budget one researcher-day to implement and validate the two adapters, then at most two days or a predeclared dollar cap for the interleaved runs and analysis. Run a two-trial-per-arm instrumentation pilot first and exclude it from inference.

**Hold fixed**

- exact contract, repository snapshot, hidden evaluator, and acceptance rule;
- model/version, provider route, sampling settings, invariant safety/authority instructions, and credentials class;
- tools, permissions, sandbox, infrastructure, and starting artifacts;
- hard per-trial token/dollar and wall-clock cap;
- maximum remediation rounds and terminal failure rule;
- evaluator feedback exposed after a failed candidate;
- price schedule and cost-accounting rules;
- no cross-trial memory or human intervention.

**Vary only the harness policy**

| Flat append-context arm | Decomposition arm |
|---|---|
| One root conversation. Contract, reasoning, tool calls, tool outputs, evaluator feedback, and remediation remain in an appended history until acceptance or cap. No sub-agents or compaction. | Root receives the contract plus symbolic handles. It plans fixed roles; same-model sub-calls inspect bounded contract/repository slices. Tool and sub-call outputs remain in external variables and pass to later calls by handle. Root sees typed status summaries, not full intermediate payloads. |

This treatment intentionally changes call count, prompt/context construction, information routing, and orchestration. Those are the harness. Tools, model, task, evaluator, and budget remain fixed.

**Run protocol**

1. Start from a clean frozen snapshot.
2. Execute until the harness submits a candidate, exhausts budget, or declares failure.
3. Evaluate outside the agent’s authority.
4. On rejection, return the same structured failure evidence and allow the same bounded remediation policy.
5. Stop at first acceptance or cap. Preserve failures as right-censored observations; do not drop them.

### Measures

For every trial record:

- accepted/not accepted and cost to first acceptance;
- cost through first candidate, `C0`;
- total cost through acceptance, `Caccept`;
- **acceptance premium**, `P = Caccept - C0`, when accepted, with censoring at the cap otherwise;
- input/output/cached tokens by root and sub-call role;
- tool and evaluator compute, wall time, and provider charges;
- number of calls, fan-out, retries, remediation rounds, and verifier invocations;
- root-context length/composition over time and task-specific bytes exposed to root;
- failure category and evidence completeness.

Report empirical/Kaplan–Meier acceptance-by-cost curves, accepted yield at predeclared budgets, restricted mean cost to the common cap, and median/p90 only where estimable. Report total cost and premium separately: decomposition could spend more before the first candidate but require less remediation, or the reverse.

### Falsification

Predeclare practical equivalence, not merely a null-hypothesis test. For example, falsify a **practically material harness effect for this contract** if the uncertainty interval for the paired restricted-mean total-cost difference lies wholly within ±10% **and** acceptance-by-budget differences lie within ±5 percentage points at every predeclared budget, with the premium distribution also inside its equivalence bound.

Failure to reach those precision bounds is **Inconclusive**, not evidence of no effect. A decomposition arm that costs more without improving accepted yield or remediation falsifies the narrower “decomposition lowers cost-to-acceptance” claim, even though it still changed the distribution.

### Known confounds

- provider nondeterminism, load, caching, and temporal model-route drift;
- small sample and weak power in the tails;
- pretraining contamination from the contract or repository;
- decomposition prompts encoding researcher knowledge unavailable to the flat arm;
- sub-call parallelism trading wall time against tokens and compute;
- flat-context truncation making feasibility, not gradual rot, the treatment effect;
- typed summaries losing evidence or quietly performing extra task-specific reasoning;
- evaluator leakage, incompleteness, or false acceptance;
- hidden-test failures arriving only after candidate generation;
- correlated repeated trials on one task, limiting transfer to a work class;
- budget and stopping-policy interactions with each harness;
- price-schedule changes converting identical resource use into different dollars;
- human cleanup or review omitted from a machine-only contract.

The experiment can establish a local configuration effect. It cannot validate LID, the quotient-set mechanism, or generalize to other contracts without further loops and human approval.

## 5. Limits and open questions

### The post’s own hedges and limitations

- The central relation is described with “similar,” “nearly,” “roughly,” “in theory,” and a loose `ε` threshold; the Appendix says rigorous formalization is still needed.
- LID is hard to characterize. Benchmark competence is offered only as a proxy.
- Token-for-token identity is rare; one-token changes can alter semantics and output behavior.
- The trajectory metrics do not capture semantic similarity or whether the same decomposition was used.
- The ideal domain abstraction often fails: RLMs still print task-specific information into the root context.
- A short-task RLM can learn a non-generalizing one-sub-call shortcut. MRCRv2 needed a decomposition nudge.
- The amount of supervision or distillation needed is open. “No supervision at scale” is stated as intuition.
- Context offloading alone does not protect long trajectories; returned feedback can make the root OOD.
- The sole footnote says recursive application is intended but recursion is not required for LID.
- Training incurs 1.5–3× runtime plus unquantified memory overhead.
- The MRCRv2 base comparison is infeasible at 2M tokens and omitted.
- Figure 8 uses surface proxies, the best checkpoint, and nearest prior train trajectory; its five metrics are not a semantic or output-distribution test.

### First skeptical-review attacks

1. **The “equivalence relation” is not formal.** `d < ε` need not be transitive, `T` changes meaning, and `Hi/Q` is undefined.
2. **Mechanism is not identified.** There is no ablation of offloading, programmatic sub-calling, recursion, decomposition hints, and additional compute.
3. **No variance or replication is reported.** Curves lack seeds, confidence intervals, task-level sample sizes, and raw records.
4. **Selection may explain transfer.** The three domain pairs were chosen because they share an asserted latent strategy; dissimilar negative controls and prospective class assignment are absent.
5. **The comparison is compute-unequal.** The RLM uses more calls and 1.5–3× runtime. The result may be test-time/training compute scaling rather than abstraction alone.
6. **Aggregate wording outruns plots.** “Same train lift” is not literal at the final length checkpoint; ~10× does not hold for strategy transfer; “8–32×” hides a 4× input case.
7. **Task metadata conflicts.** MRCRv2 is 2-needle → 8-needle in prose and 8-needle → 8-needle in Figure 6. Figure 7’s caption calls cross-domain splits “length-varying.”
8. **The base baseline is incomplete.** MRCRv2 cannot run, while the aggregate headline spans six tasks.
9. **Surface similarity is expected from the treatment.** Hiding context mechanically increases lexical/length similarity; that does not show it caused reward transfer.
10. **External validity is narrow.** One base model, six length environments, three strategy pairs, and author-selected metrics do not establish a general harness law.
11. **Absolute utility is unclear.** Reward lift is not acceptance probability, and several final task scores remain modest.
12. **Production economics are absent.** No inference cost, retries, verifier, human review, failures, tails, or amortization analysis exists.

### Open questions for Envelope

- Can task comparability be defined by equality of **acceptance-relevant sufficient state**, rather than root-token similarity?
- Which trajectory features predict transfer in acceptance probability and cost after controlling for task difficulty?
- Can qualification use observed per-call operating envelopes without claiming access to the true training distribution?
- Are hidden sub-call count and content required coordinates of any cost-relevant equivalence class?
- Does decomposition reduce remediation tails enough to repay its extra first-pass calls?
- Which drift signals forecast a change in accepted yield or cost early enough to justify requalification?
- Does a class learned on one acceptance contract transfer when the task decomposition stays fixed but the evidence standard changes?

## 6. Five quotes

Copyright constraint: these are five exact, load-bearing **excerpts** totaling 25 words, not full sentences.

1. **“generalization is largely the job”** — Puts the harness, not only model weights, inside Envelope’s configuration identity.
2. **“every observation is locally in-distribution”** — States the proposed local design invariant that could motivate qualification probes.
3. **“many tasks share the same equivalence”** — Supplies the bridge to comparable-work classes, while leaving the relation undefined.
4. **“this is not always guaranteed”** — Blocks treating decomposition as an automatic transfer or pricing guarantee.
5. **“a more rigorous treatment”** — Confirms that the quotient language is a research direction, not a finished formal basis for pricing.
