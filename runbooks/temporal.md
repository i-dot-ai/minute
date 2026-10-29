# Access the Temporal UI

Connect to the selected environment's Temporal server through an AWS Systems Manager port-forwarding session, then run the Temporal UI locally to inspect workflows and activity retries. The commands below also show how to close the session when you finish.

Run `aws-login` first to authenticate with AWS for the intended environment, then set `ENV` to `dev`, `preprod`, or `prod` in the commands below.

For the independent application/server release commands and the one-time state migration, see [Temporal releases](temporal-releases.md).

```console
aws-login

ENV=preprod

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
