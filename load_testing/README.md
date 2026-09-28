# Load Testing

The load testing script authenticates by reusing your own logged-in browser session. The deployed environments sit behind two checkpoints: an edge/WAF layer and an AWS Cognito sign-in. When you log in through the browser, both checkpoints are cleared and your session is stored as a `Cookie` on every request. By copying that cookie and passing it to the load testing script, each request is recognised as your user and passes through both checkpoints. Note the cookie is tied to your user and will eventually expire. If that happens, just repeat the steps below to grab a fresh one.

## Get **your** Cookie

1. Go to [https://minute.dev.i.ai.gov.uk/](https://minute.dev.i.ai.gov.uk/)
2. Go to `View > Developer > Developer Tools... > Network`
3. Refresh the page
4. Search for `/api/proxy/users/me`
5. Copy `Headers > Request headers > Cookie`

## Run Concurrent Uploads

```bash
# bbc-podcasting-house
uv run python load_testing/download_bcc_podcasting_house.py  # -> .downloads/*.mp3 [*.wav]
uv run python load_testing/run.py --scenario=bbc-podcasting-house --num=16 --cookie=X-Amzn-Oidc-Data-0=tHXL...

# all these fancy pens (1s)
uv run python load_testing/run.py --scenario=bbc-podcasting-house --num=16 --cookie=X-Amzn-Oidc-Data-0=tHXL...
```

## Health and Metrics

--- [ECS](https://eu-west-2.console.aws.amazon.com/ecs/v2/clusters/i-dot-ai-dev-ecs-cluster/services?region=eu-west-2) ---

| TASK     | LINK |
| -------- | ------- |
| FRONTEND | [i-dot-ai-dev-minute-frontend-ecs-service](https://eu-west-2.console.aws.amazon.com/ecs/v2/clusters/i-dot-ai-dev-ecs-cluster/services/i-dot-ai-dev-minute-frontend-ecs-service/health?region=eu-west-2) |
| BACKEND | [i-dot-ai-dev-minute-backend-ecs-service](https://eu-west-2.console.aws.amazon.com/ecs/v2/clusters/i-dot-ai-dev-ecs-cluster/services/i-dot-ai-dev-minute-backend-ecs-service/health?region=eu-west-2) |
| WORKER | [i-dot-ai-dev-minute-worker-ecs-service](https://eu-west-2.console.aws.amazon.com/ecs/v2/clusters/i-dot-ai-dev-ecs-cluster/services/i-dot-ai-dev-minute-worker-ecs-service/health?region=eu-west-2) |


## Logs

--- [CloudWatch](https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#log-analytics) ---

```
SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-dev-minute-worker-logs" START=-1h END=0s
| fields @timestamp, @message
| filter @message like /(?i)(error|exception|fail)/
| sort @timestamp desc
```
