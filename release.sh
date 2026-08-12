#!/bin/bash
# Usage:
## Just pass the name of the env we want to tag and deploy.
## This will create a tag locally with a format of $ENV-$BRANCH-$CURRENT_USER-$TIMESTAMP
## Then push it to the remote git.
set -euo pipefail

ENV=${1:-}
BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_USER=$(whoami)
TIMESTAMP=$(date +%d-%m-%y--%H%M%S)
TAG_NAME="release-$ENV-$BRANCH-$CURRENT_USER-$TIMESTAMP"

if [ "$ENV" == 'prod' ]; then
    echo -e "\033[0;31mYou can only deploy to prod through a merge into main.\033[0m"
    exit 1
fi

# Only these produce a tag that .github/workflows/release.yml matches
# (release-dev-** / release-preprod-**). Any other value pushes a tag that no
# workflow is listening for, so the release silently does nothing.
if [ "$ENV" != 'dev' ] && [ "$ENV" != 'preprod' ]; then
    echo -e "\033[0;31mInvalid environment: '$ENV'\033[0m"
    echo "Usage: ./release.sh <dev|preprod>   (or: make release env=dev)"
    exit 1
fi

echo "Current branch name is" "$BRANCH"
echo "Current environment name is" "$ENV"
echo "Timestamp assigned will be $TIMESTAMP"
echo "New tag name will be " "$TAG_NAME"

# tag.gpgsign=true is forced off here: a signed tag is an annotated tag, and on an
# annotated-tag push GitHub sets github.sha to the tag object rather than the commit.
# release.yml feeds that straight into IMAGE_TAG, so terraform would then look for an
# ECR image tagged with a sha that build-push never built.
echo "Applying local tag"
git -c tag.gpgsign=false tag "$TAG_NAME"

echo "Pushing tag"
git push origin "$TAG_NAME"
