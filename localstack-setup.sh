#!/bin/sh
echo "Initializing localstack"

if [ -f /ready.txt ]; then
  rm /ready.txt
fi

apt install jq -y

################################
## TRANSCRIPTION QUEUE
################################

TRANSCRIPTION_QUEUE_URL=$(awslocal sqs create-queue --queue-name $TRANSCRIPTION_QUEUE_NAME| jq -r '.QueueUrl')
TRANSCRIPTION_DEADLETTER_QUEUE_URL=$(awslocal sqs create-queue --queue-name $TRANSCRIPTION_DEADLETTER_QUEUE_NAME | jq -r '.QueueUrl')
echo "Main queue URL: $TRANSCRIPTION_QUEUE_URL"
echo "Dead letter queue URL: $TRANSCRIPTION_DEADLETTER_QUEUE_URL"

echo "Purging $TRANSCRIPTION_QUEUE_URL"
awslocal sqs purge-queue --queue-url $TRANSCRIPTION_QUEUE_URL
# Extract the dead letter queue ARN from the URL
# LocalStack URL format: http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/queue-name
# ARN format: arn:aws:sqs:us-east-1:000000000000:queue-name
TRANSCRIPTION_DEADLETTER_ARN="arn:aws:sqs:${AWS_DEFAULT_REGION}:000000000000:$DEADLETTER_QUEUE_NAME"


echo "Dead letter queue ARN: $TRANSCRIPTION_DEADLETTER_ARN"

awslocal sqs set-queue-attributes \
--queue-url $TRANSCRIPTION_QUEUE_URL \
--attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$TRANSCRIPTION_DEADLETTER_ARN\\\",\\\"maxReceiveCount\\\":\\\"4\\\"}\"
}"

##############################
## LLM QUEUE
##############################

LLM_QUEUE_URL=$(awslocal sqs create-queue --queue-name $LLM_QUEUE_NAME| jq -r '.QueueUrl')
LLM_DEADLETTER_QUEUE_URL=$(awslocal sqs create-queue --queue-name $LLM_DEADLETTER_QUEUE_NAME | jq -r '.QueueUrl')

echo "LLM queue URL: $LLM_QUEUE_URL"
echo "LLM Dead letter queue URL: $LLM_DEADLETTER_QUEUE_URL"

echo "Purging $LLM_QUEUE_URL"
awslocal sqs purge-queue --queue-url $LLM_QUEUE_URL
# Extract the dead letter queue ARN from the URL
# LocalStack URL format: http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/queue-name
# ARN format: arn:aws:sqs:us-east-1:000000000000:queue-name
LLM_DEADLETTER_ARN="arn:aws:sqs:${AWS_DEFAULT_REGION}:000000000000:$DEADLETTER_QUEUE_NAME"

echo "LLM Dead letter queue ARN: $LLM_DEADLETTER_ARN"

awslocal sqs set-queue-attributes \
--queue-url $LLM_QUEUE_URL \
--attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$LLM_DEADLETTER_ARN\\\",\\\"maxReceiveCount\\\":\\\"4\\\"}\"
}"

# docker-compose healthcheck waits for this file
touch "/ready.txt"