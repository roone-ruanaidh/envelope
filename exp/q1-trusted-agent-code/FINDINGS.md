# Q1 findings — harness before task

Q1/L1–L3 produced useful harness evidence, but no cost-to-accepted-completion observation. All three runs stopped `Inconclusive` before model invocation. Together they show that the experiment qualified individual repairs without qualifying the complete path to the task.

## Observed

- [Q1/L1](l1-contract-reproduction/RESULT.md) stopped when synthetic dispatch tests read live run state. Q1/L2 isolated that state.
- [Q1/L2](l2-contract-reproduction/RESULT.md) reached candidate creation, where the command-stream limit was inherited as a process-wide file-size limit and blocked the VM disk. Q1/L3 moved stream bounds to the parent.
- [Q1/L3](l3-contract-reproduction/RESULT.md) reached candidate bootstrap, then collapsed the sandbox failure to `probe_command_failed`. Its [verifier](l1-contract-reproduction/reproduction/verify_candidate_boundary.py) captured the probe error but discarded it, while the terminal record retained 2,425 lines of provisioning output.
- A disposable post-run diagnostic reproduced the Q1/L3 path on pinned Codex `0.144.6`. The managed profile combined an inherited `:workspace` policy with redundant custom rules: an unsupported readable glob, a deny for an absent `.agents` path, and inheritance that contradicted the probe's outside-read boundary. Deleting only those three entries made the original full boundary verifier pass. This diagnostic was outside Q1/L3 measurement and is not Q1/L3 evidence.

## Finding

The isolation goal was not the problem. Multiple overlapping mechanisms expressed it differently, tests mocked the real boundary, qualification stopped before that boundary, and the useful failure stream was discarded. Complexity therefore caused both the failure and the delay in identifying it.

The narrow correction preserves the declared boundary: define the custom profile directly with its existing minimal-runtime, workspace, protected-path, authentication, and network rules. Do not inherit a broader built-in profile or regulate paths absent from the candidate.

## What changes

1. Delete `extends = ":workspace"`, `.agents = "deny"`, and `"**/AGENTS.md" = "read"` from the candidate profile. Keep the exact top-level `AGENTS.md` rule and reject candidate-created Codex control paths at transfer.
2. Preserve bounded probe exit, stdout, stderr, and a fixed failure phase. Remove the unparsed `findmnt --json` dump.
3. Qualify the exact pre-agent path—create, bootstrap, the same boundary assertions, probe, and pass rule, then teardown—through the implementation used by execution. A disk-only path is insufficient.
4. Defer broader runner redesign until after this observation. The result selects no next inquiry or change.

## What stays

The candidate remains a fresh no-mount VM with no command network, unreadable authentication and outside control, protected contract and toolchain, and a writable workspace. The sealed evaluator, one-shot execution, bounded remediation, separate cost categories, deterministic disposition, and human source-review gate remain unchanged.

## Q1/L4 handoff

The separately reviewed Q1/L4 contract adopts this narrow correction, bounded probe diagnostics, and exact pre-agent qualification with zero residue. This finding changes no workload, acceptance rule, disposition, or human boundary; Q1/L4 execution still requires separate explicit approval.

## Q1/L5 observation

Q1/L5's exact boundary qualification passed, then measured execution stopped in evaluator dispatch validation with zero agent attempts. The test derived candidate home from the evaluator's home basename, making `HOST_HOME` and `CANDIDATE_HOME` identical; one redaction label necessarily consumed both values. This is environment-dependent test state and a real candidate-home derivation error, not a model result.

The indexed `redactions.json` generically says the API key was sent through stdin. The command record and run state show it was only available to the runner: no candidate login or `codex exec` occurred. Preserve the bound evidence unchanged and treat that sentence as inaccurate. Q1/L5's narrower outer stopping sentence was also an agent drafting error; the pre-existing human approval permits at most Q1/L5–L7 until the first recorded agent invocation. Neither correction changes Q1/L5's `Inconclusive` disposition.
