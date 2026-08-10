#!/bin/bash
# SPDX-License-Identifier: MIT

function usage {
    echo "OAI GitHub PR validation script (Signed-off-by, commit signature and merge commits)"
    echo ""
    echo "Usage:"
    echo "------"
    echo "    $0 -s <source-branch> -t <target-branch> -r <owner/repo> -p <pull-request-number>"
    echo ""
    echo "Options:"
    echo "--------"
    echo "    -s"
    echo "    The source branch of the pull request. Default value is current Git Branch (HEAD)"
    echo ""
    echo "    -t"
    echo "    The target branch of the pull request. Default value is develop"
    echo ""
    echo "    -r"
    echo "    The repository in owner/repo form, used to verify commit signatures"
    echo "    through the GitHub API. Without it the signature check is skipped."
    echo ""
    echo "    -p"
    echo "    The pull request number, used to verify commit signatures through the"
    echo "    GitHub API. Defaults to \$GITHUB_PR_NUMBER when the pipeline exports"
    echo "    it. Without it the signature check is skipped."
    echo ""
    echo "    -h"
    echo "    Print this help message."
    echo ""
}

# Parse arguments properly
SOURCE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
TARGET_BRANCH="origin/develop"
GITHUB_REPO=""
# The pipeline exports GITHUB_PR_NUMBER, so -p is optional there.
PR_NUMBER="${GITHUB_PR_NUMBER:-}"

while getopts ":s:t:r:p:h" opt; do
    case "$opt" in
        s)
            SOURCE_BRANCH="$OPTARG"
            ;;
        t)
            TARGET_BRANCH="$OPTARG"
            ;;
        r)
            GITHUB_REPO="$OPTARG"
            ;;
        p)
            PR_NUMBER="$OPTARG"
            ;;
        h)
            usage
            exit 0
            ;;
        :)
            echo "Error: Option -$OPTARG requires a value."
            echo ""
            usage
            exit 2
            ;;
        \?)
            echo "Error: Invalid option -$OPTARG"
            echo ""
            usage
            exit 2
            ;;
    esac
done

# ----------------------------
# Merged commits
# ----------------------------
if [[ "$SOURCE_BRANCH" =~ ^[0-9a-f]{40}$ ]]; then
  # note: if no branch could be found, it will result in "" and git rev-list
  # will use the commit ID. Exclude "HEAD detached at", then use first branch
  # name.
  BRANCH_NAME=$(git branch -a --points-at $SOURCE_BRANCH --format='%(refname:short)' | grep -v detached | head -n1)
  echo "SHA recognized in $SOURCE_BRANCH, using \"$BRANCH_NAME\" as branch name"
else
  BRANCH_NAME="$SOURCE_BRANCH"
fi
mergeCommits=$(git rev-list --merges --abbrev-commit "$TARGET_BRANCH".."$SOURCE_BRANCH")
    if [[ -n "$mergeCommits" ]]; then
        message="Error: Following merge commits are found in the source branch history. Please rebase your branch.\n\n"
        message+="$(echo "$mergeCommits" | paste -sd ',' | sed 's/,/, /g')\n"
        echo -e "$message"
        exit 3
    fi

# ----------------------------
# Check commits missing Signed-off-by
# ----------------------------
unsignedCommits=$(
    for c in $(git rev-list "$TARGET_BRANCH".."$SOURCE_BRANCH" --no-merges); do
        if ! git log -1 --format=%B "$c" | grep -q "Signed-off-by:"; then
            git log -1 --format='%h' "$c"
        fi
    done | paste -sd ',' | sed 's/,/, /g'
)

# ----------------------------
# Check commits missing a verified signature
# ----------------------------
# GitHub holds every contributor's public key, so it can tell a valid signature
# from an unverifiable one. Only the 'verified' boolean is read, so GPG, SSH and
# S/MIME signatures are all accepted -- whatever GitHub marks as verified passes.
# The endpoint is public, no token needed.
#
# Every case that cannot check sets signatureCheckSkipped: an empty
# unverifiedCommits would read as "all signed".

unverifiedCommits=""
signatureCheckSkipped=""

if [ -z "$PR_NUMBER" ]; then
    signatureCheckSkipped="No pull request number given (-p), commit signatures were not checked."
elif [ -z "$GITHUB_REPO" ]; then
    signatureCheckSkipped="No repository given (-r <owner>/<repo>), commit signatures were not checked."
else
    apiResponse=$(mktemp)
    httpCode=$(curl -sS -m 20 -o "$apiResponse" -w '%{http_code}' \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${GITHUB_REPO}/pulls/${PR_NUMBER}/commits?per_page=100")
    if [ "$httpCode" != "200" ]; then
        signatureCheckSkipped="Could not reach the GitHub API (HTTP $httpCode), commit signatures were not checked."
    # jq exits non-zero when missing, or when the answer is not a commit array.
    elif ! unverifiedCommits=$(jq -r '[.[] | select(.commit.verification.verified == false) | .sha[:7]] | join(", ")' "$apiResponse" 2>/dev/null); then
        signatureCheckSkipped="Unexpected answer from the GitHub API, commit signatures were not checked."
    fi
    rm -f "$apiResponse"
fi

# ----------------------------
# Report
# ----------------------------
# Signed checks - exit 1. Merge commits - exit 3
#
# Printed first, so it shows when the Signed-off-by check fails too.
[ -n "$signatureCheckSkipped" ] && echo -e "$signatureCheckSkipped\n"

message=""

if [ -n "$unsignedCommits" ]; then
    message+="The following commit(s) are missing a Signed-off-by:\n\n$unsignedCommits\n\n"
    message+="Please use 'git commit -s' or 'git commit --signoff' to sign your commits.\n\n"
fi

if [ -n "$unverifiedCommits" ]; then
    message+="The following commit(s) are missing a verified signature:\n\n$unverifiedCommits\n\n"
    message+="Please use 'git commit -S' to sign your commits, with either a GPG or an SSH\n"
    message+="key, and make sure the matching public key is added to your GitHub account.\n\n"
fi

if [ -n "$message" ]; then
    message+="For detailed instructions, refer to the CONTRIBUTING file at the root of this repository."
    echo -e "$message"
    exit 1
fi

if [ -n "$signatureCheckSkipped" ]; then
    echo "All commits are signed off using 'git commit -s'."
else
    echo "All commits are signed off using 'git commit -s' and carry a verified signature."
fi
exit 0
