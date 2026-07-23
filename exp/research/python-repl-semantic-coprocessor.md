# Python REPL as working memory for programmatic language agents

- **Research cutoff:** July 23, 2026
- **Status:** unpromoted synthesis; not a question, loop contract, or design
- **Read with:** [Envelope](../../README.md), [recursive language model control](recursive-language-model-control.md), and [harness compositional generalization](harness-compositional-generalization.md)

## Finding

A Python REPL is useful to a language agent because it combines three properties that ordinary tool calling separates:

1. a persistent symbolic address space;
2. exact, cheap computation over values too large to show the model; and
3. programmatic composition of model calls and tools without returning every intermediate value to the root context.

That makes the REPL a strong **working-memory tier**, not durable memory or a trustworthy controller. Its namespace is hidden mutable process state; arbitrary objects cannot be reliably reconstructed from source history; and arbitrary Python collapses data access, control flow, and external authority into model-authored code.

The smallest clean Envelope boundary is:

> Durable artifacts and the event journal are memory of record. The REPL is a disposable, reconstructible binding table and computation surface over those artifacts. Deterministic code owns traversal, budgets, joins, and effect admission. Models are invoked as typed semantic operators only where an explicit semantic unknown remains. Tools that mutate the world are actuators behind a separate capability boundary.

This retains the central RLM mechanism—task-specific information can move through variables and sub-calls without entering the root model's trajectory—while preventing a live Python heap from becoming control, authority, or evidence.

## What the REPL changes

