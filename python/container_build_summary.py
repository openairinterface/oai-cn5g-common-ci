# SPDX-License-Identifier: MIT
#
# Container Images Build Summary -- generic, log-driven.
# NF name is a parameter; deps, stages, and base images are discovered from the
# build log and Dockerfile, so it works for any NF emitting the build markers.

import os
import re

_ANSI = re.compile(r'\x1b\[[0-9;]*m')


def _clean(line):
    return _ANSI.sub('', line).rstrip('\n')


# ---------------------------------------------------------------------------
# Dockerfile parsing -- base builder image + runtime image, generically.
# ---------------------------------------------------------------------------
def parse_base_images(dockerfile_path, nf):
    """Return {'builder': img, 'runtime': img} resolved from FROM lines.

    Resolves ARG-substituted bases and stage aliases. Builder = stage whose
    alias contains 'builder'; runtime = 'oai-<nf>' (else the last FROM).
    """
    result = {'builder': None, 'runtime': None}
    if not os.path.isfile(dockerfile_path):
        return result

    args = {}
    stages = {}          # alias -> raw base token
    order = []           # (alias, base) in file order
    from_re = re.compile(r'^\s*FROM\s+(\S+)(?:\s+[Aa][Ss]\s+(\S+))?', re.I)
    arg_re = re.compile(r'^\s*ARG\s+([A-Za-z_][A-Za-z0-9_]*)=(.+)$', re.I)

    with open(dockerfile_path) as f:
        for raw in f:
            line = raw.strip()
            m = arg_re.match(line)
            if m:
                args.setdefault(m.group(1), m.group(2).strip().strip('"\''))
                continue
            m = from_re.match(line)
            if m:
                base, alias = m.group(1), m.group(2)
                alias = alias or base
                stages[alias] = base
                order.append((alias, base))

    def resolve(token, seen=None):
        seen = seen or set()
        if token in seen:
            return token
        seen.add(token)
        # ${VAR} or $VAR substitution from ARG defaults
        var = re.match(r'^\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?$', token)
        if var and var.group(1) in args:
            return resolve(args[var.group(1)], seen)
        # stage alias -> follow to its base
        if token in stages and stages[token] != token:
            return resolve(stages[token], seen)
        return token

    for alias, base in order:
        if 'builder' in alias.lower() and result['builder'] is None:
            result['builder'] = resolve(base)
        if alias == f'oai-{nf}':
            result['runtime'] = resolve(base)
    if result['runtime'] is None and order:
        result['runtime'] = resolve(order[-1][1])
    if result['builder'] is None and order:
        result['builder'] = resolve(order[0][1])
    return result


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------
def parse_dependencies(lines, nf):
    """Discover installed dependencies from install markers, in order.

    Returns (deps, overall_ok), deps = list of {name, done}. Pairs each
    'Starting to install X' with the next 'X installation complete', so a
    name mismatch (libyaml_cpp -> yaml-cpp) doesn't break pairing.
    """
    deps = []
    start_re = re.compile(r'Starting to install\s+(.+?)\s*$', re.I)
    complete_re = re.compile(r'(.+?)\s+installation complete\s*$', re.I)
    success_re = re.compile(rf'{re.escape(nf)}\s+deps installation successful', re.I)
    overall_ok = False

    # distro packages are a distinct phase with its own completion marker
    distro_done = False
    for line in lines:
        if re.search(r'distro libs installation complete', line, re.I):
            distro_done = True
            break
    if any(re.search(r'Install distro libs', l, re.I) for l in lines):
        deps.append({'name': 'distro packages', 'done': distro_done})

    for line in lines:
        m = start_re.search(line)
        if m:
            deps.append({'name': m.group(1).strip(), 'done': False})
            continue
        m = complete_re.search(line)
        if m and 'distro libs' not in line.lower():
            # mark the most recent not-yet-done lib as complete
            for d in reversed(deps):
                if not d['done'] and d['name'] != 'distro packages':
                    d['done'] = True
                    break
        if success_re.search(line):
            overall_ok = True

    # collapse multi-arch duplicates: one entry per name, first-seen order,
    # done only if every occurrence of that name completed.
    collapsed = {}
    for d in deps:
        if d['name'] in collapsed:
            collapsed[d['name']]['done'] = collapsed[d['name']]['done'] and d['done']
        else:
            collapsed[d['name']] = {'name': d['name'], 'done': d['done']}
    deps = list(collapsed.values())
    return deps, overall_ok


