# SPDX-License-Identifier: MIT
#
# Command-line interface for generateHtmlReport.py.
# Defines the arguments the Jenkinsfiles pass in: target NF, job/build identity,
# git source and target refs, and the optional pull-request metadata.

import argparse
import re

def _parse_args() -> argparse.Namespace:
    """Parse the command line args

    Returns:
        argparse.Namespace: the created parser
    """
    example_text = '''example:
        ./generateHtmlReport.py --help'''

    parser = argparse.ArgumentParser(description='OAI 5G CORE NETWORK Utility tool',
                                    epilog=example_text,
                                    formatter_class=argparse.RawDescriptionHelpFormatter)

    # Pipeline Name
    parser.add_argument(
        '--job-name', '-jn',
        action='store',
        help='Pipeline name',
    )

    # Build Number
    parser.add_argument(
        '--build-id', '-id',
        action='store',
        help='Build ID or number',
    )

    # Build URL
    parser.add_argument(
        '--build-url',
        action='store',
        help='Build URL',
    )

    # GIT repo URL
    parser.add_argument(
        '--git-url',
        action='store',
        help='GIT repo URL',
    )

    # GIT source branch
    parser.add_argument(
        '--git-src-branch',
        action='store',
        help='GIT source branch',
    )

    # GIT source commit
    parser.add_argument(
        '--git-src-commit',
        action='store',
        help='GIT source commit (SHA-ONE)',
    )

    # GIT source is a pull request
    parser.add_argument(
        '--git-pull-request',
        dest='git_pull_request',
        action='store_true',
        default=False,
        help='GIT source is a pull request',
    )

    # GIT destination branch
    parser.add_argument(
        '--git-dst-branch',
        action='store',
        help='GIT destination branch',
    )

    # GIT destination commit
    parser.add_argument(
        '--git-dst-commit',
        action='store',
        help='GIT destination commit (SHA-ONE)',
    )

    # Network Function name (e.g. amf, smf, ausf...)
    parser.add_argument(
        '--nf',
        action='store',
        help='Network Function name (e.g. amf, smf, ausf)',
    )

    # Whether to include the unit-tests section in the generated report
    parser.add_argument(
        '--has-unit-tests',
        action='store_true',
        default=False,
        help='Include the unit-tests section in the report',
    )

    # Pull request URL (only used when --git-pull-request is set)
    parser.add_argument(
        '--pr-url',
        action='store',
        help='Pull request URL, substituted into the report',
    )

    # Pull request title -- raw, untrusted author-controlled text; html_builder.py
    # sanitizes it before embedding into the HTML report
    parser.add_argument(
        '--pr-title',
        action='store',
        help='Pull request title, substituted into the report',
    )

    # Report generation timestamp
    parser.add_argument(
        '--build-time',
        action='store',
        help='Build start time, substituted into the report',
    )

    args, unknown = parser.parse_known_args()
    return args
