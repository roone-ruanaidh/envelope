# Q1/L1 — contract reproduction

> **Archived:** Executed contract. Q1 is retired; its executable authorities and terminal evidence remain in Git history.

> **Question:** What does it cost to move one agent-produced lease service from declared completion to accepted completion under a fixed contract and settlement procedure?

This loop contributes one configuration-specific observation to [Q1](../QUESTION.md). It can inform later human decisions about verification, evidence, remediation, and review, but authorizes no next loop or promotion. It does not establish population reliability, production readiness, security outside the declared boundary, or correctness beyond the public contract.

## Target

Measure the separate observable costs and evidence produced as one isolated implementation moves through declared completion, deterministic non-human settlement, and explicit human source review.

The implementation agent is pinned to `codex-cli 0.144.6`, `gpt-5.6-luna`, and reasoning effort `max`. The model identifier does not claim an immutable backend revision.

## Authorities and boundaries

- The reviewed question-and-loop commit on clean `main` is the executable contract. Execution and finalization require its full object ID and exact `HEAD`; the commit is never amended or rebased after execution begins.
- `public/contract/` is the complete candidate-visible acceptance contract. `evaluator/` and its reference and defect fixtures are sealed.
- `reproduction/` contains the reviewed provisioning, agent-control, transfer, evidence, accounting, and settlement authorities. `evaluator-authority.json` pins the already prepared, dedicated `q1-l1-evaluator`; the measured run never creates, repairs, updates, or upgrades it.
- The candidate receives one fresh Lima VM with no host mounts, no command network, protected contract, toolchain, and control paths, and a writable candidate workspace. Managed requirements prevent candidate-written configuration from weakening that boundary. Codex alone may reach the API control plane.
- `OPENAI_API_KEY` enters `codex login --with-api-key` through stdin, is never forwarded to the candidate environment or retained as evidence, and is removed before candidate teardown. Its absence means execution has not begun.
- Humans own this contract, acceptance meaning, final source attestation, promotion, publication, and shipping. Agents own the approved procedure, reproducible public-safe evidence, deterministic non-human disposition, result draft, and terminal local commit. Agents never infer human attestation.

## Procedure

1. **Prepare and preflight.** Before the run ID, clocks, or evidence exist, the agent may reconcile only positively attributed disposable Q1/L1 setup artifacts with no run record, then must prove a zero-residue Q1/L1 namespace. Existing candidate VMs, run roots, evidence or result artifacts, ambiguous ownership, or unverifiable absence stop for human review without deletion. Preparation occurs outside `run_l1.py`; `execute` only verifies the prepared baseline. Under the exclusive process lock, require clean `main`, exact reviewed `HEAD`, no prior result or evidence generation, the API key, and the dedicated evaluator in `Running` state.
2. **Validate the evaluator.** Start the run clocks and evidence, recheck zero scoped residue, and exact-compare the evaluator's Lima config, image, packages, Python runtime, tool hashes, and isolation capabilities with its authority. Run dispatch, evaluator, and isolation validation. Drift, residue, absence, or failure settles `Inconclusive`; never repair the evaluator inside the run.
3. **Provision and invoke.** Create a never-reused candidate VM and require its boundary and provenance reports. Authenticate through stdin and make one 30-minute Codex invocation with the canonical prompt and completion schema. Completed candidate means only: CLI exit zero, schema-valid `status: declared_complete`, and a nonempty NUL-free foreground argv. A blocked, failed, or timed-out invocation has no new candidate; partial workspace bytes are never transferred.
4. **Snapshot and transfer.** Quiesce candidate-user processes, then copy every candidate-owned regular file exactly once through descriptor-relative, no-follow opens into private staging. Exclude only provisioner-owned `.git`, `.venv`, and `public/contract`. Ownership ambiguity, replacement of an exclusion, links, special files, changed descriptors, surviving processes, or a limit breach makes transfer inadmissible. Create a normalized archive and sorted SHA-256 manifest, verify both on the host, transfer the same bytes to a fresh evaluator run root, and verify again.
5. **Run every non-human gate.** For each completed attempt, run all three gates even when typing fails: clean locked dependency bootstrap; strict mypy over the complete read-only candidate; and the sealed black-box behavioral suite in a no-route, bounded Bubblewrap environment. Reverify the candidate manifest after all gates. Candidate typing or behavioral findings are admissible failures. Bootstrap, wrapper, isolation, resource, integrity, report, or evidence faults are `Inconclusive`.
6. **Remediate once when eligible.** Only an initial completed candidate with an admissible typing or behavioral failure may resume the same Codex thread. Feedback is limited to failed gate names, typing output, failed behavioral records, startup error, and candidate service-log tail; it excludes passed hidden scenarios, evaluator source, reference behavior, defect identities, and evaluator-validation results. A completed remediation receives a fresh transfer, bootstrap, typing, and behavior run. If remediation produces no completed candidate, preserve the last declared snapshot as evidence and settle `Inconclusive`. No third invocation exists.
7. **Settle and stop.** A final admissible candidate failure is `Rejected`; an infrastructure, evidence, or undefined-boundary fault is `Inconclusive`. A closed automatic terminal generation produces the local result commit and stops. If every non-human gate passes, clean exact run-scoped state, close and verify the pending evidence generation, draft `RESULT.md`, and stop at `PendingHumanReview`.
8. **Finalize only explicit review.** Supply the exact final source, foreground argv, manifest hash, and candidate-identity hash with `HUMAN_REVIEW.md`. `Affirmative` settles `Accepted`. `Negative` must identify a declared clause and an existing source line or file, foreground-argv argument, or required missing path; it settles `Rejected`. No response or any other response remains pending. Human review is final and non-remediating.

