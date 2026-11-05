# Access the Temporal UI

Connect to the selected environment's Temporal server through an AWS Systems Manager port-forwarding session, then run the Temporal UI locally to inspect workflows and activity retries. The commands below also show how to close the session when you finish.

Run `aws-login` first to authenticate with AWS for the intended environment, then set `ENV` to `dev`, `preprod`, or `prod` in the commands below.

For the independent application/server release commands and the one-time state migration, see [Temporal releases](temporal-releases.md).

```console
aws-login

ENV=dev

REGION=eu-west-2
CLUSTER="i-dot-ai-${ENV}-ecs-cluster"
SERVICE="i-dot-ai-${ENV}-minute-temporal-ecs-service"
CONTAINER="i-dot-ai-${ENV}-minute-temporal-container"

TASK=$(aws ecs list-tasks --region $REGION --cluster "$CLUSTER" --service-name "$SERVICE" --query 'taskArns[0]' --output text)
TASK_IP=$(aws ecs describe-tasks --region $REGION --cluster "$CLUSTER" --tasks "$TASK" \
  --query "tasks[0].containers[?name=='${CONTAINER}'].networkInterfaces[0].privateIpv4Address | [0]" --output text)
RUNTIME=$(aws ecs describe-tasks --region $REGION --cluster "$CLUSTER" --tasks "$TASK" \
  --query "tasks[0].containers[?name=='${CONTAINER}'].runtimeId | [0]" --output text)

TARGET="ecs:${CLUSTER}_${TASK##*/}_${RUNTIME}"

aws ssm start-session --region $REGION --target "$TARGET" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$TASK_IP\"],\"portNumber\":[\"7233\"],\"localPortNumber\":[\"7233\"]}"
```

Leave that running ("Waiting for connections…"), then:

```console
docker run --rm -p 8081:8080 -e TEMPORAL_ADDRESS=host.docker.internal:7233 temporalio/ui
# http://localhost:8081
```

## Search jobs and find assets

In the UI's workflow list, use these visibility queries (replace the placeholders with UUIDs):

```sql
UserId = '<user UUID>'
UserId = '<user UUID>' AND WorkflowType = 'TranscriptionWorkflow'
UserId = '<user UUID>' AND WorkflowType IN ('MinuteGenerationWorkflow', 'MinuteEditWorkflow')
MinuteId = '<minute UUID>'
MinuteVersionId = '<minute version UUID>'
TranscriptionId = '<transcription UUID>'
```

Temporal search attributes use PascalCase; application/API fields keep snake_case (`MinuteVersionId` corresponds to `minute_version_id`, not `version_minute_id`). Every new transcription, minute-generation and AI-edit run is indexed by all four IDs at start, including queued/failed runs. The initial minute version is produced inside `TranscriptionWorkflow`, so include that workflow type when looking for all minutes. Manual edits have no Temporal workflow.

Register `UserId`, `TranscriptionId`, `MinuteId` and `MinuteVersionId` as **Keyword**. These are the only four custom search attributes needed.

After audio preparation succeeds, open the transcription workflow's **Memo** to see `AudioUploadSizeMb` (megabytes of the original upload, **not** the converted MP3; 1 MB = 1,000,000 bytes) and `AudioDurationSeconds` (seconds measured from the prepared audio, or a four-hour fallback if duration probing fails). These are display-only metadata: they need no registration and cannot be used in workflow-list queries. For example, 985,225 bytes is `0.985225` MB. If duration cannot be determined, the worker logs a warning and continues using 14,400 seconds for processing; the Memo duration also reflects that fallback rather than a measurement. Metrics remain visible if later STT or summary processing fails. Older audio-preparation results without upload size remain readable; they do not invent a size value.

Use the indexed IDs to find the corresponding transcript, minute and version records in Postgres. Audio assets are linked through `recording.transcription_id`. New runs store business IDs as search attributes and audio metrics as Memo metadata, not storage keys or bucket names.

### Rollout and limits

The Temporal namespace task registers the four ID attributes during server releases and local Compose startup. Application-only releases do not run this task: verify the attributes before deploying application code to an existing server, and register any missing names manually using the commands below. Missing or wrongly typed ID attributes can cause workflow starts to fail at runtime. Audio Memo fields need no setup. No server redeployment is needed for manual registration.

