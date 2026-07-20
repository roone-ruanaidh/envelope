# Q1/L1 — contract reproduction

> **Question:** What does it cost to move one agent-produced lease service from declared completion to accepted completion under a fixed contract and settlement procedure?

This loop belongs to [`Q1 — cost of trusted agent-produced code`](../QUESTION.md). It measures one isolated implementation run. It can change which verification, evidence, remediation, and human-review steps later Envelope work retains. It does not establish population reliability, production readiness, security outside the declared boundary, or correctness beyond the public contract.

The dispatchability implementation is pending human review. No candidate run or disposition exists.

## Authorities and inputs

- The reviewed question-and-loop commit on clean `main` is the executable contract. `QUESTION.md` and `LOOP.md` are copied and indexed as run authorities. Both execution and finalization receive the commit's full object ID explicitly, require exact `HEAD`, and may not amend or rebase it.
- [`public/contract`](public/contract) is the complete candidate-visible acceptance contract.
- `evaluator/`, its behavioral reference, and deliberate defects are sealed from the implementation environment.
- `reproduction/candidate-lima.yaml`, the pinned package lists, `candidate-codex-config.toml`, and admin-enforced `candidate-codex-requirements.toml` define candidate provisioning and authority.
- `reproduction/evaluator-authority.json` pins the dedicated `q1-l1-evaluator` normalized Lima configuration, selected image digest, disabled automatic package updates, complete installed-package inventory, Python runtime tree, evaluator tools, and isolation capabilities. Agent-owned setup may start it and reconcile disposable setup artifacts before the measured run; after the executable contract is reviewed, the loop never creates, repairs, updates, or upgrades it.
- `reproduction/agent-initial-prompt.md`, `agent-remediation-prompt.md`, and `agent-completion.schema.json` define invocation and declared completion.
- `reproduction/HUMAN_REVIEW.md` defines the only judgment gate.
- An `OPENAI_API_KEY` supplied out of band is a control input, never evidence. Absence before the run means execution has not begun.

## Agent and human boundaries

The implementation agent receives one fresh no-host-mount Lima workspace containing only the protected public contract, protected locked virtual environment, and writable candidate files. Its commands cannot read outside the workspace, modify `.venv`, `public/contract`, Codex control paths, or repository instruction files; they cannot use the network. `/etc/codex/requirements.toml` enforces the permission profile, disabled features, approval policy, and web-search restriction so candidate-written configuration cannot weaken them.

Codex itself may use the API control plane. Authentication enters `codex login --with-api-key` through stdin, is not placed in argv, environment forwarded to the VM, prompt, candidate files, logs, or evidence, and is removed with `codex logout` before the candidate VM is deleted.

Humans own this contract, changes to meaning or acceptance, the final source attestation, promotion, publication, and shipping. Agents own the approved procedure, evidence capture, deterministic non-human disposition, the result draft, and a terminal local commit. Agents do not infer a human attestation.

## Budget and stopping rule

