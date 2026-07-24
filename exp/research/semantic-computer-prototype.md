# Semantic computer prototype

- **Research date:** July 23, 2026
- **Status:** build orientation; unpromoted and not an approved experiment

## Direction

Build one reproducible Linux semantic computer with two interchangeable semantic
processors: Laguna XS 2.1 and Laguna S 2.1.

This is not two agents or a Python harness comparison. The stable object is the
computer. Model size is one replaceable architectural variable.

| Computer component | Initial implementation |
|---|---|
| Physical machine | Linux on an NVIDIA GPU host |
| Semantic processor | Laguna XS 2.1 or Laguna S 2.1 |
| Device runtime | Pinned inference engine, weights, quantization, chat template, tool parser, context limit, and reasoning mode |
| Deterministic processor | Control, scheduling, memory movement, validation, replay, and accounting |
| Authoritative memory | Durable task state, artifacts, and execution journal |
| Working cache | Model context and KV cache |
| Deterministic work surface | Inspectable REPL |
| I/O and actuators | Tools |
| Program | Task contract |
| Machine evidence | Instruction and resource trace |

The minimum complete execution path is:

```text
task contract
  -> durable task state
  -> selected context projection
  -> semantic instruction
  -> model result or proposed effect
  -> deterministic validation and execution
  -> journaled state transition
  -> acceptance or next instruction
```

The context window is a cache, not the workspace. Durable state remains
authoritative; code decides what enters context.

A conventional agent harness makes the model the principal that owns the
trajectory and calls tools. An RLM commonly lets that model reach into an
external REPL and invoke more models. Envelope reverses ownership: the task is a
process; the kernel owns control, memory, effects, and accounting; models are
replaceable devices receiving bounded semantic instructions.

## Processor substitutions

Run the same computer, task programs, memory policy, and instruction contracts
against Laguna XS and S first. This asks whether one machine abstraction
survives a within-family semantic-processor swap. Model-specific optimization
should follow only after the fixed-policy comparison; otherwise processor
capacity and architecture adaptation are confounded.

The resulting research has two independent axes:

| | Smaller task working set | Larger task working set |
|---|---|---|
| **Laguna XS** | execution trace | execution trace |
| **Laguna S** | execution trace | execution trace |

RLM research varies task working-set size and shows that a shared decomposition
can transfer across much longer tasks. This prototype adds processor capacity as
a second axis:

> Does one semantic computer preserve a stable task-execution structure across
> increasing task working-set size and increasing semantic-processor capacity?

The build should make the answer visible rather than assume it. Its traces can
show:

- whether XS needs more decomposition, cache fills, or semantic dispatches;
- whether S reduces dispatch count or only increases cost per dispatch;
- whether one memory policy works across both processors;
- which semantic instructions fail or change shape by processor size;
- where repeated semantic work can be substituted with deterministic code.

Cross-family substitution is then necessary to distinguish a semantic computer
from a Laguna-specific appliance. Add processors as controlled contrasts, not a
model zoo:

| Contrast | Processors | What it tests |
|---|---|---|
| Within-family scaling | Laguna XS 33B-A3B → Laguna S 118B-A8B | One machine across processor capacity |
| Matched sparse geometry across families | Laguna XS 33B-A3B ↔ Qwen 3.6 35B-A3B | Portability across weights, training, tokenizer, and protocol |
| Sparse versus dense | Qwen 3.6 35B-A3B ↔ Qwen 3.6 27B dense | Effect of active compute and model architecture |
| Second family architecture | Gemma 4 26B-A4B ↔ Gemma 4 31B dense | Portability beyond one vendor and serving convention |
| Later large-scale substitution | Inkling-Small, after weight release | A substantially different MoE and reasoning system |

“Size” is not one scalar. Each processor profile must distinguish:

