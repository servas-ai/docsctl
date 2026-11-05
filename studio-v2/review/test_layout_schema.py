"""Regression against real returned record shapes; no PDF/font/browser rendering."""
import copy
import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import full_report as full
import refine_pages as refine

FIXTURE=json.loads((Path(__file__).parent/'painter-record-fixtures.json').read_text())
SIZES=[(841.8898,595.2756)]*2

def line(box,page=1):return {'page':page,'call':1,'bbox':box}

class LayoutSchemaTests(unittest.TestCase):
    def test_real_raster_contract(self):
        r=full.layout_audit([], [FIXTURE['raster']], SIZES)
        self.assertEqual(r['status'],'PASS_GEOMETRY_ONLY');self.assertEqual(r['checked_images'],1)
    def test_real_legacy_vector_fails_closed_not_keyerror(self):
        r=full.layout_audit([line([0,0,1,1],2)],[FIXTURE['legacy_vector']],SIZES)
        self.assertEqual(r['status'],'FAIL_GEOMETRY');self.assertEqual(r['failures'][0]['gate'],'IMAGE_RECORD_SCHEMA')
        self.assertEqual(r['failures'][0]['missing'],['x_pt','y_top_pt','width_pt','height_pt'])
    def test_geometryless_image_fails_even_without_text(self):
        self.assertEqual(full.layout_audit([],[FIXTURE['legacy_vector']],SIZES)['status'],'FAIL_GEOMETRY')
    def test_real_raster_collision_detected(self):
        im=FIXTURE['raster'];x,y=im['x_pt'],im['y_top_pt']
        self.assertEqual(full.layout_audit([line([x+1,y+1,x+5,y+5])],[im],SIZES)['failures'][0]['gate'],'TEXT_IMAGE_COLLISION')
    def test_separate_text_pass(self):self.assertFalse(full.layout_audit([line([10,100,50,110])],[FIXTURE['raster']],SIZES)['failures'])
    def test_missing_each_coordinate(self):
        for k in ('x_pt','y_top_pt','width_pt','height_pt'):
            with self.subTest(k=k):
                im=copy.deepcopy(FIXTURE['raster']);del im[k]
                self.assertEqual(full.layout_audit([],[im],SIZES)['status'],'FAIL_GEOMETRY')
    def test_bad_coordinates_fail(self):
        for v in (None,'42',True,float('nan'),float('inf')):
            with self.subTest(v=v):
                im={**FIXTURE['raster'],'x_pt':v}
                self.assertEqual(full.layout_audit([],[im],SIZES)['status'],'FAIL_GEOMETRY')
    def test_nonpositive_dimensions_fail(self):
        for k in ('width_pt','height_pt'):
            for v in (0,-1):self.assertEqual(full.layout_audit([],[{**FIXTURE['raster'],k:v}],SIZES)['status'],'FAIL_GEOMETRY')
    def test_outside_image_fails(self):
        r=full.layout_audit([],[{**FIXTURE['raster'],'x_pt':900}],SIZES)
        self.assertEqual(r['failures'][0]['gate'],'IMAGE_OUTSIDE_PAGE')
    def test_invalid_page_fails(self):
        for p in (0,-1,3,True,1.5):self.assertEqual(full.layout_audit([],[{**FIXTURE['raster'],'page':p}],SIZES)['status'],'FAIL_GEOMETRY')
    def test_text_guard_preserved(self):self.assertEqual(full.layout_audit([line([0,0,900,20])],[],SIZES)['failures'][0]['gate'],'TEXT_OUTSIDE_PAGE')
    def test_no_cross_page_collision(self):self.assertFalse(full.layout_audit([line([42,30,60,40],2)],[FIXTURE['raster']],SIZES)['failures'])
    def test_inputs_not_mutated(self):
        images=[copy.deepcopy(FIXTURE['raster'])];before=copy.deepcopy(images)
        full.layout_audit([],images,SIZES);self.assertEqual(images,before)
    def test_image_sum_overflow_fails(self):
        self.assertEqual(full.layout_audit([],[{**FIXTURE['raster'],'x_pt':1e308,'width_pt':1e308}],SIZES)['status'],'FAIL_GEOMETRY')

class VectorProducerTests(unittest.TestCase):
    def produce(self,scale):
        draws=[]
        class Shape:
            def __init__(self,*a,**k):pass
            def add(self,*a):pass
            def translate(self,*a):pass
            def scale(self,*a):pass
        modules={}
        for n in ('reportlab.graphics.svgpath','reportlab.graphics.renderPDF','reportlab.graphics.shapes','reportlab.lib.colors'):
            modules[n]=types.ModuleType(n)
        modules['reportlab.graphics.svgpath'].SvgPath=Shape
        modules['reportlab.graphics.shapes'].Drawing=Shape;modules['reportlab.graphics.shapes'].Group=Shape
        modules['reportlab.graphics.renderPDF'].draw=lambda *args:draws.append(args)
        modules['reportlab.lib.colors'].toColor=lambda s:s
        # Inert synthetic path with the actual returned Puck viewBox aspect; no brand bytes.
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'synthetic.svg';path.write_text('<svg viewBox="0 0 1300 326"><path d="M0 0L1300 0L1300 326Z" fill="black"/></svg>')
            p=types.SimpleNamespace(scale=scale,h=595.2756,page=2,images=[],c=object())
            with patch.dict(sys.modules,modules):
                refine.draw_provider(p,{'path':str(path),'kind':'svg_paths'},238,188,113,20)
        return p,draws
    def test_real_producer_writes_fitted_box(self):
        p,draws=self.produce(1);im=p.images[0];self.assertEqual(len(draws),1)
        self.assertAlmostEqual(im['width_pt'],1300*20/326)
        self.assertAlmostEqual(im['height_pt'],20)
        self.assertAlmostEqual(im['x_pt'],238+(113-im['width_pt'])/2)
        self.assertAlmostEqual(im['y_top_pt'],188)
        self.assertAlmostEqual(draws[0][2],im['x_pt'])
        self.assertAlmostEqual(draws[0][3],p.h-im['y_top_pt']-im['height_pt'])
    def test_a2_scaled_once(self):
        a,_=self.produce(1);b,_=self.produce(2)
        for k in ('x_pt','y_top_pt','width_pt','height_pt'):self.assertAlmostEqual(b.images[0][k],2*a.images[0][k])
    def test_producer_to_audit_end_to_end_collision(self):
        p,_=self.produce(1);im=p.images[0];x,y=im['x_pt'],im['y_top_pt']
        r=full.layout_audit([line([x+2,y+2,x+10,y+10],2)],p.images,SIZES)
        self.assertEqual(r['failures'][0]['gate'],'TEXT_IMAGE_COLLISION')
    def test_producer_to_audit_end_to_end_clear(self):
        p,_=self.produce(2)
        self.assertEqual(full.layout_audit([line([0,0,10,10],2)],p.images,[(1683.7796,1190.5512)]*2)['status'],'PASS_GEOMETRY_ONLY')

if __name__=='__main__':unittest.main()
