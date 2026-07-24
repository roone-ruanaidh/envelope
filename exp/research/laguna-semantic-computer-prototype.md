# Laguna semantic computer prototype

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

## What the two models expose

Run the same computer, task programs, memory policy, and instruction contracts
against both models first. This asks whether one machine abstraction survives a
semantic-processor swap. Model-specific optimization should follow only after
the fixed-policy comparison; otherwise processor capacity and architecture
adaptation are confounded.

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
- processor profiles for Laguna XS and S;
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
- Zhang and Khattab, [“Language model harnesses are compositional generalizers”](https://alexzhang13.github.io/blog/2026/harness/)
- Local synthesis: [Harness compositional generalization](harness-compositional-generalization.md)
- Local synthesis: [Recursive language model control](recursive-language-model-control.md)
