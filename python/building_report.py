# SPDX-License-Identifier: MIT
#
# "Container Images Build Summary" section of the HTML report.
# Thin wrapper over the generic container_build_summary module: finds the
# per-variant build logs under archives/ and the Dockerfiles under docker/.

import os

from common.python.container_build_summary import parse_variant, render_section

# variant key (also the log-name stem) -> pill label. Absent logs are skipped.
_VARIANTS = [
    ('ubuntu', 'Build Ubuntu Image'),
    ('ubuntu_lttng', 'Build Ubuntu Image with LTTNG'),
    ('rhel', 'Build RHEL Image'),
]


def build_summary(args, nfName):
    """Return the HTML for the Container Images Build Summary section.

    Only variants whose build log is present are rendered.
    """
    cwd = os.getcwd()
    archives_dir = os.path.join(cwd, 'archives')
    docker_dir = os.path.join(cwd, 'docker')

    variants = []
    for key, label in _VARIANTS:
        data = parse_variant(nfName, key, archives_dir, docker_dir)
        # LTTNG log has no stage markers -- collapse to one PASS/FAIL row.
        if key == 'ubuntu_lttng' and data['present']:
            fail_lines = [l for s in data['stages'] for l in s.get('fail_lines', [])]
            data['stages'] = [{
                'name': 'Image build',
                'status': 'OK' if data['overall_ok'] else 'FAILED',
                'details': (data.get('image_size') or 'Image built successfully')
                           if data['overall_ok'] else 'Build failed',
                'fail_lines': fail_lines,
            }]
        variants.append((key, label, data))
    return render_section(nfName, variants)
