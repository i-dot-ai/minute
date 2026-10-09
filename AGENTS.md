# Minute — System Architecture

Minute turns meeting recordings into transcripts and structured minutes for public-sector
meetings. This document describes the current architecture and data flow as implemented in
this repository, and is explicit about the moving parts that are easy to get wrong: the queue,
the lock/claim model, visibility timeouts, heartbeats, and idempotency.

For how to run it locally see the [README](README.md); for the database diagram see
[`minute_database_schema.png`](minute_database_schema.png).

---

## 1. Components

```
                          ┌────────────────────────┐
                          │        Frontend        │  Next.js (port 3000)
                          │  (browser → API proxy) │
                          └───────────┬────────────┘
                                      │ HTTP (OIDC auth header)
                          ┌───────────▼────────────┐
                          │        Backend         │  FastAPI (port 8080)
                          │  routes + auth + cron  │
                          └───┬──────────┬─────────┘
              writes rows,    │          │ presigned URLs / object checks
              publishes msg   │          ▼
                     ┌────────▼──────┐  ┌──────────────────┐
                     │  PostgreSQL   │  │  Object storage  │
                     │  (Aurora/13)  │  │  S3 (MiniStack)  │
                     └────────▲──────┘  └────────▲─────────┘
                              │                   │
                          ┌───┴───────────────────┴──────┐
                          │            Worker             │  long-running ECS task
                          │  consumer + workflows/actions │
                          └───────────────▲───────────────┘
                                          │ long-poll
                              ┌───────────┴────────────┐
                              │  SQS single queue + DLQ │
                              └────────────────────────┘
```

| Component | Code | Runtime |
|---|---|---|
| Frontend | `frontend/` | Next.js |
| Backend (API) | `backend/` | FastAPI / uvicorn |
| Worker | `worker/` | Python asyncio, long-running ECS task |
| Shared code | `common/` | imported by backend and worker |
| Infrastructure | `terraform/` | ECS Fargate, Aurora, S3, SQS, ALB, SSM |

The backend and worker **share the database schema and settings** (`common/database`,
`common/settings.py`, `common/types.py`) but **do not import each other**. The backend never
imports the `worker` package; the worker never imports `backend`.

---

## 2. Data model

Defined in [`common/database/postgres_models.py`](common/database/postgres_models.py).

| Table | Purpose | Key columns |
|---|---|---|
| `user` | Authenticated user | `email` (lowercased, unique), `data_retention_days`, `default_template_id`, `default_template_name` |
| `recording` | A stored audio object | `s3_file_key`, `user_id`, `transcription_id` (nullable; NULL = orphan) |
| `transcription` | One transcription job + result | `status`, `title`, `dialogue_entries` (JSONB), `error`, `user_id`, `claimed_at` |
| `minute` | A minute (one template) for a transcription | `transcription_id`, `template_name`, `user_template_id`, `agenda` |
| `minute_version` | A version of a minute (generation or edit) | `status`, `html_content`, `error`, `ai_edit_instructions`, `content_source`, `claimed_at` |
| `user_template` / `template_question` | User-authored custom templates | `name`, `content`, `description`, `type`, `questions` |

Enums:

- `JobStatus`: `AWAITING_START`, `IN_PROGRESS`, `COMPLETED`, `FAILED` — a PostgreSQL native
  enum named `jobstatus`, **stored by member name (UPPERCASE)**.
- `ContentSource`: `MANUAL_EDIT`, `AI_EDIT`, `INITIAL_GENERATION`.

> The tables `chat`, `hallucination`, and `transcriptionjobstate` exist in migrations but have
> no models — dead schema, removal deferred.

`recording.transcription_id` is nullable: recordings are created *before* a transcription
exists (upload), and orphaned recordings are cleaned up later.

---

## 3. End-to-end data flow

### 3.1 Upload + start a transcription

1. `POST /recordings` → creates a `recording` row and returns a **presigned `PUT` URL**.
2. Browser uploads the audio directly to object storage via the presigned URL.
3. `POST /transcriptions` → validates the object exists, then creates `transcription` +
   `minute` + `minute_version` rows (all `AWAITING_START`), links the recording, and publishes
   one `MINUTE` message to the worker queue. The message id is the **`minute_version.id`**.

### 3.2 Worker: MINUTE job (`worker/workflows/generate_minute_version.py`)

