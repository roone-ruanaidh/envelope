# Q1/L10 result — contract reproduction

## Observed evidence

- Run: `20260721T210243Z-d16bed28`
- Executable contract commit: `c35cdb399eef7b891f82c9dc3791f918497754c1`
- Candidate attempts completed: 1
- Authentication preflight: HTTP `200`
- Luna completed one invocation in `810.555392` seconds and declared `['.venv/bin/python3', 'main.py']`
- Reported usage: `4,124,256` input tokens (`3,998,290` cached), `56,734` output tokens, and `29,260` reasoning-output tokens; monetary charge was unavailable
- Luna wrote `main.py` and `Makefile`, ran local typing and behavioral checks, removed generated test artifacts, and returned a valid completion declaration
- Candidate export then failed before typing or behavior evaluation because the snapshotter rejected the top-level `.agents` control placeholder created for the Codex invocation
- Evidence: [`evidence/20260721T210243Z-d16bed28`](evidence/20260721T210243Z-d16bed28)
- Separate cost and latency ledger: [`evidence/20260721T210243Z-d16bed28/accounting.json`](evidence/20260721T210243Z-d16bed28/accounting.json)

Final non-human gates:

    "unavailable"

## Disposition

**Inconclusive.**

Reason:

    "the harness rejected its own Codex runtime control placeholder during candidate export"

## Deviations and unknowns

The candidate VM was correctly torn down after export failed, so there is no reproducible candidate snapshot to inspect or evaluate. The agent event stream records Luna's actions and declaration but cannot substitute for transferred source. See `evidence/20260721T210243Z-d16bed28/unavailable.json`; missing observations remain unknown rather than zero.

## Effect on Q1

Q1/L10 establishes that Luna can act on the workload and declare a candidate. It does not establish candidate quality or cost to accepted completion because the harness stopped before every candidate gate.

## Possible next loops

Under the standing human approval through Q1/L11, omit only exact empty top-level Codex runtime placeholders during the trusted snapshot while continuing to reject nonempty or nested control paths, then rerun the frozen workload.

## Promotion candidate

None. Loop success and promotion are separate human decisions.
