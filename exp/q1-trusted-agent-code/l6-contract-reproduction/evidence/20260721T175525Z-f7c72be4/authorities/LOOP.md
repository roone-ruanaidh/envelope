# Q1/L6 — hermetic candidate-home evidence

> **Question:** Can the frozen lease-service workload reach its first agent invocation after making candidate-home redaction and its evaluator test environment-independent?

Q1/L5's exact candidate-boundary qualification passed. Measured execution then stopped in evaluator dispatch validation with zero agent attempts because the test derived candidate home from the evaluator's home basename. On the evaluator, `HOST_HOME` and the constructed `CANDIDATE_HOME` were identical, so the first replacement consumed both values and the test demanded an impossible second redaction record. Q1/L6 tests the smallest correction once. It is troubleshooting, not a benchmark, reliability claim, or model comparison.

## Change and lineage

1. Derive candidate home from the same Lima user contract as execution: `/home/<host-account>.guest`, independent of the current process home.
2. Test four distinct redaction classes with fixed paths, add an explicit identical-path regression, and bind verifier identity to the runner's Lima identity.
3. Record API-key stdin omission only after candidate login is attempted. Q1/L5's indexed evidence remains unchanged; its adjacent finding records the earlier generic sentence as inaccurate.

The baseline is Q1/L5 run `20260721T173838Z-aef45487`, terminal result commit `ae60848ae9465019a547d53bd95f62a1fa12144f`. Its `Inconclusive` disposition remains valid. Its “stop at measured execution” outer sentence was an agent drafting error relative to the controlling human approval; it does not alter Q1/L5 or authorize Q1/L6 by itself.

## Frozen contract

Q1/L6 incorporates the workload, acceptance, model, environments, budgets, evidence, accounting, dispositions, and human boundary in [Q1/L1](../l1-contract-reproduction/LOOP.md), the exact pre-agent qualification and failure closure in [Q1/L4](../l4-contract-reproduction/LOOP.md), and Q1/L5's reviewed single-metadata-authority candidate boundary. The workload remains `q1-lease-service-v1`: `codex-cli 0.144.6`, `gpt-5.6-luna`, reasoning effort `max`, one fresh candidate VM, one initial invocation, and at most one eligible same-thread remediation.

Humans still own acceptance meaning, source attestation, promotion, publication, and shipping. Agents own this approved qualification, one measured execution after a pass, public-safe evidence, deterministic non-human settlement, and the result draft.

## Procedure and stopping rule

1. Bind a clean reviewed commit and run the unchanged exact candidate-boundary qualification once outside task-cost measurement.
2. A started qualification failure closes Q1/L6 `Inconclusive`; do not retry it. A refusal before its durable marker is not an attempt. Unverifiable terminal evidence stops for human recovery without rewrite.
3. After a qualification pass, execute the unchanged workload once with out-of-band authentication, every non-human gate, and at most one eligible same-thread remediation.
4. `Accepted`, `Rejected`, `Inconclusive`, and `PendingHumanReview` retain their existing meanings. Diagnostics never change acceptance.
5. Under the existing human-approved Q1/L5–L7 troubleshooting sequence, at most three distinct one-shot loop contracts may be used to reach the first agent invocation; Q1/L6 is the second. A terminal loop may advance only when verified run state records `agent_attempts_invoked: 0`. Commit it before defining the smallest evidence-derived mechanical correction in the next numbered loop.
6. Stop immediately when any run records `agent_attempts_invoked >= 1`, Q1/L7 closes, terminal evidence cannot close and verify, continuation would change meaning or require an unscored decision, or the human source gate is reached. No retry, fourth loop, attestation, promotion, publication, push, or shipping is authorized by this sequence.

## Evidence, cost, and disposition

Required evidence and cost separation are unchanged. Qualification is setup, never task cost. Agent, candidate-VM, evaluator, trusted-machine, human, and wall costs remain separate; unobserved values remain `unknown`.

`Accepted` still requires every non-human gate plus affirmative human review. `Rejected` still requires an admissible final candidate failure or concrete human source finding. A started qualification failure, or infrastructure, evidence, or undefined-boundary failure after measurement begins, is `Inconclusive`.

## Verify and run

```sh
cd exp/q1-trusted-agent-code/l1-contract-reproduction
make verify-dispatch
python3 -B -I ../l6-contract-reproduction/reproduction/run_l6.py plan
python3 -B -I ../l6-contract-reproduction/reproduction/run_l6.py qualify \
  --contract-commit <full-reviewed-commit>
python3 -B -I ../l6-contract-reproduction/reproduction/run_l6.py execute \
  --contract-commit <full-reviewed-commit>
```

Finalization after `PendingHumanReview` still requires explicit external attestation. The runner may commit a terminal result locally; it never pushes.