def _extract_failure(lines, max_lines=40):
    """Collect the meaningful failure lines: compiler error: lines and the
    BuildKit / process failure markers. Returns a list of strings."""
    out = []
    for line in lines:
        if re.search(r'\berror:', line) or \
           re.search(r'ERROR: failed to solve|did not complete successfully|Error \d+$', line):
            out.append(line.strip())
    if len(out) > max_lines:
        head = out[:max_lines - 1]
        head.append(f'... ({len(out) - (max_lines - 1)} more) ...')
        out = head
    return out


def parse_variant(nf, variant, archives_dir, docker_dir):
    """Parse one image-build log into a structured summary dict."""
    log_name = f'{nf}_{variant}_image_build.log'
    log_path = os.path.join(archives_dir, log_name)
    data = {
        'variant': variant, 'log_name': log_name, 'present': os.path.isfile(log_path),
        'base_images': {}, 'dockerfile': None, 'stages': [],
        'image_tag': None, 'image_size': None, 'last_log_line': None, 'overall_ok': False,
    }
    if not data['present']:
        return data

    dockerfile = os.path.join(docker_dir, f'Dockerfile.{nf}.{"rhel9" if variant == "rhel" else "ubuntu"}')
    data['dockerfile'] = os.path.relpath(dockerfile) if os.path.isfile(dockerfile) else None
    data['base_images'] = parse_base_images(dockerfile, nf)

    with open(log_path, errors='replace') as f:
        lines = [_clean(l) for l in f]

    non_empty = [l for l in lines if l.strip()]
    data['last_log_line'] = non_empty[-1] if non_empty else ''

    # --- platforms (multi-arch buildx logs tag each stage with linux/<arch>) ---
    plats = sorted(set(re.findall(r'\blinux/([a-z0-9]+)\b', '\n'.join(lines))))
    data['platforms'] = ', '.join(f'linux/{p}' for p in plats) if plats else None

    # --- image tag / size ---
    for line in lines:
        # tag from a push / tag / imagetools line: oai-<nf>:<tag>
        m = re.search(rf'oai-{re.escape(nf)}:([A-Za-z0-9][\w.\-]*)', line)
        if m and data['image_tag'] is None and re.search(r'Pushing|Successfully (?:tagged|pushed)|imagetools', line):
            data['image_tag'] = m.group(1)
        m = re.search(r'Image Size:\s*([0-9.]+)\s*([KMGT]B)', line, re.I)
        if m:
            data['image_size'] = f'{m.group(1)} {m.group(2)}'
    # Ubuntu: tag + size come from `docker images` output
    # (REPO  TAG  IMAGE_ID  CREATED  SIZE).
    for line in lines:
        if re.search(rf'oai-{re.escape(nf)}\b', line) and ' ago' in line:
            m = re.search(rf'oai-{re.escape(nf)}\s+(\S+)\s+[0-9a-f]{{12}}', line)
            if m and data['image_tag'] is None:
                data['image_tag'] = m.group(1)
            if data['image_size'] is None:
                m = re.search(r'([0-9.]+)\s?([KMGT]?B)\s*$', line)
                if m:
                    data['image_size'] = f'{m.group(1)} {m.group(2)}'
            break

    # --- dependency phase ---
    deps, deps_ok = parse_dependencies(lines, nf)

    # --- compile phase ---
    compiled = any(re.search(rf'\b{re.escape(nf)} compiled\b', l, re.I) for l in lines)
    installed = any(re.search(rf'\b{re.escape(nf)} installed\b', l, re.I) for l in lines)
    # count errors/warnings only after deps finished (avoid dependency-build noise)
    try:
        start_idx = next(i for i, l in enumerate(lines)
                         if re.search(r'deps installation successful', l, re.I))
    except StopIteration:
        start_idx = 0
    compile_region = lines[start_idx:]
    nb_err = sum(1 for l in compile_region if re.search(r'\berror:', l))
    nb_warn = sum(1 for l in compile_region if re.search(r'\bwarning:', l))
    build_ok = compiled and installed and nb_err == 0

    # --- cache / failure awareness --------------------------------------
    # A fully-cached build prints only '#N CACHED' and none of the runtime
    # markers, so absence of markers is never a failure -- only a positive one.
    failed_lines = _extract_failure(lines)
    build_failed = bool(failed_lines)
    cached = any(re.search(r'#\d+\s+CACHED\b', l) for l in lines)
    produced = (installed or compiled or cached
                or any(re.search(r'writing image sha256|exporting.*to image|naming to ',
                                 l, re.I) for l in lines)
                or bool(re.search(r'status is SUCCESS\s*$', data['last_log_line'] or '', re.I)))
    success = produced and not build_failed

    def _status(done):
        """OK if the stage's marker was seen; CACHED if the build succeeded but
        the marker was cache-suppressed; FAILED only on a real failure signal."""
        if done:
            return 'OK'
        return 'CACHED' if success else 'FAILED'

    # --- assemble stages with cascade -----------------------------------
    # CACHED counts as initial-done only when the build didn't fail, else an
    # early base RUN failure with cache-served layers is mislabelled OK.
    initial_done = (bool(deps) or (cached and not build_failed)
                    or any('Install build tools' in l for l in lines))
    initial_status = _status(initial_done)
    data['stages'].append({'name': 'Initial operations', 'status': initial_status,
                           'details': 'All initial operations went alright'
                           if initial_status != 'FAILED' else 'Base image preparation failed',
                           'fail_lines': failed_lines if initial_status == 'FAILED' else []})

    if initial_status == 'FAILED':
        _skip_rest(data, ['Dependencies', 'Builder image', 'Target image size'])
        _finalize(data, deps)
        return data

    deps_status = _status(deps_ok)
    dep_stage = {'name': 'Dependencies', 'status': deps_status, 'details': None,
                 'fail_lines': failed_lines if deps_status == 'FAILED' else []}
    if deps:
        dep_stage['deps'] = deps
    elif deps_status == 'CACHED':
        dep_stage['details'] = 'All dependencies served from the build cache'
    data['stages'].append(dep_stage)

    if deps_status == 'FAILED':
        _skip_rest(data, ['Builder image', 'Target image size'])
        _finalize(data, deps)
        return data

    build_status = _status(build_ok)
    data['stages'].append({
        'name': 'Builder image',
        'status': build_status,
        'details': ('Builder layers served from the build cache' if build_status == 'CACHED'
                    else f'{nb_err} errors, {nb_warn} warnings'),
        'fail_lines': failed_lines if build_status == 'FAILED' else [],
    })

    if build_status == 'FAILED':
        _skip_rest(data, ['Target image size'])
        _finalize(data, deps)
        return data

    # reaching this stage does not mean the image was created: the target stage
    # runs after the builder, so a failure there lands here -- as does a stage the
    # pipeline declared failed after pushing, which leaves no BuildKit error
    stage_failed = bool(re.search(r'status is FAILURE\s*$', data['last_log_line'] or '', re.I))
    target_ok = success and not stage_failed
    size_txt = data['image_size'] or 'created'
    data['stages'].append({'name': 'Target image size',
                           'status': 'OK' if target_ok else 'FAILED',
                           'details': size_txt if target_ok else 'Target image was not created',
                           'fail_lines': [] if target_ok else failed_lines})
    _finalize(data, deps)
    return data