With the tunnel above open and the local server stopped so it does not occupy port `7233`, use the CLI from the locally built `minute-temporal:latest` image without starting a server. First confirm the namespace belongs to the intended environment, then list existing attributes:

```console
docker run --rm --entrypoint temporal minute-temporal:latest operator namespace describe \
  --address host.docker.internal:7233 --namespace default --output json

docker run --rm --entrypoint temporal minute-temporal:latest operator search-attribute list \
  --address host.docker.internal:7233 --namespace default --output json

# Omit any name/type pairs that already exist; verify their types match.
docker run --rm --entrypoint temporal minute-temporal:latest operator search-attribute create \
  --address host.docker.internal:7233 --namespace default \
  --name UserId --type Keyword \
  --name TranscriptionId --type Keyword \
  --name MinuteId --type Keyword \
  --name MinuteVersionId --type Keyword
```

Repeat the list command to verify all four names and types before releasing the application. For local development, Compose registers them automatically; use `docker compose exec temporal temporal operator ... --address localhost:7233 --namespace default` with the same list/create arguments to verify or repair an existing namespace. Verify ID attributes before submitting jobs or running the paid end-to-end test. Existing runs are not backfilled.

Uploads never submitted for transcription and manual-only edits are not indexed. Temporal visibility is eventually consistent and workflow history/metadata expires with namespace retention; it is not the permanent asset inventory or a replacement for user data-retention/deletion handling. Local experimental runs using older attribute names are not migrated or replay-compatible; start new runs to use the final names. Their existing history is not purged by this change.

If you've lost that terminal (or want to kill it remotely):
```bash
# list active sessions
aws ssm describe-sessions --state Active \
  --query 'Sessions[].{Id:SessionId,Target:Target,Started:StartDate}' --output table

# terminate by id (yours was diego.peteiro@dsit.gov.uk-fcg3xoiktu2svznu27qzrtfrye)
aws ssm terminate-session --session-id "<SessionId>"
```

## Processing status API

Authenticated Minute users can request `GET /status?horizon=10m` from the backend.
The horizon defaults to `10m`; whole minutes/hours from `1m` to `24h` are accepted.
Responses are cached for 30 seconds per backend process and include:

- Approximate workflow-run counts and failure rates overall and for transcription,
  minute generation and AI editing. Starts/closures are counted within the horizon;
  in-progress counts include older runs.
- P50, P90, P99 and maximum successful processing time and current in-progress age
  per workflow type, in seconds, with sample counts. Percentiles use nearest rank.
- The collection window/timestamp. Empty distributions and failure rates without
  outcomes are `null`, not zero. Temporal errors/timeouts return HTTP 503.

Processing time includes queue waiting, execution and retries, but not upload time.
The transcription pipeline includes summarisation after the transcript becomes ready;
optional enrichment/summary failures do not necessarily fail the workflow. The failure
rate is `(failed + timed_out) / (completed + failed + timed_out)`, excluding cancellations,
terminations and continue-as-new. Runs are not unique recordings or activity tasks.

Visibility is eventually consistent. Verify namespace retention covers the requested
horizon. Timing reads are capped at 1,000 runs per workflow type/population: if exceeded,
that distribution has `truncated: true` and null timings, and the response has `partial: true`.
Counts still use the Count API; they are not capped. No histories or execution payloads
are read or exposed. These metrics are not a service-availability verdict; show running
counts/ages alongside successful processing times, especially with small samples.

### Hourly transcription status

`GET /status/hourly` supplies the `/status` page with 24 hourly buckets (the current
hour is incomplete) and a separate last-10-minutes window, cached for one minute.
The frontend API also caches successful responses for one minute per process and
shares in-flight refreshes across users. The page renders before metrics arrive
and refreshes once a minute while visible. Failed refreshes are not cached.
All windows include their start and exclude their end, bounded by `collected_at`.
Completed, failed and timed-out counts come from Temporal's Count API, grouped by
execution status for each window. Counts and error rates are not capped, but still
reflect eventually consistent visibility data.

Processing times use up to 20,000 listed completed runs. Audio duration comes from
the `AudioDurationSeconds` Memo key, with `audio_seconds` accepted for older status-page
runs. Runs without the audio duration memo still contribute to mean processing time,
but not per-audio-hour metrics. If the read limit is exceeded, `partial: true` means timing figures are
incomplete; the page warns about this without hiding counts or error rates. Mean
processing time divides by the number of listed runs, not the uncapped count.
