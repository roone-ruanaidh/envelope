# Q1/L11 — consistent candidate snapshot boundary

> **Archived:** Executed contract. Q1 is retired; its executable authorities and terminal evidence remain in Git history.

> **Question:** What do Luna's candidate and evaluator results show once Codex runtime placeholders no longer block candidate transfer?

Q1/L10 produced the first Luna candidate, but the trusted snapshotter rejected the empty `.agents` placeholder left by the Codex invocation before any candidate gate ran. Q1/L11 removes only exact empty top-level runtime placeholders after candidate processes are quiesced. Control-path content, nested controls, links, and wrongly owned placeholders remain inadmissible.

The baseline is Q1/L10 run `20260721T210243Z-d16bed28`, terminal commit `805d106a69537d23d7fae3f7c6a718de4ba8e4fc`. Its `Inconclusive` disposition remains unchanged.

## Frozen contract

Q1/L11 otherwise incorporates Q1/L10 and Q1/L1 unchanged: workload, environments, Luna at max reasoning, invocation and remediation budgets, evidence, accounting, gates, dispositions, and human source-review stop. The intervention changes transfer mechanics, not accepted candidate source or acceptance meaning.

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
python3 -B -I ../l11-contract-reproduction/reproduction/run_l11.py plan
python3 -B -I ../l11-contract-reproduction/reproduction/run_l11.py execute \
  --contract-commit <full-reviewed-commit>
```

The runner may commit a terminal result locally; it never pushes.
