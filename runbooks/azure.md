# Azure

## Azure STT

### Number of requests by status code

> [!IMPORTANT]  
> Look out for [429 Too Many Requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/429) if the application is unhealthy.

[Source](https://github.com/i-dot-ai/minute/blob/main/common/services/transcription_services/azure.py) / [CloudWatch](https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#log-analytics)

```
<!-- Dev -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-dev-minute-worker-logs" START=-120m END=0s
| fields @timestamp, status_code
| filter tag = "azure_stt"
| stats count(*) as num_requests
  by bin(5m) as interval, status_code
| sort interval desc

<!-- Pre-Prod -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-preprod-minute-worker-logs" START=-120m END=0s
| fields @timestamp, status_code
| filter tag = "azure_stt"
| stats count(*) as num_requests
  by bin(5m) as interval, status_code
| sort interval desc

<!-- Prod -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-prod-minute-worker-logs" START=-120m END=0s
| fields @timestamp, status_code
| filter tag = "azure_stt"
| stats count(*) as num_requests
  by bin(5m) as interval, status_code
| sort interval desc
```

## Azure STT Batch

### Number of requests by status code

[Source](https://github.com/i-dot-ai/minute/blob/main/common/services/transcription_services/azure_async.py) / [CloudWatch](https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#log-analytics)

```
<!-- Dev -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-dev-minute-worker-logs" START=-120m END=0s
| fields @timestamp, status_code
| filter tag = "azure_stt_batch"
| stats count(*) as num_requests
  by bin(5m) as interval, status_code
| sort interval desc

<!-- Pre-Prod -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-preprod-minute-worker-logs" START=-120m END=0s
| fields @timestamp, status_code
| filter tag = "azure_stt_batch"
| stats count(*) as num_requests
  by bin(5m) as interval, status_code
| sort interval desc

<!-- Prod -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-prod-minute-worker-logs" START=-120m END=0s
| fields @timestamp, status_code
| filter tag = "azure_stt_batch"
| stats count(*) as num_requests
  by bin(5m) as interval, status_code
| sort interval desc
```