def _skip_rest(data, names):
    for n in names:
        data['stages'].append({'name': n, 'status': 'SKIPPED',
                               'details': 'Not executed — a previous stage failed', 'fail_lines': []})


def _finalize(data, deps):
    # a cached stage is a successful stage -- the layer was reused, not skipped
    data['overall_ok'] = all(s['status'] in ('OK', 'CACHED') for s in data['stages'])


# ---------------------------------------------------------------------------
# Rendering -- Bootstrap 3 nav-pills + OAI colour palette (matches the report)
# ---------------------------------------------------------------------------
_STATUS_BG = {'OK': 'lightgreen', 'FAILED': 'lightcoral', 'SKIPPED': 'lightgray', 'CACHED': '#bfe3ea'}


def _esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def _render_deps(deps):
    if not deps:
        return '-'
    done = sum(1 for d in deps if d['done'])
    failed = next((d['name'] for d in deps if not d['done']), None)
    items = []
    for d in deps:
        mark = '&#10003;' if d['done'] else '&#10007;'
        color = '#3c763d' if d['done'] else '#a94442'
        weight = 'normal' if d['done'] else 'bold'
        items.append(f'<li style="color:{color};font-weight:{weight}">'
                     f'<b>{mark}</b> {_esc(d["name"])}</li>')
    if failed is None:
        head = f'All build dependencies installed ({done}):'
    else:
        # denominator is meaningless here: the install aborts at the first
        # failure, so dependencies after it never start and can't be counted.
        head = (f'Installation failed at <b>{_esc(failed)}</b> — earlier dependencies '
                f'installed OK; the build aborted, so later ones were not attempted:')
    return (f'{head}<ul style="list-style:none;padding-left:4px;margin:4px 0 0;'
            f'columns:2;font-size:12.5px">{"".join(items)}</ul>')


