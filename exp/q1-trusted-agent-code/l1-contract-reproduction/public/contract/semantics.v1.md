# Lease Job Service semantics v1

- **Normative version:** 1.0.0
- **Wire contract:** `openapi.v1.json`
**Python arm:** `python-arm-requirements.v1.txt`, `mypy.v1.ini`

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. This document, the
OpenAPI file, the Python dependency lock, and the mypy configuration together are the complete
public acceptance contract for Q1/L1. A conflict between them is a contract error;
none silently overrides another.

## 1. Scope and execution profile

The service is an HTTP/JSON lease queue: one service instance backed by one SQLite database and one
injected logical clock. A conforming candidate uses FastAPI, SQLite, and no source or runtime
dependency on evaluator-owned code. The evaluator observes only HTTP and process-lifecycle
behavior; implementation evidence is adjudicated by the separate typing and human-review gates.

The candidate MUST use only the Python packages and exact versions in
`python-arm-requirements.v1.txt`, plus Python's standard library. It MUST NOT rely on an otherwise
ambient package in the evaluator VM or weaken or modify a public contract artifact.

`make typecheck` MUST run `python3 -m mypy --config-file public/contract/mypy.v1.ini .` and exit zero.
It MUST cover every candidate-owned Python module. Candidate configuration MUST NOT exclude a
module, ignore a missing import, disable an error code, add a per-module override, or otherwise
weaken the supplied configuration.

Every candidate-owned function and method MUST be annotated. Request and response bodies MUST use
explicit Pydantic models configured with strict validation (coercion disabled) and extra fields
forbidden. Public models, domain state, storage interfaces, and state-transition interfaces MUST
NOT contain `Any`, casts, or type suppressions. A dynamic value from a third-party boundary MUST be
narrowed immediately. Any unavoidable boundary cast or suppression is an acceptance finding that
must be enumerated and approved during human review; none is approved by this contract in advance.

The evaluator starts the foreground command supplied as `SERVICE_COMMAND` with:

```text
Q1_L1_HOST=<host from the supplied base URL>
Q1_L1_PORT=<port from the supplied base URL>
Q1_L1_DATABASE_PATH=<absolute path to an evaluator-owned SQLite file>
Q1_L1_CLOCK_INITIAL_MS=<decimal integer in 0..9223372036854775807>
```

The supplied base URL uses unencrypted HTTP on `127.0.0.1` or `localhost`, with an explicit port
and no credentials, query, fragment, or path prefix. The service is never evaluated over a remote
or cloud network.

`SERVICE_COMMAND` MUST remain in the foreground, bind `Q1_L1_HOST:Q1_L1_PORT`, become ready through
`GET /healthz`, and exit with status zero after `SIGTERM`. It MUST use `Q1_L1_DATABASE_PATH` and MUST
NOT substitute in-memory or another undeclared storage. The evaluator uses a fresh database for a
suite and the same path across that suite's restarts. It may use both graceful and abrupt restarts.

The acceptance profile bounds startup at 8 seconds, each HTTP request at 3 seconds, the whole suite
at 45 seconds, and graceful shutdown at 1.5 seconds. The controller may force-kill an unresponsive
process, but requiring that kill fails cleanup acceptance.

## 2. Representation and validation

Except for the declared empty `204` response, every successful and error response has a JSON body
encoded as UTF-8 and uses `application/json`. A JSON-body operation requires a media type of
`application/json`; parameters such as `charset` are allowed.
Another media type returns `415` and error code `unsupported_media_type`. Syntactically invalid
JSON returns `400` and `invalid_json`. Syntactically valid JSON that violates its OpenAPI schema,
including an omitted or extra field, a boolean supplied as an integer, an out-of-range value, or a
malformed UUID, returns `422` and `validation_error`.

The evaluator sends `Content-Length` and no request body larger than 1,048,576 encoded bytes.
Streaming, chunked, or larger request bodies are outside the Q1/L1 acceptance profile.

String lengths are Unicode code-point counts. String comparisons are exact and case-sensitive,
with no trimming, case folding, or Unicode normalization. The declared inclusive bounds are:

