# SPDX-License-Identifier: MIT
#
# "OAI Coding / Formatting Guidelines Check" section of the HTML report.
# Takes the checked/failing counts from src/oai_rules_result.txt and, when
# present, the offending filenames from src/oai_rules_result_list.txt; copies
# both into archives/ and renders the pass/fail chapter with a details table.

import os
import shutil
import common.python.cls_cmd as cls_cmd
from common.python.html_builder import (
    generate_chapter,
    generate_button_header,
    generate_button_footer,
    pluralize,
)

# Dockerfile that defines the clang-format check environment (see Jenkinsfile).
CLANG_FORMAT_DOCKERFILE = 'ci-scripts/common/docker/Dockerfile.ci.clang-format'


def _html_escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def coding_formatting_log_check(args):
    cwd = os.getcwd()
    details = ''
    chapterName = 'OAI Coding / Formatting Guidelines Check'
    if os.path.isfile(f'{cwd}/src/oai_rules_result.txt'):
        shutil.copy(f'{cwd}/src/oai_rules_result.txt', f'{cwd}/archives')
        myCmd = cls_cmd.LocalCmd()
        cmd = f'grep NB_FILES_FAILING_CHECK {cwd}/src/oai_rules_result.txt | sed -e "s#NB_FILES_FAILING_CHECK=##"'
        nbFailRet = myCmd.run(cmd)
        cmd = f'grep NB_FILES_CHECKED {cwd}/src/oai_rules_result.txt | sed -e "s#NB_FILES_CHECKED=##"'
        nbTotalRet = myCmd.run(cmd)
        myCmd.close()
        nbFail, nbTotal = nbFailRet.stdout.strip(), nbTotalRet.stdout.strip()
        if not (nbFail.isdigit() and nbTotal.isdigit()):
            return details + generate_chapter(
                chapterName, 'Was NOT performed (with CLANG-FORMAT tool).', False)
        nbFail, nbTotal = int(nbFail), int(nbTotal)
        scope = 'in this pull request' if args.git_pull_request else 'in the repository'
        if nbFail == 0:
            message = f'All {pluralize(nbTotal, "file")} {scope} follow the OAI coding / formatting rules.'
        else:
            message = f'{pluralize(nbFail, "file")} to reformat {scope} ({nbTotal} checked).'
        details += generate_chapter(chapterName, message, (nbFail == 0))

        if os.path.isfile(f'{cwd}/src/oai_rules_result_list.txt'):
            shutil.copy(f'{cwd}/src/oai_rules_result_list.txt', f'{cwd}/archives')
            details += generate_button_header('oai-formatting-details', 'More details on formatting check')

            # Summary table: environment + counts + how to fix.
            details += '  <table class="table-bordered" width = "90%" align = "center" border = "1">\n'
            if os.path.isfile(f'{cwd}/{CLANG_FORMAT_DOCKERFILE}'):
                details += ('    <tr><td bgcolor="lightcyan" style="width:30%">Dockerfile</td>'
                            f'<td><code>{CLANG_FORMAT_DOCKERFILE}</code></td></tr>\n')
            details += ('    <tr><td bgcolor="lightcyan">Number of files checked</td>'
                        f'<td>{nbTotalRet.stdout.strip()}</td></tr>\n')
            details += ('    <tr><td bgcolor="lightcyan">Number of files not following the rules</td>'
                        f'<td>{nbFailRet.stdout.strip()}</td></tr>\n')
            details += ('    <tr><td bgcolor="lightcyan">Command to fix</td>'
                        '<td><code>cd src && clang-format -i filename(s)</code></td></tr>\n')
            details += '  </table>\n  <br>\n'

            # File list table.
            details += '  <table class="table-bordered" width = "90%" align = "center" border = "1">\n'
            details += '    <tr bgcolor = "#33CCFF" ><th>File(s) not following OAI coding / formatting rules</th></tr>\n'
            with open(cwd + '/src/oai_rules_result_list.txt', 'r') as filelist:
                for line in filelist:
                    fname = line.strip()
                    if fname:
                        details += f'    <tr><td><code>{_html_escape(fname)}</code></td></tr>\n'
            details += '  </table>\n  <br>\n'
            details += generate_button_footer()
    else:
        details += generate_chapter(chapterName, 'Was NOT performed (with CLANG-FORMAT tool).', False)

    return details