- One initial Codex invocation and at most one remediation invocation.
- Each invocation has a 30-minute hard wall timeout.
- Every other command has a 10-minute default hard timeout. Candidate provisioning has 30 minutes; each agent has a 30-minute guest timeout inside a 31-minute outer timeout. Cleanup and pending-evidence closure share one 5-minute aggregate window, normal human finalization after the durable attempt marker has one 300-second hard wall deadline with no shorter internal cutoff or closure reserve, and the automated execute phase has 3 hours total.
- There are no automatic retries. A second agent invocation is the single approved same-thread remediation, not a retry. Finalization never resumes prior terminal work: any pre-existing `finalization-attempt.json`, settlement, finalization-completion receipt, terminal evidence index, or recognized partial terminal artifact requires human recovery and is never closed automatically.
- Transfer admits at most 10,000 traversed entries including empty directories, 16 MiB per regular file, 128 MiB total regular-file bytes, depth 32, 1,024 filesystem bytes per relative path, and an 8 MiB encoded manifest.
- Control documents admit at most 128 argv entries, 8 KiB UTF-8 per entry, 64 KiB UTF-8 aggregate including separators, and 1 MiB each for completion, prompt, and human attestation. Each command stream is capped at 32 MiB and retained run evidence at 512 MiB; 64 MiB inside that total is reserved for closure controls and indexes and, while human review is pending, terminal settlement.
- Each isolated evaluator generation is capped at four CPU equivalents, 4 GiB aggregate memory with no swap, 256 tasks, and one shared 1 GiB writable-state capacity. These are outer evaluator limits, not candidate acceptance thresholds.
- Any outer deadline, quota, control, stream, evidence, or resource-envelope breach settles `Inconclusive` and overrides a candidate-looking exit or report. The declared behavioral suite's existing 45-second contract deadline remains a candidate failure when no outer breach occurred.
- Before the run ID, clocks, or evidence exist, the execution agent prepares the dedicated Q1/L1 namespace and requires no prior evidence generation, `q1-l1-candidate-<run-id>` VM, `/tmp/q1-l1-run-<run-id>` root, or referenced process, cgroup, mount, or loop backing. The agent may remove only positively attributed disposable setup artifacts that have no run record, then must verify their absence. A candidate VM, run root, evidence or result artifact, ambiguous ownership, or unverifiable absence stops for human review without deletion. Preparation is outside the measured run and has no disposition.
- Preparation and any bounded setup cleanup occur outside `run_l1.py`; `run_l1.py execute` only verifies the prepared baseline before opening a measured run.
- Remediation resumes the initial recorded Codex thread in the same workspace.
- Stop remediation when all non-human gates pass, the one remediation is consumed, the agent returns `blocked`, an invocation does not exit zero with a valid declaration, or an infrastructure/evidence fault occurs.
- CLI exit zero plus schema-valid `status: declared_complete` and a nonempty NUL-free foreground argv is the only completed-candidate predicate.
- A blocked, failed, or timed-out invocation has no new declared candidate. Partial workspace bytes are never transferred. If remediation is incomplete, preserve the last declared snapshot as evidence but settle the procedure `Inconclusive`.
- Human review is final and non-remediating. A negative review rejects this run; further work requires a separately approved change or loop.

## Procedure

### 1. Preflight

1. Under the exclusive process lock and before the measured run begins, require clean `main`, no existing `RESULT.md` or evidence generation, the reviewed executable contract commit, the API-key control input, the dedicated `q1-l1-evaluator` in `Running` state, and the prepared zero-residue Q1/L1 namespace. A preparation fault stops before a run exists; it has no experimental disposition.
2. Start the run ID, UTC and monotonic clocks, command record, and public-safe evidence directory.
3. Recheck zero scoped residue, then actively collect and exact-compare the evaluator's normalized Lima config, ordered selected-architecture images, complete package inventory, runtime tree, tool hashes/versions, and isolation capabilities against `evaluator-authority.json`. Reject unmapped config fields and drift; never repair the instance. Then run `make verify-dispatch`, `make verify-evaluator`, and `make verify-isolation`. Any absence, stopped/unreachable state, new residue, mismatch, failure, or missing report after step 2 settles `Inconclusive`; do not provision or invoke the implementation agent.

### 2. Provision and invoke

1. Create a never-reused `q1-l1-candidate-<run-id>` instance through `reproduction/prepare-candidate-lima.sh`.
2. Require its standalone boundary-validation report—including home-auth denial and failed privilege escalation—and capture the image digest, authority hashes, package versions, Codex version/features/executable hash, Python version, kernel, and mount evidence. Failure or a missing report settles `Inconclusive`.
3. Authenticate through stdin.
4. Invoke pinned `codex-cli 0.142.5` with requested model `gpt-5`, reasoning effort `high`, strict config, ignored user/project command rules, JSONL events, the canonical initial prompt, and the protected output schema. The model name is a service alias; no immutable backend revision is claimed.
5. Capture the thread ID, prompt, stderr, JSONL, structured completion, externally measured duration, and reported token usage. Monetary agent charge remains `unknown` because the CLI does not report it.

