<p align="center">
  <img src="mark.svg" alt="Envelope trajectory mark" width="320">
</p>

# Envelope

Envelope is a research project on pricing AI work by verified task instead of by token.

Envelope's goal is to enable cost-effective AI workflows that can be accurately budgeted for, using qualified models, harnesses, and infrastructure. 
Envelope will not set prices. Instead, it will provide probability pricing for accepted completion of a defined task.

# Vision

Per-token pricing measures raw inputs and outputs, but a task's real price includes the remediation and verification required to reach acceptance, in addition to generation.

Envelope researches combining an acceptance contract (the criteria and constraints that define done) and user preferences (models, harnesses, infrastructure, or none at all) to price the tasks' cost-to-acceptance from measured evidence (benchmarked runs of comparable work under comparable configurations). 

To do this, Envelope will use probability pricing.
Probability pricing provides a distribution of probable costs to achieve accepted completion of the defined task, ranging from the most probable cost to the least probable cost (which may be more or less expensive).

Broader criteria, tighter constraints, preferences, or stacking tasks will reshape Envelope's probability pricing and illuminate trade-offs clearly.
**In Envelope, the price of uncertainty will stay visible instead of being averaged away.** 

# Roadmap

Each milestone builds on the last:

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Methodology for pricing verified tasks | In Progress |
| 2 | Proof-checked acceptance contracts | Not Started |
| 3 | Self-serve task pricing | Not Started |
| 4 | Qualified task harnesses | Not Started |
| 5 | Automated qualification and drift-detection | Not Started |
| 6 | Budgetable ordering | Not Started |
| 7 | Real-time pricing of novel tasks | Not Started |

Envelope is built through experimentation.
The [`exp/`](exp/) directory holds research, questions, learning loops, results, and evidence.
Artifacts leave `exp/` for `src/` **only** through an explicit promotion decision.

Envelope's provisional language boundary is:

- **Lean** owns what can be proven: acceptance, admissibility, settlement.
- **Rust** owns the system core: execution, evidence, storage, deployment.
- **Python** owns experiments and user-ergonomics.