def _render_fail(fail_lines):
    if not fail_lines:
        return ''
    body = '\n'.join('=&gt; ' + _esc(l) for l in fail_lines)
    return (f'<pre style="border:none;background-color:#fff5f5;margin-top:6px;'
            f'white-space:pre-wrap;word-break:break-word">{body}</pre>')


def render_variant_tab(nf, data, pane_id, display):
    rows = []
    bi = data['base_images']
    meta = []
    if data['dockerfile']:
        meta.append(('Dockerfile', data['dockerfile']))
    if data.get('platforms'):
        meta.append(('Platform', data['platforms']))
    builder, runtime = bi.get('builder'), bi.get('runtime')
    if builder and runtime and builder == runtime:
        # single-base Dockerfile (e.g. Ubuntu: builder + target both FROM the
        # same ubuntu:jammy) -- one row is clearer than two identical ones.
        meta.append(('Base Image', builder))
    else:
        if builder:
            meta.append(('Builder Image', builder))
        if runtime:
            meta.append(('Target Image', runtime))
    if data.get('image_tag'):
        meta.append(('Image tag', data['image_tag']))
    meta_rows = ''.join(
        f'<tr><td bgcolor="lightcyan" style="width:22%;white-space:nowrap">{_esc(k)}</td>'
        f'<td><code>{_esc(v)}</code></td></tr>' for k, v in meta)
    meta_tbl = (f'<table class="table-bordered" width="100%" border="1">{meta_rows}</table><br>'
                if meta_rows else '')

    for s in data['stages']:
        bg = _STATUS_BG.get(s['status'], 'white')
        if 'deps' in s:
            details = _render_deps(s['deps'])
        else:
            details = _esc(s.get('details') or '-')
        details += _render_fail(s.get('fail_lines'))
        rows.append(
            f'<tr><td bgcolor="lightcyan">{_esc(s["name"])}</td>'
            f'<td bgcolor="{bg}"><b>{s["status"]}</b></td>'
            f'<td>{details}</td></tr>')

    if data.get('last_log_line'):
        rows.append(f'<tr><td bgcolor="lightcyan">Last log line</td><td>-</td>'
                    f'<td><code>{_esc(data["last_log_line"])}</code></td></tr>')

    final_bg, final_txt = ('green', 'PASS') if data['overall_ok'] else ('red', 'FAIL')
    rows.append(f'<tr><th bgcolor="#33CCFF" colspan="2">Final Build Status</th>'
                f'<th bgcolor="{final_bg}"><font color="white">{final_txt}</font></th></tr>')

    return (f'<div id="{pane_id}" class="tab-pane fade">'
            f'<h3>{_esc(display)}</h3>{meta_tbl}'
            f'<table class="table-bordered" width="100%" border="1">'
            f'<tr bgcolor="#33CCFF"><th style="width:22%">Build Stage</th>'
            f'<th style="width:10%">Status</th><th>Details</th></tr>'
            f'{"".join(rows)}</table></div>')


def render_section(nf, variants):
    """variants: list of (variant_key, display_label, data). Emits the whole
    Container Images Build Summary section (alert + pills + tab panes)."""
    present = [(k, lbl, d) for k, lbl, d in variants if d['present']]
    if not present:
        return ''
    all_ok = all(d['overall_ok'] for _, _, d in present)
    alert_cls, alert_msg = ('alert-success', 'All Container Target Images were created.') if all_ok \
        else ('alert-danger', 'One or more container target images were not created.')

    pills, panes, first = [], [], True
    for k, lbl, d in present:
        pane_id = f'build-{nf}-{k}'
        state = ('<span class="glyphicon glyphicon-ok" style="color:#5cb85c"></span> '
                 if d['overall_ok'] else
                 '<span class="glyphicon glyphicon-remove" style="color:#d9534f"></span> ')
        cls = 'active' if first else ''
        pills.append(f'<li class="{cls}"><a data-toggle="pill" href="#{pane_id}">{state}{_esc(lbl)}</a></li>')
        panes.append(render_variant_tab(nf, d, pane_id, lbl))
        first = False

    # activate first pane
    panes = [p.replace('class="tab-pane fade"', 'class="tab-pane fade in active"', 1)
             if i == 0 else p for i, p in enumerate(panes)]

    return (f'<h2>Container Images Build Summary</h2>'
            f'<div class="alert {alert_cls}"><strong>{alert_msg}</strong></div>'
            f'<ul class="nav nav-pills">{"".join(pills)}</ul>'
            f'<div class="tab-content">{"".join(panes)}</div><br>')
