# SPDX-License-Identifier: MIT
#
# "Container Images Build Summary" section of the HTML report.
# Thin wrapper over the generic container_build_summary module: finds the
# per-variant build logs under archives/ and the Dockerfiles under docker/.

import os

from common.python.container_build_summary import parse_variant, render_section

# variant key -> pill label shown in the report
_VARIANTS = [
    ('ubuntu', 'Build Ubuntu Image'),
    ('rhel', 'Build RHEL Image'),
]


def build_summary(args, nfName):
    """Return the HTML for the Container Images Build Summary section.

    Only variants whose build log is present are rendered.
    """
    cwd = os.getcwd()
    archives_dir = os.path.join(cwd, 'archives')
    docker_dir = os.path.join(cwd, 'docker')

    variants = [
        (key, label, parse_variant(nfName, key, archives_dir, docker_dir))
        for key, label in _VARIANTS
    ]
    return render_section(nfName, variants)
