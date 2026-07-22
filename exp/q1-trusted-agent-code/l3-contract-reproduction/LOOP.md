# Q1/L3 — parent-bounded command streams

> **Archived:** Executed contract. Q1 is retired; its executable authorities and terminal evidence remain in Git history.

> **Question:** Can the frozen lease-service workload produce a valid cost observation when command-stream limits are enforced by the parent instead of inherited as a child-wide file-size limit?

Q1/L2 reached candidate creation, then `limactl create` inherited the harness's 32 MiB stream limit as `RLIMIT_FSIZE` and failed while creating its 40 GiB disk. Q1/L3 changes that one harness mechanism. It is a troubleshooting run, not a benchmark, reliability claim, model comparison, or selected next research branch.

## Change and lineage

The parent now captures stdout and stderr independently and terminates the command process group on overflow. Children receive no file-size limit from stream capture. Input, redaction, timeouts, evidence limits, overflow classification, and settlement remain unchanged. Q1/L2's hermetic dispatch correction remains in the baseline.

| Loop | Executable commit | Run | Result commit |
|---|---|---|---|
| Q1/L1 | `6abb9bea6c65779632f765cb76f32532af7c1f6c` | `20260721T062629Z-b09fbc7b` | `c069bc0a19b410562b30b78885efd3618fb41ec9` |
| Q1/L2 | `d7292b3f737c25cf00a92f570b85d6f3bc7e4c2b` | `20260721T071826Z-10ec801b` | `de0d74a7effaa065cdd400519af17cf0fc859e61` |

## Fixed authority and boundaries

Q1/L3 incorporates the workload, acceptance, budgets, evidence, disposition, and human boundary in [Q1/L1](../l1-contract-reproduction/LOOP.md). The workload remains `q1-lease-service-v1`: the same candidate contract, prompts, model and agent stack, environments, remediation allowance, evaluator, isolation envelope, and cost categories.

The exact reviewed Q1/L3 commit is executable. Humans still own acceptance meaning, source attestation, promotion, publication, and shipping. Agents own qualification, the single approved execution, evidence, deterministic non-human settlement, and the result draft.

## Qualification and one-run rule

Before measurement, run the launcher's `qualify` command. It first requires the reviewed commit, pinned evaluator `Running`, and zero workload residue. A precondition refusal is not an attempt. Once candidate creation begins, that one attempt cannot be repaired or repeated: it creates one disk through parent-bounded capture, verifies the VM remained `Stopped`, deletes it, rechecks source and residue, and records a public-safe receipt. It never bootstraps, authenticates, invokes an agent, or runs acceptance.

After qualification passes, execute Q1/L3 exactly once:

1. Require clean `main`, the exact commit, out-of-band authentication, no Q1/L3 result or evidence, zero workload residue, and the pinned evaluator `Running`.
2. Start clocks and evidence; capture lineage; rerun evaluator fingerprint, dispatch, evaluator-bank, and isolation validation inside measurement.
3. Run the unchanged provision → invoke → snapshot → transfer → non-human gates procedure, including at most one same-thread candidate remediation.
4. Run cleanup, evidence integrity, public safety, accounting, and settlement.

There is no harness repair, execution retry, or second Q1/L3 run. A later hypothesis requires a new human-approved loop.

## Evidence and disposition

Terminal evidence is the Q1/L1 set plus `context.json`, this contract, its launcher, the incorporated workload contract, and a copy of the qualification receipt and command record. Qualification time is labeled setup, not task cost. Agent, candidate-VM, evaluator, trusted-machine, human, and wall intervals remain separate; unavailable observations remain `unknown`, never zero.

`Accepted`, `Rejected`, and `Inconclusive` use the unchanged Q1/L1 rules. If every non-human gate passes, stop at `PendingHumanReview`; no result commit exists until a human applies the unchanged source checklist. No disposition selects a next loop or authorizes promotion.

## Verify and run

```sh
cd exp/q1-trusted-agent-code/l1-contract-reproduction
make verify-dispatch
python3 -B -I ../l3-contract-reproduction/reproduction/run_l3.py plan
python3 -B -I ../l3-contract-reproduction/reproduction/run_l3.py qualify \
  --contract-commit <full-reviewed-commit>
python3 -B -I ../l3-contract-reproduction/reproduction/run_l3.py execute \
  --contract-commit <full-reviewed-commit>
```

If execution reaches human source review, finalize only from the same directory with explicit external attestation:

```sh
python3 -B -I ../l3-contract-reproduction/reproduction/run_l3.py finalize \
  --run-id <run-id> \
  --attestation </outside/repository/human-attestation.json> \
  --contract-commit <full-reviewed-commit>
```

Automatic terminal evidence produces `RESULT.md` and a local commit. Never push from the runner.