- total parameters, which affect storage, VRAM, loading, and sharding;
- active parameters, which approximate inference computation per token;
- dense or MoE architecture, which changes bandwidth, routing, and latency;
- context capacity, which is the semantic processor's cache ceiling;
- training and post-training, which shape semantic-instruction competence;
- reasoning effort, which makes semantic compute variable;
- engine, quantization, and hardware, which physically implement the processor.

### Semantic device drivers

The invariant boundary should be the task program, semantic instruction
contracts, durable-state representation, effect boundary, and acceptance
evaluator. Each model family gets a device driver that compiles those
instructions into its chat template, tool protocol, reasoning representation,
and tokenizer.

Adding a processor should require a driver and processor profile, not kernel
changes. If Gemma or Qwen forces changes through the kernel, the supposed
semantic ISA encoded Laguna behavior as architecture. Driver complexity,
family-specific instructions, and abstraction leaks are therefore evidence.

## Validation ladder

Exhaust cheap evidence before renting GPU time, while keeping each evidence
class explicit:

1. **Lima Linux VM plus a fake model endpoint:** validate packaging, Linux
   identity, durable state, REPL behavior, instruction contracts, replay, tools,
   failure handling, and accounting.
2. **Laguna API:** validate chat templates, semantic instruction formatting,
   tool calls, reasoning-state handling, and broad behavioral compatibility.
3. **Short rented-GPU smoke tests:** validate weights, inference engine,
   quantization, GPU compatibility, serving telemetry, and failure paths.
4. **Full task programs:** evaluate the assembled computer.

Lima does not validate the NVIDIA or inference path. API execution does not
validate the local serving stack. A GPU smoke test does not validate useful task
behavior. These are successive evidence layers, not substitutes.

Laguna's documented serving behavior makes conformance testing consequential.
Its XS instructions identify version-sensitive `poolside_v1` tool parsing, and
the S instructions recommend preserving interleaved `reasoning_content`.
Weights, engine, parser, template, quantization, context limit, and reasoning
mode therefore belong to the semantic-processor configuration rather than
incidental deployment metadata.

Reasoning output should initially be retained as a durable, attributed processor
artifact. It is not automatically authoritative task state. Code may select a
projection of it back into context when useful, preserving context as a managed
cache instead of accumulated conversation history.

## Task programs

Use task sources for different kinds of evidence:

- **Poolside Terminal-Bench 2.1 trajectories:** check serving and task behavior
  against published model trajectories before attributing failures to this
  computer.
- **RLM-shaped task families:** exercise the memory hierarchy over controlled
  working-set increases. Candidate families from the cited research include
  MRCRv2, GraphWalks, OOLONG, and OOLONG-Pairs, subject to reproducible data and
  evaluators.
- **Prime tasksets:** reuse production-shaped tasks, environments, and
  evaluators where useful. They are programs supplied to the computer, not the
  computer's architecture.

The initial corpus should be small but span distinct memory and effect shapes.
Its purpose is to reveal missing instructions, poor memory behavior, expensive
transitions, and processor-dependent behavior. It should not become a broad
leaderboard before the machine exists.

### Benchmark inversion

Most model benchmarks assume:

```text
task state -> context window -> model -> answer
```

Envelope instead evaluates:

```text
task state -> durable machine memory
kernel -> bounded projection -> semantic processor
kernel -> admitted state transition or effect
```

Existing benchmarks may supply task semantics and external evaluators, while
their data is mounted as authoritative state rather than automatically placed in
the prompt. This is a deliberate change in task presentation and must be
reported as a system evaluation, not silently compared with a raw model score.

Where a comparison is useful, run the same task and evaluator in two modes:

1. **Direct/model-native:** the conventional presentation or established agent
   harness.
2. **Envelope-native:** external state plus bounded semantic dispatches.

Cross-processor evaluation also needs two modes:

1. **Fixed cache:** each processor receives the same logical projection budget,
   isolating processor behavior.
