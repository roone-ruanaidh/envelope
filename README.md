<p align="center">
  <img src="mark.svg" alt="Envelope trajectory mark" width="320">
</p>

# Envelope

Envelope makes AI work priceable by verified task instead of by token.
Envelope does not set prices. Instead, it provides probability pricing for accepted completion of a defined task.

Use it to build cost-effective AI workflows, or to order budgetable tasks using qualified models, harnesses, and infrastructure. 

# How It Works

Per-token pricing measures raw inputs and outputs, but a task's real price includes the remediation and verification required to reach acceptance, in addition to generation.

Envelope takes an acceptance contract (the criteria and constraints that define done) and any preferences you set (models, harnesses, infrastructure, or none at all), and prices the task from measured evidence (benchmarked runs of comparable work under comparable configurations). 

To do this, Envelope uses probability pricing.
Probability pricing provides a distribution of probable costs to achieve accepted completion of the defined task, ranging from the most probable cost to the least probable cost (which may be more or less expensive).
Broader criteria, tighter constraints, preferences, or stacking tasks will reshape Envelope's probability pricing and illuminate trade-offs clearly.

**In Envelope, the price of uncertainty stays visible instead of being averaged away.** 

# Roadmap

Envelope is built through experimentation.

The [`exp/`](exp/) directory holds candidates, active experiments, and their evidence.
Artifacts leave `exp/` for `src/` **only** through an explicit promotion decision.

GitHub issues are the work registry. 
Candidate issues imply neither priority nor sequence.

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

Envelope's provisional language boundary is:

- **Lean** owns what can be proven: acceptance, admissibility, settlement.
- **Rust** owns the system core: execution, evidence, storage, deployment.
- **Python** owns experiments and user-ergonomics.
