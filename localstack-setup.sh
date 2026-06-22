#!/bin/sh
set -eu

echo "Initializing localstack"

if [ -f /ready.txt ]; then
  rm /ready.txt
fi

# LocalStack doesn't need real AWS credentials. Clear any expired session
# tokens that may have been inherited from the host environment.
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-west-2}"
unset AWS_SESSION_TOKEN AWS_PROFILE AWS_DEFAULT_PROFILE

ENDPOINT="http://localhost:4566"

create_queue_url() {
  aws --endpoint-url="$ENDPOINT" sqs create-queue \
    --queue-name "$1" \
    --output text \
    --query 'QueueUrl'
}

################################
## TRANSCRIPTION QUEUE
################################

TRANSCRIPTION_QUEUE_URL=$(create_queue_url "$TRANSCRIPTION_QUEUE_NAME")
TRANSCRIPTION_DEADLETTER_QUEUE_URL=$(create_queue_url "$TRANSCRIPTION_DEADLETTER_QUEUE_NAME")
echo "Main queue URL: $TRANSCRIPTION_QUEUE_URL"
echo "Dead letter queue URL: $TRANSCRIPTION_DEADLETTER_QUEUE_URL"

echo "Purging $TRANSCRIPTION_QUEUE_URL"
aws --endpoint-url="$ENDPOINT" sqs purge-queue --queue-url "$TRANSCRIPTION_QUEUE_URL"

TRANSCRIPTION_DEADLETTER_ARN="arn:aws:sqs:${AWS_DEFAULT_REGION}:000000000000:${TRANSCRIPTION_DEADLETTER_QUEUE_NAME}"

echo "Dead letter queue ARN: $TRANSCRIPTION_DEADLETTER_ARN"

aws --endpoint-url="$ENDPOINT" sqs set-queue-attributes \
  --queue-url "$TRANSCRIPTION_QUEUE_URL" \
  --attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$TRANSCRIPTION_DEADLETTER_ARN\\\",\\\"maxReceiveCount\\\":\\\"4\\\"}\"
}"

##############################
## LLM QUEUE
##############################

LLM_QUEUE_URL=$(create_queue_url "$LLM_QUEUE_NAME")
LLM_DEADLETTER_QUEUE_URL=$(create_queue_url "$LLM_DEADLETTER_QUEUE_NAME")

echo "LLM queue URL: $LLM_QUEUE_URL"
echo "LLM Dead letter queue URL: $LLM_DEADLETTER_QUEUE_URL"

echo "Purging $LLM_QUEUE_URL"
aws --endpoint-url="$ENDPOINT" sqs purge-queue --queue-url "$LLM_QUEUE_URL"

LLM_DEADLETTER_ARN="arn:aws:sqs:${AWS_DEFAULT_REGION}:000000000000:${LLM_DEADLETTER_QUEUE_NAME}"

echo "LLM Dead letter queue ARN: $LLM_DEADLETTER_ARN"

aws --endpoint-url="$ENDPOINT" sqs set-queue-attributes \
  --queue-url "$LLM_QUEUE_URL" \
  --attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$LLM_DEADLETTER_ARN\\\",\\\"maxReceiveCount\\\":\\\"4\\\"}\"
}"

# docker-compose healthcheck waits for this file
touch "/ready.txt"
