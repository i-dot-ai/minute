```bash
REGION=eu-west-2
CLUSTER=i-dot-ai-dev-ecs-cluster
SERVICE=i-dot-ai-dev-minute-temporal-ecs-service

TASK=$(aws ecs list-tasks --region $REGION --cluster "$CLUSTER" --service-name "$SERVICE" --query 'taskArns[0]' --output text)
TASK_IP=$(aws ecs describe-tasks --region $REGION --cluster "$CLUSTER" --tasks "$TASK" \
  --query 'tasks[0].containers[?name==`i-dot-ai-dev-minute-temporal-container`].networkInterfaces[0].privateIpv4Address | [0]' --output text)
RUNTIME=$(aws ecs describe-tasks --region $REGION --cluster "$CLUSTER" --tasks "$TASK" \
  --query 'tasks[0].containers[?name==`i-dot-ai-dev-minute-temporal-container`].runtimeId | [0]' --output text)

TARGET="ecs:${CLUSTER}_${TASK##*/}_${RUNTIME}"

aws ssm start-session --region $REGION --target "$TARGET" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$TASK_IP\"],\"portNumber\":[\"7233\"],\"localPortNumber\":[\"7233\"]}"
```

Leave that running ("Waiting for connections…"), then:

```bash
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
