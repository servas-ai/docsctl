"""Bounded page refinements for an existing, externally supplied Painter.

No cover renderer, brand tokens, fonts, customer artwork, runtime paths, network
access or PDF invocation live in this module. The owner runner supplies those.
Coordinates deliberately preserve the reviewed A4 landscape baseline.
"""
from __future__ import annotations
import hashlib
import math
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from repair_assets import FOOTNOTE, MATRIX_ASSET_ROLES, bitmap_box

STATUS_LABELS = {
    'native': 'Kernfunktion', 'adapter': 'eigene Integration',
    'outside': 'nicht Hauptaufgabe', 'unknown': 'im PR noch offen',
}
FORBIDDEN_RETURN_SUFFIXES = {'.ttf', '.otf', '.woff', '.woff2', '.pem', '.key'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or '\\' in relative or '\0' in relative:
        raise ValueError('invalid relative path')
    if relative.startswith('/') or any(p in ('', '.', '..') for p in relative.split('/')):
        raise ValueError('non-canonical relative path')
    base = root.resolve(strict=True)
    current = base
    for part in PurePosixPath(relative).parts:
        current /= part
        if current.is_symlink():
            raise ValueError('symlink rejected')
    target = current.resolve(strict=True)
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError('not a contained file')
    return target


def verify_return(root: Path, receipt: dict) -> list[dict]:
    entries = receipt.get('output_files')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 200:
        raise ValueError('invalid return manifest')
    seen, checked = set(), []
    for item in entries:
        rel = item.get('path')
        if rel in seen:
            raise ValueError('duplicate manifest path')
        seen.add(rel)
        path = checked_path(root, rel)
        if path.suffix.lower() in FORBIDDEN_RETURN_SUFFIXES:
            raise ValueError('forbidden return file')
        if path.stat().st_size > 20_000_000:
            raise ValueError('artifact exceeds limit')
        data = path.read_bytes()
        if len(data) != item['bytes'] or digest(data) != item['sha256']:
            raise ValueError('artifact hash/length mismatch')
        checked.append({'path': rel, 'sha256': item['sha256'], 'bytes': len(data)})
    return checked


def validate_spec(spec: dict) -> dict:
    if not isinstance(spec, dict) or spec.get('schema') != 1:
        raise ValueError('invalid refinement spec')
    from datetime import date
    date.fromisoformat(spec['checked_date'])
    providers = spec['providers']
    if len(providers) != 4 or len({p['name'] for p in providers}) != 4:
        raise ValueError('four distinct provider columns required')
    for p in providers:
        if len(p['name']) > 20 or len(p['display_domain']) > 28:
            raise ValueError('provider label too long')
        u = urlsplit(p['documentation_url'])
        if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ValueError('invalid documentation URL')
    nodes = spec['flow']['nodes']
    if len(nodes) != 4 or [n['id'] for n in nodes] != ['source', 'render', 'candidate', 'review']:
        raise ValueError('review must follow a real PDF candidate')
    for n in nodes:
        for k, limit in [('title', 24), ('owner', 36), ('input', 58), ('output', 58)]:
            if not isinstance(n[k], str) or len(n[k]) > limit:
                raise ValueError('invalid flow field')
    if spec['flow'].get('automatic_release') is not False:
        raise ValueError('automatic design release forbidden')
    return spec


def matrix_rows(data: dict, spec: dict) -> list[dict]:
    """Explicit evidence corrections without silently altering the layout/table size."""
    import copy
    rows = copy.deepcopy(data['comparison']['rows'])
    if not 8 <= len(rows) <= 16:
        raise ValueError('matrix size outside reviewed bounds')
    for row in rows:
        if len(row['cells']) != 4:
            raise ValueError('four cells required')
        if row['label'] in spec.get('row_patches', {}):
            row['cells'] = copy.deepcopy(spec['row_patches'][row['label']])
        if len(row['cells']) != 4:
            raise ValueError('patched row must retain four cells')
        for cell in row['cells']:
            if cell['status'] not in STATUS_LABELS or len(cell['text']) > 48:
                raise ValueError('invalid comparison cell')
    return rows


def simple_svg(raw: bytes) -> tuple[list[float], list[tuple[str, str, str]]]:
    """Strict filled-path subset; reject unsupported SVG rather than fake a logo.

    Colors and geometry remain unchanged. No CSS, external URLs, transforms,
    scripts, images, XML entities or network resolution are supported.
    """
    if len(raw) > 300_000 or b'<!' in raw or b'<?' in raw:
        raise ValueError('unsupported XML header or size')
    root = ET.fromstring(raw)
    local = lambda name: name.rsplit('}', 1)[-1]
    if local(root.tag) != 'svg':
        raise ValueError('not SVG')
    if set(root.attrib) - {'width', 'height', 'viewBox', 'fill', 'version'}:
        raise ValueError('unsupported SVG root attribute')
    view = [float(v) for v in re.split(r'[ ,]+', root.attrib['viewBox'].strip())]
    if len(view) != 4 or not all(math.isfinite(v) for v in view) or min(view[2:]) <= 0:
        raise ValueError('invalid viewbox')
    paths = []
    for child in root:
        if local(child.tag) != 'path' or len(child):
            raise ValueError('only direct filled paths supported')
        if set(child.attrib) - {'d', 'fill', 'fill-rule', 'clip-rule'}:
            raise ValueError('unsupported path attribute')
        color = child.get('fill', root.get('fill', 'black'))
        if color not in ('white', 'black', 'none') and not re.fullmatch(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})', color):
            raise ValueError('unsupported fill')
        rule = child.get('fill-rule', 'nonzero')
        if rule not in ('evenodd', 'nonzero'):
            raise ValueError('unsupported fill rule')
        path = child.get('d', '')
        if not path or len(path) > 100_000 or not re.fullmatch(r'[MmZzLlHhVvCcSsQqTtAaEe0-9+.,\s-]+', path):
            raise ValueError('unsupported SVG path')
        paths.append((path, color, rule))
    if not 1 <= len(paths) <= 100:
        raise ValueError('path count outside bounds')
    return view, paths