### 3. Transfer the declared candidate

The trusted outer harness first terminates and verifies the absence of non-controller processes owned by the candidate user. It then copies every candidate-owned regular file exactly once through descriptor-relative, no-follow opens into private staging, regardless of ignore rules, cache name, extension, content, or mode. It excludes only provisioner-owned `.git`, `.venv`, and `public/contract`; an owner mismatch, candidate-owned replacement of an exclusion, selected symlink, multiply-linked file, special file, changed descriptor, limit breach, or process that cannot be quiesced makes transfer inadmissible and settles `Inconclusive`.

The exporter enforces the declared entry/file/total/depth/path/manifest limits while walking, reading, loading, extracting, and verifying. It creates the normalized archive and sorted SHA-256 manifest from staging; the manifest records path, bytes, size, and mode. The host extracts and verifies the source snapshot, then transfers the same archive and manifest into `q1-l1-evaluator`. Evaluation uses the new `/tmp/q1-l1-run-<run-id>` root outside the evaluator tree; it verifies the manifest before adding the identical public contract and a new virtual environment and after all gates finish. Any mismatch settles `Inconclusive`.

### 4. Run every non-human gate

Run all applicable gates for every completed attempt; a typing failure does not skip behavior.

1. **Clean bootstrap:** create an empty Python 3.14 virtual environment, install every exact version in `python-arm-requirements.v1.txt` with `--no-deps`, and run `pip check`. Package/environment failure is an infrastructure failure and settles `Inconclusive`.
2. **Strict typing:** inside a read-only candidate mount and no-route network namespace, run `python3 -m mypy --config-file public/contract/mypy.v1.ini .` with cache in bounded isolated temporary storage and Python safe-path/user-site isolation so candidate files cannot impersonate the locked typechecker. The production wrapper places the complete candidate tree in the fixed CPU/memory/PID cgroup and 1 GiB writable capacity. A mypy failure is an admissible candidate failure; any wrapper, isolation, or resource-envelope failure settles `Inconclusive`. Candidate-owned build commands never run with evaluator access. Human review verifies that `make typecheck` delegates to this exact command.
3. **Behavior:** pass the bounded declared foreground argv as an argv list—never through a shell—to `evaluator.rerun`. The candidate runs read-only under Bubblewrap in a no-route namespace and the same cgroup/writable-state envelope; restart-persistent evaluator-owned SQLite state and temporary bytes share the 1 GiB capacity. A trusted inner launcher remaps a candidate’s own exit 125; raw Bubblewrap/wrapper 125 and any detected CPU, memory, PID, or state exhaustion remain isolation failures. The isolation preflight exercises no-route, read-only source, evaluator absence, bounded state persistence, descendant teardown, typechecker shadowing, resource breaches, and both sentinel origins through the production wrappers.

Behavioral verification proves only the declared black-box scenarios. It does not satisfy bootstrap, typing, or human review.

### 5. Remediate once when eligible

Remediation is eligible only when a completed initial candidate has an admissible typing or behavioral failure. Feedback contains failed gate names, typing stdout/stderr, failed behavioral test records, startup error, and candidate service-log tail. It excludes passed hidden scenarios, evaluator source, reference behavior, deliberate-defect identities, and evaluator-validation results.

Resume the same Codex thread with the canonical remediation prompt. A completed remediation repeats transfer, clean bootstrap, typing, and behavior from fresh evaluation state. No third invocation exists.

### 6. Settle or request human review

