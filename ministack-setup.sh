#!/bin/sh
echo "Initializing ministack"

if [ -f /ready.txt ]; then
  rm /ready.txt
fi

# AWS credentials, endpoint, region and the queue/bucket names all come from the dev
# .env, mounted into this container via env_file. The bundled `aws` CLI is the plain
# one (not `awslocal`), so point it at the endpoint and parse output with
# --query/--output to avoid depending on jq.
AWS="aws --endpoint-url $AWS_ENDPOINT_URL"

################################
## WORKER QUEUE
################################

WORKER_QUEUE_URL=$($AWS sqs create-queue --queue-name "$WORKER_QUEUE_NAME" --query QueueUrl --output text)
WORKER_DEADLETTER_QUEUE_URL=$($AWS sqs create-queue --queue-name "$WORKER_DEADLETTER_QUEUE_NAME" --query QueueUrl --output text)
echo "Worker queue URL: $WORKER_QUEUE_URL"
echo "Dead letter queue URL: $WORKER_DEADLETTER_QUEUE_URL"

echo "Purging $WORKER_QUEUE_URL"
$AWS sqs purge-queue --queue-url "$WORKER_QUEUE_URL"

# Derive the dead-letter ARN from the created queue rather than hardcoding the
# account id, so the redrive policy points at the real queue.
WORKER_DEADLETTER_ARN=$($AWS sqs get-queue-attributes \
  --queue-url "$WORKER_DEADLETTER_QUEUE_URL" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

echo "Dead letter queue ARN: $WORKER_DEADLETTER_ARN"

$AWS sqs set-queue-attributes \
--queue-url "$WORKER_QUEUE_URL" \
--attributes "{
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$WORKER_DEADLETTER_ARN\\\",\\\"maxReceiveCount\\\":\\\"10\\\"}\"
}"

##############################
## DATA BUCKET
##############################

# Mirrors the real bucket in terraform/s3.tf so local dev and the e2e tests never
# touch dev AWS. create-bucket is not idempotent, so tolerate an existing bucket.
echo "Creating S3 bucket $DATA_S3_BUCKET"
$AWS s3api create-bucket \
  --bucket "$DATA_S3_BUCKET" \
  --create-bucket-configuration "LocationConstraint=$AWS_DEFAULT_REGION" \
  >/dev/null 2>&1 || echo "Bucket $DATA_S3_BUCKET already exists"

# The browser PUTs straight to a presigned URL, so the local bucket needs CORS
# rules like the real one. Origins are wide open here — local only.
$AWS s3api put-bucket-cors --bucket "$DATA_S3_BUCKET" --cors-configuration '{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["PUT", "GET", "POST"],
      "AllowedOrigins": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}'

echo "S3 bucket ready: $DATA_S3_BUCKET"

# docker-compose healthcheck waits for this file
touch "/ready.txt"