| Field | Minimum | Maximum |
|---|---:|---:|
| `idempotency_key` | 1 | 128 |
| `worker_id` | 1 | 128 |
| `lease_token` | 1 | 256 |
| `payload` | 0 | 65,536 |
| `result` | 0 | 65,536 |
| `failure.code` | 1 | 64 |
| `failure.message` | 1 | 4,096 |
| `ttl_ms` | 1 | 60,000 |
| `now_ms` | 0 | 9,223,372,036,854,775,807 |

`job_id` values are UUIDs returned in canonical lowercase text. A `job_id` path accepts textual
case variants and compares them by UUID value. A `lease_token` is an opaque, case-sensitive string.
Clients must return it exactly; the contract assigns no syntax or value semantics beyond its length
bounds.

Errors have exactly this shape:

```json
{"error":{"code":"job_not_found","message":"non-empty diagnostic text"}}
```

The message text is not otherwise acceptance-sensitive. A rejected request MUST NOT change the
clock, idempotency association, lease authority, terminal outcome, or any observable logical state
beyond expiration already caused by an earlier clock advance.

## 3. Job representation and invariants

Every `Job` includes every field declared in OpenAPI. Its states and field invariants are:

| `state` | `lease` | `result` | `failure` |
|---|---|---|---|
| `pending` | `null` | `null` | `null` |
| `leased` | `{worker_id, expires_at_ms}` | `null` | `null` |
| `succeeded` | `null` | string | `null` |
| `failed` | `null` | `null` | `{code, message}` |

A generated lease token MUST be fresh for that acquisition and MUST NOT be reused.

The worker ID is recorded metadata, not authority. The lease token alone authorizes heartbeat,
completion, or failure for its path job. There is no per-worker claim limit.

## 4. Injected clock and expiration

The service MUST NOT read wall-clock time for contract behavior. `GET /_evaluator/clock` returns
the process's current logical time. `PUT /_evaluator/clock` sets an absolute value. Setting the same
value is a successful no-op. Setting a lower value returns `409 clock_rewind` without mutation.

The clock is process-local and is deliberately **not persistent**. On every process start it is
initialized from `Q1_L1_CLOCK_INITIAL_MS`. Before a restart, the evaluator supplies a nondecreasing
next logical time; this preserves monotonic time without making the clock part of durable service
state. Evaluator-selected values always leave enough signed-int64 headroom for the requested lease
TTL.

A lease is live exactly when:

```text
now_ms < expires_at_ms
```

It is expired when `now_ms >= expires_at_ms`, including equality. From that instant, reads and
domain operations MUST present and treat the job as `pending`, with no lease authority. This is an
observable state rule, not a storage prescription: an implementation may derive the projection or
materialize it transactionally.

Advancing the clock need not scan or rewrite jobs. The evaluator does not change the clock while a
domain request is in flight; domain linearizability is evaluated at a stable logical time.

## 5. Operations

### Health

`GET /healthz` returns `200` and exactly:

```json
{"status":"ok","contract_version":"1.0.0"}
```

only after the database is initialized and requests can be served. The service need not republish
the OpenAPI document at runtime; `openapi.v1.json` is the single schema authority.

### Submit a job

`POST /v1/jobs` accepts `{idempotency_key, payload}`.

- If the key does not exist, the service atomically creates one `pending` job and returns `201` with
  that job.
- If the key exists with the exact same payload, the service returns `200` with that existing job's
  **current logical representation**. This replay does not otherwise mutate it.
- If the key exists with a different payload, the service returns `409 idempotency_conflict`.

The key uniqueness and the new/replay status decision are atomic under concurrent submissions.
Exactly one of simultaneous equivalent first submissions returns `201`; the others return `200`
and all identify the same job.

### Query a job

`GET /v1/jobs/{job_id}` returns `200` with the job's current logical representation. An unknown
well-formed UUID returns `404 job_not_found`.

### Acquire a lease

`POST /v1/leases` accepts `{worker_id, ttl_ms}`. In one atomic operation it treats expired leases as
pending, chooses any pending job, creates a fresh token, records the worker, sets
`expires_at_ms = now_ms + ttl_ms`, and returns `200` with `{job, lease_token}`. If no job is eligible
it returns `204` with an empty body.

