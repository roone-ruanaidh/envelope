# Recursive language model control: moving memory, loops, and parallelism into code

**Research cutoff:** 2026-07-21

**Status:** research, not promoted design

## Finding

Recursive language models (RLMs) demonstrate a useful inversion: keep the large input and working state in an external environment, let a model inspect narrow projections, and let code invoke further model calls. This can process inputs far beyond a model's native context window. It does **not** make the resulting system deterministic. In the reference RLM, the model still writes the decomposition, loop, stopping rule, aggregation code, and final-answer protocol during each run. The memory moved out of the context window, but much of the control plane remained inside model output.

The cleaner target is a deterministic recursive controller with stochastic semantic leaves:

1. A model may propose a typed, finite plan when code cannot select one.
2. Code validates the whole plan, its decreasing recursion measure, effects, and resource reservations before dispatch.
3. A durable state machine executes ready nodes, including model calls, and records every admitted event.
4. Parallel work may finish in any order, but identifiers, joins, reductions, and dispositions use a declared canonical order.
5. Lean proves invariants of the plan language and controller. It does not prove that an external model response is true or that a provider call happened.
6. Python is the best research workbench and a poor security or evidence boundary. Bend is potentially useful for regular pure computation, not the network-bound control plane. Bend2 is not yet a qualifiable dependency because no stable public implementation or technical specification was available at the cutoff.

This extends the existing qualified-harness design rather than replacing it. The durable journal remains authoritative; the model-visible context remains a bounded projection. The new contribution is to make recursive control an explicit, checkable plan instead of a Python program improvised by the model.

## What RLMs establish

The original RLM design stores the prompt as a symbolic variable in a Python REPL. The root model sees metadata rather than the full prompt, emits code to inspect or transform slices, and can call another model over selected material. Results return to the REPL, while only truncated standard output enters the root model's conversation. A final value is also returned through the environment rather than copied through the entire conversation. The paper identifies the symbolic prompt handle, environment-held final answer, programmatic recursive calls, and REPL as essential features ([paper, version 3](https://arxiv.org/html/2512.24601v3)).

That separation is real and valuable:

- **Large data is addressable, not resident.** Text, code, search results, intermediate values, and evidence can live behind handles.
- **Code performs exact work.** Parsing, searching, filtering, counting, hashing, sorting, deduplication, schema validation, and deterministic reduction need not consume model context or inference.
- **Context becomes a projection.** The model receives the smallest view needed for the current semantic decision.
- **Recursive calls become ordinary effects.** A program can generate prompts from data, call leaves in batches, and aggregate the returned values.

