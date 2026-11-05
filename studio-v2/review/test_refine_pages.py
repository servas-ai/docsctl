"""Pure contract tests. No PDF, font, browser, network or model execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import refine_pages as r
HERE=Path(__file__).resolve().parent
SPEC=json.loads((HERE/'refinement.json').read_text())

def matrix_fixture():
    keys=['Kernaufgabe','Canvas / Editor','Direkte PDF-Ausgabe','Tabellen',
          'Formelsatz','Eigene Marke','Stand in docsctl PR #1','Sinnvolle Systemrolle']
    return {'comparison':{'rows':[{'label':k,'cells':[{'text':'Test','status':'adapter'} for _ in range(4)]} for k in keys]}}

class CanvasRecorder:
    def __init__(self): self.links=[]
    def linkURL(self,*args,**kw): self.links.append(args)

class PainterRecorder:
    """Records layout commands; deliberately does not draw or emulate font metrics."""
    def __init__(self):
        self.events=[];self.texts=[];self.symbols=[];self.images=[]
        self.c=CanvasRecorder();self.h=595.2756;self.scale=1;self.page=0
    def begin(self): self.page+=1;self.events.append(('begin',))
    def end(self): self.events.append(('end',))
    def header(self,*args,**kw): self.events.append(('header',args))
    def kicker(self,*args,**kw): self.events.append(('kicker',args))
    def text(self,value,x,top,width,*args,**kw):
        if not 0 <= x < 842 or not 0 <= top < 550 or width <= 0: raise AssertionError('unbounded coordinate')
        self.texts.append(value);self.events.append(('text',x,top,width))
    def rect(self,*args,**kw): self.events.append(('rect',args,kw))
    def line(self,*args,**kw): self.events.append(('line',args,kw))
    def icon(self,*args,**kw): self.events.append(('icon',args,kw))
    def symbol(self,status,*args,**kw): self.symbols.append(status)
    def image(self,*args,**kw): self.images.append((args,kw))
    def links(self,*args,**kw): self.events.append(('links',args,kw))

class ReturnContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'a.txt').write_bytes(b'abc')
        self.receipt={'output_files':[{'path':'a.txt','bytes':3,'sha256':r.digest(b'abc')}]}
    def tearDown(self): self.tmp.cleanup()
    def test_valid_hash(self): self.assertEqual(len(r.verify_return(self.root,self.receipt)),1)
    def test_wrong_size(self):
        self.receipt['output_files'][0]['bytes']=4
        with self.assertRaises(ValueError):r.verify_return(self.root,self.receipt)
    def test_wrong_hash(self):
        self.receipt['output_files'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):r.verify_return(self.root,self.receipt)
    def test_duplicate_entry(self):
        self.receipt['output_files']*=2
        with self.assertRaises(ValueError):r.verify_return(self.root,self.receipt)
    def test_empty_manifest(self):
        with self.assertRaises(ValueError):r.verify_return(self.root,{'output_files':[]})
    def test_too_many_entries(self):
        with self.assertRaises(ValueError):r.verify_return(self.root,{'output_files':[{}]*201})
    def test_traversal(self):
        with self.assertRaises(ValueError):r.checked_path(self.root,'../a.txt')
    def test_absolute_path(self):
        with self.assertRaises(ValueError):r.checked_path(self.root,'/etc/passwd')
    def test_repeated_slash(self):
        with self.assertRaises(ValueError):r.checked_path(self.root,'d//a.txt')
    def test_dot_path(self):
        with self.assertRaises(ValueError):r.checked_path(self.root,'./a.txt')
    def test_symlink(self):
        (self.root/'link').symlink_to(self.root/'a.txt')
        with self.assertRaises(ValueError):r.checked_path(self.root,'link')
    def test_no_font_return(self):
        (self.root/'f.ttf').write_bytes(b'x')
        self.receipt={'output_files':[{'path':'f.ttf','bytes':1,'sha256':r.digest(b'x')}]}
        with self.assertRaises(ValueError):r.verify_return(self.root,self.receipt)

class SpecAndLayout(unittest.TestCase):
    def test_valid_spec(self): self.assertEqual(r.validate_spec(copy.deepcopy(SPEC))['schema'],1)
    def test_duplicate_providers(self):
        d=copy.deepcopy(SPEC);d['providers'][1]=d['providers'][0]
        with self.assertRaises(ValueError):r.validate_spec(d)
    def test_no_http_source(self):
        d=copy.deepcopy(SPEC);d['providers'][0]['documentation_url']='http://example.org'
        with self.assertRaises(ValueError):r.validate_spec(d)
    def test_no_url_credentials(self):
        d=copy.deepcopy(SPEC);d['providers'][0]['documentation_url']='https://user:pass@example.org'
        with self.assertRaises(ValueError):r.validate_spec(d)
    def test_no_source_query_secret(self):
        d=copy.deepcopy(SPEC);d['providers'][0]['documentation_url']='https://example.org/?key=secret'
        with self.assertRaises(ValueError):r.validate_spec(d)
    def test_review_order(self):
        d=copy.deepcopy(SPEC);d['flow']['nodes'][2:]=reversed(d['flow']['nodes'][2:])
        with self.assertRaises(ValueError):r.validate_spec(d)
    def test_no_auto_release(self):
        d=copy.deepcopy(SPEC);d['flow']['automatic_release']=True
        with self.assertRaises(ValueError):r.validate_spec(d)
    def test_copy_preserves_input(self):
        d=matrix_fixture();before=copy.deepcopy(d);r.matrix_rows(d,SPEC);self.assertEqual(d,before)
    def test_row_count_preserved(self):
        d=matrix_fixture();self.assertEqual(len(r.matrix_rows(d,SPEC)),len(d['comparison']['rows']))
    def test_pr_state_all_unknown(self):
        rows=r.matrix_rows(matrix_fixture(),SPEC);row=next(x for x in rows if x['label']=='Stand in docsctl PR #1')
        self.assertEqual([c['status'] for c in row['cells']],['unknown']*4)
    def test_bad_patch_width(self):
        d=copy.deepcopy(SPEC);d['row_patches']['Tabellen']=[]
        with self.assertRaises(ValueError):r.matrix_rows(matrix_fixture(),d)
    def test_four_legend_states(self): self.assertEqual(set(r.STATUS_LABELS),{'native','adapter','outside','unknown'})
    def test_matrix_records_all_four_symbols(self):
        p=PainterRecorder();r.page_matrix(p,matrix_fixture(),SPEC,{})
        self.assertEqual(p.symbols[-4:],['native','adapter','outside','unknown'])
        self.assertTrue(any(SPEC['checked_date'] in t for t in p.texts))
        self.assertEqual(len(p.c.links),4)
    def test_a2_uses_same_content(self):
        a,b=PainterRecorder(),PainterRecorder();r.page_matrix(a,matrix_fixture(),SPEC,{});r.page_matrix(b,matrix_fixture(),SPEC,{},True)
        self.assertEqual(a.texts,b.texts)
    def test_evidence_no_hero(self):
        p=PainterRecorder();r.page_evidence(p,{k:{'path':Path(k),'pixel_size':[300,100],'display_dpi':300} for k in ['old_identity','new_identity','old_table','new_table']})
        self.assertEqual(len(p.images),4)
        self.assertTrue(all('actual_pdf_' in item[0][-1] for item in p.images))
        self.assertTrue(any('Layoutvergleich, nicht gleiche Daten' in t for t in p.texts))
    def test_diagram_has_actual_owners(self):
        p=PainterRecorder();r.page_architecture(p,SPEC)
        for node in SPEC['flow']['nodes']:
            self.assertIn(node['owner'],p.texts);self.assertIn(node['input'],p.texts);self.assertIn(node['output'],p.texts)
        self.assertIn('PR bleibt Draft',p.texts)
    def test_mermaid_matches_review_semantics(self):
        s=r.architecture_mmd(SPEC)
        self.assertIn('source --> render --> candidate --> review',s)
        self.assertIn('Quellenbefund| source',s);self.assertIn('PR-Draft',s)
    def test_mermaid_rejects_label_injection(self):
        d=copy.deepcopy(SPEC);d['flow']['nodes'][0]['title']='x" --> evil'
        with self.assertRaises(ValueError):r.architecture_mmd(d)
    def test_no_cover_implementation(self):
        tree=ast.parse((HERE/'refine_pages.py').read_text())
        self.assertNotIn('page_cover',[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))])

class SVGContract(unittest.TestCase):
    good=b'<svg viewBox="0 0 10 10"><path d="M0 0L10 10Z" fill="#123456"/></svg>'
    def test_original_geometry_and_color(self):
        view,paths=r.simple_svg(self.good);self.assertEqual(view,[0,0,10,10]);self.assertEqual(paths[0],('M0 0L10 10Z','#123456','nonzero'))
    def test_script_rejected(self):
        with self.assertRaises(ValueError):r.simple_svg(b'<svg viewBox="0 0 10 10"><script/></svg>')
    def test_external_image_rejected(self):
        with self.assertRaises(ValueError):r.simple_svg(b'<svg viewBox="0 0 10 10"><image href="http://example.org/a"/></svg>')
    def test_entities_rejected(self):
        with self.assertRaises(ValueError):r.simple_svg(b'<!DOCTYPE svg><svg/>')
    def test_transform_rejected(self):
        with self.assertRaises(ValueError):r.simple_svg(b'<svg viewBox="0 0 10 10"><path d="M0 0" transform="scale(2)"/></svg>')
    def test_nonfinite_view_rejected(self):
        with self.assertRaises(ValueError):r.simple_svg(self.good.replace(b'10 10',b'inf 10',1))
    def test_css_rejected(self):
        with self.assertRaises(ValueError):r.simple_svg(self.good.replace(b'fill="#123456"',b'style="fill:red"'))
    def test_invalid_hex_rejected(self):
        with self.assertRaises(ValueError):r.simple_svg(self.good.replace(b'#123456',b'#12345'))
    def test_oversize_rejected(self):
        with self.assertRaises(ValueError):r.simple_svg(b'x'*300001)

if __name__=='__main__': unittest.main(verbosity=2)