The single queue carries `WorkerMessage(id=minute_version_id, type=MINUTE|EDIT)`.

```
Received MINUTE job
  └─ load version ─→ minute ─→ transcription (+recordings)
  └─ claim transcription            (CAS, see §5)
       ├─ FAILED      → mark version FAILED, delete message
       ├─ MISSING     → delete message
       ├─ IN_PROGRESS → rehide message (another worker owns it)
       ├─ COMPLETED   → skip transcription, go to compose
       └─ CLAIMED     → transcription phase:
                          prepare_audio  (download; convert to mono mp3 if needed)
                          transcribe     (Azure Speech, synchronous HTTP; T-slot)
                          identify_speakers (LLM; L-slot)
                          generate_meeting_title (LLM; L-slot)
                          mark transcription COMPLETED
  └─ compose phase:
       claim minute_version          (CAS)
         ├─ COMPLETED/FAILED/MISSING → delete message
         ├─ IN_PROGRESS              → rehide message
         └─ CLAIMED                  → compose_minutes (LLM/template)
                                       mark version COMPLETED, delete message
```

`prepare_audio` conversion is idempotent by convention: recordings are ordered
`created_datetime DESC`, so on resume `recordings[0]` is the previously converted mono mp3 and
conversion is skipped. Conversion output is always mono mp3 (`ac=1`), which is what makes the
gate `{.mp3} + 1 channel` reliable.

### 3.3 Worker: EDIT job (`worker/workflows/edit_minute_version.py`)

1. `POST /minutes/{minute_id}/versions` with `ai_edit_instructions` creates a new
   `minute_version` (status `AWAITING_START`) and publishes an `EDIT` message.
2. Worker loads the target version (carries the instruction) and the **source** version
   (`ai_edit_instructions.source_id`), claims the target, runs the edit LLM call, marks
   `COMPLETED`.
3. A missing source, or a target with no instructions, is recorded as `FAILED` on the target
   and the message is deleted (no infinite redelivery).

### 3.4 Additional minutes & retry

- `POST /transcription/{transcription_id}/minutes` creates another `minute` (+ version) for an
  **already-completed** transcription and publishes a `MINUTE` message. The workflow sees the
  transcription `COMPLETED`, skips straight to compose.
- `POST /transcriptions/{id}/retry` (only for a `FAILED` transcription) resets **both** the
  `transcription` and its single `minute_version` to `AWAITING_START` (clearing `claimed_at`,
  `error`, `dialogue_entries`, `html_content`) and republishes a `MINUTE` message.

### 3.5 Backend cleanup (daily)

`backend/cleanup_job.py`, scheduled at 23:00 UTC via APScheduler in the backend process:

1. **Retention**: delete transcriptions older than each user's `data_retention_days`.
2. **Orphans**: delete `recording` rows with `transcription_id IS NULL` (and their objects).
3. **Stalled jobs**: mark `IN_PROGRESS` rows whose `claimed_at` is older than 24h as `FAILED`
   ("finalised by cleanup process") — the backstop if a worker dies and nothing re-claims.

---

## 4. The queue

- **Exactly one primary queue + one dead-letter queue** (`terraform/sqs.tf`,
  `ministack-setup.sh`). Names from `WORKER_QUEUE_NAME` / `WORKER_DEADLETTER_QUEUE_NAME`.
- Access via `common/services/queue_services/sqs.py` (`SQSQueueService`). One queue serves both
  task types; the task type is in the message body.

Message shape (`common/types.py`):

```json
{ "id": "<minute_version_id>", "type": "MINUTE|EDIT", "data": { "source_id": "<uuid>" } | null }
```

| Property | Value | Where |
|---|---|---|
| Polling | long-poll, `WaitTimeSeconds=20`, `MaxNumberOfMessages=1` | `sqs.py` |
| Visibility timeout | `JOB_VISIBILITY_TIMEOUT_SECS` = **300s** | `common/settings.py` |
| Heartbeat interval | `JOB_HEARTBEAT_INTERVAL_SECS` = **120s** | `common/settings.py` |
| Redrive | `maxReceiveCount` = **10** | `terraform/sqs.tf`, `ministack-setup.sh` |
| Dead-letter | malformed / unknown / EDIT-without-source messages are deadlettered | `worker/consumer.py` |

