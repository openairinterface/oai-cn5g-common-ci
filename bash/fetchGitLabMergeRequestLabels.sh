#!/bin/bash


#/*
# * Licensed to the OpenAirInterface (OAI) Software Alliance under one or more
# * contributor license agreements.  See the NOTICE file distributed with
# * this work for additional information regarding copyright ownership.
# * The OpenAirInterface Software Alliance licenses this file to You under
# * the OAI Public License, Version 1.1  (the "License"); you may not use this file
# * except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.openairinterface.org/?page_id=698
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# *-------------------------------------------------------------------------------
# * For more information about the OpenAirInterface (OAI) Software Alliance:
# *      contact@openairinterface.org
# */


# Usage: ./fetchGitLabMergeRequestLabels.sh --network_function <NF_NAME> --merge_id <MR_ID>

# --- Configuration ---
GITLAB_URL="https://gitlab.eurecom.fr"
NETWORK_FUNCTION=""
MERGE_REQUEST_ID=""
PROJECT_PATH=""

# --- Usage Function ---
usage() {
    echo "OAI Core Network"
    echo "Usage: $0 --network_function <NF_NAME> --merge_id <MR_ID>"
    echo "       $0 -h | --help"
    echo ""
    echo "Required Arguments:"
    echo "  --network_function <NF_NAME>  The name of the OAI network function (e.g., 'lmf', 'amf')."
    echo "  --merge_id <MR_ID>            The Internal ID (IID) of the GitLab Merge Request."
    echo ""
    echo "Help option"
    echo "  -h | --help        Display this help message and exit."
    echo ""
    echo "Example:"
    echo "  $0 --network_function lmf --merge_id 100"
    echo ""
}

# --- Argument Parsing ---
# Check for --help
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 0
fi

if [ $# -lt 4 ]; then
    echo "Error: Missing arguments or incorrect format." >&2
    usage
    exit 1
fi

while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    --network_function)
    NETWORK_FUNCTION="$2"
    shift
    shift
    ;;
    --merge_id)
    MERGE_REQUEST_ID="$2"
    shift
    shift
    ;;
    -h|--help)
    usage
    exit 0
    ;;
    *)
    echo "Syntax Error: unknown option: $key" >&2
    usage
    exit 1
esac
done

if [ -z "$NETWORK_FUNCTION" ] || [ -z "$MERGE_REQUEST_ID" ]; then
    echo "Error: Both network function and merge ID must be specified." >&2
    usage
    exit 1
fi

# The GitLab path format is oai/cn5g/oai-cn5g-<NF_NAME> (e.g., oai-cn5g-lmf)
PROJECT_PATH="oai%2Fcn5g%2Foai-cn5g-${NETWORK_FUNCTION}"

# --- Fetch Labels ---
LABELS=$(curl --silent "${GITLAB_URL}/api/v4/projects/${PROJECT_PATH}/merge_requests/${MERGE_REQUEST_ID}" | jq '.labels' || echo "[]")

# --- Check Labels using grep -c ---
IS_MR_CI=$(echo "$LABELS" | grep -c "CI")
IS_MR_BUILD_ONLY=$(echo "$LABELS" | grep -c "BUILD_ONLY")
IS_MR_DOCUMENTATION=$(echo "$LABELS" | grep -ic "documentation")

# --- Determine Pipeline Type ---

# 1. Full CI
if [ "$IS_MR_CI" -ge 1 ]; then
    echo "CI"
    exit 0
fi

# 2. Build Only
if [ "$IS_MR_BUILD_ONLY" -ge 1 ]; then
    echo "BUILD_ONLY"
    exit 0
fi

# 3. Documentation Only
if [ "$IS_MR_DOCUMENTATION" -ge 1 ]; then
    echo "documentation"
    exit 0
fi

# 4. Default: NONE
echo "NONE"
exit 0
