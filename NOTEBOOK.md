# Notebook

A curated record of the evidence and ideas that change how I think about Envelope and inference engineering.
Entries connect experiments, research, and outside influences.

## 2026-07-21

### The environment is the first cost to measure and optimize

I began by treating models, harnesses, and infrastructure as configurations beneath task pricing.
[Q1](exp/q1-trusted-agent-code/DEBRIEF.md) changed that: nine loops preceded the first substantive GPT-5.6-Luna generation, every observed terminal failure came from the environment or harness, and GPT-5.6-Luna's candidate never reached trusted evaluation.

The model may or may not have passed; what Q1 established is that environment establishment, verification, and attribution may be the highest-leverage cost-to-acceptance work.

A qualified environment is reusable capital and capability: build it as a versioned, consumable artifact, measure what it costs to establish and maintain, and observe how it changes the cost of accepted work.

### Inference, recursion, and memory—oh my!

A memory hierarchy as a qualified environment—and the modular parts that can be derived from it—feels like a compelling direction in response to Q1 learning and what I'm seeing on X.
Some initial thoughts as I research inference engines, RLMs, and state machines further:

- Context window as cache
- Durable state via OS-level artifacts
- Code as the gate to the cache
- Model as semantic coprocessor to deterministic computation

A provisional language boundary for that might be:

- Python discovers operators and orchestrates bounded model calls.
- Rust owns control, isolation, accounting, and evidence.
- Lean proves machine bounds, replay, and settlement — not external truth.

Some recent relevant materials that have stuck with me:

- Together AI's [Open-Source Inference Engineering for the Agentic Era](https://docs.google.com/presentation/d/1antvLocE7BIbbpLnkHT6SfoCwAIuXYdnLIZxDaX5dIw/edit#slide=id.g39324cdc3cd_1_292)
- NVIDIA's [Inside NVIDIA Vera CPU: Olympus Cores Built for Maximum Single-Threaded Performance in Agentic AI](https://developer.nvidia.com/blog/inside-nvidia-vera-cpu-olympus-cores-built-for-maximum-single-threaded-performance-in-agentic-ai/)
- [Language model harnesses are compositional generalizers](https://alexzhang13.github.io/blog/2026/harness/), by Alex L. Zhang and Omar Khattab (MIT CSAIL)
- [This video from Theo (T3 Stack/Code)](https://www.youtube.com/watch?v=xmGY276gEFY)
