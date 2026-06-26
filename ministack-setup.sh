#!/bin/sh
echo "Initializing ministack"

if [ -f /ready.txt ]; then
  rm /ready.txt
fi

# MiniStack injects AWS_ENDPOINT_URL into init scripts; default it for safety.
# It bundles the plain `aws` CLI (not `awslocal`), so we point the CLI at the
# local endpoint explicitly and parse output with --query/--output to avoid
# depending on jq.
AWS_ENDPOINT_URL="${AWS_ENDPOINT_URL:-http://localhost:4566}"

# The dev .env is loaded into this container (env_file) and may inject real,
# often expired, AWS credentials. MiniStack does not validate credentials, so
# clear any expired session and use dummy creds — otherwise the AWS CLI rejects
# the env credentials with "refreshed credentials are still expired".
unset AWS_SESSION_TOKEN AWS_CREDENTIAL_EXPIRATION
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-west-2}"

AWS="aws --endpoint-url $AWS_ENDPOINT_URL"

################################
## TRANSCRIPTION QUEUE
################################

TRANSCRIPTION_QUEUE_URL=$($AWS sqs create-queue --queue-name "$TRANSCRIPTION_QUEUE_NAME" --query QueueUrl --output text)
TRANSCRIPTION_DEADLETTER_QUEUE_URL=$($AWS sqs create-queue --queue-name "$TRANSCRIPTION_DEADLETTER_QUEUE_NAME" --query QueueUrl --output text)
echo "Main queue URL: $TRANSCRIPTION_QUEUE_URL"
echo "Dead letter queue URL: $TRANSCRIPTION_DEADLETTER_QUEUE_URL"

echo "Purging $TRANSCRIPTION_QUEUE_URL"
$AWS sqs purge-queue --queue-url "$TRANSCRIPTION_QUEUE_URL"

# Derive the dead-letter ARN from the created queue rather than hardcoding the
# account id, so the redrive policy points at the real queue.
TRANSCRIPTION_DEADLETTER_ARN=$($AWS sqs get-queue-attributes \
  --queue-url "$TRANSCRIPTION_DEADLETTER_QUEUE_URL" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

echo "Dead letter queue ARN: $TRANSCRIPTION_DEADLETTER_ARN"

$AWS sqs set-queue-attributes \
--queue-url "$TRANSCRIPTION_QUEUE_URL" \
--attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$TRANSCRIPTION_DEADLETTER_ARN\\\",\\\"maxReceiveCount\\\":\\\"4\\\"}\"
}"

##############################
## LLM QUEUE
##############################

LLM_QUEUE_URL=$($AWS sqs create-queue --queue-name "$LLM_QUEUE_NAME" --query QueueUrl --output text)
LLM_DEADLETTER_QUEUE_URL=$($AWS sqs create-queue --queue-name "$LLM_DEADLETTER_QUEUE_NAME" --query QueueUrl --output text)

echo "LLM queue URL: $LLM_QUEUE_URL"
echo "LLM Dead letter queue URL: $LLM_DEADLETTER_QUEUE_URL"

echo "Purging $LLM_QUEUE_URL"
$AWS sqs purge-queue --queue-url "$LLM_QUEUE_URL"

# Derive the dead-letter ARN from the created queue rather than hardcoding the
# account id, so the redrive policy points at the real queue.
LLM_DEADLETTER_ARN=$($AWS sqs get-queue-attributes \
  --queue-url "$LLM_DEADLETTER_QUEUE_URL" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

echo "LLM Dead letter queue ARN: $LLM_DEADLETTER_ARN"

$AWS sqs set-queue-attributes \
--queue-url "$LLM_QUEUE_URL" \
--attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$LLM_DEADLETTER_ARN\\\",\\\"maxReceiveCount\\\":\\\"4\\\"}\"
}"

# docker-compose healthcheck waits for this file
touch "/ready.txt"
