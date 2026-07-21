# Q1/L5 — single Codex metadata authority

> **Question:** Can the frozen lease-service workload reach task execution when Codex alone protects an initially absent workspace `.codex` path?

Q1/L4 exercised the real pre-agent path and exposed one remaining overlap before the Python probe began: pinned Codex automatically protected missing workspace `.codex`, while the custom profile denied the same missing path. Bubblewrap attempted incompatible directory and file masks and stopped with `Is a directory`. Q1/L5 tests the smallest correction once. It is troubleshooting, not a benchmark, reliability claim, or model comparison.

## Change and lineage

Delete only the workspace `.codex = "deny"` rule. Keep the user-home `~/.codex = "deny"` rule, initially absent workspace path, built-in Codex metadata protection, child-write and creation probes, candidate-control transfer rejection, pinned stack, and every declared boundary outcome.

The baseline is Q1/L4 run `20260721T170944Z-919d5660`, terminal result commit `4e83baae3884e23dd7c1b59293800218ab157006`.

## Frozen contract

Q1/L5 incorporates the workload, acceptance, model, environments, budgets, evidence, accounting, dispositions, and human boundary in [Q1/L1](../l1-contract-reproduction/LOOP.md), plus the exact pre-agent qualification and failure closure in [Q1/L4](../l4-contract-reproduction/LOOP.md). The workload remains `q1-lease-service-v1`: `codex-cli 0.144.6`, `gpt-5.6-luna`, reasoning effort `max`, one fresh candidate VM, one initial invocation, and at most one eligible same-thread remediation.

Humans still own acceptance meaning, source attestation, promotion, publication, and shipping. Agents own this approved qualification, one measured execution after a pass, public-safe evidence, deterministic non-human settlement, and the result draft.

## Procedure and stopping rule

1. Bind a clean reviewed commit and run the unchanged exact candidate-boundary qualification once, outside task-cost measurement.
2. Passing requires the same provenance, command sequence, probe output, teardown, source, residue, index, and completion receipt as Q1/L4. Diagnostics never change acceptance.
3. A started qualification failure closes Q1/L5 `Inconclusive`; do not retry it. A refusal before its durable marker is not an attempt. Unverifiable terminal evidence stops for human recovery without rewrite.
4. After a qualification pass, execute the unchanged workload once with out-of-band authentication. Run every non-human gate and at most one eligible same-thread remediation.
5. Automatic `Rejected` or `Inconclusive` is terminal for Q1/L5. If all non-human gates pass, stop at `PendingHumanReview` for the unchanged source checklist.
6. This result authorizes no next loop. Under the separately approved Q1/L5–L7 troubleshooting sequence, only a terminal qualification failure before task measurement begins may lead to the smallest evidence-derived mechanical correction in Q1/L6. Stop as soon as any loop begins measured execution or, if none does, after Q1/L7. No loop may authorize promotion.

## Evidence, cost, and disposition

Required evidence and cost separation are unchanged. Qualification is setup, never task cost. Agent, candidate-VM, evaluator, trusted-machine, human, and wall costs remain separate; unobserved values remain `unknown`.

`Accepted` still requires every non-human gate plus affirmative human review. `Rejected` still requires an admissible final candidate failure or concrete human source finding. A started qualification failure, or infrastructure, evidence, or undefined-boundary failure after measurement begins, is `Inconclusive`.

## Verify and run

```sh
cd exp/q1-trusted-agent-code/l1-contract-reproduction
make verify-dispatch
python3 -B -I ../l5-contract-reproduction/reproduction/run_l5.py plan
python3 -B -I ../l5-contract-reproduction/reproduction/run_l5.py qualify \
  --contract-commit <full-reviewed-commit>
python3 -B -I ../l5-contract-reproduction/reproduction/run_l5.py execute \
  --contract-commit <full-reviewed-commit>
```

Finalization after `PendingHumanReview` still requires explicit external attestation. The runner may commit a terminal result locally; it never pushes.
