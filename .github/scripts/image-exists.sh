#!/bin/bash
# Only an absent image permits a build; failed lookups must not overwrite release artifacts.
set -euo pipefail

if result=$(aws ecr describe-images \
  --repository-name "$ECR_REPOSITORY" \
  --image-ids "imageTag=$IMAGE_TAG" \
  --query 'imageDetails[0].imageDigest' --output text 2>&1); then
  if [[ ! "$result" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    printf 'Unexpected ECR response: %s\n' "$result" >&2
    exit 1
  fi
  echo 'exists=true' >> "$GITHUB_OUTPUT"
  printf 'Reusing %s:%s\n' "$ECR_REPOSITORY" "$IMAGE_TAG"
elif [[ "$result" == *'(ImageNotFoundException)'* ]]; then
  echo 'exists=false' >> "$GITHUB_OUTPUT"
else
  printf '%s\n' "$result" >&2
  exit 1
fi
