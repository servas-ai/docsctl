"""Offline data/geometry contracts. Not a PDF build or typography/render test."""
import ast
import copy
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import repair_assets as a
import refine_pages as r
from test_refine_pages import PainterRecorder, matrix_fixture, SPEC

HERE=Path(__file__).resolve().parent

class SVGRepair(unittest.TestCase):
    source=b'''<?xml version="1.0" encoding="utf-8"?>
<!-- metadata only --><svg xmlns="http://www.w3.org/2000/svg" id="Layer_1"
x="0px" y="0px" viewBox="0 0 100 40" style="enable-background:new 0 0 100 40;" xml:space="preserve">
<g><g><path d="M1,2h5v6Z"/></g></g>
<g fill="#123456"><polygon points="10,10 20,30 40,20 10,10"/></g></svg>'''
    def parse(self,s):return a.normalize_filled_svg(s)
    def test_inert_header_and_groups_supported(self):
        raw,meta=self.parse(self.source);view,paths=r.simple_svg(raw)
        self.assertEqual(view,[0,0,100,40]);self.assertEqual(meta['groups'],3)
        self.assertEqual(meta['paths'],1);self.assertEqual(meta['polygons'],1)
        self.assertEqual(meta['xml_declarations_removed'],1);self.assertEqual(meta['comments_removed'],1)
    def test_path_bytes_and_default_black_preserved(self):
        raw,_=self.parse(self.source);self.assertEqual(r.simple_svg(raw)[1][0],('M1,2h5v6Z','black','nonzero'))
    def test_exact_polygon_vertices_and_fill(self):
        raw,_=self.parse(self.source);self.assertEqual(r.simple_svg(raw)[1][1],('M10 10 L20 30 L40 20 L10 10 Z','#123456','nonzero'))
    def test_inherited_fill_rule(self):
        raw,_=self.parse(self.source.replace(b'<g fill=',b'<g fill-rule="evenodd" fill='))
        self.assertEqual(r.simple_svg(raw)[1][1][2],'evenodd')
    def test_no_geometry_approximation_claim(self):self.assertFalse(self.parse(self.source)[1]['redrawn_or_approximated'])
    def test_deterministic_normalization(self):self.assertEqual(self.parse(self.source),self.parse(self.source))
    def test_external_entities_rejected(self):
        with self.assertRaises(ValueError):self.parse(b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg/>')
    def test_processing_instruction_rejected(self):
        with self.assertRaises(ValueError):self.parse(b'<?xml-stylesheet href="https://example.org/a"?><svg/>')
    def test_script_rejected(self):
        with self.assertRaises(ValueError):self.parse(b'<svg viewBox="0 0 10 10"><script/></svg>')
    def test_image_rejected(self):
        with self.assertRaises(ValueError):self.parse(b'<svg viewBox="0 0 10 10"><image href="a"/></svg>')
    def test_use_rejected(self):
        with self.assertRaises(ValueError):self.parse(b'<svg viewBox="0 0 10 10"><use href="#a"/></svg>')
    def test_group_transform_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.source.replace(b'<g>',b'<g transform="scale(2)">',1))
    def test_css_fill_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.source.replace(b'enable-background:new 0 0 100 40;',b'fill:red;'))
    def test_nonzero_root_offset_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.source.replace(b'x="0px"',b'x="2px"'))
    def test_event_attribute_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.source.replace(b'<g>',b'<g onload="evil()">',1))
    def test_polygon_odd_coordinate_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.source.replace(b'10,10 20,30 40,20 10,10',b'0,0 1,1 2'))
    def test_nonfinite_coordinates_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.source.replace(b'20,30',b'20,1e999'))
    def test_foreign_namespace_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.source.replace(b'http://www.w3.org/2000/svg',b'https://evil.invalid/svg'))
    def test_oversize_source_rejected(self):
        with self.assertRaises(ValueError):self.parse(b'x'*300001)
    def test_not_an_automatic_identity_review(self):self.assertEqual(self.parse(self.source)[1]['visual_review'],'NOT_RUN')

class GlyphRepair(unittest.TestCase):
    def test_zero_is_missing(self):self.assertEqual(a.missing_glyphs('A\u2260B',{65:1,0x2260:0,66:2}),['U+2260'])
    def test_absent_is_missing(self):self.assertEqual(a.missing_glyphs('A\u2260B',{65:1,66:2}),['U+2260'])
    def test_real_mapping_accepted(self):self.assertEqual(a.missing_glyphs('A\u2260B',{65:1,0x2260:3,66:2}),[])
    def test_whitespace_layout_is_not_a_glyph(self):self.assertEqual(a.missing_glyphs('\n\t\r',{}),[])
    def test_null_character_is_not_ignored(self):self.assertEqual(a.missing_glyphs('\0',{}),['U+0000'])
    def test_replacement_character_not_silently_allowed(self):self.assertEqual(a.missing_glyphs('\ufffd',{}),['U+FFFD'])
    def test_footnote_plain_language(self):
        self.assertNotIn('\u2260',a.FOOTNOTE);self.assertIn('bedeutet nicht',a.FOOTNOTE)
    def test_matrix_uses_fixed_footnote(self):
        p=PainterRecorder();r.page_matrix(p,matrix_fixture(),SPEC,{})
        self.assertIn(a.FOOTNOTE,p.texts);self.assertFalse(any('\u2260' in t for t in p.texts))

