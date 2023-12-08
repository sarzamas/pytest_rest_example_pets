#!/usr/bin/env bash

# Delete all logs for a given workflow
# Usage: delete-logs.sh <repository> <workflow-name>

set -oe pipefail

REPOSITORY=$1
WORKFLOW_NAME=$2

# Validate arguments
if [[ -z "$REPOSITORY" ]]; then
  echo ":octocat: Repository name is required"
  exit 1
fi

if [[ -z "$WORKFLOW_NAME" ]]; then
  echo ":octocat: Workflow name is required"
  exit 1
fi

echo ":octocat: Getting all completed runs for workflow '$WORKFLOW_NAME' in $REPOSITORY..."

RUNS=$(
  gh api \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$REPOSITORY/actions/workflows/$WORKFLOW_NAME/runs" \
    --paginate \
    --jq '.workflow_runs[] | select(.conclusion != "") | .id'
)

echo ":octocat: Found $(echo "$RUNS" | wc -l) completed runs for workflow '$WORKFLOW_NAME' - ✅OK!"
echo "$RUNS"

# Delete logs for each run
for RUN in $RUNS; do
  echo ":octocat: Deleting logs for run $RUN..."
  gh api \
    --silent \
    --method DELETE \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$REPOSITORY/actions/runs/$RUN/logs" \
  && \
  echo " - Successfully deleted all logs for run $RUN - ✅OK!" || echo " - Failed to delete logs for run $RUN - ❌NOK!"


gh api \
  --method GET \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/octocat"

  # Sleep for 100ms to avoid rate limiting
  sleep 0.1
done