def draw_provider(p, asset: dict, x: float, top: float, width: float, height: float) -> None:
    path = Path(asset['path'])
    if asset['kind'] != 'svg_paths':
        p.image(path, x, top, width, height, 'original_provider_' + asset['role'])
        return
    from reportlab.graphics.svgpath import SvgPath
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing, Group
    from reportlab.lib.colors import toColor
    view, items = simple_svg(path.read_bytes())
    vx, vy, vw, vh = view
    factor = min(width/vw, height/vh)
    group = Group()
    for d, color, rule in items:
        group.add(SvgPath(d, fillColor=None if color == 'none' else toColor(color),
                          strokeColor=None, fillMode=0 if rule == 'evenodd' else 1))
    group.translate(-vx, vh+vy)
    group.scale(1, -1)
    drawing = Drawing(vw, vh)
    drawing.add(group)
    drawing.scale(factor, factor)
    renderPDF.draw(drawing, p.c, x+(width-vw*factor)/2, p.h-top-height+(height-vh*factor)/2)
    # Same fitted box as renderPDF.draw, in physical page points, top-left origin.
    # Raster Painter.image records use this identical contract; scale exactly once.
    dw, dh = vw*factor, vh*factor
    dx, dy = x+(width-dw)/2, top+(height-dh)/2
    p.images.append({'page': p.page, 'role': 'original_provider_wordmark_vector',
                     'x_pt': dx*p.scale, 'y_top_pt': dy*p.scale,
                     'width_pt': dw*p.scale, 'height_pt': dh*p.scale,
                     'source_sha256': digest(path.read_bytes()), 'transformation': 'scale only'})


