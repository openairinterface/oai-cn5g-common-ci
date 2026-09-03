#!/bin/bash
# SPDX-License-Identifier: MIT
#
# Formats C/C++ sources with the clang-format major version the CI uses,
# on the file list produced by checkCodingFormattingRules.sh.

set -euo pipefail

# Paths, relative to the repository root.
CHECKER="ci-scripts/common/bash/checkCodingFormattingRules.sh"
CI_DOCKERFILE="ci-scripts/common/docker/Dockerfile.ci.clang-format"
RESULT="src/oai_rules_result.txt"
RESULT_LIST="src/oai_rules_result_list.txt"

IMAGE_REPO="oai-clang-format"

# Options.
DRY_RUN=0
SHOW_VERSION=0
BRANCH_MODE=0
SOURCE_BRANCH="HEAD"
TARGET_BRANCH="develop"

# Discovered at run time.
ROOT=""
MAJOR=""
BASE_IMAGE=""
CONFIG_KEY=""
CF_LOCAL=""
CF_VERSION=""
IMAGE=""
LOCAL_BLOCKER=""
NB_TOTAL=0
SOURCES=()

# Prints the help text.
function usage {
    echo "OAI Code Formatting script"
    echo ""
    echo "  Formats C/C++ source files using the same clang-format major version"
    echo "  and file selection used by CI."
    echo ""
    echo "  The clang-format major version and base image are read from the CI"
    echo "  Dockerfile. A local clang-format of that major version is used when"
    echo "  available; otherwise, the formatter runs from a reusable Docker image."
    echo ""
    echo "  The list of files to format comes from checkCodingFormattingRules.sh,"
    echo "  so this script changes exactly what CI would reject."
    echo ""
    echo "  By default, the entire repository is formatted. Use --diff to"
    echo "  restrict the work to the branch-aware file set."
    echo ""
    echo "Usage:"
    echo "  format-code.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -n, --dry-run, --check"
    echo "      Check formatting without modifying files."
    echo "      Exits 1 if formatting is required, 0 otherwise."
    echo ""
    echo "      --diff"
    echo "      Limit the checker to the branch-aware file set used by CI,"
    echo "      instead of the whole repository."
    echo "      Defaults to HEAD versus origin/develop; override with the"
    echo "      two options below. Passing either of those implies --diff."
    echo ""
    echo "  -s, --source-branch BRANCH"
    echo "      Source branch of the change. Default: HEAD. Implies --diff."
    echo ""
    echo "  -t, --target-branch BRANCH"
    echo "      Target branch of the change, as a bare name such as 'develop':"
    echo "      the checker prefixes it with origin/ itself, so passing"
    echo "      'origin/develop' would look up 'origin/origin/develop' and"
    echo "      fail. Default: develop. Implies --diff."
    echo ""
    echo "  -v, --version"
    echo "      Print the clang-format version that will be used."
    echo "      Never builds the Docker image."
    echo ""
    echo "  -h, --help"
    echo "      Show this help message."
    echo ""
    echo "Examples:"
    echo "  format-code.sh"
    echo "      Format the entire repository."
    echo ""
    echo "  format-code.sh --dry-run"
    echo "      Check the entire repository without modifying files."
    echo ""
    echo "  format-code.sh --diff"
    echo "      Format the files changed between HEAD and origin/develop."
    echo ""
    echo "  format-code.sh --diff -s feature -t develop"
    echo "      Format the files changed by the feature branch."
    echo ""
    echo "  format-code.sh --dry-run --diff -s feature -t develop"
    echo "      Check the files changed by the feature branch."
    echo ""
    echo "Notes:"
    echo "  --diff limits the checker to the branch-aware file set used by CI."
    echo "  It does not necessarily mean only files modified by the current"
    echo "  branch, because CI also checks common-src. It is therefore not"
    echo "  equivalent to 'git diff --name-only'."
    echo ""
    echo "  CI may report formatting violations in files that were not modified"
    echo "  by the current branch, particularly after a clang-format version"
    echo "  update. Run the full-repository formatter (no --diff) when changing"
    echo "  formatter versions, or when CI reports formatting failures outside"
    echo "  your changes."
    echo ""
}