The reported evaluations support the mechanism, not a universal depth rule. Performance varies by task and model; depth zero or one often beats deeper recursion, while some tasks benefit from depth two or three. The paper also reports syntax and finalization failures, large run-to-run variation in child-call counts, long-tailed cost and latency, weak models spawning excessive calls, and the difficulty of using one decomposition prompt across models. Its own limitations call out guardrails, exploding subcall costs, asynchronous execution, and sandboxing ([evaluation and limitations](https://arxiv.org/html/2512.24601v3#S5)).

The reference [`rlm` implementation](https://github.com/alexzhang13/rlm) has since added useful operational bounds: maximum root iterations, depth, time, tokens, cost, consecutive errors, and bounded concurrent child calls. Its local REPL preserves a namespace, executes model-authored Python, and uses a thread pool for batched calls. Batch results are placed back in input order even though futures complete out of order. These are strong prototype mechanics. They are not yet a qualified controller:

- limits around a model turn are generally observed after that turn has spent resources;
- parallel children share the parent's reported remaining budget rather than receiving atomic reservations from one global ledger;
- optional trajectory/JSONL logging is not a crash-safe write-ahead journal;
- the local executor runs in the harness process and exposes powerful Python facilities;
- a model-written program still determines topology, fan-out, retry, aggregation, and finalization.

The important distinction is therefore:

> RLMs externalize **state and computation**. A qualified RLM harness must also externalize **control, authority, and accounting**.

### A useful constrained successor

The 2026 λ-RLM paper makes this distinction explicit. It replaces the open-ended model-authored loop with a typed functional runtime and deterministic `Split`, `Map`, `Filter`, `Reduce`, `Concat`, and `Cross` combinators. Models are leaves in a program whose topology, depth, and call count can be analyzed before execution. The paper proves termination and cost bounds under explicit assumptions that leaf calls halt within their bounds and combinators are total and deterministic ([λ-RLM paper](https://arxiv.org/html/2603.20105v1)).

This is the right architectural direction, with two qualifications.

First, the paper's accuracy analysis assumes independence across disjoint chunks and reliable composition. Those assumptions are useful theory, not general facts about language-model errors. Second, the public [`lambda-RLM` repository](https://github.com/lambda-calculus-LLM/lambda-RLM) identifies a Python implementation; no machine-checked Lean or Coq proof artifact was found at the cutoff. “Typed” and “pre-verified” should therefore be treated as properties of the described calculus and paper argument, not as a kernel-checked implementation claim.

Its evaluation also exposes the cost of restricting control. The unconstrained RLM wins several code-oriented cases because it can navigate a repository, backtrack, choose content-aware chunks, and adapt its batching. The goal is not a fixed plan for every task. It is **validated adaptation**: a model can propose or revise a plan, but code decides whether that plan is admissible and reserves its consequences before it runs.

## Deterministic recursive control

### Three different meanings of “deterministic”

They must not be collapsed:

1. **Deterministic control:** given the same controller state and admitted event, the next state and requested effects are identical.
2. **Deterministic replay:** given the same recorded leaf outputs, the controller reconstructs the same joins, reductions, final value, and disposition.
3. **Deterministic re-execution:** repeating external model calls produces identical leaf outputs.

The first two are achievable. The third is generally not: provider implementations, model revisions, floating-point kernels, serving routes, and sampling can change results even at nominal temperature zero. Re-execution must create a new trajectory. Replay consumes the sealed results of the old one.

The controller can be expressed as a pure transition around an effect boundary:

```text
step : State × AdmittedEvent -> State × List EffectIntent

State = {
  run_id,
  plan_digest,
  frontier,
  node_states,
  reservations,
  evidence_refs,
  accumulator
}
```

The harness journals the intent before an executor performs it. The executor returns an observation. The reconciler checks identity, admissibility, and reservation settlement, then admits an event. Only admitted events advance the state machine. This preserves the existing distinction between authoritative journal and bounded model projection.

### Compile recursion into durable state

A recursive call stack is convenient runtime state and poor durable state. A crash loses frames, local variables, in-flight ownership, and the exact point at which an effect crossed the process boundary. Recursive semantics should compile into a finite plan or an explicit frontier whose nodes have stable identities.

A minimal research plan algebra is:

```text
Plan<A> :=
  Read(handle, query)                         -> data
  Pure(operation, inputs)                     -> value
  Model(call_spec, inputs, reservation)       -> semantic value
  Map(ordered_items, child, max_parallel)     -> ordered values
  Reduce(fixed_tree, operation, children)     -> value
  Select(predicate, then_plan, else_plan)     -> value
  Divide(rank, split, child, combine, bounds) -> value
```

There is no unbounded `while`, arbitrary `eval`, or invisible child spawn. `Divide` is admitted only when:

- `rank` is well founded and every recursive child has a smaller rank;
- maximum depth, fan-out, total nodes, and total model calls are known or conservatively bounded;
- every effect type is declared;
- every node has a typed result and failure policy;
- the plan's maximum resource claim can be reserved;
- reduction order and overflow behavior are fixed.

The compiled plan may still be generated by a model. It is an untrusted candidate until the validator accepts it. If evidence justifies adaptation, the model proposes a new plan version against the remaining state and budget; that proposal is another explicit, journaled validation event. This retains backtracking without granting model output direct control authority.

### Budget before dispatch

Post-hoc counters are telemetry, not hard bounds. A parallel harness needs a reservation ledger:

```text
reserve(max_calls, max_tokens, max_cost, deadline)
dispatch(reservation_id, idempotency_key)
settle(actual_usage) | expire | cancel
refund(unused_capacity)
```

The parent cannot promise the same remaining budget independently to several children. Capacity is atomically partitioned before dispatch. A child may sub-reserve only from its allocation. Unknown provider billing or token accounting settles conservatively until authoritative usage arrives. Timeout and cancellation are dispositions with evidence, not missing rows.

This is especially important because RLM cost is topology-dependent. A weak decomposition can multiply calls, and parallel fan-out can cross a global budget before any response returns. A validated node-count bound plus pre-dispatch reservations turns “maximum calls” from a prompt request into a system property.

### Parallel completion without parallel nondeterminism

Parallel execution should change latency, not meaning. The requirements are mechanical:

- derive node IDs from the plan path, such as `root/02/001`, not completion order;
- assign idempotency keys before dispatch;
- journal observations in real arrival order;
- expose children to reducers in canonical plan order;
- declare a fixed reduction tree when an operation is order-sensitive;
- permit arbitrary reduction trees only for operations proven associative and commutative over the actual value type;
- record retry attempts separately and select the accepted attempt by a fixed policy;
- propagate explicit `Success`, `Failed`, or `Inconclusive` values instead of converting exceptions to prose;
- make cancellation, duplicate delivery, and late completion ordinary state transitions.

The output can then be deterministic relative to the map from node ID to admitted leaf result even when thread scheduling and network completion order differ. The arrival-order journal remains truthful; the canonical materialized view remains reproducible.

### What should leave the model first

The useful boundary is semantic uncertainty, not convenience:

1. Put exact operations in code: parsing, indexing, slicing, hashing, schema checks, set operations, arithmetic, bounds, authorization, accounting, and evidence binding.
2. Put known task-family topology in a typed plan: decomposition, finite recursion, concurrency, retries, joins, and stopping.
3. Put search heuristics in code when their objective is explicit and testable.
4. Use a model for semantic classification, synthesis, interpretation, or plan proposal where no adequate deterministic rule exists.
5. Represent semantic aggregation as an explicit model node when it truly requires judgment; do not disguise it as a deterministic reducer.
6. Keep acceptance outside the model. Code checks evidence and policy; Lean checks the claimed logical implication.

Moving a decision into Python does not make the decision justified. A script can prove that every chunk was visited; it cannot prove that the resulting summary is faithful unless faithfulness has a formal, mechanically decidable specification.

## Language fit

| Language | Best role | Do not make it |
|---|---|---|
| Python REPL | Research workbench; inspect external state; prototype plan operators; orchestrate network-bound leaf calls | Security boundary, durable state store, or proof root |
| Lean | Specify the plan calculus and prove controller invariants, termination, bounds, and replay properties | Provider client, evidence collector, or proof that an external observation is true |
| Bend | Candidate accelerator for large, regular, pure recursive transforms with exploitable divide-and-conquer shape | Primary RLM scheduler or durable I/O harness |
| Bend2 | Watch as a possible future proof-plus-parallel-compute target | Current dependency or basis for architectural guarantees |
| Rust, per the repository's existing boundary | Durable controller, journal, reservations, sandbox boundary, provider adapters, reconciliation | Source of theorem-level claims merely because it is typed |

## Python REPL

Python's standard [`code` module](https://docs.python.org/3/library/code.html) separates an interactive interpreter, which owns a namespace, from an interactive console, which adds input buffering and prompts. `runsource` distinguishes incomplete input from complete code and reports syntax or runtime failures. That is almost exactly the ergonomic primitive an RLM experiment wants: a persistent symbolic workspace with short code/result turns.

The REPL fits four research needs well:

- keep a large object behind `context` or a content-addressed handle;
- use mature libraries for parsing, search, tabular work, and visualization;
- rapidly test candidate decompositions and reducers;
- issue many network-bound model calls using `asyncio` or bounded threads.

It also creates four risks:

1. **Hidden mutable state.** Names can be rebound, objects mutated, modules monkey-patched, and results made dependent on cell history. A transcript alone may not reconstruct the heap.
2. **Authority leakage.** Python [`exec`](https://docs.python.org/3/library/functions.html#exec) executes arbitrary code. Replacing `__builtins__` is customization, not isolation. Model-authored code needs an operating-system boundary with explicit filesystem, network, process, time, and memory limits.
3. **Weak durability.** A live namespace is not a journal. Durable values should be immutable artifacts identified by digest, with bindings recorded as events.
4. **Misleading parallelism.** [`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html) is appropriate for waiting on independent provider calls, but recursive tasks that block while waiting on children in the same bounded pool can deadlock. Cancellation also cannot generally stop work that is already running.

The right evolution is:

```text
open Python REPL
  -> restricted Python AST
  -> closed typed plan IR interpreted by audited code
```

The open REPL remains valuable for discovering the operator set. Promoted execution should not replay arbitrary model-authored Python. It should compile an accepted plan to named, versioned operations. Python values exposed to the model are disposable projections; durable objects and authority remain in the harness.

For parallel model calls, threads or async tasks are sufficient because the bottleneck is remote latency. Results should be written into preassigned slots keyed by node ID. CPU-heavy transforms can use processes or a native implementation, but provider orchestration does not become faster merely by moving to a GPU language.

## Lean: proofs, propositions, and assertions

Lean is both a pure functional programming language and an interactive theorem prover based on dependent type theory. Tactics construct proof terms; a small kernel checks those terms ([Lean reference](https://lean-lang.org/doc/reference/latest/)). The relevant vocabulary is:

- A **proposition** is a type in `Prop`: the statement to establish.
- A **theorem** is a declaration whose value is a proof term of that proposition.
- A **dependent type** can encode an invariant in an interface, such as a bounded index or a value paired with evidence that a predicate holds.
- A **termination proof** shows that recursion is structural or decreases according to a well-founded relation.
- A **tactic** is a program that helps build a proof; its output is still checked by the kernel.
- A runtime **assertion** tests one execution. It is not a proof for all inputs.

Lean directly fits the hard parts of recursive control. Its recursive-definition checker rejects arbitrary general recursion unless termination is established, using structural recursion or an explicit well-founded measure ([recursive definitions](https://lean-lang.org/doc/reference/latest/Definitions/Recursive-Definitions/)). A plan semantics could support proofs of:

- `step` is deterministic;
- every admitted `Divide` child decreases rank;
- plan execution has a finite node and call bound;
- reservations are conserved and never become negative;
- no effect executes without prior authority;
- canonical reduction is independent of completion order, given the same admitted leaf-result map;
- replay reaches one terminal disposition;
- a terminal accepted value refers to all evidence required by its acceptance rule.

Lean should prove these statements over a small abstract machine, not orchestrate live model providers. External facts enter as explicit premises or evidence references. Lean can prove “if these observations are admitted and satisfy this predicate, then this disposition follows.” It cannot prove that a provider really returned bytes, that a timestamp is honest, or that a semantic judgment is correct. Those facts remain Rust reconciliation and evidence-boundary obligations, consistent with the existing `axiom-lean` research.

Proof validation also needs discipline. Lean's own validation guidance notes that theorem trust is relative to imports and axioms; `sorry` introduces an axiom, and `#print axioms` exposes dependencies ([validating proofs](https://lean-lang.org/doc/reference/latest/ValidatingProofs/)). A qualified artifact therefore needs pinned sources and toolchain, prohibited shortcuts, a reported axiom closure, and a local kernel check.

Lean supports tasks and threads, but that does not make it the natural operational scheduler. Its [`Task` model](https://lean-lang.org/doc/reference/latest/IO/Tasks-and-Threads/) is useful for parallel pure computation and proof checking; external provider I/O, durable retries, deadlines, idempotency, and billing reconciliation still belong in the system core. Keep the theorem boundary narrow enough that runtime concurrency cannot silently enlarge the trusted computing base.

## Bend and Bend2

### What Bend offers

[Bend](https://github.com/HigherOrderCO/Bend) is a higher-order language compiled through HVM2. Its public design emphasizes unrestricted recursion, continuations, and automatic parallelization without explicit threads, locks, or channels. The runtime can target a sequential Rust interpreter, multicore C, or CUDA. The key condition is program shape: linear recursion remains sequential, while divide-and-conquer exposes independent reductions that can run in parallel. Bend's own documentation calls the compiler immature, notes that CUDA support targets NVIDIA GPUs, and advises the C backend for practical deployment. [HVM2](https://github.com/HigherOrderCO/HVM2) likewise describes its CUDA backend as less stable.

This makes Bend interesting for pure RLM subproblems with a large regular tree:

- deterministic map/filter/reduce over many independent chunks;
- pairwise or tree-shaped comparisons;
- exhaustive candidate scoring with an exact objective;
- large immutable transformations over compact values;
- possibly parallel proof search, once the proof object is independently checked.

It is a weak fit for the main harness. Model calls are coarse, slow, network-bound effects. Their difficulty is budgeting, backpressure, retries, cancellation, identity, durable journaling, and evidence—not arithmetic throughput. RLM plans are often irregular and adaptive, so available parallelism may be too small or too dynamic to amortize serialization and GPU launch costs. Bend's unrestricted recursion is also the opposite of a bounded controller unless a separate validator proves decreasing structure and cost.

Automatic parallel execution must not be equated with qualified determinism. Before using Bend for a promoted pure operator, the same pinned program and inputs would need differential tests across the reference interpreter, C, and CUDA backends; a precise numeric and overflow specification; stable serialization; failure semantics; and a bound on memory growth. A pure accelerator may sit behind the same operation interface as a Rust reference implementation. It should not determine acceptance until equivalence is established.

### Bend2 status

No stable public Bend2 repository, release, language reference, proof-kernel specification, or reproducible benchmark suite from the official organization was available at the cutoff. Public statements describe ambitions that include dependent types, theorem proving, and HVM4 parallelism, but the described scope and release timing have changed. [HVM4](https://github.com/HigherOrderCO/HVM4) is public and explicitly warns that it is pre-launch and should be used at one's own risk.

Therefore Bend2 is a research watch item, not evidence for a design decision. If it is released, qualify it against concrete questions:

1. What is the formal language and trusted kernel, if any?
2. Are proof terms independently checkable, and what axioms or unsafe escape hatches exist?
3. Which recursive programs terminate, and how are totality and effects represented?
4. Are results bit-for-bit or semantically identical across sequential, C, and GPU backends?
5. How are nondeterministic foreign effects isolated from pure reduction?
6. What are worst-case work, span, memory, and graph-growth bounds?
7. Can it beat a simple Rust/Python reference on actual harness workloads, including transfer overhead?

If those answers are strong, Bend2 could eventually collapse two currently separate roles: Lean-like certification of pure recursive operators and Bend-like massively parallel execution. Until then, designing to that possibility would place the architecture on unavailable evidence. The stable boundary is Lean for proofs and Rust/Python for execution, with Bend evaluated only as a replaceable pure accelerator.

## Proposed harness shape

```text
                         bounded View(handle, query)
                                   |
                                   v
untrusted request -> planner/model -> CandidatePlan
                                      |
                                      v
                           deterministic validator
                       types / rank / effects / bounds
                                      |
                                      v
                            sealed Plan + reservations
                                      |
                                      v
                         durable frontier scheduler
                         /          |           \
                    pure op     model leaf     pure op
                         \          |           /
                          admitted result events
                                      |
                                      v
                         canonical join / reducer
                                      |
                                      v
                        acceptance reconciliation
                         Rust evidence + Lean rule
```

The model sees projections, never the authoritative store. The scheduler sees typed handles, never free-form instructions. Executors receive individual intents with least authority. The reconciler admits observations. Lean checks the pure implication from admitted premises to disposition.

This shape supports three modes without separate semantics:

- **Research:** the Python REPL proposes operations and plans; traces reveal which operators recur.
- **Qualified execution:** only closed, versioned operators and validated plans execute.
- **Replay:** no provider calls occur; admitted leaf outputs reconstruct the controller result.

The progression should be empirical. Do not begin by designing a universal recursive DSL. Capture real RLM trajectories, identify repeated control structures, and promote the smallest operator set that removes the largest amount of model-authored control. An operator earns promotion when its semantics, resource behavior, and evidence are precise enough to test and eventually prove.

## Failure analysis

The design still breaks if:

- a validator's cost model underestimates provider or expansion cost;
- a semantic reducer is mislabeled as pure;
- stable ordering masks missing or duplicated observations;
- a retry policy selects a convenient answer rather than a predetermined attempt;
- content-addressed caching omits model, prompt, tool, policy, or environment identity;
- a “decreasing” rank does not bound breadth, so total work still explodes;
- plan compilation materializes a graph too large to store;
- model-visible projections omit evidence needed for the semantic decision;
- the proof theorem formalizes a weaker machine than the production interpreter;
- Bend backend differences alter a value later treated as authoritative;
- a sandbox contains files but still permits network exfiltration or host resource exhaustion.

The sharpest unresolved problem is adaptive semantic decomposition. Known plans are easy to bound but brittle; unconstrained model plans are flexible but dangerous. A useful plan language must let evidence trigger bounded replanning without recreating an open Python control plane. That is the next research question worth approving.

## Decision consequences

This research supports the following provisional decisions, none promoted here:

1. Treat external symbolic state and narrow views as the lasting RLM contribution.
2. Treat model-authored Python loops as a discovery mechanism, not the promoted harness.
3. Represent recursion as a validated finite plan or explicit decreasing frontier.
4. Reserve global budget before parallel dispatch and settle it from evidence.
5. Define reproducibility as deterministic replay over sealed leaf outputs, not identical model re-execution.
6. Use Lean for controller theorems and proof checking, not live orchestration or external-fact creation.
7. Evaluate Bend only on pure, regular, compute-heavy operators against a reference implementation.
8. Revisit Bend2 only after a pinned public release makes its proof and runtime claims inspectable.

## Primary sources

- Zhang, Kraska, and Khattab, [*Recursive Language Models*](https://arxiv.org/abs/2512.24601), version 3, 2026-05-11; [reference implementation](https://github.com/alexzhang13/rlm).
- Liu et al., [*λ-RLM: A Typed Functional Runtime for Recursive Language Models*](https://arxiv.org/abs/2603.20105), 2026-03-20; [reference implementation](https://github.com/lambda-calculus-LLM/lambda-RLM).
- Python Software Foundation, [`code` — interpreter base classes](https://docs.python.org/3/library/code.html), [`exec`](https://docs.python.org/3/library/functions.html#exec), and [`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html).
- Lean project, [language reference](https://lean-lang.org/doc/reference/latest/), [recursive definitions](https://lean-lang.org/doc/reference/latest/Definitions/Recursive-Definitions/), [validating proofs](https://lean-lang.org/doc/reference/latest/ValidatingProofs/), and [tasks and threads](https://lean-lang.org/doc/reference/latest/IO/Tasks-and-Threads/).
- HigherOrderCO, [Bend](https://github.com/HigherOrderCO/Bend), [HVM2](https://github.com/HigherOrderCO/HVM2), and [HVM4](https://github.com/HigherOrderCO/HVM4) public repositories.

Claims above distinguish published design claims from repository behavior and from this research's architectural inference. No RLM implementation was executed, no benchmark was reproduced, no Bend2 artifact was available to test, and no proposed controller theorem was formalized in Lean.