def page_matrix(p, data: dict, spec: dict, assets: dict, expanded: bool = False) -> None:
    p.begin()
    p.header('Vergleich / Aufgaben statt Ranglisten', 'A2 / 01' if expanded else '02 / 04')
    p.kicker('Vier Rollen. Ein Dokument-System.')
    p.text('Das richtige Werkzeug.\nAm richtigen Platz.', 44, 95, 525, 31, '400', leading=32,
           max_height=85, tracking=-.55)
    p.text('Funktionsvergleich, kein Benchmark.\nQuellen geprüft: ' + spec['checked_date'] + '.',
           578, 112, 217, 8.5, color='muted', max_height=42)
    x, top, label_w, col_w = 44, 183, 182, 143
    colors = ['#FDE8DA', '#E8F0FA', '#E6F2EB', '#EFE9F7']
    for j, provider in enumerate(spec['providers']):
        cx = x+label_w+j*col_w
        p.rect(cx+2, top, col_w-4, 43, colors[j], radius=5)
        asset = assets.get(provider['name'])
        if asset and asset['role'] in MATRIX_ASSET_ROLES:
            if asset['role'] == 'favicon':
                draw_provider(p, asset, cx+12, top+6, 17, 17)
                p.text(provider['name'], cx+36, top+7, col_w-44, 10.2, '450', max_height=19)
            else:
                draw_provider(p, asset, cx+12, top+5, col_w-30, 20)
        else:
            p.text(provider['name'], cx+12, top+7, col_w-24, 10.2, '450', max_height=19)
        source_label = f"[{j+1}] {provider['display_domain']}"
        p.text(source_label, cx+12, top+29, col_w-23, 6.3, color='muted', max_height=10)
        p.c.linkURL(provider['documentation_url'],
                    (cx*p.scale, (p.h-top-43)*p.scale, (cx+col_w)*p.scale, (p.h-top)*p.scale),
                    relative=0, thickness=0)
    p.text('Kriterium', x, top+9, label_w-10, 9, '450')
    rows = matrix_rows(data, spec)
    row_h = 17.4
    for i, row in enumerate(rows):
        yy = top+49+i*row_h
        if i % 2 == 0:
            p.rect(x, yy, 754, row_h, 'surface')
        label = row['label'] + (' [5]' if row['label'] == 'Stand in docsctl PR #1' else '')
        p.text(label, x+6, yy+2.5, label_w-14, 7.3, '450', max_height=row_h-1)
        for j, cell in enumerate(row['cells']):
            cx = x+label_w+j*col_w
            p.symbol(cell['status'], cx+10, yy+8)
            p.text(cell['text'], cx+19, yy+2.5, col_w-24, 7.0, max_height=row_h-1)
    yy = top+49+len(rows)*row_h+10
    for status, xx, width in [('native',48,96), ('adapter',176,120), ('outside',337,137), ('unknown',517,160)]:
        p.symbol(status, xx, yy+4)
        p.text(STATUS_LABELS[status], xx+10, yy, width, 6.8, color='muted')
    p.text(FOOTNOTE,
           44, yy+16, 754, 6.7, color='muted')
    p.links([{'id':5, 'short':'PR-Stand ' + spec['pr_base_short'], 'url':spec['pr_source_url']}], yy+31)
    missing = sum(p['name'] not in assets for p in spec['providers'])
    tail = 'Typst: Textlabel; README-Banner nur im Herkunftsbeleg.'
    if missing:
        tail = f'{missing} Zeichen offen; Typst-Banner nur im Herkunftsbeleg.'
    p.text(tail, 350, yy+31, 445, 6.4, color='muted')
    p.end()


def arrow(p, x1, y1, x2, y2, color='ink', dashed=False):
    p.line(x1, y1, x2, y2, color, .85, dashed)
    angle = math.atan2(y2-y1, x2-x1)
    for turn in (-.55, .55):
        p.line(x2-4*math.cos(angle+turn), y2-4*math.sin(angle+turn), x2, y2, color, .85)


