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
## DATA BUCKET
################################

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