# Prints each argument on stderr and exits.
#   $1    exit code
#   $2..  message lines
function error_exit {
    local code="$1"
    shift
    local line
    for line in "$@"
    do
        echo "$line" >&2
    done
    exit "$code"
}

# Prints a usage error on stderr and exits 2.
#   $1  message
function usage_error {
    echo "Error: $1" >&2
    echo "" >&2
    usage >&2
    exit 2
}

# Rejects an option value that is missing or looks like another option.
#   $1  option as the user wrote it
#   $2  candidate value
function need_value {
    if [ -z "$2" ] || [ "${2:0:1}" = "-" ]
    then
        usage_error "Option $1 requires a value."
    fi
}

# Parses the command line.
#   $@     the script arguments
#   sets   DRY_RUN, SHOW_VERSION, BRANCH_MODE, SOURCE_BRANCH, TARGET_BRANCH
#
# getopts handles the short forms; the "-:" entry lets the same loop accept
# the long forms, so there is one parser rather than two.
function parse_args {
    local opt
    while getopts ":s:t:nvh-:" opt
    do
        case "$opt" in
            -)
                case "$OPTARG" in
                    source-branch)
                        need_value "--source-branch" "${!OPTIND:-}"
                        SOURCE_BRANCH="${!OPTIND}"; OPTIND=$((OPTIND + 1)); BRANCH_MODE=1
                        ;;
                    source-branch=*)
                        need_value "--source-branch" "${OPTARG#*=}"
                        SOURCE_BRANCH="${OPTARG#*=}"; BRANCH_MODE=1
                        ;;
                    target-branch)
                        need_value "--target-branch" "${!OPTIND:-}"
                        TARGET_BRANCH="${!OPTIND}"; OPTIND=$((OPTIND + 1)); BRANCH_MODE=1
                        ;;
                    target-branch=*)
                        need_value "--target-branch" "${OPTARG#*=}"
                        TARGET_BRANCH="${OPTARG#*=}"; BRANCH_MODE=1
                        ;;
                    diff)          BRANCH_MODE=1 ;;
                    dry-run|check) DRY_RUN=1 ;;
                    version)       SHOW_VERSION=1 ;;
                    help)          usage; exit 0 ;;
                    *)             usage_error "Invalid option --$OPTARG" ;;
                esac
                ;;
            s) SOURCE_BRANCH="$OPTARG"; BRANCH_MODE=1 ;;
            t) TARGET_BRANCH="$OPTARG"; BRANCH_MODE=1 ;;
            n) DRY_RUN=1 ;;
            v) SHOW_VERSION=1 ;;
            h) usage; exit 0 ;;
            :) usage_error "Option -$OPTARG requires a value." ;;
            \?) usage_error "Invalid option -$OPTARG" ;;
        esac
    done
    shift $((OPTIND - 1))
    if (( $# != 0 ))
    then
        usage_error "unexpected argument: $1"
    fi
}

# Moves to the repository root, which is also where every path above is
# resolved from. This call is what proves git is installed.
#   sets  ROOT
function enter_repo_root {
    ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=""
    [ -n "$ROOT" ] || error_exit 1 "ERROR: not inside a git repository"
    cd "$ROOT" || error_exit 1 "ERROR: cannot enter $ROOT"

    local f
    for f in "$CHECKER" "$CI_DOCKERFILE"
    do
        [ -f "$f" ] || error_exit 1 "ERROR: cannot find $f"
    done
}

# Reads the clang-format major version and base image out of the CI Dockerfile,
# so the CI remains the single place where the toolchain is defined.
# Comment lines are skipped: a note such as "# bumped from clang-format-12"
# would otherwise be picked up ahead of the real package.
#
# CONFIG_KEY is a digest of exactly the two values the fallback image is built
# from. It becomes part of the image tag, so changing either one selects a
# different tag and the stale image is never reused. It deliberately does not
# digest the whole Dockerfile: edits to the comments or to the checker
# invocation do not change the image, and would only force needless rebuilds.
#   sets  MAJOR, BASE_IMAGE, CONFIG_KEY
function read_ci_config {
    MAJOR=$(sed -n '/^[[:space:]]*#/d; s/.*clang-format-\([0-9][0-9]*\).*/\1/p' \
        "$CI_DOCKERFILE" | head -1)
    BASE_IMAGE=$(sed -n '/^[[:space:]]*#/d; s/^FROM \([^ ]*\).*/\1/p' \
        "$CI_DOCKERFILE" | head -1)
    if [ -z "$MAJOR" ] || [ -z "$BASE_IMAGE" ]
    then
        error_exit 1 "ERROR: could not read the clang-format version or base image from $CI_DOCKERFILE"
    fi
    CONFIG_KEY=$(printf '%s|clang-format-%s' "$BASE_IMAGE" "$MAJOR" \
        | sha256sum | cut -c1-12)
}

# Extracts X.Y.Z from "clang-format --version" output read on stdin.
function cf_version_string {
    sed -n 's/.*clang-format version \([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/p'
}

# Looks for a local clang-format of the required major version.
#   sets  CF_LOCAL, CF_VERSION on success
function find_local_formatter {
    local candidate found
    for candidate in "clang-format-${MAJOR}" "clang-format"
    do
        command -v "$candidate" > /dev/null 2>&1 || continue
        found=$("$candidate" --version 2>/dev/null | cf_version_string) || found=""
        if [ "${found%%.*}" = "$MAJOR" ]
        then
            CF_LOCAL="$candidate"
            CF_VERSION="$found"
            return 0
        fi
    done
    return 1
}

# Decides whether the local toolchain can run the CI checker. The checker
# builds its file list with tree, and without tree it silently reports zero
# files, so a local clang-format alone is not enough.
#   sets    LOCAL_BLOCKER with the reason when it cannot
#   returns 0 when the local path is usable
function local_path_usable {
    if [ -z "$CF_LOCAL" ]
    then
        LOCAL_BLOCKER="no clang-format ${MAJOR}.x on PATH"
        return 1
    fi
    if ! command -v tree > /dev/null 2>&1
    then
        LOCAL_BLOCKER="tree is not installed, which the CI checker needs"
        return 1
    fi
    return 0
}

# Looks for an image this script built earlier for the current CI config.
# The tag carries both the formatter version and CONFIG_KEY, so a match
# confirms the config and reveals the version without starting a container.
#   sets    IMAGE, CF_VERSION on a hit
#   returns 0 on a hit, 1 otherwise
function find_cached_image {
    local tag
    tag=$(docker images "$IMAGE_REPO" --format '{{.Tag}}' 2>/dev/null \
        | grep -- "-${CONFIG_KEY}\$" | head -1) || tag=""
    [ -n "$tag" ] || return 1
    IMAGE="${IMAGE_REPO}:${tag}"
    CF_VERSION="${tag%-${CONFIG_KEY}}"
    return 0
}

# Builds the fallback image and tags it twice: once with CONFIG_KEY as the
# lookup handle, and once with the bare version for humans reading
# "docker images".
#   sets  IMAGE, CF_VERSION
function build_image {
    local tmp_tag="${IMAGE_REPO}:build-$$"
    echo "Building ${IMAGE_REPO} from ${BASE_IMAGE} with clang-format-${MAJOR} (first run only) ..."

    # Deliberately not quiet: on the one run where this happens, the apt
    # output is what makes a failure diagnosable.
    if ! docker build -t "$tmp_tag" - <<EOF
FROM ${BASE_IMAGE}
RUN apt-get update && \
    apt-get install --yes git tree clang-format-${MAJOR} && \
    update-alternatives --install /usr/bin/clang-format clang-format \
      /usr/bin/clang-format-${MAJOR} 20 && \
    rm -rf /var/lib/apt/lists/*
EOF
    then
        error_exit 1 "ERROR: failed to build the clang-format image"
    fi

    CF_VERSION=$(docker run --rm "$tmp_tag" clang-format --version 2>/dev/null \
        | cf_version_string) || CF_VERSION=""
    if [ -z "$CF_VERSION" ]
    then
        docker rmi -f "$tmp_tag" > /dev/null 2>&1 || true
        error_exit 1 "ERROR: could not read the clang-format version from the built image"
    fi

    IMAGE="${IMAGE_REPO}:${CF_VERSION}-${CONFIG_KEY}"
    docker tag "$tmp_tag" "$IMAGE"
    docker tag "$tmp_tag" "${IMAGE_REPO}:${CF_VERSION}"
    docker rmi "$tmp_tag" > /dev/null 2>&1 || true
    echo "Tagged ${IMAGE_REPO}:${CF_VERSION}"
}

# Chooses the toolchain: local first, then a cached image, then a build.
#   $1  "no-build" to report only what is already available
function resolve_formatter {
    local mode="${1:-build}"

    find_local_formatter || true
    local_path_usable && return 0

    # The local formatter cannot be used; fall back to Docker.
    CF_LOCAL=""
    CF_VERSION=""
    if ! command -v docker > /dev/null 2>&1
    then
        error_exit 1 "ERROR: cannot run the CI checker locally (${LOCAL_BLOCKER})," \
                     "       and docker is not available as a fallback." \
                     "       Install clang-format-${MAJOR} and tree, or install docker."
    fi

    find_cached_image && return 0
    [ "$mode" = "no-build" ] && return 1
    build_image
}

# Reports the required and effective versions, without ever building.
function print_version {
    echo "clang-format required by CI : ${MAJOR}.x  (${CI_DOCKERFILE})"

    local local_name="" local_version=""
    if find_local_formatter
    then
        local_name="$CF_LOCAL"
        local_version="$CF_VERSION"
    fi

    local resolved=0
    if resolve_formatter "no-build"
    then
        resolved=1
    fi

    # Note a local formatter that exists but cannot be used, so that a missing
    # tree is not mistaken for a missing formatter.
    if [ -n "$local_name" ] && [ -z "$CF_LOCAL" ]
    then
        echo "clang-format found locally  : ${local_version}  (${local_name}), unusable:"
        echo "                              ${LOCAL_BLOCKER}"
    fi

    if (( resolved == 1 ))
    then
        if [ -n "$CF_LOCAL" ]
        then
            echo "clang-format that will run  : ${CF_VERSION}  (local ${CF_LOCAL})"
        else
            echo "clang-format that will run  : ${CF_VERSION}  (docker ${IMAGE_REPO}:${CF_VERSION})"
        fi
    else
        echo "clang-format that will run  : not resolved yet"
        echo "                              ${LOCAL_BLOCKER}; no image built for this CI config."
        echo "                              It is built on the first formatting run."
    fi
}

# Runs a command with the chosen toolchain, from the repository root. The
# Docker path mounts the repository at /home so the checker sees CI's layout.
function run_tool {
    if [ -n "$CF_LOCAL" ]
    then
        PATH="$(dirname "$(command -v "$CF_LOCAL")"):$PATH" "$@"
    else
        docker run --rm -i --user "$(id -u):$(id -g)" \
          -v "$ROOT:/home" -w /home -e HOME=/tmp "$IMAGE" "$@"
    fi
}

# Validates the branch pair. The checker prefixes the target with origin/ and
# does not fail loudly when that does not resolve: it falls back to an empty
# revision and silently checks a different file set.
function validate_branches {
    if [ "${TARGET_BRANCH#origin/}" != "$TARGET_BRANCH" ]
    then
        error_exit 2 "ERROR: --target-branch takes a bare branch name, not '$TARGET_BRANCH'." \
                     "       The checker prefixes it with origin/ itself, so this would" \
                     "       look up 'origin/$TARGET_BRANCH'." \
                     "       Use: --target-branch ${TARGET_BRANCH#origin/}"
    fi
    if ! git rev-parse --verify --quiet "origin/${TARGET_BRANCH}^{commit}" > /dev/null
    then
        error_exit 1 "ERROR: origin/${TARGET_BRANCH} does not resolve." \
                     "       Fetch it first, for example:" \
                     "         git fetch origin ${TARGET_BRANCH}"
    fi
    if ! git rev-parse --verify --quiet "${SOURCE_BRANCH}^{commit}" > /dev/null
    then
        error_exit 1 "ERROR: ${SOURCE_BRANCH} does not resolve as a --source-branch."
    fi
}

# Runs the CI checker, which owns the definition of "wrongly formatted".
# Its result files are a CI artefact, so they are cleared first (a stale pair
# must never be read as this run's output) and removed again on exit.
function run_checker {
    rm -f "$RESULT" "$RESULT_LIST"
    trap 'rm -f "$RESULT" "$RESULT_LIST"' EXIT

    if (( BRANCH_MODE == 1 ))
    then
        echo "Source Branch is    : $SOURCE_BRANCH"
        echo "Target Branch is    : $TARGET_BRANCH"
        run_tool "./$CHECKER" --src-branch "$SOURCE_BRANCH" \
            --target-branch "$TARGET_BRANCH" > /dev/null \
            || error_exit 1 "ERROR: $CHECKER failed"
    else
        run_tool "./$CHECKER" > /dev/null || error_exit 1 "ERROR: $CHECKER failed"
    fi
}

# Reads what the checker produced. A listed file that does not exist means the
# checker and this script disagree about the tree, which is reported rather
# than skipped: silently dropping it could turn a real failure into a pass.
#   sets  NB_TOTAL, SOURCES
function collect_results {
    [ -f "$RESULT" ] || error_exit 1 "ERROR: $CHECKER produced no result file"

    NB_TOTAL=$(sed -n 's/^NB_FILES_CHECKED=//p' "$RESULT")
    : "${NB_TOTAL:=0}"

    SOURCES=()
    [ -f "$RESULT_LIST" ] || return 0
    local f
    while IFS= read -r f
    do
        [ -n "$f" ] || continue
        [ -f "$f" ] || error_exit 1 "ERROR: $CHECKER reported a file that does not exist: $f"
        SOURCES+=("$f")
    done < "$RESULT_LIST"
}

# Rewrites the offending files in one batch: with the Docker path a container
# per file costs far more than the formatting. NUL-delimited, because xargs
# otherwise treats quotes and backslashes in paths as syntax.
function format_files {
    printf '%s\0' "${SOURCES[@]}" | run_tool xargs -0 -r clang-format -i \
        || error_exit 1 "ERROR: clang-format failed"
}

function main {
    parse_args "$@"
    enter_repo_root
    read_ci_config

    if (( SHOW_VERSION == 1 ))
    then
        print_version
        exit 0
    fi

    # Before any Docker work, so a bad branch fails in a second, not a build.
    if (( BRANCH_MODE == 1 ))
    then
        validate_branches
    fi

    resolve_formatter
    if [ -n "$CF_LOCAL" ]
    then
        echo "Using: local ${CF_LOCAL} (${CF_VERSION})"
    else
        echo "Using: docker ${IMAGE_REPO}:${CF_VERSION}"
    fi

    run_checker
    collect_results

    local nb_hit=${#SOURCES[@]}
    if (( nb_hit != 0 ))
    then
        printf '  %s\n' "${SOURCES[@]}"
    fi

    if (( DRY_RUN == 1 ))
    then
        if (( nb_hit == 0 ))
        then
            echo "Formatting check passed: all ${NB_TOTAL} files are correctly formatted."
            exit 0
        fi
        echo "Formatting check failed: ${nb_hit} of ${NB_TOTAL} files require formatting."
        exit 1
    fi

    if (( nb_hit == 0 ))
    then
        echo "Nothing to do: all ${NB_TOTAL} files are already correctly formatted."
        exit 0
    fi

    format_files
    echo "Reformatted ${nb_hit} of ${NB_TOTAL} files."
}

main "$@"
