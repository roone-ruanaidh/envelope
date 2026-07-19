# Inherited-oracle reconstruction — candidate audit

- **Audit date:** July 11, 2026
- **Disposition at audit:** candidate — preserved, unsequenced, and unnumbered

## Objective

Find an existing, inherited black-box job service for a later behavioral-reimplementation experiment, provided that it:

- has lease/visibility-timeout behavior, worker claims, renewal, completion, failure, and concurrency;
- exposes or can be mechanically projected into an OpenAPI-described HTTP interface;
- runs locally and can be frozen;
- has a permissive license;
- is small enough to operate for a solo experiment;
- has a plausibly low risk of having appeared in model training data;
- can be sealed from the agent during the experiment.

Absolute absence from training data is not provable for public software. The practical objective is to minimize contamination, measure warning signs, and prevent runtime source or network access.

## Recommended candidate: Spooled

[Spooled](https://github.com/Spooled-Cloud/spooled-backend) is currently the best fit.

| Criterion | Finding |
|---|---|
| Semantics | At-least-once job processing with claims, worker ownership, adjustable leases, heartbeat renewal, completion/failure, retries, DLQ, priorities, and concurrent claiming |
| Interface | Native REST API plus a published [OpenAPI specification](https://spooled.cloud/docs/api/) and gRPC schema |
| Local execution | Self-hosted Docker/Compose; Rust service with PostgreSQL and optional Redis |
| License | Apache-2.0 |
| Reproducibility | Source, image, schema, dependencies, and database can be pinned to a commit/image digest |
| Project age | GitHub repository created December 9, 2025 |
| Exposure | Approximately 82 GitHub stars at audit time; active but still relatively obscure |
| Recency | Documentation updated July 8, 2026; repository actively updated July 11, 2026 |
| Experiment fit | Strong: `/jobs/claim`, `/jobs/{id}/complete`, `/fail`, and `/heartbeat` map directly to the intended lease-service challenge |
| Operational burden | Moderate: more complex than the desired agent implementation, but manageable as a sealed reference service |

The important native behavior is documented as:

- workers claim jobs with a configurable lease duration;
- the claim makes a job unavailable to other workers;
- heartbeat extends the lease;
- completion and failure are associated with worker identity;
- expiry releases work for another worker;
- database locking coordinates concurrent claims;
- retries and terminal/DLQ behavior create additional state-machine depth.

This is substantially closer to the intended inherited-oracle construct than a generic CRUD service.

## Why Spooled has relatively low contamination risk

The repository postdates December 2025, has limited public adoption, and much of its current documentation and behavior was published or updated during 2026. That makes direct weight-level memorization less likely than for SQS, Celery, Redis Streams, Beanstalkd, Temporal, or PGMQ.

It does **not** make contamination impossible:

- a frontier model may include late-2025 or 2026 web/code data;
- documentation is public and explicitly machine-readable;
- an agent with network access could identify the service immediately;
- endpoint names and response shapes may reveal the source;
- future reruns after publication will have greater contamination risk.

Therefore the candidate is acceptable only with the controls below.

## Proposed oracle exposure

Do not give the agent the repository, image name, project identity, documentation, SDKs, or native OpenAPI document.

Instead, expose a narrow, mechanically projected façade over a frozen Spooled instance:

```text
submit work
inspect work
claim work
renew claim
complete work
fail work
inspect selected queue/work state
```

The façade may rename paths and fields, strip identifying headers, isolate authentication setup, and hide unrelated billing, organization, schedule, webhook, and workflow surfaces. It must not invent job semantics. Contract tests should demonstrate that every façade operation is a faithful translation of the pinned native operation.

This preserves inherited behavior while reducing lexical/source recognition. The experiment remains black-box recreation of an existing system, not implementation from a public SDK.

## Contamination-control protocol

### Before agent execution

1. Freeze an exact repository commit, container digest, database version, configuration, and native OpenAPI digest.
2. Record the repository creation date, public popularity, documentation dates, and search exposure in the qualification bundle.
3. Select the exposed subset and generate a neutral façade schema without copying project-specific prose.
4. Remove source, Git history, package caches, image labels, service names, error banners, and outbound network access from the agent environment.
5. Keep the evaluator, façade implementation, native schema, and oracle identity outside the agent-readable filesystem.
6. Use synthetic queue, worker, and payload names that do not identify the project.

### During execution

1. Permit black-box queries only through the façade.
2. Log every query, response digest, timing, and error.
3. Rate-limit and budget oracle access.
4. Deny general internet access and package/source lookup.
5. Detect attempts to enumerate hidden endpoints, inspect infrastructure, access container metadata, or recover source identity.

### Contamination probes

1. Before revealing oracle responses, ask the agent to state whether it recognizes the interface and what prior system it resembles; treat self-report only as weak evidence.
2. Include behavior whose current details derive from the pinned 2026 revision rather than generic queue knowledge.
3. Compare a contract-only arm with an oracle-access arm. Unexpectedly exact behavior without oracle queries is a contamination warning.
4. Examine transcripts for project names, native endpoint names, exact undocumented defaults, or implementation-specific explanations.
5. Report contamination as `not detected`, `suspected`, or `detected`; never claim it was proven absent.

## Time and concurrency implications

Spooled uses real lease durations rather than the injected test clock originally imagined for the agent implementation. The initial projection should use very short supported lease durations and monotonic client-side timing, then repeat boundary tests enough to characterize scheduler jitter.

If wall-clock tests are too slow or flaky, there are two acceptable responses:

1. narrow the first acceptance claim to time windows that can be measured reliably; or
2. add a test-clock façade only if it can be proved observationally equivalent to native behavior for the tested operations.

Do not silently create new time semantics merely to make the evaluator convenient.

## Alternatives considered

### PGMQ

[PGMQ](https://github.com/pgmq/pgmq) is a strong technical alternative: local Postgres operation, visibility timeouts, renewal, queue operations, and REST exposure through Supabase/PostgREST. It is easier to operate than Spooled.

It is not the preferred first oracle because it has substantially more exposure—approximately 4,900 stars, public use by Supabase, and a longer history—and is a queue primitive rather than a complete worker/job HTTP service. Training contamination is more plausible, and more interface semantics would need to be authored.

### Vercel Queues

[Vercel Queues](https://vercel.com/docs/queues) has excellent native semantics: receive starts a lease, lease extension, acknowledgement, redelivery, TTL, consumer groups, and a current REST API.

It is not preferred because it is a managed, mutable service that cannot be frozen or self-hosted. Authentication, external availability, provider changes, and cost would become experimental confounders. It may become useful in a later managed-versus-local experiment.

### Strait

[Strait](https://strait.dev/) is a recent open-source Postgres orchestration service with jobs, runs, retries, approvals, budgets, and REST APIs. It is interesting for a later full-orchestration experiment, but its public description emphasizes advisory-lock/DAG runtime semantics rather than the narrow renewable lease contract desired for the inherited-oracle experiment. Its broader surface would add unnecessary ambiguity.

### Mature queue systems

SQS, Celery, Redis Streams, NATS JetStream, Beanstalkd, Temporal, and similar systems have strong semantics but very high documentation and training-data exposure. Several are also too operationally broad or provider-dependent for the first experiment.

## Decision rule

Proceed with Spooled as the inherited oracle if a short freeze-and-projection spike confirms all of the following:

1. a pinned version builds and runs locally without a hosted dependency;
2. claim, renewal, ownership, expiry, completion, and concurrent-claim behavior are stable enough to measure;
3. the exposed subset can be faithfully projected without authoring new semantics;
4. source and identity can be sealed from the agent;
5. the evaluator can distinguish native behavior from realistic seeded defects;
6. license and attribution requirements are satisfied;
7. the operational burden remains reasonable for a solo experiment.

If any of conditions 1–5 fail, do not force the candidate. Audit one additional recent project, then author the smallest independent reference service if no inherited oracle survives.

## Relationship to E1

This methodology is intentionally preserved as a candidate. It asks a larger question than the first vertical slice:

> Can an agent behaviorally recreate an inherited black-box system, and can memorization and evaluator exposure be controlled well enough to interpret the result?

Experiment 1 instead asks the narrower foundational question:

> What does it cost to trust agent-produced code against a declared, human-authored contract and evaluator?

For Experiment 1, the agent receives the contract and no inherited-oracle access. General queue knowledge is expected substrate rather than a contamination confound. The experiment measures the premium introduced by verification, review, remediation, and acceptance.

The inherited-oracle work may resume only through a future charter decision. It has no assigned experiment number or sequence. Its next engineering artifact would be a bounded **oracle freeze-and-projection specification**, followed by a short technical spike. That spike would pin the candidate, enumerate exposed operations, define façade/native equivalence tests, apply the contamination controls above, and accept or reject Spooled under a strict time budget.
