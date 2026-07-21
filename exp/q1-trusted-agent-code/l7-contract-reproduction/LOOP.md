# Q1/L7 — live candidate Lima shape

> **Question:** Can the frozen lease-service workload reach its first agent invocation after binding candidate-environment evidence to Lima's live empty-field representation?

Q1/L6 passed exact qualification, evaluator validation, candidate bootstrap, and the boundary probe. It then stopped before login with zero agent attempts because the trusted candidate observer expected fields that the live Lima record omits. A disposable no-model diagnostic found the exact delta: candidate `config` omits empty `mounts`, evaluator-only `param`, and inactive `vmOpts.qemu`; the top-level candidate record also omits `param`. The diagnostic VM was deleted and zero candidate residue was verified. Q1/L7 tests the mechanical observer correction once. It is troubleshooting, not a benchmark, reliability claim, or model comparison.

## Change and lineage

1. Keep evaluator parameter checks unchanged, but require candidate `param` to be absent at both live-record levels.
2. Require candidate `mounts` to be absent from the live config while preserving the reviewed YAML's empty mount list and the boundary probe's host-workspace absence proof; normalize it as `mounts: []` in evidence.
3. Require inactive `vmOpts.qemu` to be absent for the VZ candidate, use a live-shaped fixture, and continue rejecting unknown instance or config fields.

The baseline is Q1/L6 run `20260721T175525Z-f7c72be4`, terminal result commit `f00af3cab9c952bb42b8490973c4de697c0ccb4c`. Its `Inconclusive` disposition and indexed evidence remain unchanged.

## Frozen contract

Q1/L7 incorporates the workload, acceptance, model, environments, budgets, evidence, accounting, dispositions, and human boundary in [Q1/L1](../l1-contract-reproduction/LOOP.md); the exact pre-agent qualification and failure closure in [Q1/L4](../l4-contract-reproduction/LOOP.md); Q1/L5's single-metadata-authority candidate boundary; and Q1/L6's hermetic candidate identity, redaction, and login-omission evidence. The workload remains `q1-lease-service-v1`: `codex-cli 0.144.6`, `gpt-5.6-luna`, reasoning effort `max`, one fresh candidate VM, one initial invocation, and at most one eligible same-thread remediation.

Humans still own acceptance meaning, source attestation, promotion, publication, and shipping. Agents own this approved qualification, one measured execution after a pass, public-safe evidence, deterministic non-human settlement, and the result draft.

## Procedure and stopping rule

1. Bind a clean reviewed commit and run the unchanged exact candidate-boundary qualification once outside task-cost measurement.
2. A started qualification failure closes Q1/L7 `Inconclusive`; do not retry it. A refusal before its durable marker is not an attempt. Unverifiable terminal evidence stops for human recovery without rewrite.
3. After a qualification pass, execute the unchanged workload once with out-of-band authentication, every non-human gate, and at most one eligible same-thread remediation.
4. `Accepted`, `Rejected`, `Inconclusive`, and `PendingHumanReview` retain their existing meanings. Diagnostics never change acceptance.
5. Under the extended human-approved Q1/L5–L9 troubleshooting sequence, at most five distinct one-shot loop contracts may be used to reach the first agent invocation; Q1/L7 is the third. A terminal loop may advance only when verified run state records `agent_attempts_invoked: 0`. Commit it before defining the smallest evidence-derived mechanical correction in the next numbered loop.
6. If execution records `agent_attempts_invoked >= 1`, the outer troubleshooting sequence ends while this already-approved execution continues only through its inherited automatic terminal or `PendingHumanReview` boundary. Otherwise stop at Q1/L9 closure, an unverifiable terminal state, a meaning-changing or unscored boundary, or the human source gate. No retry, Q1/L10, attestation, promotion, publication, push, or shipping is authorized.

## Evidence, cost, and disposition

Required evidence and cost separation are unchanged. Qualification and the disposable diagnostic are setup, never task cost. Agent, candidate-VM, evaluator, trusted-machine, human, and wall costs remain separate; unobserved values remain `unknown`.

`Accepted` still requires every non-human gate plus affirmative human review. `Rejected` still requires an admissible final candidate failure or concrete human source finding. A started qualification failure, or infrastructure, evidence, or undefined-boundary failure after measurement begins, is `Inconclusive`.

## Verify and run

```sh
cd exp/q1-trusted-agent-code/l1-contract-reproduction
make verify-dispatch
python3 -B -I ../l7-contract-reproduction/reproduction/run_l7.py plan
python3 -B -I ../l7-contract-reproduction/reproduction/run_l7.py qualify \
  --contract-commit <full-reviewed-commit>
python3 -B -I ../l7-contract-reproduction/reproduction/run_l7.py execute \
  --contract-commit <full-reviewed-commit>
```

Finalization after `PendingHumanReview` still requires explicit external attestation. The runner may commit a terminal result locally; it never pushes.
