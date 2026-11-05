"""Small, offline repair contracts: glyph coverage, original SVGs and crop sizes.

No fetch, renderer, font substitution, brand bytes or runtime paths. Normalization
keeps filled geometry/colors; it does not approximate unsupported SVG features.
"""
from __future__ import annotations
import math
import re
import xml.etree.ElementTree as ET

ROLE_LABELS = {
    'wordmark': 'Original-Wortmarke',
    'favicon': 'Favicon / Bildzeichen',
    'readme_banner': 'README-Banner; keine freistehende Wortmarke',
}
MATRIX_ASSET_ROLES = frozenset({'wordmark', 'favicon'})
FOOTNOTE = ('Produktfunktion bedeutet nicht: im PR integriert oder getestet. '
            'Systemrolle = Architekturvorschlag.')
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
SVG_NS = 'http://www.w3.org/2000/svg'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'


def missing_glyphs(text: str, char_to_glyph: dict) -> list[str]:
    """Glyph zero is .notdef, never evidence of supported text. No fallback."""
    return [f'U+{cp:04X}' for cp in sorted({ord(c) for c in text
            if c not in '\n\t\r' and not char_to_glyph.get(ord(c), 0)})]


def bitmap_box(pixel_size, max_width, max_height, target_dpi=300, page_scale=1):
    """Contain a bitmap while preventing magnification below the DPI floor.

    DPI describes sampled pixels, not recovered detail from an embedded image.
    The caller records native image resolution separately. Returns base PDF pts.
    """
    vals = [*pixel_size, max_width, max_height, target_dpi, page_scale]
    if len(pixel_size) != 2 or not all(isinstance(v, (int, float)) and
                                     math.isfinite(v) and v > 0 for v in vals):
        raise ValueError('INVALID_BITMAP_BOX')
    w, h = pixel_size
    factor = min(max_width/w, max_height/h, 72/(target_dpi*page_scale))
    return w*factor, h*factor


def crop_plan(page_size, raster_size, old_box, dpi):
    """Map an existing exact raster selection to a top-origin PDF region.

    Integer floor/ceil covers the selected original area; no change of subject.
    """
    if len(page_size) != 2 or len(raster_size) != 2 or len(old_box) != 4:
        raise ValueError('INVALID_CROP_SHAPE')
    values = [*page_size, *raster_size, *old_box, dpi]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError('NONFINITE_CROP')
    pw, ph = page_size
    rw, rh = raster_size
    x0, y0, x1, y1 = old_box
    if min(pw, ph, rw, rh) <= 0 or not 72 <= dpi <= 600:
        raise ValueError('INVALID_CROP_DIMENSIONS')
    if not (0 <= x0 < x1 <= rw and 0 <= y0 < y1 <= rh):
        raise ValueError('CROP_OUTSIDE_PAGE')
    points = [x0/rw*pw, y0/rh*ph, x1/rw*pw, y1/rh*ph]
    px = [math.floor(points[0]*dpi/72), math.floor(points[1]*dpi/72),
          math.ceil(points[2]*dpi/72), math.ceil(points[3]*dpi/72)]
    width, height = px[2]-px[0], px[3]-px[1]
    if width*height > 6_000_000:
        raise ValueError('REGION_PIXEL_BUDGET')
    return {'pdf_box_pt': points, 'dpi': dpi,
            'poppler_box_px': [px[0], px[1], width, height]}


def _numbers(value: str) -> list[str]:
    rest = re.sub(NUMBER, '', value)
    if re.sub(r'[\s,]+', '', rest):
        raise ValueError('UNSUPPORTED_SVG_NUMBER')
    tokens = re.findall(NUMBER, value)
    if not all(math.isfinite(float(t)) and abs(float(t)) <= 1_000_000 for t in tokens):
        raise ValueError('NONFINITE_SVG_NUMBER')
    return tokens


