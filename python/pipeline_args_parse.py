# SPDX-License-Identifier: MIT

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

    # GIT MR or PR
    parser.add_argument(
        '--git-merge-request',
        action='store_true',
        default=False,
        help='GIT source commit (SHA-ONE)',
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

    args, unknown = parser.parse_known_args()
    # for backward compatibility, once all pipelines are correct, let remove all this section
    for item in unknown:
        if re.search('job_name=', item) is not None:
            args.job_name = re.sub('\-\-job_name=', '', item)
        if re.search('job_id=', item) is not None:
            args.build_id = re.sub('\-\-job_id=', '', item)
        if re.search('job_url=', item) is not None:
            args.build_url = re.sub('\-\-job_url=', '', item)
        if re.search('git_url=', item) is not None:
            args.git_url = re.sub('\-\-git_url=', '', item)
        if re.search('git_src_branch=', item) is not None:
            args.git_src_branch = re.sub('\-\-git_src_branch=', '', item)
        if re.search('git_src_commit=', item) is not None:
            args.git_src_commit = re.sub('\-\-git_src_commit=', '', item)
        if re.search('git_target_branch=', item) is not None:
            args.git_dst_branch = re.sub('\-\-git_target_branch=', '', item)
        if re.search('git_target_commit=', item) is not None:
            args.git_dst_commit = re.sub('\-\-git_target_commit=', '', item)
        if re.search('git_pull_request=True', item) is not None:
            args.git_merge_request = True
    return args