The RLM paper places the input in a REPL variable, lets the root model inspect and transform selected portions, and exposes model calls as functions. Only bounded execution feedback needs to return to the root model. The newer harness argument attributes RLM generalization to both **context offloading** and **programmatic sub-agent calling**: input-specific values can remain in variables and flow directly into later calls, making the root trajectories of structurally similar tasks more alike ([RLM paper](https://arxiv.org/html/2512.24601v3), [harness essay](https://alexzhang13.github.io/blog/2026/harness/)).

The REPL contributes four mechanisms:

- **Indirection.** A short name or handle stands for a large value. The model reasons about identity, shape, and operations without repeatedly consuming the payload.
- **Closure under composition.** Code can feed one tool or model result into another without serializing that result through the root conversation.
- **Exact reduction.** Parsing, indexing, sorting, set operations, arithmetic, validation, and aggregation remain ordinary computation.
- **Interactive repair.** Execution errors and small projections let the model revise a program without regenerating the entire computation.

The last property distinguishes a REPL from one-shot program generation. The first three explain its memory value.

They do not establish that unseen tasks are genuinely in-distribution or that similar root token trajectories have equal acceptance and cost behavior. The harness essay explicitly treats trajectory distance as difficult to define and evaluates proxies. For Envelope, root-trajectory similarity is a candidate mechanism or diagnostic, not qualification evidence.

## Related designs expose different boundaries

| Design | What moves into code or external state | What remains model-owned | Lesson for Envelope |
|---|---|---|---|
| PAL | Exact solution execution in Python | One-shot program decomposition | An interpreter can remove arithmetic and symbolic error without providing memory or agent control. |
| CodeAct | Multi-turn actions, tool composition, and persistent Python variables | Action choice and arbitrary executable control | A single code action space is expressive, but expressiveness also enlarges authority and hidden state. |
| MemGPT | Paging between context and external memory | Memory selection and control flow | A memory hierarchy need not require a REPL, but model-managed paging remains stochastic policy. |
| BINDER | LM calls embedded inside SQL or Python, followed by symbolic execution | Program synthesis and semantic API results | This is the clearest early form of an LM as a semantic coprocessor to deterministic computation. |
| LOTUS | Declarative semantic filter, join, sort, and aggregation operators over tables | Each operator's semantic result | Named semantic operators let a system plan, optimize, batch, and evaluate model work separately from query meaning. |
| RLM | Input, intermediate values, exact computation, and recursive model calls in a persistent REPL | Decomposition, fan-out, loops, aggregation, stopping, and finalization | The REPL externalizes state and computation, but not necessarily control or authority. |
| λ-RLM | Typed, bounded functional combinators with model leaves | Leaf semantics within a predeclared topology | Closing the control language makes termination and call bounds analyzable, at the cost of unconstrained adaptation. |

PAL reports gains from letting a model generate the decomposition while a Python runtime performs the exact reasoning ([PAL](https://arxiv.org/abs/2211.10435)). CodeAct reports that executable Python actions improve tool composition and permit multi-turn revision ([CodeAct](https://arxiv.org/abs/2402.01030)). BINDER binds model calls into a symbolic host program, then lets the host interpreter compute from their returned values ([BINDER](https://arxiv.org/abs/2210.02875)). LOTUS generalizes this boundary into declarative semantic operators with alternative execution plans and operator-specific optimizations ([LOTUS](https://arxiv.org/abs/2407.11418)).

These results support the interfaces they test. They do not show that arbitrary Python is the right promoted runtime, that model outputs are true, or that the reported benchmark improvements transfer to Envelope's acceptance contracts.

## Candidate memory hierarchy

This is a logical hierarchy of visibility, cost, and authority, not a literal hardware latency hierarchy.

| Tier | Contents | Lifetime | Owner | Model access |
|---|---|---|---|---|
| M0 — invocation context | Current operation, bounded evidence view, schemas, receipts | One model call | Context builder | Direct tokens |
| M1 — control context | Task contract projection, stable handles, recent cell receipts, remaining bounds | Root trajectory | Harness policy | Direct tokens |
| M2 — REPL workspace | Names bound to immutable handles, small scalars, candidate programs, derived views | One disposable session | Sandboxed runtime | Code and bounded print |
| M3 — artifact store | Source inputs, immutable tables, indexes, model observations, candidate outputs | Across sessions and crashes | Artifact custodian | Bounded views by handle |
| M4 — journal and catalog | Event order, provenance, bindings, configuration, reservations, dispositions | Authoritative run history | Deterministic controller | Selected projections only |

The context window is the most expensive semantic cache. The REPL is cheaper addressable working memory. The artifact store holds payloads. The journal says what happened and which values are admissible.

Two rules make the distinction real:

1. **A REPL binding is a convenience, not evidence.** A value becomes durable only when written as an immutable artifact and bound by a journaled event.
2. **A summary is a derived cache entry, not replacement memory.** It retains the source handles, operation identity, model configuration, and evidence needed to invalidate or regenerate it.

MemGPT's virtual-context design also treats the context window as constrained memory and external storage as a slower tier, but lets the model request paging operations ([MemGPT](https://arxiv.org/abs/2310.08560)). Envelope should test a narrower policy: deterministic selection for exact predicates and indexes; model-proposed selection only for named semantic relevance questions; controller validation and budget reservation before either projection enters context.

### Semantic demand paging

A semantic cache miss is not “Python is inconvenient.” It is a declared operation whose answer cannot be computed exactly from available structured data:

```text
exact:
  parse / hash / index / slice / sort / join-on-key / count / validate

semantic:
  relevance / entailment / equivalence / classification /
  interpretation / synthesis / judgmental aggregation
```

On a semantic miss, the controller invokes a model over the smallest sufficient immutable view. The result is sealed as an **observation**, not accepted as a fact:

```text
semantic(
  operation_id,
  input_handles,
  output_schema,
  model_and_prompt_identity,
  reservation
) -> observation_handle
```

Caching that handle means “reuse this recorded observation under this declared policy.” It must not mean “the answer is now deterministic” or “the observation is true.” A new model, prompt, source artifact, policy, or validity interval creates a different cache identity.

## A reconstructible REPL

Python's `code.InteractiveInterpreter` makes the namespace explicit as a caller-supplied mapping; `InteractiveConsole` adds input buffering and prompts ([Python `code`](https://docs.python.org/3/library/code.html)). That is enough to build an agent-facing REPL, but not enough to make its heap reproducible.

A normal namespace may contain open files, sockets, futures, threads, generators, closures, monkey-patched modules, aliased mutable objects, and references into native libraries. Source history records statements, not the complete state transitions those objects experienced. Serializing the heap does not fix the trust boundary: many values are not safely serializable, and Python warns that unpickling untrusted data can execute arbitrary code ([Python `pickle`](https://docs.python.org/3/library/pickle.html)).

The reconstructible unit should therefore be a **cell transaction over handles**, not a process snapshot:

```text
CellInput = {
  cell_id,
  source_digest,
  base_binding_manifest,
  allowed_operation_versions,
  capability_handles,
  reservations
}

CellReceipt = {
  admitted_input_handles,
  requested_semantic_calls,
  requested_effects,
  admitted_observation_handles,
  new_artifact_handles,
  candidate_binding_delta,
  stdout_and_stderr_projection,
  resource_use,
  terminal_status
}
```

The controller validates the candidate binding delta and commits a new immutable binding manifest. Restart reconstructs names from that manifest and the artifact store. Live Python objects remain disposable.

This is stricter than a notebook transcript and intentionally less convenient than an unrestricted heap. It gives up implicit mutation in exchange for:

- crash recovery without replaying external effects;
- deterministic replay over sealed semantic observations;
- explicit garbage collection from reachable handles;
- cell-level cost and provenance;
- a reviewable boundary between computation and authority.

In research mode, unrestricted Python can reveal useful operators. Its transcript should be treated as discovery evidence, not as the future execution format. Repeated operations can later become named, versioned functions or typed plan nodes.

## Three planes that Python otherwise collapses

### 1. Deterministic computation

Pure or replayable operations transform admitted artifacts into new artifacts. The controller can rerun them, compare digests, and use canonical ordering.

```text
compute(operation_id, input_handles, parameters) -> artifact_handle
```

### 2. Semantic computation

The model is a foreign semantic coprocessor. It receives an operation-specific projection and returns a schema-constrained observation. The surrounding program may deterministically batch, join, count, or route those observations, but it cannot make their semantic content deterministic.

```text
observe(semantic_operation, view_handles, schema, reservation)
  -> observation_handle
```

### 3. Effects

Read-only tools are external sensors; mutating tools are actuators. Neither should be ambient Python libraries holding raw credentials. Model-authored code may request a named effect, but only the controller can validate, reserve, journal, and dispatch it.

```text
request_effect(capability, arguments, preconditions, reservation)
  -> effect_intent

admit(effect_intent) -> dispatch_receipt -> external_observation
```

This prevents a semantic output from becoming an action merely because it was returned inside executable Python. It also permits dry-run, human approval, idempotency, retry, and reconciliation to remain properties of the controller rather than prompt instructions.

## Programmatic sub-agents

The clean abstraction is a semantic function with an explicit envelope, not a peer process inheriting the parent's ambient state:

```text
subcall = {
  operation_id,
  input_view_handles,
  expected_schema,
  prompt_and_model_identity,
  call_budget,
  deadline,
  allowed_child_operations
}
```

A sub-agent should not receive the parent REPL heap, raw credentials, or undeclared authority to recurse. It returns an observation handle. The controller assigns stable node IDs before dispatch, records arrival order truthfully, and exposes results to joins in canonical plan order.

Programmatic sub-calling still matters even when topology is code-owned. Batched calls can consume task-specific inputs and write task-specific observations without any of those payloads entering the root control context. The root model can see:

```text
batch semantic_filter completed:
  1,024 inputs / 73 positive / 5 inconclusive / evidence=sha256:...
```

instead of 1,024 prompts and responses. If the root needs to interpret the positives, it requests a bounded view or a new semantic operation. This is the durable form of the RLM buffer pattern.

## Where Python, Rust, and Lean fit

Choose the language from the consequence of failure, not from which language can express the operation.

| Concern | Best research home | Best qualified home | Reason |
|---|---|---|---|
| Interactive inspection, decomposition discovery, ad hoc transforms | Python REPL | Omit or retain as a disposable client | Fast learning and library access matter more than long-lived semantics. |
| Experiment analysis, estimators, plots, calibration | Python | Python over immutable exported evidence | These are derived analyses, not execution authority. |
| Large exact transforms | Python until the operator and workload stabilize | Rust only when qualification, predictable resources, or measured performance justify it | Rewriting ordinary data work early adds a second implementation without reducing uncertainty. |
| Binding manifests and artifact custody | Rust | Rust | Durable identities, atomic commit protocol, bounded decoding, and explicit error paths belong outside the disposable interpreter. |
| Journal, reservations, scheduling, retry, cancellation, reconciliation | Rust | Rust | These operations define cost, authority, and crash behavior. Python exceptions and process lifetime must not decide settlement. |
| Model and tool adapters | Python prototypes | Rust controller adapters; isolated executors may use another language | Requests need stable identities, deadlines, idempotency, usage settlement, and least-authority credentials. |
| Sandbox supervision | OS boundary controlled by Rust | OS boundary controlled by Rust | Rust memory safety is not sandboxing; the operating system must enforce process, filesystem, network, time, and memory limits. |
| Plan algebra and transition semantics | Executable prototype in Python or Rust | Rust implementation with a deliberately small Lean model | The runtime must be operational; only stable, load-bearing semantics are worth formalizing. |
| Termination, decreasing rank, bounded topology, reservation conservation, admissible state transitions | Assertions and property tests first | Lean proofs where the proposition is precise | These are universal controller claims that testing alone cannot establish. |
| External observation truth, model quality, provider behavior | Empirical evidence | Empirical qualification and human review | Neither Rust's type system nor a Lean theorem can prove an external semantic result true. |

### Rust should own the membrane

The Rust process should sit between the Python session and every durable or external capability:

```text
model-authored Python
        |
        | candidate cell / typed requests
        v
Rust controller
  validate -> reserve -> journal -> dispatch -> reconcile -> commit
        |
        +---- immutable artifact store
        +---- isolated semantic-call executor
        +---- isolated tool executor
        +---- model-visible bounded receipts
```

Python receives opaque handles and narrow client functions. It does not receive store paths, database connections, provider credentials, or mutable controller objects. Killing the Python process must leave the last committed binding manifest and all admitted effects intelligible to Rust.

Rust is better here because the membrane needs one explicit representation for ownership, state transitions, errors, and concurrency. Rust does **not** by itself provide crash consistency, idempotency, least authority, or process isolation; those remain protocol and operating-system properties that the Rust controller must implement and evidence.

### Lean should prove the stable kernel, not mirror the system

Lean is useful after repeated trajectories reveal a small controller kernel. Candidate theorems include:

- every admitted recursive expansion decreases a well-founded measure;
- a sealed plan cannot exceed its declared node and model-call bounds;
- reservations are neither duplicated nor overspent by legal transitions;
- duplicate or late observations cannot change a settled node;
- canonical reduction is invariant to child completion order;
- replay over the same admitted observation map yields the same controller result;
- acceptance follows from the declared admitted premises.

Lean should not model Python objects, provider APIs, thread scheduling, filesystems, billing systems, or the truth of model observations. Those details would enlarge the formal model without making the external systems provable.

The dangerous seam is conformance:

> A theorem about a Lean transition function does not prove that the Rust controller implements that function.

Keep this gap visible. Use one small versioned transition vocabulary, generate conformance traces from the Lean model where practical, and run the same traces against Rust. Differential and property tests can detect divergence; they do not turn the Rust binary into a proved implementation. If the formal and operational semantics begin to require parallel special cases, the boundary is too broad and should be reduced rather than patched.

### Promotion order

The least wasteful progression is:

```text
Python trajectory
  -> repeated operator
  -> named Rust operation with evidence and failure semantics
  -> stable transition rule
  -> Lean proposition and proof, only if the universal claim matters
```

Do not translate the whole REPL to Rust or formalize a universal agent DSL in Lean. Promote only the operations whose failure would compromise replay, authority, cost bounds, or acceptance.

## Candidate experiment

The next useful experiment is not “can an agent use Python?” CodeAct, PAL, and RLM already establish that it can. The unresolved Envelope question is:

> Does a handle-only, reconstructible REPL preserve the context and composition benefits of an unrestricted RLM workspace while making crash recovery and replay mechanically reliable?

A smallest credible comparison would hold the task, model, prompts, tools, budgets, and acceptance contract fixed across:

1. append-context tool and sub-agent outputs;
2. an unrestricted persistent Python REPL; and
3. a handle-only REPL with immutable artifacts, typed semantic calls, and journaled binding manifests.

The task should require semantic filtering over a corpus, exact aggregation, and one externally observable but safely reversible actuation. Predeclared measures should include:

- accepted completion and evidence admissibility;
- root-context task-specific bytes and tokens;
- external bytes processed per root-context byte;
- model-authored branches and semantic call count;
- unjournaled live-state dependencies;
- recovery after process termination at a declared cell boundary;
- replay equivalence after reordering recorded child completions;
- total and tail cost and latency.

The handle-only design fails if it materially lowers acceptance or forces task payloads back into the root context. The unrestricted design fails the trust objective if a killed session cannot reconstruct the same controller result from its transcript and sealed observations. This candidate does not authorize a question or loop.

## Provisional consequences

1. Treat the REPL as M2 working memory and operator discovery, never memory of record.
2. Preserve RLM-style indirection: handles and aggregate receipts enter root context; payloads remain externally addressable.
3. Represent model calls as versioned semantic operators that return observations.
4. Keep tool effects behind controller-owned capability admission; do not expose ambient credentials to Python.
5. Make a committed binding manifest, not a live heap or transcript, the REPL recovery boundary.
6. Move recurring model-authored loops into named operators or a typed plan only after trajectories reveal the smallest useful algebra.
7. Put the durable capability membrane in Rust and formalize only its stable, load-bearing kernel in Lean.
8. Test the handle-only restriction against acceptance and context efficiency before promoting any REPL design.

## Stop claims

This research does not establish that:

- Python state is durable because variables persist across cells;
- recorded source reconstructs an arbitrary Python namespace;
- a cached model observation is deterministic or true;
- similar root trajectories define comparable work;
- deterministic orchestration makes model re-execution deterministic;
- sandboxed arbitrary Python is an adequate authority boundary;
- a semantic operator can be treated as a pure reducer;
- the performance or cost results of PAL, CodeAct, MemGPT, BINDER, LOTUS, RLM, or the harness-training essay transfer to Envelope.

## Primary sources

- Zhang, Kraska, and Khattab, [*Recursive Language Models*](https://arxiv.org/abs/2512.24601), version 3, May 11, 2026; [reference implementation](https://github.com/alexzhang13/rlm).
- Zhang, [*Language model harnesses are compositional generalizers*](https://alexzhang13.github.io/blog/2026/harness/), 2026.
- Liu et al., [*λ-RLM: A Typed Functional Runtime for Recursive Language Models*](https://arxiv.org/abs/2603.20105), March 20, 2026.
- Gao et al., [*PAL: Program-aided Language Models*](https://arxiv.org/abs/2211.10435), 2022.
- Wang et al., [*Executable Code Actions Elicit Better LLM Agents*](https://arxiv.org/abs/2402.01030), 2024.
- Packer et al., [*MemGPT: Towards LLMs as Operating Systems*](https://arxiv.org/abs/2310.08560), 2023.
- Cheng et al., [*Binding Language Models in Symbolic Languages*](https://arxiv.org/abs/2210.02875), 2022.
- Patel et al., [*Semantic Operators: A Declarative Model for Rich, AI-based Data Processing*](https://arxiv.org/abs/2407.11418), 2024.
- Python Software Foundation, [`code` — interpreter base classes](https://docs.python.org/3/library/code.html) and [`pickle` — object serialization](https://docs.python.org/3/library/pickle.html).
- Lean project, [recursive definitions](https://lean-lang.org/doc/reference/latest/Definitions/Recursive-Definitions/) and [validating proofs](https://lean-lang.org/doc/reference/latest/ValidatingProofs/).

No cited implementation was executed and no reported benchmark was reproduced. The memory hierarchy, cell transaction, effect boundary, and candidate experiment are architectural inferences from the cited mechanisms, not source claims.