def normalize_filled_svg(raw: bytes) -> tuple[bytes, dict]:
    """Flatten inert groups and exact polygons into a filled-path-only SVG.

    Supports the actual Illustrator-style Puck source without broadening to CSS,
    transforms, links, images, scripts, use, clipping, DTD or XML entities.
    Initial UTF-8 XML declaration and comments are inert metadata only. Element
    order, viewBox, path strings, polygon vertices and inherited fills survive.
    """
    if not raw or len(raw) > 300_000:
        raise ValueError('SVG_SIZE_LIMIT')
    text = raw.decode('utf-8-sig')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)', text, re.I):
        raise ValueError('SVG_DTD_OR_ENTITY')
    text, declarations = re.subn(
        r'^\s*<\?xml\s+version=[\'"]1\.0[\'"]\s+encoding=[\'"]utf-8[\'"]\s*\?>',
        '', text, count=1, flags=re.I)
    if '<?' in text:
        raise ValueError('SVG_PROCESSING_INSTRUCTION')
    comments = len(re.findall(r'<!--.*?-->', text, re.S))
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    if '<!' in text or len(text) > 300_000:
        raise ValueError('UNSUPPORTED_XML_DECLARATION')
    root = ET.fromstring(text)

    def local(tag):
        if not isinstance(tag, str):
            raise ValueError('UNSUPPORTED_SVG_NODE')
        if tag.startswith('{'):
            ns, name = tag[1:].split('}', 1)
            if ns != SVG_NS:
                raise ValueError('FOREIGN_SVG_NAMESPACE')
            return name
        return tag

    if local(root.tag) != 'svg':
        raise ValueError('NOT_SVG')
    allowed = {'width', 'height', 'viewBox', 'fill', 'fill-rule', 'version',
               'id', 'x', 'y', 'style', XML_SPACE}
    if set(root.attrib) - allowed:
        raise ValueError('UNSUPPORTED_ROOT_ATTRIBUTE')
    view = _numbers(root.get('viewBox', ''))
    if len(view) != 4 or min(float(view[2]), float(view[3])) <= 0:
        raise ValueError('INVALID_SVG_VIEWBOX')
    for key in ('width', 'height', 'x', 'y'):
        if key in root.attrib:
            value = root.attrib[key]
            if not re.fullmatch(NUMBER+r'(?:px)?', value):
                raise ValueError('UNSUPPORTED_ROOT_LENGTH')
            number = float(value.removesuffix('px'))
            if not math.isfinite(number) or (key in ('x', 'y') and number != 0):
                raise ValueError('UNSUPPORTED_ROOT_OFFSET')
    if XML_SPACE in root.attrib and root.attrib[XML_SPACE] not in ('default', 'preserve'):
        raise ValueError('UNSUPPORTED_XML_SPACE')
    if 'style' in root.attrib:
        match = re.fullmatch(r'\s*enable-background\s*:\s*new\s+([^;]+)\s*;?\s*', root.attrib['style'])
        if not match or list(map(float, _numbers(match.group(1)))) != list(map(float, view)):
            raise ValueError('UNSUPPORTED_ROOT_CSS')
    output = ET.Element('svg', {'viewBox': ' '.join(view)})
    counts = {'groups': 0, 'paths': 0, 'polygons': 0}

    def paint(node, inherited_fill, inherited_rule):
        fill = node.get('fill', inherited_fill)
        rule = node.get('fill-rule', inherited_rule)
        if fill not in ('black', 'white', 'none') and not re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?', fill):
            raise ValueError('UNSUPPORTED_FILL')
        if rule not in ('nonzero', 'evenodd'):
            raise ValueError('UNSUPPORTED_FILL_RULE')
        if node.get('clip-rule', 'nonzero') not in ('nonzero', 'evenodd'):
            raise ValueError('UNSUPPORTED_CLIP_RULE')
        return fill, rule

    def visit(node, inherited_fill, inherited_rule, depth=0):
        if depth > 8:
            raise ValueError('SVG_NESTING_LIMIT')
        tag = local(node.tag)
        permitted = {'id', 'fill', 'fill-rule'}
        if tag == 'path': permitted |= {'d', 'clip-rule'}
        elif tag == 'polygon': permitted |= {'points', 'clip-rule'}
        elif tag != 'g': raise ValueError('UNSUPPORTED_SVG_ELEMENT_'+tag)
        if set(node.attrib) - permitted:
            raise ValueError('UNSUPPORTED_SVG_ATTRIBUTE')
        if (node.text or '').strip() or (node.tail or '').strip():
            raise ValueError('SVG_VISIBLE_TEXT_NOT_SUPPORTED')
        fill, rule = paint(node, inherited_fill, inherited_rule)
        if tag == 'g':
            counts['groups'] += 1
            if counts['groups'] > 100: raise ValueError('SVG_GROUP_LIMIT')
            for child in node: visit(child, fill, rule, depth+1)
            return
        if len(node): raise ValueError('SHAPE_CHILDREN_NOT_SUPPORTED')
        if tag == 'polygon':
            tokens = _numbers(node.get('points', ''))
            if len(tokens) < 6 or len(tokens) % 2 or len(tokens) > 2000:
                raise ValueError('INVALID_POLYGON')
            pairs = [' '.join(tokens[i:i+2]) for i in range(0, len(tokens), 2)]
            d = 'M'+pairs[0]+''.join(' L'+xy for xy in pairs[1:])+' Z'
            counts['polygons'] += 1
        else:
            d = node.get('d', '')
            if not d or len(d) > 100_000 or not re.fullmatch(r'[MmZzLlHhVvCcSsQqTtAaEe0-9+.,\s-]+', d):
                raise ValueError('UNSUPPORTED_PATH')
            if not all(math.isfinite(float(x)) and abs(float(x)) <= 1_000_000 for x in re.findall(NUMBER, d)):
                raise ValueError('NONFINITE_PATH')
            counts['paths'] += 1
        if counts['paths']+counts['polygons'] > 100:
            raise ValueError('SVG_SHAPE_LIMIT')
        ET.SubElement(output, 'path', {'d': d, 'fill': fill, 'fill-rule': rule})

    if (root.text or '').strip(): raise ValueError('SVG_VISIBLE_TEXT_NOT_SUPPORTED')
    fill, rule = paint(root, 'black', 'nonzero')
    for child in root: visit(child, fill, rule)
    if not len(output): raise ValueError('EMPTY_SVG')
    return ET.tostring(output, encoding='utf-8'), {
        **counts, 'xml_declarations_removed': declarations, 'comments_removed': comments,
        'geometry': 'path strings unchanged; polygon vertices closed exactly; groups without transforms flattened',
        'colors': 'original and inherited fills preserved',
        'viewBox': list(map(float, view)), 'redrawn_or_approximated': False,
        'visual_review': 'NOT_RUN',
    }