Delivery handling in the consumer:

- **`delete`** — job fully handled (success, or a failure recorded in the DB). The message is
  deleted.
- **`rehide`** — another worker owns the job. The message visibility is extended, not reset.
- **crash** — an unexpected exception rehides the message so it redelivers; repeated failures
  eventually reach the DLQ via the redrive policy.

---

## 5. Locks, claims, and idempotency (the critical part)

There is **no distributed lock service**; exclusion is a PostgreSQL compare-and-swap (CAS).
All claim/status statements live in `common/database/repository/` — the single place these
invariants are implemented. Repository functions **never commit**; the caller owns the
transaction.

### 5.1 The lease (`claimed_at`)

`transcription.claimed_at` and `minute_version.claimed_at` (TIMESTAMPTZ, nullable) are the
leases. They are written **only** by the claim CAS and the heartbeat.

### 5.2 Two-level claim

A job is a `minute_version`, but its pipeline has two independently-failable phases, so there
are two claims:

1. the **transcription** claim gates `prepare_audio → transcribe → speakers → title`, and
2. the **minute_version** claim gates `compose` (and the whole edit workflow).

The transcription row is the authority on "who is transcribing" (many minute versions can
share one transcription), and the stale sweep judges each row's liveness from its own
`claimed_at`.

### 5.3 The CAS

```sql
UPDATE <table>
   SET status = 'IN_PROGRESS', claimed_at = now()
 WHERE id = :id
   AND ( status = 'AWAITING_START'
      OR ( status = 'IN_PROGRESS'
           AND (claimed_at IS NULL OR claimed_at < now() - :stale) ) );
```

`rowcount == 1` → `CLAIMED`. `rowcount == 0` → the row is read back and classified as
`COMPLETED`, `FAILED`, `IN_PROGRESS` (fresh lease → another worker owns it), or `MISSING`.

`JobStatus` values are bound by **member name** (`AWAITING_START`, …), matching the native pg
enum labels. Never compare against the lowercase `StrEnum.value`.

### 5.4 Heartbeat (keeps long jobs alive)

