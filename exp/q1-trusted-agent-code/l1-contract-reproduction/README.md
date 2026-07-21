# Q1/L1 — contract reproduction

Q1/L1 measures the cost of moving one agent-produced lease service from declared completion to accepted completion under a fixed contract. It is one configuration-specific observation, not a reliability benchmark or model comparison.

The candidate builds a typed FastAPI/SQLite job-leasing service tested for idempotency, lease authority, concurrency, logical time, and restart persistence.

Read [Q1](../QUESTION.md) for the research question and [LOOP.md](LOOP.md) for the approved execution and disposition contract. This README is only a map; `LOOP.md` and its reviewed authorities control execution.

The flow is: isolated agent workspace → immutable declared snapshot → sealed bootstrap, typing, and behavior gates → at most one same-thread remediation → human source review. Evidence keeps agent, machine, human, and wall time separate; missing costs remain unknown.

| Area | Role |
|---|---|
| [`public/contract/`](public/contract/) | Everything the implementation agent may know about acceptance. |
| [`evaluator/`](evaluator/) | Sealed black-box acceptance and evaluator self-validation. |
| [`reproduction/`](reproduction/) | Provisioning, isolation, transfer, orchestration, evidence, and settlement. |

Start with [`run_l1.py`](reproduction/run_l1.py) for `plan | execute | finalize`, [`verify_evaluator.py`](evaluator/verify_evaluator.py) for evaluator validity, and [`candidate_transfer.py`](reproduction/candidate_transfer.py) for the candidate-to-evaluator trust boundary.
