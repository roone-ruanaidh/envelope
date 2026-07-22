# Q1 findings — harness before task

All eleven loops ended `Inconclusive` before trusted candidate evaluation. The ledger preserves each approved contract, terminal attribution, observable agent and wall time, and the Git commits containing the complete evidence.

| Loop | Boundary reached | Terminal cause | Agent / wall time | Commits |
|---|---|---|---|---|
| [Q1/L1](l1-contract-reproduction/LOOP.md) | Evaluator dispatch | Synthetic dispatch tests read live run state | 0 / 1.4s | Contract `6abb9be`; terminal `c069bc0` |
| [Q1/L2](l2-contract-reproduction/LOOP.md) | Candidate provisioning | A process-wide file-size limit blocked the VM disk | 0 / 29.0s | Contract `d7292b3`; terminal `de0d74a` |
| [Q1/L3](l3-contract-reproduction/LOOP.md) | Candidate boundary | The verifier collapsed the probe failure to `probe_command_failed` | 0 / 204.8s | Contract `aad8f60`; terminal `42b4c48` |
| [Q1/L4](l4-contract-reproduction/LOOP.md) | Exact boundary qualification | Bubblewrap collided with the provisioned `.codex` directory | 0 / 177.4s | Contract `bc986bc`; terminal `4e83baa` |
| [Q1/L5](l5-contract-reproduction/LOOP.md) | Evaluator dispatch | Candidate and evaluator home identities collided | 0 / 2.8s | Contract `30e9d15`; terminal `ae60848` |
| [Q1/L6](l6-contract-reproduction/LOOP.md) | Live Lima observation | Live candidate-configuration inspection exited `125` | 0 / 208.3s | Contract `8c96fd1`; terminal `f00af3c` |
| [Q1/L7](l7-contract-reproduction/LOOP.md) | Provider authentication | Both transports returned `401 invalid_api_key` before generation | 17.2s / 225.2s | Contract `3ca2542`; terminal `8ea3946`; public projection `9de1e94` |
| [Q1/L8](l8-contract-reproduction/LOOP.md) | Provider schema | Structured Outputs rejected a root `oneOf` before generation | 1.8s / 211.9s | Contract `9846c7c`; terminal `744a139` |
| [Q1/L9](l9-contract-reproduction/LOOP.md) | Provider schema | Constant-valued fields lacked explicit string types | 1.3s / 210.4s | Contract `4b16fa7`; terminal `5b1e496` |
| [Q1/L10](l10-contract-reproduction/LOOP.md) | Candidate export | The snapshotter rejected its own empty `.agents` runtime placeholder | 810.6s / 1,018.3s | Contract `c35cdb3`; terminal `805d106` |
| [Q1/L11](l11-contract-reproduction/LOOP.md) | Trusted typing gate | A mode-`0700` parent blocked Bubblewrap's UID `65534` from traversing to the transferred candidate | 833.3s / 1,047.3s | Contract `cac2946`; terminal `28a5a60` |

Post-run diagnostics attributed Q1/L3 to overlapping sandbox rules (first recorded at `bc986bc`) and Q1/L6 to mocked fields absent from Lima's canonical state (first recorded at `3ca2542`). Neither was terminal evidence.

Q1/L10 reported 4,124,256 input tokens; Q1/L11 reported 4,044,907. Earlier invocations produced no usable token report. The retained per-loop accounting and unavailable-observation records keep agent, machine, human, and wall categories separate.

## Finding

The isolation goal was not the problem. Overlapping controls, mocks of live boundaries, provider incompatibilities, and discarded failure detail made the harness both the dominant observed cost center and the terminal failure surface. Qualification must exercise the exact production path, one unknown and one state transition at a time.

This does not establish whether Luna's candidate would pass. Candidate typing, behavior, remediation, human review, monetary cost, and cost-to-acceptance remain unknown.

## Retained code

[`candidate_transfer.py`](l1-contract-reproduction/reproduction/candidate_transfer.py) remains as unpromoted research code because Q1/L11 successfully used that exact primitive to export and verify the only transferred candidate. Its verification code and complete execution evidence remain at terminal commit `28a5a60`; reuse is not qualified.
