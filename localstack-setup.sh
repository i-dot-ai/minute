#!/bin/sh
echo "Initializing localstack"

apt install jq -y



QUEUE_URL=$(awslocal sqs create-queue --queue-name $QUEUE_NAME| jq -r '.QueueUrl')
DEADLETTER_QUEUE_URL=$(awslocal sqs create-queue --queue-name $DEADLETTER_QUEUE_NAME | jq -r '.QueueUrl')

echo "Main queue URL: $QUEUE_URL"
echo "Dead letter queue URL: $DEADLETTER_QUEUE_URL"

echo "Purging $QUEUE_URL"
awslocal sqs purge-queue --queue-url $QUEUE_URL
# Extract the dead letter queue ARN from the URL
# LocalStack URL format: http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/queue-name
# ARN format: arn:aws:sqs:us-east-1:000000000000:queue-name
DEADLETTER_ARN="arn:aws:sqs:${AWS_DEFAULT_REGION}:000000000000:$DEADLETTER_QUEUE_NAME"


echo "Dead letter queue ARN: $DEADLETTER_ARN"

awslocal sqs set-queue-attributes \
--queue-url $QUEUE_URL \
--attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$DEADLETTER_ARN\\\",\\\"maxReceiveCount\\\":\\\"4\\\"}\"
}"