- A final admissible candidate-gate failure after completed remediation settles `Rejected`. Any automatic `Rejected | Inconclusive` disposition is terminal only after its closed evidence generation verifies; the agent then creates the local result commit and stops without human finalization.
- All non-human gates passing produces `PendingHumanReview`, not a terminal disposition.
- At that boundary, within the one aggregate 5-minute window, remove authentication, delete and verify absence of the candidate VM, remove and verify absence of the exact run-scoped `q1-l1-evaluator` root, process, cgroup, mount, and loop state, normalize host-local paths, scan/redact secret control input, draft `RESULT.md`, copy that draft into the evidence, index the evidence, and verify it. The deadline controller must then atomically complete before appending the index-hash-bound `execution-completion.json` receipt. Only that receipt closes a pending or automatic-terminal generation; its own durable-write and verification tail is recorded as `unknown`. If the hard cutoff wins, execution writes no receipt or further repository/evidence bytes, returns exit 2 with `status: Inconclusive`, `terminal_evidence: incomplete`, and `recovery: human_required`, and stops. Missing or partial completion evidence is uncommittable and requires human recovery. Any earlier cleanup, safety, or closure failure settles `Inconclusive`; residue blocks later execution for human recovery.
- Supply the exact final source, foreground argv, manifest hash, and composite candidate-identity hash with `reproduction/HUMAN_REVIEW.md`. No response or any response other than a schema-valid `Affirmative | Negative` remains pending.
- `Affirmative` settles `Accepted`; `Negative` with a concrete declared-clause finding at an existing typed source line, whole source file, foreground-argv, or missing-path location settles `Rejected`.
- Finalization never rewrites the closed pending generation. Under the process lock, a fresh invocation first verifies exact `HEAD` and the execution-completion receipt, then appends and durably fsyncs `finalization-attempt.json`; only then does it arm the hard timer, preserving the full 300 seconds for normal finalization. The marker binds the run and contract, is never rewritten or removed automatically, and is included in any successful terminal evidence index. The invocation must validate and complete the settlement containing the attestation or evidence fault, terminal accounting and RESULT bytes, projected terminal `RESULT.md`, full terminal evidence index, and terminal verification before the hard cutoff. The deadline controller must then atomically complete before appending the index-hash-bound `finalization-completion.json` receipt; only that receipt makes the terminal generation committable, and its own durable-write and verification tail is `unknown`. If the cutoff wins, automation performs no further repository or evidence writes, gives a killed checkout-guard child only a nonblocking reap before runner exit, returns exit 2, emits exactly `{"failure_stage":"finalization_deadline","recovery":"human_required","status":"Inconclusive","terminal_evidence":"incomplete"}` on stderr, and stops. Any partial terminal artifacts remain append-only and uncommittable; a later invocation treats them as human recovery and never closes them automatically. A pending evidence/source fault settled before the cutoff is `Inconclusive`; invalid attestation or checkout mismatch leaves the pending generation unchanged.
- `PendingHumanReview` stops for human attestation and can reach a local result commit only after terminal settlement verifies public safety and reproducibility. An automatic `Rejected | Inconclusive` reaches that commit through its verified closed generation instead. Never push.

## Evidence and accounting

Required evidence, when its stage is reached:

- executable contract commit, copied and indexed `QUESTION.md` and `LOOP.md`, and hashes/copies of every other run authority;
- exact evaluator-environment observation after a match, non-echoing authority-comparison and residue reports, dispatch/evaluator/isolation reports, and candidate boundary validation;
- candidate image/config/tool/package provenance;
- prompts, sanitized agent JSONL and stderr, structured completions, thread ID, requested model/reasoning setting, per-invocation usage and elapsed time;
- each quiesced declared source snapshot, source-plus-argv identity, SHA-256 manifest, archive/manifest hashes, and transfer verification;
- per-attempt bootstrap, typing, behavior, and summary reports;
- remediation feedback;
- ordered commands with argv, UTC start/end, monotonic duration, exit, timeout, and stdout/stderr references;
- separate agent elapsed/usage; completed trusted-machine command intervals, monotonic execute/finalization elapsed lower bounds, index scan-and-hash intervals, and explicit `unknown` immutable-artifact self-recording tails; candidate provisioning start plus the lower-bound interval from first verified instance existence through the last verified-present observation, with full VM lifetime left `unknown` and right-censoring when absence is not verified; evaluator workload with standing provisioning/idle excluded; human active minutes and a review-wait upper bound; and wall elapsed lower bound through its recorded cutoff;
- an explicit nonexclusive-overlap rule: agent, candidate-VM, and evaluator intervals overlap trusted-machine and wall intervals and must never be summed;
- human checklist, final-manifest and source-plus-argv identity hashes, decision, structured findings, narrowly typed approved boundary exceptions, and active minutes or `unknown` when review occurs;
- explicit redactions, intentionally omitted secrets, and unavailable observations;
- the indexed pending RESULT draft, append-only index-bound execution-completion receipt, append-only `finalization-attempt.json` when finalization begins, projected terminal `RESULT.md`, append-only settlement and index-bound finalization-completion receipt when human review occurs, and SHA-256 pending/terminal evidence indexes.

