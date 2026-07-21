# Q1/L1 human source review

Review the exact final candidate manifest, source, and foreground argv identified by the run's candidate-identity hash. The argv is executable identity because an argument may itself contain code. Non-human gates already own dependency installation, mypy execution, observable behavior, evaluator validity, and transfer integrity. Do not re-adjudicate them here.

Return `Affirmative` only when every item below is true. Return `Negative` with a concrete typed location when any item is false. A location identifies an existing source line, a whole existing source file when line semantics do not apply, a canonical foreground-command argument, or a required regular-file path absent from the source manifest. If the supplied source or evidence is incomplete, do not attest; the runner settles the evidence fault `Inconclusive`. With complete evidence, any response other than `Affirmative` or `Negative` leaves the run pending.

1. **Framework and dependency boundary** — The implementation uses FastAPI and SQLite, has no source or runtime dependency on evaluator-owned code, and contains no vendored, dynamic, or other dependency outside the standard library and public lock. (`semantics.v1.md` §1, paragraphs 1–2.)
2. **Validation-model architecture** — Every request and response body uses an explicit Pydantic model with coercion disabled and extra fields forbidden. (`semantics.v1.md` §1, typing paragraphs.)
3. **Typing interface and boundary discipline** — `make typecheck` runs exactly `python3 -m mypy --config-file public/contract/mypy.v1.ini .`. Public models, domain state, storage interfaces, and state-transition interfaces contain no `Any`, cast, or type suppression; third-party dynamic values are narrowed immediately. Every cast or suppression outside those prohibited surfaces is enumerated with a typed location, boundary, and necessity and is explicitly approved. Core-surface violations cannot be waived. (`semantics.v1.md` §1, typing paragraphs.)
4. **Declared storage and time mechanisms** — `Q1_L1_DATABASE_PATH` is the SQLite durable store, no in-memory or alternate store substitutes for it, contract behavior never reads wall-clock time, and durable job, idempotency, lease, and terminal state is stored in SQLite. (`semantics.v1.md` §§1, 4, and 7.)

The attestation records:

- reviewed candidate-manifest SHA-256;
- reviewed candidate-identity SHA-256, binding that manifest to the canonical foreground argv;
- `Affirmative | Negative`;
- findings with `clause` exactly `"1" | "2" | "3" | "4"` for the numbered checklist item above and nonempty `detail`, plus exactly one `location`: `{"kind":"source_line","file":...,"line":...}`, `{"kind":"source_file","file":...}`, `{"kind":"service_command_argument","argument_index":...}`, or `{"kind":"missing_workspace_path","path":...}`;
- approved exceptions with `boundary`, `necessity`, `kind` exactly `boundary_cast_or_suppression_outside_prohibited_surfaces`, and a source-line or service-command-argument `location`;
- active review minutes, or `unknown`.

An affirmative attestation has no findings. Only an otherwise compliant cast or suppression outside the prohibited core surfaces can appear as an approved exception; core-surface violations and other checklist clauses cannot be waived.

A negative review is terminal for this run and does not authorize more remediation.

Write the attestation outside the repository. An affirmative record has exactly this shape:

```json
{
  "active_minutes": "unknown",
  "approved_boundary_exceptions": [],
  "decision": "Affirmative",
  "findings": [],
  "reviewed_candidate_identity_sha256": "<64 lowercase hex characters>",
  "reviewed_manifest_sha256": "<64 lowercase hex characters>"
}
```