def page_architecture(p, spec: dict) -> None:
    p.begin()
    p.header('Architektur / Tatsächlicher Prüfweg', '03 / 04')
    p.kicker('Eingaben. Zuständigkeit. Rückweg.')
    p.text('Eine Quelle.\nJeder Schritt prüfbar.', 44, 95, 570, 33, leading=34,
           max_height=90, tracking=-.7)
    p.text('Build01: PDF + Raster erzeugt.\nReview: Änderungen offen, keine Freigabe.',
           578, 120, 220, 8.1, color='muted', max_height=42)
    xs = [44, 239, 434, 629]
    colors = ['peach', 'pale_blue', 'pale_teal', 'pale_violet']
    for i, node in enumerate(spec['flow']['nodes']):
        x = xs[i]
        p.text(node['owner'], x+1, 203, 165, 7.1, '450', color='muted', max_height=12)
        p.rect(x, 224, 166, 143, colors[i], radius=10)
        p.icon(['document','layers','document','check'][i], x+15, 238, size=17)
        p.text(node['title'], x+15, 262, 138, 12.4, '450', max_height=20)
        p.text('IN', x+15, 293, 20, 6.1, '600', color='muted')
        p.text(node['input'], x+39, 291, 114, 7.2, max_height=27)
        p.text('OUT', x+15, 329, 22, 6.1, '600', color='muted')
        p.text(node['output'], x+39, 327, 114, 7.2, max_height=27)
        if i < 3:
            arrow(p, x+166, 275, xs[i+1]-5, 275)
    # The candidate is produced before review. No export/approval bypass arrow.
    p.line(712, 367, 712, 407, 'orange', .9)
    arrow(p, 712, 407, 322, 407, 'orange', True)
    arrow(p, 322, 407, 322, 370, 'orange', True)
    arrow(p, 322, 407, 127, 407, 'orange', True)
    arrow(p, 127, 407, 127, 370, 'orange', True)
    p.rect(388, 393, 244, 27, 'paper')
    p.text('Befund → Quelle oder Layout ändern → neu bauen', 395, 399, 234, 7.0,
           color='muted', max_height=15)
    arrow(p, 760, 367, 760, 444, 'muted', True)
    p.rect(44, 448, 754, 52, 'surface', radius=8)
    p.icon('document', 59, 461, 'muted', 16)
    p.text('PR bleibt Draft', 85, 458, 179, 10.1, '450', max_height=17)
    p.text('PDF + Quellen + Seitenraster + Review verlinken.', 85, 478, 300, 7.2,
           color='muted', max_height=13)
    p.text('Verantwortung: Fachowner', 424, 459, 219, 8.7, '450', max_height=16)
    p.text('Kein Merge. Kein Deployment. Kein automatischer Design-PASS.',
           424, 478, 354, 7.2, color='muted', max_height=13)
    p.text('Beispiele: report.json → design-proof-A4.pdf → page-001.png → execution-result.json.',
           44, 516, 754, 6.8, color='muted')
    p.text('ReportLab-Vektordiagramm + editierbare Mermaid-Quelle; native Mermaid-Ausführung weiterhin offen.',
           44, 531, 754, 6.5, color='muted')
    p.end()


def evidence_crops(baseline: Path, out: Path) -> tuple[dict, list[dict]]:
    """Only crop existing server PDF rasters; never synthesize product screenshots."""
    from PIL import Image
    selections = {
        'old_identity': ('before-pages/page-001.png', (.047,.033,.25,.09)),
        'new_identity': ('design-proof-A4-pages/page-001.png', (.046,.039,.186,.092)),
        'old_table': ('before-pages/page-007.png', (.045,.29,.955,.60)),
        'new_table': ('design-proof-A4-pages/page-002.png', (.045,.30,.955,.57)),
    }
    paths, records = {}, []
    target = out/'evidence-crops'
    target.mkdir(mode=0o700)
    for name,(relative,box) in selections.items():
        source = checked_path(baseline, relative)
        with Image.open(source) as im:
            w,h=im.size
            crop=tuple(round(v*s) for v,s in zip(box,(w,h,w,h)))
            dest=target/(name+'.png')
            im.crop(crop).save(dest)
        paths[name]={'path':dest, 'pixel_size':[crop[2]-crop[0],crop[3]-crop[1]], 'display_dpi':300}
        records.append({'id':name, 'source':relative, 'source_sha256':digest(source.read_bytes()),
                        'crop_pixels':list(crop), 'output_sha256':digest(dest.read_bytes()),
                        'role':'actual_pdf_raster_crop', 'new_screenshot':False})
    return paths,records