2. **Native machine:** each processor uses its deployable context, reasoning,
   and serving configuration, comparing useful complete machines.

Because tokenizers differ, define fixed logical projections in stable task units
such as bytes, records, files, or artifacts; record the resulting tokens as a
processor-specific resource cost.

## Evidence to retain

Acceptance remains the external result, but the machine trace is the primary
architectural evidence:

- semantic instruction type and count;
- input, output, and cached tokens;
- each selected context projection;
- durable-state and artifact growth;
- deterministic instruction count and time;
- tool effects and receipts;
- retries, recovery, and rejected proposals;
- wall time, GPU time, utilization, and VRAM;
- terminal acceptance and evaluator evidence.

This produces resource accounting from the instruction stream itself. Monetary
cost is then one tariff over that resource trace, not the definition of the
computation.

## Public artifact

The useful result is a reproducible semantic computer, not merely a benchmark
report:

- one Linux machine definition;
- one deterministic runtime and memory hierarchy;
- device drivers and processor profiles, beginning with Laguna XS and S;
- a local Lima conformance profile;
- a reproducible NVIDIA deployment profile;
- task programs and evaluator adapters;
- inspectable traces and a short working demonstration.

The same design could later run locally, on a remote GPU box, or behind a model
API. The first implementation need only establish that the machine boundary is
real and that swapping semantic processors and task programs produces
diagnosable differences.

## Licensing language

Describe Laguna precisely as **open-weight under OpenMDW-1.1**, rather than
unqualified “open source.” The license permits broad use, modification, and
distribution under its terms, but is not presented as a standard OSI license.
That precision matters for the enterprise provenance claim.

## Sources

