# Q1/L10 — explicit completion scalar types

> **Archived:** Executed contract. Q1 is retired; its executable authorities and terminal evidence remain in Git history.

> **Question:** Can Luna act on the frozen workload once every constant-valued completion field also declares its provider-required JSON type?

Q1/L9 passed the root-object boundary, then OpenAI rejected the first `status` field because `const` lacked an explicit `type`. Luna still did not infer or edit. Q1/L10 adds only `"type": "string"` to both unchanged status fields and verifies that invariant.

The baseline is Q1/L9 run `20260721T205408Z-36bfc6d1`, terminal commit `5b1e496bc3ee5bc7c673668c0cabb875896af801`. Its `Inconclusive` disposition remains unchanged.

## Frozen contract

Q1/L10 otherwise incorporates Q1/L9 and Q1/L1 unchanged: workload, environments, Luna at max reasoning, invocation and remediation budgets, evidence, accounting, gates, dispositions, and human source-review stop. This is schema troubleshooting, not a benchmark or model claim.

## Procedure and stop

1. Bind a clean reviewed commit and pass the offline dispatch suite.
2. Execute once through every non-human gate and at most one eligible same-thread remediation.
3. A provider, infrastructure, or evidence failure settles `Inconclusive` when evidence can close; otherwise stop for human recovery.
4. Stop at automatic terminal disposition or `PendingHumanReview`. Humans retain source attestation, promotion, publication, and shipping.

Required evidence and separate agent, candidate-VM, evaluator, trusted-machine, human, and wall-time accounting remain unchanged.

## Verify and run

```sh
cd exp/q1-trusted-agent-code/l1-contract-reproduction
make verify-dispatch
python3 -B -I ../l10-contract-reproduction/reproduction/run_l10.py plan
python3 -B -I ../l10-contract-reproduction/reproduction/run_l10.py execute \
  --contract-commit <full-reviewed-commit>
```

The runner may commit a terminal result locally; it never pushes.