def place_evidence(p, crop: dict, x, top, width, height, role):
    if not isinstance(crop, dict) or set(crop) != {'path', 'pixel_size', 'display_dpi'}:
        raise ValueError('verified crop metadata required')
    w, h = bitmap_box(crop['pixel_size'], width, height, crop['display_dpi'], p.scale)
    p.image(crop['path'], x+(width-w)/2, top+(height-h)/2, w, h, role)


def page_evidence(p, crops: dict) -> None:
    p.begin()
    p.header('Dokumentansichten / Vorher und Build01', '04 / 04')
    p.kicker('Echte Ausschnitte statt zweiter Dekoseite')
    p.text('Die Änderung.\nDirekt im Dokument.',44,95,520,31,leading=32,
           max_height=85,tracking=-.55)
    p.text('Echte PDF-Ausschnitte; keine neue Produktansicht.\nReviewanhang, keine finale Freigabe.',
           578,112,217,8.2,color='muted',max_height=42)
    # Two side-by-side panels with a shared label rail, not another hero image.
    for x,title,tint in [(44,'VORHER / ABGELEHNT','surface'),(427,'BUILD01 / BEIBEHALTEN','pale_teal')]:
        p.rect(x,183,371,27,tint,radius=5)
        p.text(title,x+10,190,350,7.4,'450',max_height=13,tracking=.35)
    for key,x in [('old_identity',44),('new_identity',427)]:
        p.rect(x,219,371,124,'paper',stroke='rule')
        place_evidence(p,crops[key],x+7,224,357,114,'actual_pdf_identity_crop')
    p.text('Textschriftzug ohne das originale Bildzeichen.',44,350,365,8.0,color='muted',max_height=15)
    p.text('Original-Asterisk und originale Wortmarke.',427,350,365,8.0,color='muted',max_height=15)
    for key,x in [('old_table',44),('new_table',427)]:
        p.rect(x,380,371,112,'paper',stroke='rule')
        place_evidence(p,crops[key],x+5,383,361,106,'actual_pdf_table_crop')
    p.text('Vorlagenfähigkeiten statt konkreter Werkzeuge.',44,499,371,7.2,color='muted',max_height=15)
    p.text('Vier Tool-Rollen: Farbe, Status und präzise Zellen.',427,499,371,7.2,color='muted',max_height=15)
    p.text('Layoutvergleich, nicht gleiche Daten. Quellen: abgelehnte PDF S. 1/7 und Build01 S. 1/2; Ausschnitte ohne Retusche.',
           44,523,754,6.4,color='muted',max_height=12)
    p.end()


def architecture_mmd(spec: dict) -> str:
    """Keep the editable graph semantics consistent with the vector diagram."""
    nodes=spec['flow']['nodes']
    lines=['flowchart LR']
    for n in nodes:
        label=' | '.join([n['title'], n['owner'], 'IN: '+n['input'], 'OUT: '+n['output']])
        if any(c in label for c in ['"','<','>','\\','\n']):
            raise ValueError('unsafe graph label')
        lines.append(f'  {n["id"]}["{label}"]')
    lines += ['  source --> render --> candidate --> review',
              '  review -->|Befund: Quelle oder Layout korrigieren| render',
              '  review -->|Quellenbefund| source',
              '  review -->|Nach dokumentierter Prüfung| draft["PR-Draft: PDF, Quellen, Raster, Review"]',
              '  draft -.-> noauto["Kein automatischer Merge oder Design-PASS"]']
    return '\n'.join(lines)+'\n'
