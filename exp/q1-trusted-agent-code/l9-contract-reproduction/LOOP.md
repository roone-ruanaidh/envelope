# Q1/L9 — compatible structured completion

> **Question:** Can Luna produce and declare a candidate when the unchanged completion alternatives are carried in the provider-supported root-object shape?

Q1/L8 authenticated successfully and passed candidate login, provisioning, and isolation. OpenAI rejected the root `oneOf` output schema before generation, so Luna never acted. Q1/L9 corrects only that wire format. It is troubleshooting, not a benchmark, reliability claim, or model comparison.

## Change and lineage

The schema now has one required root field, `completion`, whose nested `anyOf` contains the unchanged `declared_complete` and `blocked` objects. The runner requires that exact one-key envelope, unwraps it, and applies the existing semantic validator. Thus the accepted declaration set and downstream completion file remain unchanged.

The baseline is Q1/L8 run `20260721T204010Z-87c2d9c9`, terminal commit `744a13986555adcd93adf0f59102ffada9f871e5`. Its `Inconclusive` disposition remains unchanged.

## Frozen contract

Q1/L9 otherwise incorporates Q1/L8 and the Q1/L1 workload, environments, model (`gpt-5.6-luna`, reasoning effort `max`), budgets, remediation, evidence, accounting, gates, dispositions, and human boundary unchanged. Humans still own acceptance meaning, source attestation, promotion, publication, and shipping.

## Procedure and stop

1. Bind a clean reviewed commit and pass the offline dispatch suite.
2. Execute once through every non-human gate and at most one eligible same-thread remediation.
3. Another provider-schema, infrastructure, or evidence failure settles `Inconclusive` when evidence can close; otherwise stop for human recovery.
4. Stop at automatic terminal disposition or `PendingHumanReview`. No next loop, attestation, promotion, publication, push, or shipping is authorized by this loop.

Required evidence and separate agent, candidate-VM, evaluator, trusted-machine, human, and wall-time accounting remain unchanged. `Accepted`, `Rejected`, and `Inconclusive` retain their prior definitions.

## Verify and run

```sh
cd exp/q1-trusted-agent-code/l1-contract-reproduction
make verify-dispatch
python3 -B -I ../l9-contract-reproduction/reproduction/run_l9.py plan
python3 -B -I ../l9-contract-reproduction/reproduction/run_l9.py execute \
  --contract-commit <full-reviewed-commit>
```

Finalization after `PendingHumanReview` still requires explicit external attestation. The runner may commit a terminal result locally; it never pushes.