No selection ordering, fairness, or priority is promised. Concurrent claims MUST NOT create two
live leases for one job. With `N` eligible jobs, at most `N` simultaneous claims may succeed and
each successful grant names a distinct job.

### Heartbeat

`POST /v1/jobs/{job_id}/heartbeat` accepts `{lease_token, ttl_ms}`. For the current live token it
sets `expires_at_ms = now_ms + ttl_ms`, retaining the token and worker, then returns `200` with the
job. Renewal is based on the current clock, not on the old expiry; it may shorten a lease.

An expired or non-current token returns `409 lease_not_current`.

### Complete or fail

`POST /v1/jobs/{job_id}/complete` accepts `{lease_token, result}`. A current live holder atomically
changes the job to `succeeded`, stores `result`, clears all lease data and authority, and returns
`200` with the job.

`POST /v1/jobs/{job_id}/fail` accepts `{lease_token, failure:{code,message}}`. A current live holder
atomically changes the job to `failed`, stores the failure, clears all lease data and authority,
and returns `200` with the job.

An expired, stale, foreign, or otherwise non-current token returns `409 lease_not_current` without
mutation. A terminal job has no current lease, so heartbeat, completion, or failure against it also
returns `409 lease_not_current`.

For every token operation, an unknown well-formed path UUID returns `404 job_not_found`.

## 6. Errors and precedence

| Status | Code | Condition |
|---:|---|---|
| 400 | `invalid_json` | Body is not syntactically valid JSON. |
| 404 | `job_not_found` | Well-formed `job_id` does not exist. |
| 409 | `idempotency_conflict` | Existing key is submitted with another payload. |
| 409 | `lease_not_current` | The target job has no live lease matching the supplied token. |
| 409 | `clock_rewind` | Clock PUT is lower than current time. |
| 415 | `unsupported_media_type` | JSON-body operation does not use `application/json`. |
| 422 | `validation_error` | Path or decoded body violates the declared schema. |

Request syntax and schema validation occur before state-dependent behavior. When one request
simultaneously presents multiple independently sufficient failures, which applicable declared
error is returned is otherwise unspecified and is not acceptance-tested.

## 7. Consistency and durability

The concurrent same-key submission and lease claim/reclaim histories declared in Section 5 are
linearizable at the stable evaluator clock. Mixed concurrent heartbeat, completion, and failure
histories are not part of Q1/L1 acceptance; those operations are exercised sequentially. All
state needed to preserve jobs, idempotency, current token, lease metadata, and terminal outcomes is
durable in SQLite. A success response MUST be sent only after its state transition is committed.

Restarting the service with the same `Q1_L1_DATABASE_PATH` and restored logical time MUST preserve:

- pending, live leased, succeeded, and failed jobs and their exact public fields;
- idempotency-key association and replay behavior;
- current live token authority, worker, and expiry;
- stored result or failure.

This applies after graceful shutdown and after abrupt process termination performed after an
acknowledged response. Crashes during an in-flight operation are not exercised in Q1/L1.

## 8. Explicitly unspecified behavior

The following are intentionally unspecified and MUST NOT be enforced by hidden acceptance tests:

- which eligible pending job a claim selects, including ordering and fairness;
- job UUID version or randomness algorithm, beyond validity, canonical output, and uniqueness;
- exact error `message` wording;
- response headers not declared in OpenAPI;
- behavior for undeclared query parameters, undeclared HTTP methods, or paths outside this surface;
- SQLite schema, transaction mechanism, journal mode, indexes, and application module layout;
- behavior when restarted with `Q1_L1_CLOCK_INITIAL_MS` below the last value supplied before shutdown,
  because that is outside the evaluator lifecycle profile;
- relative precedence for combined failures except the validation-first rule in section 6;
- numeric exhaustion near the signed-int64 ceiling; evaluator clock values remain far below it.

## 9. Out of scope

This contract does not claim production readiness, authentication, authorization beyond lease-token
authority, token secrecy against a network observer, transport encryption, multi-tenant isolation,
distributed or replicated operation, availability during process failure, scheduling fairness,
rate limiting, payload interpretation, cancellation, deletion, pagination, retention, wall-clock
accuracy, hostile descendants that escape the launched process group, deliberate CPU or memory
exhaustion, or correctness outside the declared and tested domain.
