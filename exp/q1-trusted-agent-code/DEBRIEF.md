# Q1 debrief — trust machinery before acceptance

Q1 asked what it costs to move agent-produced code from declared to accepted completion. Eleven loops ended `Inconclusive`; none reached trusted candidate evaluation. Nine repaired the execution path before the first substantive model generation. Q1 therefore did not price accepted completion. It showed that establishing the environment dominated the observed work.

## What the loops taught

| Loops | Boundary reached | Learning |
|---|---|---|
| Q1/L1–L4 | Runner and candidate isolation | Independent checks passed while the integrated path failed. Limits leaked across processes, overlapping sandbox rules contradicted one another, and useful failure detail was discarded. Qualification must exercise the exact production path. |
| Q1/L5–L6 | Evaluator dispatch and live VM observation | Mocked identities and configuration fields differed from Lima's canonical runtime state. Environment truth must be observed, normalized, and compared at the real boundary. |
| Q1/L7–L9 | Authentication and provider protocol | A stale key and two structured-output incompatibilities stopped generation. Live authentication and request-schema preflights belong before expensive provisioning. |
| Q1/L10–L11 | Model action, export, and transfer | Luna built and tested candidates, but the harness rejected its own runtime placeholders and later blocked Bubblewrap from traversing the transferred candidate. The trust system prevented its legal path to evaluation. |

## Supported conclusion

Every observed terminal failure came from the environment or harness. This does **not** establish that Luna's code passed: candidate correctness, remediation, human review, and cost-to-acceptance were never observed. It establishes that attribution matters and that trust machinery can become both the dominant cost center and the dominant failure surface before task quality is measured.

At terminal commit `63ec75a`, Q1 contained 332,795 text lines; 308,142—92.6%—were sealed evidence and repeated authority snapshots, not application code. Its non-evidence Python surface was 22,064 lines. In Q1/L11, Luna spent 833 seconds and reported 4.04M input tokens, produced a reproducible 982-line service, and transferred it successfully; the evaluator then failed before typing. Monetary and human cost remain unknown.

## What changes

- **Retain:** `QUESTION → LOOP → FINDINGS → DEBRIEF`, explicit human gates, deterministic dispositions, separate cost categories, indexed evidence, cleanup checks, preserved unknowns, and the unpromoted candidate-transfer primitive that succeeded in Q1/L11.
- **Simplify:** one unknown and one state transition per loop; production-shaped qualification; explicit states, owners, evidence, failure branches, and stopping rules; evidence proportional to the claim.
- **Retire:** Q1 as an active execution path, monolithic first questions, mocks that substitute for live boundaries, and repairing a harness merely to complete the original plan. Preserve Q1 as evidence.
