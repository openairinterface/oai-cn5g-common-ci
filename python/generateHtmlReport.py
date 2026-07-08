#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import argparse
import re
import sys
from pathlib import Path


def _ensure_ci_scripts_on_syspath() -> None:
    """Put the NF repo's ci-scripts/ on sys.path so the sibling modules'
    internal 'common.python.X' imports resolve when running this directly."""
    ci_scripts_dir = Path(__file__).resolve().parents[2]
    if str(ci_scripts_dir) not in sys.path:
        sys.path.insert(0, str(ci_scripts_dir))


_ensure_ci_scripts_on_syspath()

from pipeline_args_parse import _parse_args
from generate_html import (
    generate_header,
    generate_footer,
    generate_git_info,
)
from code_format_checker import coding_formatting_log_check
from static_code_analysis import analyze_sca_log_check
from building_report import build_summary
from unit_tests_analysis import analyze_unit_tests_run

UBUNTU_VERSION = '22'
RHEL_VERSION = '9'

# Substring markers used when scanning existing report files.
CN5G_REPORT_MARKER = 'results_oai_cn5g_'
ROBOT_REPORT_MARKER = 'test_results_robot_'
ROBOT_BUILD_ID_MARKER = 'OAI-CN5G-RobotTest -- Build-ID'
ARCHIVES_LOG_HTML = 'archives/log.html'

# The one place a real regex is needed -- compiled once at module load.
HREF_PATTERN = re.compile(r'href="(?P<build_url>[a-zA-Z0-9\-:/.]+)"')


class HtmlReport:
    def __init__(self, nf_name: str, has_unit_tests: bool) -> None:
        self.nf_name = nf_name
        self.has_unit_tests = has_unit_tests
        self.output_dir = Path.cwd()
        self.report_path = self.output_dir / f'test_results_oai_{nf_name}.html'

    def generate(self, args: argparse.Namespace) -> None:
        with self.report_path.open('w') as wfile:
            wfile.write(generate_header(args))
            wfile.write(generate_git_info(args))
            wfile.write(build_summary(args, self.nf_name, UBUNTU_VERSION, RHEL_VERSION))
            wfile.write(coding_formatting_log_check(args))
            wfile.write(analyze_sca_log_check())
            if self.has_unit_tests:
                wfile.write(analyze_unit_tests_run())
            wfile.write(generate_footer())

    def append_to_test_reports(self, args: argparse.Namespace) -> None:
        git_info = generate_git_info(args)
        for report_file in self.output_dir.glob('*.html'):
            if CN5G_REPORT_MARKER not in report_file.name and ROBOT_REPORT_MARKER not in report_file.name:
                continue

            robot_build_url = ''
            git_info_appended = False
            lines = []
            for line in report_file.read_text().splitlines(keepends=True):
                if '<h2>' in line and not git_info_appended:
                    git_info_appended = True
                    lines.append(git_info)
                if ROBOT_BUILD_ID_MARKER in line:
                    match = HREF_PATTERN.search(line)
                    if match is not None:
                        robot_build_url = match.group('build_url')
                if ARCHIVES_LOG_HTML in line:
                    lines.append(line.replace('archives', f'{robot_build_url}/artifact/archives'))
                else:
                    lines.append(line)
            report_file.write_text(''.join(lines))


if __name__ == '__main__':
    args = _parse_args()
    if not args.nf:
        raise SystemExit('generateHtmlReport.py: --nf is required (e.g. --nf ausf)')

    report = HtmlReport(args.nf, args.has_unit_tests)
    report.generate(args)
    report.append_to_test_reports(args)
