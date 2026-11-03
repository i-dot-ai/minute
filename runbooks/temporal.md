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

Register and verify the four ID attributes manually through the Temporal CLI **before** deploying the application change. Releases and local Compose do not register them. Application releases do not check Temporal or run admin tasks; missing or wrongly typed ID attributes can cause workflow starts to fail at runtime. Audio Memo fields need no setup. No server redeployment is needed to register attributes.

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

Repeat the list command to verify all four names and types before releasing the application. For local development, use `docker compose exec temporal temporal operator ... --address localhost:7233 --namespace default` with the same list/create arguments instead of the tunnel commands. Register ID attributes before submitting jobs or running the paid end-to-end test. Existing runs are not backfilled.

Uploads never submitted for transcription and manual-only edits are not indexed. Temporal visibility is eventually consistent and workflow history/metadata expires with namespace retention; it is not the permanent asset inventory or a replacement for user data-retention/deletion handling. Local experimental runs using older attribute names are not migrated or replay-compatible; start new runs to use the final names. Their existing history is not purged by this change.

If you've lost that terminal (or want to kill it remotely):
```bash
# list active sessions
aws ssm describe-sessions --state Active \
  --query 'Sessions[].{Id:SessionId,Target:Target,Started:StartDate}' --output table

# terminate by id (yours was diego.peteiro@dsit.gov.uk-fcg3xoiktu2svznu27qzrtfrye)
aws ssm terminate-session --session-id "<SessionId>"
```
