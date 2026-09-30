# Runbooks

"How-to" guide for completing commonly repeated tasks or procedures.

## Debugging

### Messages like error, exception or fail

[CloudWatch](https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#log-analytics)

```
<!-- Dev -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-dev-minute-worker-logs" START=-8h END=0s
| fields @timestamp, @message
| filter @message like /(?i)(error|exception|fail)/
| sort @timestamp desc

<!-- Pre-Prod -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-preprod-minute-worker-logs" START=-8h END=0s
| fields @timestamp, @message
| filter @message like /(?i)(error|exception|fail)/
| sort @timestamp desc

<!-- Prod -->

SOURCE "arn:aws:logs:eu-west-2:671657536603:log-group:i-dot-ai-prod-minute-worker-logs" START=-8h END=0s
| fields @timestamp, @message
| filter @message like /(?i)(error|exception|fail)/
| sort @timestamp desc
```