class PlacementRepair(unittest.TestCase):
    def test_legacy_small_crop_not_enlarged(self):
        w,h=a.bitmap_box((252,67),357,114);self.assertAlmostEqual(w,60.48);self.assertAlmostEqual(h,16.08)
    def test_hires_identity_within_same_frame(self):
        w,h=a.bitmap_box((983,264),357,114);self.assertAlmostEqual(w,235.92);self.assertLessEqual(h,114)
    def test_page_scale_respected(self):
        w,h=a.bitmap_box((300,100),357,114,page_scale=2);self.assertEqual((w,h),(36,12))
    def test_aspect_ratio_preserved(self):
        w,h=a.bitmap_box((1000,250),100,100);self.assertEqual(w/h,4)
    def test_invalid_dimensions_rejected(self):
        for size in [(0,1),(-1,2),(float('nan'),1)]:
            with self.assertRaises(ValueError):a.bitmap_box(size,100,100)
    def test_region_reuses_exact_normalized_selection(self):
        p=a.crop_plan((840,600),(1800,1286),(83,50,335,117),600)
        self.assertAlmostEqual(p['pdf_box_pt'][0],83/1800*840)
        self.assertEqual(p['dpi'],600)
    def test_crop_bounds_rejected(self):
        with self.assertRaises(ValueError):a.crop_plan((840,600),(1800,1286),(-1,0,300,30),600)
    def test_crop_pixel_budget(self):
        with self.assertRaises(ValueError):a.crop_plan((840,600),(1800,1286),(0,0,1800,1286),600)
    def test_no_crop_metadata_rejected(self):
        with self.assertRaises(ValueError):r.place_evidence(PainterRecorder(),Path('fake'),0,0,100,100,'crop')
    def test_metadata_centers_smaller_bitmap(self):
        p=PainterRecorder();r.place_evidence(p,{'path':Path('fake'),'pixel_size':[300,100],'display_dpi':300},44,219,357,114,'crop')
        args=p.images[0][0];self.assertEqual(args[3:5],(72,24));self.assertGreater(args[1],44)

class RoleRepair(unittest.TestCase):
    def test_typst_not_wordmark(self):
        spec=json.loads((HERE/'provider-assets.json').read_text())
        self.assertEqual(next(x for x in spec['assets'] if x['id']=='typst')['role'],'readme_banner')
    def test_banner_not_drawn_in_matrix(self):
        p=PainterRecorder()
        with patch.object(r,'draw_provider') as draw:
            r.page_matrix(p,matrix_fixture(),SPEC,{'Typst':{'role':'readme_banner'}})
            draw.assert_not_called()
        self.assertIn('Typst',p.texts)
    def test_banner_label_explicit(self):self.assertIn('keine freistehende Wortmarke',a.ROLE_LABELS['readme_banner'])
    def test_pdfme_stays_favicon(self):
        spec=json.loads((HERE/'provider-assets.json').read_text())
        self.assertEqual(next(x for x in spec['assets'] if x['id']=='pdfme')['role'],'favicon')
    def test_all_provider_bytes_pinned(self):
        spec=json.loads((HERE/'provider-assets.json').read_text())
        for x in spec['assets']:
            self.assertEqual(len(x['expected_source_sha256']),64);self.assertGreater(x['expected_bytes'],0)
    def test_no_added_cover_function(self):
        for file in ('repair_assets.py','refine_pages.py'):
            t=ast.parse((HERE/file).read_text())
            self.assertFalse(any(isinstance(n,ast.FunctionDef) and n.name=='page_cover' for n in ast.walk(t)))
    def test_no_network_or_process_imports_in_pure_repair(self):
        t=ast.parse((HERE/'repair_assets.py').read_text());names=[]
        for n in ast.walk(t):
            if isinstance(n,ast.Import):names += [x.name for x in n.names]
            elif isinstance(n,ast.ImportFrom):names += [n.module or '']
        self.assertFalse(any(x.startswith(('socket','urllib','requests','subprocess')) for x in names))

if __name__=='__main__':unittest.main(verbosity=2)
