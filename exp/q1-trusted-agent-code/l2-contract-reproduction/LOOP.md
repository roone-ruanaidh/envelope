# Q1/L2 — corrected contract reproduction

> **Question:** Can the approved lease-service loop produce the missing cost observation after its dispatch tests are made hermetic?

Q1/L1 ended `Inconclusive` before model invocation because three synthetic dispatch tests read the live run evidence directory. Q1/L2 repeats that workload once after isolating their mutable test state. It is a troubleshooting run, not a benchmark, model comparison, reliability claim, or preselected next research branch.

## What changes

Only two mechanics change:

- each synthetic dispatch test receives its own temporary evidence, result, and process-lock paths;
- this loop owns a small launcher, evidence directory, result, and context record while reusing the frozen Q1/L1 workload.

The Q1/L1 terminal result and evidence remain immutable. Its executable commit was `6abb9bea6c65779632f765cb76f32532af7c1f6c`, its run was `20260721T062629Z-b09fbc7b`, and its terminal result commit was `c069bc0a19b410562b30b78885efd3618fb41ec9`.

## Frozen workload

Q1/L2 incorporates the procedure, limits, evidence rules, settlement rules, acceptance meaning, and human boundary in [Q1/L1](../l1-contract-reproduction/LOOP.md). The current executable contract commit binds that reference and every reused authority.

The workload remains `q1-lease-service-v1`:

- `codex-cli 0.144.6`, `gpt-5.6-luna`, reasoning effort `max`;
- one fresh isolated candidate VM, stdin API-key authentication, one initial invocation, and at most one same-thread remediation;
- the same candidate-visible contract, prompts, completion schema, managed environment, snapshot, transfer, clean bootstrap, strict typing, sealed behavior suite, and candidate-identity checks;
- the same pre-existing `q1-l1-evaluator`, resource namespace, fingerprint authority, isolation envelope, and zero-residue rule;
- the exact [Q1/L1 human source checklist](../l1-contract-reproduction/reproduction/HUMAN_REVIEW.md), reached only after every non-human gate passes.

The `q1-l1` infrastructure and protocol names identify that frozen workload; they do not identify this loop's evidence or result.

## Procedure and stopping rule

1. On clean `main`, require the exact reviewed Q1/L2 contract commit, out-of-band `OPENAI_API_KEY`, no Q1/L2 evidence or result, no workload candidate VM or evaluator residue, and the pinned evaluator already `Running`.
2. Start clocks and Q1/L2 evidence. Record the loop/workload relationship, copy both active-loop and frozen-workload authorities, then run evaluator fingerprint, dispatch, evaluator, and isolation validation inside measurement.
3. If validation passes, execute the unchanged Q1/L1 provision → invoke → snapshot → transfer → all non-human gates → eligible one-time remediation procedure.
4. Run cleanup, evidence integrity, public-safety, and settlement gates. An automatic terminal state produces `RESULT.md` and a local commit. `PendingHumanReview` stops without a result commit until an explicit attestation is supplied through this loop's launcher.
5. Stop after this one run. The result records what the run adds to Q1 and returns the whole evidence set for human discussion. Automation neither selects nor authorizes a next loop or promotion.

No in-run repair, retry, evaluator update, acceptance change, or undefined judgment is allowed. An undefined boundary settles `Inconclusive` after measurement begins; before measurement it stops without a disposition.

## Evidence and disposition

Required evidence is the Q1/L1 set plus `context.json`, this loop contract, its launcher, and the incorporated workload contract. Costs remain separate: agent usage/time, candidate-VM interval, evaluator workload, trusted-machine time, human attention, and wall time. Missing measurements remain `unknown`, never zero.

| State | Effect on Q1 |
|---|---|
| `Accepted` | One configuration-specific cost-to-accepted-completion observation. |
| `Rejected` | A cost-to-rejection observation, not accepted-completion cost. |
| `Inconclusive` | Recorded cost and failure evidence, but no valid accepted-completion observation. |
| `PendingHumanReview` | Non-human cost observed; accepted completion still requires explicit source attestation. |

`Accepted`, `Rejected`, and `Inconclusive` use the unchanged Q1/L1 rules. None authorizes a next loop. `PendingHumanReview` is nonterminal and cannot be committed as a result.

## Limits

The Q1/L1 budgets are unchanged: two agent invocations maximum, 30 minutes each with no retries; three hours automated execution; a five-minute cleanup reserve; 300 seconds for finalization; 10-minute default commands; 30-minute provisioning; 31-minute outer agent timeout; and the same transfer, control, evidence, evaluator-resource, and 45-second public behavioral limits.

## Verify and run

Read-only:

```sh
cd ../l1-contract-reproduction && make verify-dispatch
python3 -B -I ../l2-contract-reproduction/reproduction/run_l2.py plan
```

After the exact contract commit is reviewed and execution is explicitly approved:

```sh
python3 -B -I reproduction/run_l2.py execute \
  --contract-commit <full-reviewed-commit>
```

If the run reaches human review, finalize only with the explicit external attestation:

```sh
python3 -B -I reproduction/run_l2.py finalize \
  --run-id <run-id> \
  --attestation </outside/repository/human-attestation.json> \
  --contract-commit <full-reviewed-commit>
```

Never push from the loop runner.
