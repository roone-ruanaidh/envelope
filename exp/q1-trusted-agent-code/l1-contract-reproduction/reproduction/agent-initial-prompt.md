Implement the complete lease job service defined by every file in `public/contract/`.

You own only the current candidate workspace. The public contract and `.venv` are read-only. You cannot access the evaluator, host workspace, network, credentials, or files outside this workspace. Do not create `AGENTS.md`, `.agents/`, or `.codex/` control files.

Use the installed Python arm. Supply a `Makefile` whose `typecheck` target executes the exact command required by the public contract. Exercise your implementation locally before declaring completion. Remove generated caches, databases, logs, and other test output before declaring completion. Do not weaken, replace, or copy a public contract artifact and do not add a dependency.

Your final response must match the supplied JSON schema. Put the declaration under `completion`. Return `declared_complete` only after the workspace contains the candidate you intend to evaluate, with `service_command` as the exact foreground argv to run from the workspace root. Preserve empty non-executable arguments when they are intentional. If you cannot complete without an undefined decision or unavailable authority, return `blocked` with the reason. Do not ask a question.
