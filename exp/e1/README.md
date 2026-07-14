# E1 — trusted agent-produced code

> **Question:** What does it cost to move one agent-produced lease service from declared completion to accepted completion under a frozen contract and settlement procedure?

E1 defines a lease-based job-service contract and measures the work required to settle one isolated agent implementation against it. The accounting boundary keeps agent usage, machine execution, human attention, and wall latency separate; unavailable observations remain unknown rather than zero.

## Settlement

Accepted completion requires:

- all behavioral scenarios to pass;
- strict typing under the public pinned configuration;
- a clean bootstrap from locked dependencies; and
- affirmative human source review of the declared implementation constraints.

The public implementation contract is in [`public/contract`](public/contract). The evaluator, behavioral reference, and deliberate defects are experimenter-owned and excluded from the implementation agent's environment.

One candidate and any remediation share one isolated workspace and budget. The run settles as `Accepted`, `Rejected`, or `Inconclusive`. E1 does not establish population reliability, production readiness, security outside the declared boundary, or correctness beyond the contract.

## Reproduction

Run behavioral verification against a foreground candidate service:

```sh
make verify \
  BASE_URL=http://127.0.0.1:8765 \
  SERVICE_COMMAND='python3 -m candidate_service'
```

The service receives `CT_HOST`, `CT_PORT`, `CT_DATABASE_PATH`, and `CT_CLOCK_INITIAL_MS`. `make verify` proves only the declared black-box behaviors; it does not satisfy the typing, bootstrap, or human-review gates.

Validate the evaluator and its sealed inventory with:

```sh
make verify-evaluator
make verify-freeze
```

Authoritative validation runs in the recorded Lima instance:

```sh
limactl shell ct-ev -- sh -lc 'cd /Users/engineer/ws/ev/exp/e1 && make verify-evaluator'
```

Candidate authoring uses the no-host-mount Lima environment declared in `reproduction/candidate-lima.yaml`. Setup installs the pinned toolchain and public dependency lock before the agent phase; agent commands can access only the public bundle and candidate workspace and cannot use the network.

## Records

- [`freeze-manifest.json`](freeze-manifest.json) defines the sealed inventory, run budget, ledger, and freeze state.
- [`reproduction/environment.json`](reproduction/environment.json) records the execution environment.
- [`reproduction/validation.json`](reproduction/validation.json) records validation and run evidence.
- [GitHub issue #1](https://github.com/roone-ruanaidh/envelope/issues/1) tracks decisions and lifecycle state.