Loss of evidence required to support a reached stage settles `Inconclusive`. A field explicitly recorded as `unknown` is present evidence, not missing evidence, and does not itself change disposition. Agent, local-machine, and human monetary costs remain separately `unknown` unless directly observed; they are never zero-filled. Wall time begins when the runner creates the run; `wall.elapsed_lower_bound_seconds` ends at `wall.recorded_cutoff_at`. Immutable-artifact serialization, durable write, projection, and final-verification tails remain `unknown`, never zero-filled. Review wait is an upper bound because its request timestamp precedes final pending-artifact closure.

Only reproducible public-safe evidence may enter the terminal commit. Every manifested candidate-owned cache, log, database, generated file, and other regular file is controlled candidate evidence and is commit-eligible when public-safe. Credentials, authentication state, transient harness/evaluator virtual environments and caches, evaluator databases outside the manifested candidate, VM disks, and uncontrolled archives are never committed.

## Disposition

Envelope vocabulary maps `Pass = Accepted` and `Fail = Rejected`.

- **Accepted:** evaluator and evidence are admissible; bootstrap, typing, and behavior pass for the final declared candidate; human review is affirmative.
- **Rejected:** the final completed candidate retains an admissible typing or behavioral failure after its permitted remediation, or human review identifies a concrete declared implementation violation.
- **Inconclusive:** after the measured run begins, public-contract conflict; evaluator absence, stopped state, drift, new residue, or isolation invalidity; authentication/API/service failure; provisioning, bootstrap-environment, ownership, transfer, integrity, or evidence failure; any approved outer deadline/quota/size/resource breach; blocked/failed/timed-out invocation without a new completed candidate; or any other undefined boundary. Pre-run preparation has no disposition.
- **PendingHumanReview:** all non-human gates pass but the required human attestation does not yet exist. This is not terminal and cannot be committed as a result.

Candidate protocol, startup, lifecycle, typing, the declared 45-second behavioral deadline, and behavioral findings produced by an otherwise admissible gate are candidate failures. Outer timeout/output/evidence/resource records are checked first and override candidate-looking output. Wrapper sentinel 125, report-generation failure, missing required artifact, or command/report disagreement is infrastructure failure. Automation does not infer another cause. A discovered conflict among public contract artifacts is evaluator invalidity and settles `Inconclusive`.

## Reproduction

Phase 2 verification is local and does not provision or invoke an agent:

```sh
make verify-dispatch
python3 -B -I reproduction/run_l1.py plan
```

Authoritative runtime/evaluator validation occurs against the already reviewed, prepared, Running `q1-l1-evaluator` prerequisite during execution; the runner will not create, start, repair, or upgrade it. After the reviewed dispatchability changes are committed and the second human approval is explicit, execute with `OPENAI_API_KEY` supplied out of band:

```sh
python3 -B -I reproduction/run_l1.py execute \
  --contract-commit <full-reviewed-commit>
```

If the run reaches human review, record the explicit attestation afterward:

```sh
python3 -B -I reproduction/run_l1.py finalize \
  --run-id <run-id> \
  --attestation </outside/repository/human-attestation.json> \
  --contract-commit <full-reviewed-commit>
```
