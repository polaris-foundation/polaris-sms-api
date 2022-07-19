#!/usr/bin/env bash

set -eu

help (){
    echo "Usage: $0 cc k8s"
    echo " cc - country code (e.g. uk, us)"
    echo " k8s - Kubernetes cluster (e.g uk-dev-api-upstream, us-dev-upstream-api001)"
}

check_options(){
  if [[ -z "$1" ]]; then
    echo "==== Please supply $2 to deploy ===="
    help
    exit 2
  fi
}

check_options "${1+x}" "country code"
check_options "${2+x}" "k8s cluster"

CC="$1"
K8S_CLUSTER="$2"
[[ "${CC}" == "uk" ]] && ENV="dev" || ENV="usdev"

RELEASE_CONFIG="${CIRCLE_PROJECT_REPONAME}.yaml"
RELEASE_CONFIG_BRANCH="master"
GIT_REPO="https://api.github.com/repos/draysontechnologies/devops-release-config/contents/${K8S_CLUSTER}/${RELEASE_CONFIG}?ref=${RELEASE_CONFIG_BRANCH}"
CD_ARTIFACT=$(base64 -w 0 <(eval "echo \"$(<.circleci/${CIRCLE_PROJECT_REPONAME}.tml)\""))
COMMIT_SHA=$(curl -H "Authorization: token ${GIT_PAT}" \
                  -H "X-OAuth-Scopes: repo, user" \
                  -H "X-Accepted-OAuth-Scopes: user" \
                  -H "Accept: application/vnd.github.v3+json" \
                  "${GIT_REPO}" | jq -r .sha)
COMMIT_DATA=$(cat <<EOF
{
  "path": "${K8S_CLUSTER}/${RELEASE_CONFIG}",
  "message": "Release artifact for ${CIRCLE_PROJECT_REPONAME}",
  "content": "${CD_ARTIFACT}",
  "branch": "${RELEASE_CONFIG_BRANCH}",
  "sha": "${COMMIT_SHA}"
}
EOF
)
RESPONSE_FILE=/tmp/upload.txt
STATUS_CODE=$(curl -i -X PUT -w '%{http_code}' -o ${RESPONSE_FILE} \
                -H "Authorization: token ${GIT_PAT}" \
                -H "X-OAuth-Scopes: repo, user" \
                -H "X-Accepted-OAuth-Scopes: user" \
                -H "Accept: application/vnd.github.v3+json" \
                -d "${COMMIT_DATA}" \
                "${GIT_REPO}")

# Display response
tail ${RESPONSE_FILE}

# Fail job on unexpected status code.
if [[ ${STATUS_CODE} -gt 299 ]]; then
    echo "Unexpected HTTP response status code ${STATUS_CODE}"
    exit 1
fi