- Poolside, [Laguna XS 2.1 model card](https://huggingface.co/poolside/Laguna-XS-2.1)
- Poolside, [Laguna S 2.1 model card](https://huggingface.co/poolside/Laguna-S-2.1)
- Poolside, [OpenMDW 1.1 license](https://huggingface.co/poolside/Laguna-XS-2.1/blob/main/LICENSE.md)
- Poolside, [published trajectories](https://trajectories.poolside.ai/)
- Qwen, [Qwen 3.6 35B-A3B](https://qwen.ai/blog?id=qwen3.6-35b-a3b)
- Qwen, [Qwen 3.6 27B model card](https://huggingface.co/Qwen/Qwen3.6-27B)
- Google, [Gemma 4 overview](https://ai.google.dev/gemma/docs/core)
- Thinking Machines Lab, [Inkling and Inkling-Small](https://thinkingmachines.ai/news/introducing-inkling/)
- Zhang and Khattab, [“Language model harnesses are compositional generalizers”](https://alexzhang13.github.io/blog/2026/harness/)
- Local synthesis: [Harness compositional generalization](harness-compositional-generalization.md)
- Local synthesis: [Recursive language model control](recursive-language-model-control.md)

## Addendum: build interpretation after hierarchy research

This addendum condenses the implications of the inference-tier research for an
initial semantic-computer build. It narrows what the prototype tests; it does
not promote the architecture or assume that it should replace model-owned
harnesses.

The semantic computer is a **research apparatus for code-owned durable control
with a replaceable, fallible semantic processor**. The kernel owns commitments:
durable state, budgets, effects, authority, acceptance, and accounting. A model
may still own rich local search or decomposition inside one bounded semantic
instruction. Its result is an attributed observation or proposal, not truth.

The context/KV layer is literally a cache of projected external state. Success
there does not imply that judgments are reusable, routable to a cheaper model,
learnable by a specialist, or compilable into code. Those are separate
properties that the machine trace should measure.

Keep three experiments separate:

1. **Substitution:** one processor per run; test whether the computer boundary
   survives XS, S, then a second model family.
2. **Routing:** make multiple processors available and learn which is competent
   for each instruction class.
3. **Promotion:** separately test response caches, skills, specialist models,
   and deterministic rules. Repetition alone licenses none of them.

“Same computer” should mean stable task-contract semantics, authority and effect
boundaries, accepted-transition semantics, evidence format, and kernel—not an
identical execution trace. The semantic ISA is therefore a hypothesis. Device
driver size, family-specific exceptions, and required kernel changes are
evidence about whether it is real. If cross-family substitution changes the
kernel or task meaning, the current result is a family-specific appliance.

Validation will often be partial. Deterministic code can check schemas, scope,
authority, state preconditions, tests, invariants, and receipts; it may not
establish semantic truth. The runtime should support `accept`, `reject`,
`abstain`, `escalate`, and `request more evidence`. Use explicit journal/replay
as the initial recovery model; add live restarts only if a workload demonstrates
sequential ambiguity that explicit steps cannot express cleanly.

The trace is the first reusable capability. In addition to the evidence already
listed, retain processor and driver versions, instruction-contract version,
exact context projections, candidate outputs, validation policy and verdict,
independent outcome evidence, rejected alternatives, and promotion lineage.
This supports measurement of competence regions, recurrence, resolution
equivalence, specialist generalization, rule scope, dependency, and total
acceptance cost.

Build in this order: fake-endpoint conformance, fixed-policy XS, fixed-policy S,
then one cross-family processor. Hold the logical projection and semantic
instruction contract fixed before allowing processor-native optimization. Add
routing or promotion only after those traces show what relation exists.

Prefer a small language-neutral semantic IR. Python is the practical
model-facing experiment surface; Rust is a candidate durable/capability kernel;
proof tooling should check only stable encoded invariants. Common Lisp, OCaml,
and Racket are later control-semantics probes, not alternative implementations
of the whole computer.

## Addendum: benchmark task sources

The initial build should reuse existing task semantics, environments, and
evaluators. The semantic computer is an alternate execution adapter: task data
is mounted as durable state, while the upstream evaluator remains the acceptance
oracle. Because this changes task presentation, results must be paired with the
benchmark's native harness rather than reported as raw-model leaderboard scores.

- **[AppWorld](https://github.com/StonyBrookNLP/appworld):** the closest match
  to the architecture. Mount its task-specific databases, identity, time, and
  API documentation; use its APIs as effects and its state-based tests to check
  correct outcomes and collateral damage.
- **[GraphWalks](https://huggingface.co/datasets/openai/graphwalks) and
  [OOLONG](https://huggingface.co/datasets/oolongbench/oolong-synth):** isolate
  the memory hierarchy. Mount graphs or records as structured state and measure
  projection, working-set scaling, repeated access, and deterministic
  preprocessing against exact or published evaluators.
- **[Terminal-Bench 2.1](https://hub.harborframework.com/datasets/terminal-bench/terminal-bench-2-1/latest)
  through [Harbor](https://github.com/harbor-framework/harbor):** test general
  computation across filesystems, processes, compilation, and heterogeneous
  tools. Keep its containers, resource limits, and executable verifiers fixed;
  use published trajectories for exploratory failure analysis, not training.
- **[τ-bench](https://github.com/sierra-research/tau2-bench):** test policy,
  authority, admissibility, mutable tools, and sequential interaction. Pin the
  task and grader version and repeat trials because the user simulator adds
  variance.
- **[SWE-bench Verified](https://github.com/SWE-bench/SWE-bench):** later test
  repository-scale diagnosis, code mutation, test-gated acceptance, and theory
  preservation. It is valuable but substantially heavier and narrower than the
  first four.

Suggested order: **AppWorld → GraphWalks/OOLONG → Terminal-Bench → τ-bench →
SWE-bench Verified**. Use train, development, or generated task families while
building routing and promotion; keep test splits frozen. These benchmarks can
test the computer's mechanisms, but not establish real-workload escalation
locality, long-term promotion economics, or human competence maintenance. Those
still require instrumented operational or longitudinal evidence.