## Limits and stopping rules

| Envelope | Limit |
|---|---|
| Agent | One initial plus at most one same-thread remediation; 30 minutes each; no retries |
| Run | Three hours total automated execution |
| Commands | 10 minutes default; 30 minutes candidate provisioning; 31-minute outer agent timeout |
| Closure | One aggregate 5-minute cleanup/pending-evidence window; 300 seconds for finalization after its durable attempt marker |
| Transfer | 10,000 entries; 16 MiB/file; 128 MiB total; depth 32; 1,024 path bytes; 8 MiB manifest |
| Controls | 128 argv entries; 8 KiB/entry; 64 KiB aggregate; 1 MiB each for prompt, completion, and attestation |
| Evidence | 32 MiB/command stream; 512 MiB retained, including a 64 MiB closure reserve |
| Evaluator | 4 CPU equivalents; 4 GiB memory; no swap; 256 tasks; 1 GiB shared writable state |

Any outer deadline, quota, control, stream, evidence, transfer, or resource breach overrides candidate-looking output and settles `Inconclusive`. The public contract's 45-second behavioral deadline remains a candidate failure when no outer breach occurred. Stop remediation when the gates pass, the allowance is consumed, the agent returns `blocked`, no valid completed candidate exists, or infrastructure/evidence fails.

Admissible protocol, startup, lifecycle, typing, behavioral, and declared 45-second deadline findings are candidate failures. Outer-envelope records take precedence; wrapper sentinel 125, report failure, a missing required artifact, command/report disagreement, or conflict among public contract artifacts is infrastructure failure and settles `Inconclusive`. Automation infers no other cause. Evaluator resource limits are outer controls, not candidate acceptance thresholds.

Evidence closure is append-only. The pending generation is closed only by its verified index-bound `execution-completion.json`; finalization begins with one durable `finalization-attempt.json` and closes only through a verified index-bound `finalization-completion.json`. Pre-existing or partial terminal artifacts, a missed hard cutoff, or residue after cleanup require human recovery; automation never resumes or rewrites them.

## Evidence and accounting

When its stage is reached, evidence must include:

- the contract commit and copies or hashes of every run authority;
- evaluator fingerprint, residue, dispatch, self-validation, isolation, and candidate-boundary reports;
- candidate and toolchain provenance, prompts, sanitized JSONL and stderr, structured completion, thread ID, requested model and effort, and per-invocation token usage and elapsed time;
- every declared candidate snapshot, manifest, archive identity, foreground argv, and transfer verification;
- bootstrap, typing, behavior, summary, and remediation-feedback reports for every evaluated attempt;
- ordered command argv, UTC and monotonic timing, exit, timeout, and output references;
- separate agent usage/time, trusted-machine intervals, candidate-VM observed lifetime lower bound, evaluator workload excluding standing provisioning and idle time, human active minutes, review-wait upper bound, and wall-time lower bound;
- redactions, unavailable observations, human attestation when reached, result drafts, settlements, indexes, and completion receipts.

Agent, candidate-VM, evaluator, trusted-machine, human, and wall intervals are nonexclusive and must not be summed. Candidate-VM measurement runs from first verified existence through last verified presence; its full lifetime remains `unknown` and is right-censored unless absence is verified. Wall time begins when the runner creates the run and ends at its recorded cutoff. Execute/finalization and index intervals are lower bounds; immutable-artifact serialization, durable write, projection, and final-verification tails remain `unknown`.

The pinned Codex JSONL reports token categories but not cache-write tokens or monetary charge; both remain `unknown`. Other monetary costs also remain separately `unknown` unless directly observed. Missing required evidence for a reached stage settles `Inconclusive`; an explicit `unknown` is present evidence and does not. Only reproducible public-safe evidence may enter a terminal commit. Credentials, auth state, VM disks, transient environments, evaluator databases, and uncontrolled archives never do.

## Disposition

Envelope maps `Pass = Accepted` and `Fail = Rejected`.

| State | Rule |
|---|---|
| `Accepted` | Admissible evaluator and evidence; final candidate passes bootstrap, typing, and behavior; human review is affirmative. |
| `Rejected` | Final completed candidate retains an admissible typing or behavioral failure after permitted remediation, or human review identifies a concrete declared violation. |
| `Inconclusive` | After measurement begins, evaluator, contract, authentication, provisioning, transfer, isolation, resource, deadline, cleanup, evidence, or undefined-boundary failure prevents a valid decision. Pre-run preparation has no disposition. |
| `PendingHumanReview` | Every non-human gate passes but explicit human attestation is absent. This state is nonterminal and cannot be committed as a result. |

## Verify and run

Read-only verification does not provision infrastructure or invoke an agent:

```sh
make verify-dispatch
python3 -B -I reproduction/run_l1.py plan
```

After this executable contract is committed and explicitly approved for execution:

```sh
python3 -B -I reproduction/run_l1.py execute \
  --contract-commit <full-reviewed-commit>
```

If execution reaches human review, finalize only with the explicit external attestation:

```sh
python3 -B -I reproduction/run_l1.py finalize \
  --run-id <run-id> \
  --attestation </outside/repository/human-attestation.json> \
  --contract-commit <full-reviewed-commit>
```

Never push from the loop runner.
