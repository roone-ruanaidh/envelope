Continue the same Q1/L1 implementation in the same workspace. Correct the candidate using only the public contract and the failed-gate evidence below. Do not infer hidden requirements and do not create `AGENTS.md`, `.agents/`, or `.codex/` control files.

The evidence contains only admissible public-contract findings; evaluator source, reference behavior, deliberate defects, and passed hidden scenarios remain unavailable.

```json
{{FEEDBACK_JSON}}
```

Rerun your local checks and remove generated caches, databases, logs, and other test output. Your final response must match the supplied JSON schema and put the declaration under `completion`. Return `declared_complete` only when the workspace contains the remediated candidate you intend to evaluate, with its exact foreground argv. Return `blocked` when correction requires an undefined decision or unavailable authority. Do not ask a question.