While a job runs, `Consumer._heartbeat` (a task created inside the job's asyncio task) ticks
every `JOB_HEARTBEAT_INTERVAL_SECS`:

1. extends the SQS message visibility by `JOB_VISIBILITY_TIMEOUT_SECS` (so the message is not
   redelivered mid-run), and
2. calls `refresh_job_leases`, bumping `claimed_at` on whichever of the job's rows are
   `IN_PROGRESS` (so a duplicate message can never steal a live claim).

If the worker dies, both signals stop: the message redelivers within one visibility window and
the claim becomes stealable after the staleness window.

| Knob | Default | Meaning |
|---|---|---|
| `JOB_VISIBILITY_TIMEOUT_SECS` | 300 | SQS invisibility per receive/extend |
| `JOB_HEARTBEAT_INTERVAL_SECS` | 120 | how often the lease/visibility is renewed |
| `JOB_STALE_SECONDS` | 600 | lease age at which a claim is stealable on redelivery |

> Timing invariant (currently enforced by defaults, not validated): heartbeat interval must be
> less than both the visibility timeout and the stale window, or a live job can be redelivered
> and stolen.

### 5.5 Idempotency guarantees

- **Claim** ensures only one worker runs a phase; terminal rows are never re-claimable.
- **Phase skip**: a `COMPLETED` transcription routes straight to compose; a `COMPLETED`
  version is a no-op.
- **`prepare_audio`**: newest-recording rule prevents duplicate conversion on resume (a
  concurrent dual-run may still insert a second converted recording — benign, documented).
- **Retry** resets both rows, so a retried job re-runs the transcription claim cleanly.
- **Missing rows** terminate the job (`delete`) rather than looping into the DLQ.

---

## 6. Storage

`common/services/storage_services/` has a single `S3` backend (`s3`), used everywhere: presigned
PUT for uploads, presigned GET for downloads, `head_object` for existence checks, `upload_file`/
`download_file` for server-side transfers. Deployed environments talk to real AWS with the ECS
task role; local runs point at MiniStack (see below). The `Storage` Protocol in `_protocols.py`
documents the contract.

Locally the endpoint is split. Compose containers reach MiniStack at `ministack:4566`, but the
browser cannot resolve that name, and the browser is what uses the presigned URLs. So presigned
URLs are generated against `BROWSER_AWS_ENDPOINT_URL` (`http://localhost:4566` in Compose) while the
server-side client keeps `AWS_ENDPOINT_URL` (`ministack:4566`). `BROWSER_AWS_ENDPOINT_URL` defaults
to `AWS_ENDPOINT_URL`, so host-run dev and deployment need only one endpoint. MiniStack URLs use
path-style addressing; virtual-host style would produce `<bucket>.localhost`, which won't resolve.

| Setting | Host-run | Compose | Deployed |
|---|---|---|---|
| `AWS_ENDPOINT_URL` | `http://localhost:4566` | `http://ministack:4566` | unset (real AWS) |
| `BROWSER_AWS_ENDPOINT_URL` | unset (falls back) | `http://localhost:4566` | unset |

---

## 7. Transcription

`worker/actions/prepare_audio.py` + `common/services/stt/`
(the `STT` Protocol and `Azure` service).

- **Only synchronous Azure Speech fast transcription is supported** (the AWS Transcribe async
  adapter and the adapter registry/ABC were removed).
  `Azure.transcribe()` requires `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION`
  (`is_transcription_available()`).
- The prepared file is POSTed as multipart to
  `https://<region>.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe`.
- **Region failover**: primary, then `AZURE_SPEECH_FALLBACK_1/2`. Fail over on 429/5xx/timeout;
  a hard error fails the transcription. `tenacity` retries the region sweep (30/60/120/240s,
  5 attempts; worst case ~82 minutes).
- Azure's provider limit (~5h) means longer audio fails.

## 8. LLM & minute generation

`worker/llm/` holds the Gemini adapter (`gemini.py`) and `ChatBot`
(`create_default_chatbot(FastOrBestLLM.FAST|BEST)`). Provider/model come from
`FAST_LLM_*` / `BEST_LLM_*` settings (Gemini only). Default temperature is 1.0 (Gemini 3
recommendation).

- **Fast** is used for speaker identification, meeting title, basic minutes, and AI edits.
- **Best** is intended for full minute generation.

`compose_minutes` classifies by transcript word count:

| Meeting type | Word count | Behaviour |
|---|---|---|
| `too_short` | `< MIN_WORD_COUNT_FOR_SUMMARY` (200) | fallback text, no LLM |
| `short` | `< MIN_WORD_COUNT_FOR_FULL_SUMMARY` (199 by default → effectively disabled) | basic summary via fast LLM |
| `standard` | otherwise | template dispatch |

**Templates**: generation lives in `worker/templates/` (static registry in
`worker/templates/__init__.py`); the backend serves metadata from
`common/template_catalog.py` (metadata-only mirror, guarded by a drift test).

---

## 9. Backend

- **FastAPI** (`backend/main.py`) mounts all routers under `/api` via the frontend proxy.
- **Auth** (`backend/auth.py`, `backend/api/dependencies/get_current_user.py`): verifies the
  OIDC header via the i.AI Auth API, upserts the user by lowercased email, returns `UserDep`.
- **Routes** (`backend/api/routes/`): `health`, `transcriptions`, `users`, `minutes`,
  `templates`.
- **Triggers** (backend publishes to the worker queue):
  - `POST /transcriptions` → `MINUTE`
  - `POST /transcriptions/{id}/retry` → `MINUTE`
  - `POST /transcription/{id}/minutes` → `MINUTE` (requires a `COMPLETED` transcription)
  - `POST /minutes/{id}/versions` with `ai_edit_instructions` → `EDIT`
- **Cleanup scheduler** runs in-process (APScheduler) — see §3.5.

---

## 10. Worker runtime

`worker/main.py` → `Consumer(queue, signal_handler).run()`.

- One asyncio task per received message (max 1 message per poll), bounded by **two
  semaphores**:
  - `MAX_CONCURRENT_TRANSCRIPTIONS` (2 dev / 4 prod) — audio download/convert + STT,
  - `MAX_CONCURRENT_LLM` (4 dev / 8 prod) — speakers, title, compose, edit.
  - total capacity = sum of the two, so long transcriptions cannot starve edits.
- **Blocking calls** (boto3 SQS, ffmpeg/ffprobe subprocesses) run via `asyncio.to_thread`.
- **Graceful shutdown**: `SIGTERM`/`SIGINT` stop receiving; in-flight jobs are drained
  (`stop_grace_period: 30s` in Compose; the ECS stop timeout otherwise).
- **Liveness**: the consumer touches `HEARTBEAT_DIR/worker_consumer.heartbeat`; the ECS
  container healthcheck runs `worker/healthcheck.py`, which fails if no heartbeat is younger
  than 20 minutes.
- **Per-job context** is bound to `structlog` contextvars (task-local), so every log line for a
  job — including from actions and the heartbeat — carries `minute_version_id` and, once
  loaded, `minute_id`, `transcription_id`, `user_id` (`source_minute_version_id` for edits).

Deletion summary relative to the old design: Ray, the adapter registry/ABC, AWS Transcribe
async polling, the second queue, and `TranscriptionJobMessageData` are gone.

---

## 11. Configuration

`common/settings.py` (pydantic-settings, loaded from env + `.env`). Notable groups:

- Postgres: `POSTGRES_*`
- Queue: `WORKER_QUEUE_NAME`, `WORKER_DEADLETTER_QUEUE_NAME`
  (SQS is the only queue implementation; it is constructed directly)
- Worker concurrency/lease: `MAX_CONCURRENT_TRANSCRIPTIONS`, `MAX_CONCURRENT_LLM`,
  `JOB_VISIBILITY_TIMEOUT_SECS`, `JOB_HEARTBEAT_INTERVAL_SECS`, `JOB_STALE_SECONDS`
- Storage: `DATA_S3_BUCKET`, `AWS_ENDPOINT_URL` (server-side), `BROWSER_AWS_ENDPOINT_URL`
  (browser-facing; defaults to `AWS_ENDPOINT_URL`)
- Azure STT: `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, optional fallbacks
- LLM: `FAST_LLM_PROVIDER/MODEL_NAME`, `BEST_LLM_PROVIDER/MODEL_NAME`, Google credentials
- Auth: `REPO`, `AUTH_API_URL`
- Local emulation: `USE_MINISTACK`, `MINISTACK_URL`
- Logging: `ENVIRONMENT`, `LOG_LEVEL` (JSON outside `local`, text locally)

---

## 12. Deployment

`terraform/` (workspaces `dev`/`preprod`/`prod`):

- **ECS Fargate** services for `backend`, `frontend`, and `worker`
  (`terraform/ecs.tf`). Worker has no load balancer; in `prod` it runs 2 tasks
  (`desired_app_count`), otherwise 1.
- **Aurora PostgreSQL 16** (`terraform/rds.tf`).
- **S3** data bucket with CORS for browser uploads (`terraform/s3.tf`).
- **SQS** worker queue + DLQ (`terraform/sqs.tf`).
- **SSM Parameter Store** for secrets; **IAM** task policy for S3/SQS/SSM/KMS
  (`terraform/iam.tf`).
- **Observability**: CloudWatch alarms → SNS → Slack (`terraform/ecs.tf`).

The backend runs `alembic upgrade head` on container start (`backend/entrypoint.sh`).

---

## 13. Local development

- `docker compose up` starts `frontend` (3000), `backend` (8080), `worker`, `db` (Postgres 13,
  5432), and `ministack` (SQS + S3 emulator, 4566).
- **MiniStack** replaces AWS SQS and S3 everywhere locally. Compose containers reach it at
  `ministack:4566`; presigned URLs handed to the browser use `localhost:4566` via
  `BROWSER_AWS_ENDPOINT_URL`.
  `ministack-setup.sh` creates the queue + DLQ and the data bucket.
- `docker compose up --watch` syncs file changes into the containers.
- Tests run on the host: `make test` (offline, no paid APIs), `make test_e2e` (needs
  credentials and `.data/test_audio/`).

---

## 14. Known issues / follow-ups

- **Lease timing** is enforced only by default values; a `settings` validator for
  `heartbeat < visibility` and `heartbeat < stale` is not yet present.
- **Stale cutoff clock**: `_stale_cutoff` uses the app clock while `claimed_at` is written with
  the DB clock (`func.now()`); small skew is tolerated by design.
- **Dead schema**: `chat`, `hallucination`, `transcriptionjobstate` tables have no models.
- **Client-vs-server `claimed_at`** and the two-level claim are deliberate; see
  `common/database/repository/__init__.py` for the rationale.
