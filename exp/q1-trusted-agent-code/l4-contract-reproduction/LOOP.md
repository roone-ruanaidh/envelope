# Q1/L4 — qualified candidate boundary

> **Archived:** Executed contract. Q1 is retired; its executable authorities and terminal evidence remain in Git history.

> **Question:** Can the frozen lease-service workload reach task execution after simplifying the candidate profile and qualifying the complete boundary path?

Q1/L3 reached candidate bootstrap but stopped before model invocation. Its verifier discarded the probe error, and a later disposable diagnostic found three overlapping profile rules whose removal made the same boundary assertions, probe, and pass rule succeed. Q1/L4 tests that narrow correction once. Its result determines whether Q1 gains a task observation or another harness finding; it does not predetermine what follows. This is a troubleshooting run, not a benchmark, reliability claim, or model comparison.

## Change and lineage

Q1/L4 changes only the candidate boundary machinery:

1. Define `q1_l1` directly by deleting `extends = ":workspace"`, the absent `.agents` deny, and the unsupported recursive `AGENTS.md` read glob. Keep the exact top-level `AGENTS.md` rule and every declared boundary outcome. Enforce the existing no-candidate-control-file rule at transfer, including Codex's `AGENTS.override.md` form; this is a control boundary, not task acceptance.
2. Retain a fixed failure phase, return code, and bounded public-safe probe output; remove the unparsed `findmnt --json` dump. Diagnostics explain a result but never change it.
3. Before measurement, qualify the exact execution path through candidate creation, bootstrap, the same boundary assertions, probe, and pass rule, teardown, source recheck, and zero residue. Qualification uses no API credential or model. Evaluator residue probes are setup; no evaluator acceptance workload runs.

The baseline is Q1/L3 run `20260721T153644Z-b31c1649`, terminal result commit `42b4c48880bc98358dbad84e3b71e7d06b416211`.

## Frozen contract

Q1/L4 incorporates the workload, acceptance, model, agent stack, environments, budgets, evidence rules, accounting, dispositions, and human boundary in [Q1/L1](../l1-contract-reproduction/LOOP.md). The workload remains `q1-lease-service-v1`: `codex-cli 0.144.6`, `gpt-5.6-luna`, reasoning effort `max`, one fresh candidate VM, one initial invocation, and at most one eligible same-thread remediation.

Humans still own acceptance meaning, source attestation, promotion, publication, and shipping. Agents own the approved qualification, one measured execution, reproducible public-safe evidence, deterministic non-human settlement, and the result draft.

## Procedure and stopping rule

1. On clean `main`, bind the exact reviewed commit and verify the pinned evaluator, source, and zero workload residue.
2. Run `qualify` once outside task-cost measurement. The durable `qualification.json` `Running` record is the attempt boundary, immediately before the shared provisioner. Probe with the workspace control directory absent, matching agent start; require the same boundary pass, then always tear down and recheck source and residue. Preserve the report, boundary evidence, command and redaction records, setup accounting, bounded logs, index, and completion receipt; a failure also binds its terminal result. A refusal before the durable marker is not an attempt. A later classifiable failure settles Q1/L4 `Inconclusive` and cannot retry. If terminal evidence cannot close and verify, stop for human recovery without rewriting it.
3. Execution requires explicit approval bound to the contract commit; approval may precede qualification, but `execute` starts only after qualification passes. Then require out-of-band authentication and execute once with a fresh candidate VM. Run the unchanged evaluator validation, provision → invoke → snapshot → transfer → non-human gates → eligible one-time remediation → cleanup → settlement procedure.
4. Do not repair the harness, alter acceptance, retry execution, or run Q1/L4 again. Before the durable qualification marker, stop without disposition. At or after it, an undefined-boundary failure is `Inconclusive`, subject to the terminal-evidence recovery rule above.
5. Return the complete result for broad human discussion. Automation neither selects nor authorizes a next loop or promotion.

## Evidence, cost, and disposition

Required evidence is the Q1/L1 set plus Q1/L4 context and authorities and the complete qualification record. Its index and completion receipt bind the reviewed commit, exact command sequence, boundary report, teardown, source, residue, redactions, and setup ledger. Qualification time is setup, never task cost. Agent, candidate-VM, evaluator, trusted-machine, human, and wall costs remain separate; missing observations remain `unknown`.

`Accepted` (Pass) still requires every non-human gate plus affirmative human review. `Rejected` (Fail) still requires an admissible final candidate failure or concrete human source finding. A started qualification failure, or infrastructure, evidence, or undefined-boundary failure after measurement begins, is `Inconclusive`. If every non-human gate passes, stop at `PendingHumanReview` until a human applies the unchanged source checklist. No disposition selects the next research branch.

## Verify and run

```sh
cd exp/q1-trusted-agent-code/l1-contract-reproduction
make verify-dispatch
python3 -B -I ../l4-contract-reproduction/reproduction/run_l4.py plan
python3 -B -I ../l4-contract-reproduction/reproduction/run_l4.py qualify \
  --contract-commit <full-reviewed-commit>
python3 -B -I ../l4-contract-reproduction/reproduction/run_l4.py execute \
  --contract-commit <full-reviewed-commit>
```

If execution reaches human source review, finalize only with explicit external attestation:

```sh
python3 -B -I ../l4-contract-reproduction/reproduction/run_l4.py finalize \
  --run-id <run-id> \
  --attestation </outside/repository/human-attestation.json> \
  --contract-commit <full-reviewed-commit>
```

Automatic terminal evidence produces `RESULT.md` and a local commit. Never push from the runner.
