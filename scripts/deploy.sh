#!/usr/bin/env bash
# Asks the host to run one commit's images. usage: deploy.sh SHA
# Needs API_IMAGE, FRONTEND_IMAGE, API_HOOK and FRONTEND_HOOK in the environment.
set -euo pipefail

sha=$1
for pair in "$API_IMAGE $API_HOOK" "$FRONTEND_IMAGE $FRONTEND_HOOK"; do
  read -r image hook <<< "$pair"
  curl --fail --silent --show-error --get --output /dev/null \
    --data-urlencode "imgURL=$image:$sha" "$hook"
done
echo "Deploy of $sha requested"
