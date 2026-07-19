# L1 — contract reproduction

> **Question:** What does it cost to move one agent-produced lease service from declared completion to accepted completion under a fixed contract and settlement procedure?

This proposed loop belongs to [`Q1 — cost of trusted agent-produced code`](../QUESTION.md). It defines a lease-based job-service contract and measures the work required to settle one isolated agent implementation against it. The accounting boundary keeps agent usage, machine execution, human attention, and wall latency separate; unavailable observations remain unknown rather than zero.

No candidate run or loop disposition exists.

## Settlement

Accepted completion requires:

- all behavioral scenarios to pass;
- strict typing under the public pinned configuration;
- a clean bootstrap from locked dependencies; and
- affirmative human source review of the declared implementation constraints.

The public implementation contract is in [`public/contract`](public/contract). The evaluator, behavioral reference, and deliberate defects are loop-owned and excluded from the implementation agent's environment.

One candidate and any remediation share one isolated workspace and budget. The run settles as `Accepted`, `Rejected`, or `Inconclusive`. L1 does not establish population reliability, production readiness, security outside the declared boundary, or correctness beyond the contract.

## Reproduction

Run behavioral verification against a foreground candidate service:

```sh
make verify \
  BASE_URL=http://127.0.0.1:8765 \
  SERVICE_COMMAND='python3 -m candidate_service'
```

The service receives `CT_HOST`, `CT_PORT`, `CT_DATABASE_PATH`, and `CT_CLOCK_INITIAL_MS`. `make verify` proves only the declared black-box behaviors; it does not satisfy the typing, bootstrap, or human-review gates.

Validate the evaluator with:

```sh
make verify-evaluator
```

Authoritative validation runs in the recorded Lima instance:

```sh
limactl shell ct-ev -- sh -lc 'cd /Users/engineer/ws/ev/exp/q1-trusted-agent-code/l1-contract-reproduction && make verify-evaluator'
```

Candidate authoring uses the no-host-mount Lima environment declared in `reproduction/candidate-lima.yaml`. Setup installs the pinned toolchain and public dependency lock before the agent phase; agent commands can access only the public bundle and candidate workspace and cannot use the network.
