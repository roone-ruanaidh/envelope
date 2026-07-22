<p align="center">
  <img src="mark.svg" alt="Envelope trajectory mark" width="320">
</p>

# Envelope

Envelope is an AI research project on state-machine and RLM-style harness design.
It studies how memory management, durable state, gated context, tool design, and deterministic control change what agentic work costs.

# Hypotheses

Envelope has three initial hypotheses that will be tested in order but can fail independently:

1. Creating a state machine around an AI model will identify acceptable and unacceptable paths for common task arcs. Those paths can be generalized into RLM-style harnesses where the AI model acts as a semantic co-processor to deterministic computation.

2. AI models will reach accepted completion for the same task at a lower cost when operating inside a state-machine and RLM-style harness compared to popular agent harnesses alone (e.g., Claude Code, Codex, Pi, Devin, Hermes, OpenClaw).

3. The cost savings from the use of a state-machine and RLM-style harness compared to popular agent harnesses will be enough to recover the cost to build that custom design.

# Roadmap

Each milestone builds on the last:

| # | Milestone | Status |
|---|---|---|
| 1 | Learning loop methodology | In Progress |
| 2 | Design a memory hierarchy with durable state artifacts | Not Started |
| 3 | Establish state transition telemetry with costs | Not Started |
| 4 | Generalize task arcs into RLM-style harnesses | Not Started |
| 5 | Benchmark designs against popular agent harnesses | Not Started |
| 6 | Assess costs saved vs. cost to build | Not Started |
| 7 | Publish initial findings | Not Started |

Envelope is built through experimentation.
[`exp/`](exp/) holds questions, learning loops, results, and debriefs.

**Designs leave `exp/` for `src/` only through explicit promotion.**

[`NOTEBOOK.md`](NOTEBOOK.md) records what changes Envelope's direction over time.
