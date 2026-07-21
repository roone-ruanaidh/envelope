# Q1/L8 — authenticated public-safe invocation

> **Question:** Can the frozen lease-service workload proceed beyond Q1/L7's authentication failure when bearer acceptance is checked before measured provisioning and provider-masked key fingerprints are removed before evidence indexing?

Q1/L7 passed the evaluator, isolation, candidate provisioning, boundary, and login mechanics. Its one agent process reached OpenAI but received `401 invalid_api_key`, so no model completion or task-cost observation exists. Q1/L8 tests only the two controls earned from that run. It is troubleshooting, not a benchmark, reliability claim, or model comparison.

## Change and lineage

1. After local commit, residue, and key-presence guards—but before a run ID, clocks, evidence, run-scoped evaluator work, or candidate provisioning—send the exact in-memory credential through secret stdin to one direct `GET /v1/models` child with a 30-second total deadline. Pass only on HTTP `200`; make no retry, read no response body, and record no headers, request ID, error text, account data, or credential identifier.
2. Recognize the exact provider-masked `sk-…***…suffix` form observed in L7 as credential-shaped bytes. The recorder removes it before writing command streams. The terminal sanitizer remains a fail-closed defense: any escaped fingerprint is removed before the v3 index and forces `Inconclusive`.
3. Do not repeat the standalone candidate qualification. L7 already passed the unchanged provisioner and boundary; measured execution still revalidates both.

The baseline is Q1/L7 run `20260721T181955Z-4de70100`, public-safe terminal commit `9de1e949d7cdb4b00ca5c2451bb313af4b4b9ad5`. Its `Inconclusive` disposition remains unchanged. Q1/L8 proceeds under the later explicit human approval, not under L7's closed troubleshooting branch.

## Frozen contract

Q1/L8 otherwise incorporates the workload, acceptance, environments, budgets, evidence, accounting, dispositions, and human boundary in [Q1/L1](../l1-contract-reproduction/LOOP.md), plus the mechanical harness corrections through Q1/L7. The workload remains `q1-lease-service-v1`: `codex-cli 0.144.6`, `gpt-5.6-luna`, reasoning effort `max`, one fresh candidate VM, one initial invocation, and at most one eligible same-thread remediation.

Credential creation, replacement, permission repair, and funding are external human-owned prerequisites. The agent may consume the supplied secret but may not create, rotate, identify, or retain it. HTTP `200` proves bearer acceptance at the list-model endpoint only; it does not prove quota, model-specific access, Responses/WebSocket permission, later provider health, or inference success.

Humans still own acceptance meaning, source attestation, promotion, publication, and shipping. Agents own the approved execution, public-safe evidence, deterministic non-human settlement, and result draft.

## Procedure and stopping rule

1. Bind a clean reviewed commit and pass the offline dispatch suite.
2. Execute once. A failed or indeterminate authentication preflight is a prerequisite refusal: create no L8 run state or disposition, do not retry automatically, and stop until external credential or provider state changes.
3. After preflight passes, record only its fixed public-safe setup record, then execute the unchanged workload through every non-human gate and at most one eligible same-thread remediation.
4. Any later authentication, provider, evidence, or infrastructure failure settles `Inconclusive` when terminal evidence can close; otherwise stop for human recovery without rewriting evidence. Do not swap credentials or retry.
5. Stop at the automatic terminal disposition or `PendingHumanReview`. No next loop, attestation, promotion, publication, push, or shipping is authorized without a new human decision.

## Evidence, cost, and disposition

Required evidence and cost separation are unchanged. `setup/api-authentication-preflight.json` records only category, HTTP status, and duration; the request occurs before task measurement. Agent, candidate-VM, evaluator, trusted-machine, human, and wall costs remain separate, and unobserved values remain `unknown`.

`Accepted` still requires every non-human gate plus affirmative human review. `Rejected` still requires an admissible final candidate failure or concrete human source finding. A post-start infrastructure or evidence failure is `Inconclusive`.

## Verify and run

```sh
cd exp/q1-trusted-agent-code/l1-contract-reproduction
make verify-dispatch
python3 -B -I ../l8-contract-reproduction/reproduction/run_l8.py plan
python3 -B -I ../l8-contract-reproduction/reproduction/run_l8.py execute \
  --contract-commit <full-reviewed-commit>
```

Finalization after `PendingHumanReview` still requires explicit external attestation. The runner may commit a terminal result locally; it never pushes.
