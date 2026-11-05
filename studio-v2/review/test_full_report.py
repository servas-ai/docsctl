"""Pure tests: no PDF rendering, font loading, network, browser or VM calls."""
import ast
import copy
import inspect
import json
import unittest
from pathlib import Path
import full_report as f


def fixture():
    return {'schema':1,'date':'2026-11-05','title':'Report',
      'template':{'html_sha256':'a'*64,'script_sha256':'b'*64,'sources_sha256':'c'*64,'sections':11},
      'pages':[{'id':k,'title':k.title(),'kicker':'Section','note':'Source-bound example.',
                'source_ids':['S01'],'rows':[],'columns':['Column']*({'brand':4,'identity':3,'assets':3,'templates':6,'science':3,'quality':3,'prompts':3}.get(k,0)),'legacy_section':i,'change':'Preserve content.'} for i,k in enumerate(f.PAGE_IDS,1)],
      'sources':[{'id':'S01','title':'Primary','url':'https://example.org/docs','provenance':'test fixture'}],
      'facts':{'original':'missing','status':'not accepted'}}


class Canvas:
    def __init__(self):self.links=[]
    def linkURL(self,*a,**k):self.links.append((a,k))


class Painter:
    scale=1;h=595.2756;logo='external-logo'
    def __init__(self):self.c=Canvas();self.calls=[];self.page=0
    def begin(self):self.page+=1
    def end(self):self.calls.append(('end',))
    def header(self,*a):self.calls.append(('header',*a))
    def kicker(self,*a):self.calls.append(('kicker',*a))
    def text(self,*a,**kw):self.calls.append(('text',*a));return 10
    def rect(self,*a,**kw):self.calls.append(('rect',*a))
    def line(self,*a,**kw):self.calls.append(('line',*a))
    def image(self,*a,**kw):self.calls.append(('image',*a))
    def icon(self,*a,**kw):self.calls.append(('icon',*a))
    def symbol(self,*a,**kw):self.calls.append(('symbol',*a))
    def links(self,*a,**kw):self.calls.append(('links',*a))


class Refiner:
    STATUS_LABELS={'native':'Built in'}
    def __init__(self):self.calls=[]
    def page_matrix(self,p,*a,**kw):self.calls.append('matrix');p.begin();p.end()
    def page_architecture(self,p,*a,**kw):self.calls.append('flow');p.begin();p.end()
    def draw_provider(self,*a):self.calls.append(('asset',a))
    def matrix_rows(self,*a):return [{'label':'Role','cells':[{'text':'Example','status':'native'}]*4}]
    def architecture_mmd(self,*a):return 'flowchart LR\n  A --> B\n'


class Base:
    def __init__(self):self.cover_calls=0
    def page_cover(self,p,*a):self.cover_calls+=1;p.begin();p.end()


class ContractTests(unittest.TestCase):
    def test_valid(self):self.assertEqual(f.validate(fixture())['schema'],1)
    def test_no_mutation(self):d=fixture();r=f.validate(d);r['title']='changed';self.assertEqual(d['title'],'Report')
    def test_eleven_topics(self):
        d=fixture();d['pages'].pop()
        with self.assertRaises(ValueError):f.validate(d)
    def test_order(self):
        d=fixture();d['pages'][1],d['pages'][2]=d['pages'][2],d['pages'][1]
        with self.assertRaises(ValueError):f.validate(d)
    def test_legacy_binding(self):
        d=fixture();d['pages'][1]['legacy_section']=9
        with self.assertRaises(ValueError):f.validate(d)
    def test_source_required(self):
        d=fixture();d['pages'][0]['source_ids']=['S99']
        with self.assertRaises(ValueError):f.validate(d)
    def test_source_no_auth(self):
        d=fixture();d['sources'][0]['url']='https://user:pass@example.org'
        with self.assertRaises(ValueError):f.validate(d)
    def test_no_script(self):
        d=fixture();d['pages'][0]['note']='<script>bad</script>'
        with self.assertRaises(ValueError):f.validate(d)
    def test_no_shortcode(self):
        d=fixture();d['pages'][0]['note']='{{< include secret >}}'
        with self.assertRaises(ValueError):f.validate(d)
    def test_no_unknown_fields(self):
        d=fixture();d['run']='command'
        with self.assertRaises(ValueError):f.validate(d)
    def test_no_unknown_page_field(self):
        d=fixture();d['pages'][0]['eval']='command'
        with self.assertRaises(ValueError):f.validate(d)
    def test_bound_row_count(self):
        d=fixture();d['pages'][1]['rows']=[[]]*19
        with self.assertRaises(ValueError):f.validate(d)
    def test_ragged_table(self):
        d=fixture();d['pages'][1]['columns']=['one'];d['pages'][1]['rows']=[['a','b']]
        with self.assertRaises(ValueError):f.validate(d)
    def test_pin_required(self):
        d=fixture();d['template']['html_sha256']='short'
        with self.assertRaises(ValueError):f.validate(d)
    def test_nul_rejected(self):
        d=fixture();d['title']='bad\0'
        with self.assertRaises(ValueError):f.validate(d)
    def test_inert_html(self):
        x='<script>not executed</script>'+''.join('<section class="page"><h1>Topic</h1></section>' for _ in range(11))
        self.assertEqual(f.template_inventory(x)['section_count'],11)
    def test_wrong_template(self):
        with self.assertRaises(ValueError):f.template_inventory('<section><h1>Other</h1></section>')
    def test_48px_small(self):self.assertEqual(f.raster_box([48,48],(140,53)),(11.52,11.52))
    def test_A2_keeps_same_pixel_density(self):self.assertEqual(f.raster_box([48,48],(140,53),2),(5.76,5.76))
    def test_no_upscale_beyond_box(self):self.assertEqual(f.raster_box([1200,600],(100,60)),(100,50))
    def test_bad_pixels(self):
        with self.assertRaises(ValueError):f.raster_box([0,4],(10,10))
    def test_bad_table_geometry(self):
        with self.assertRaises(ValueError):f.table(Painter(),{'columns':['a'],'rows':[]},[700])
    def test_table_cannot_cross_footer(self):
        with self.assertRaises(ValueError):f.table(Painter(),{'columns':['a'],'rows':[['x']]*18},[754])
    def test_out_of_bounds(self):
        r=f.layout_audit([{'page':1,'call':1,'bbox':[0,0,101,10]}],[],[(100,100)])
        self.assertEqual(r['failures'][0]['gate'],'TEXT_OUTSIDE_PAGE')
    def test_collision(self):
        lines=[{'page':1,'call':i,'bbox':[0,0,20,10]} for i in (1,2)]
        self.assertEqual(f.layout_audit(lines,[],[(100,100)])['failures'][0]['gate'],'TEXT_COLLISION')
    def test_no_collision_between_pages(self):
        lines=[{'page':i,'call':i,'bbox':[0,0,20,10]} for i in (1,2)]
        self.assertEqual(f.layout_audit(lines,[],[(100,100)]*2)['failures'],[])
    def test_image_collision(self):
        r=f.layout_audit([{'page':1,'call':1,'bbox':[0,0,20,10]}],[{'page':1,'x_pt':5,'y_top_pt':5,'width_pt':20,'height_pt':20,'role':'test'}],[(100,100)])
        self.assertEqual(r['failures'][0]['gate'],'TEXT_IMAGE_COLLISION')
    def test_good_geometry_not_design_pass(self):self.assertEqual(f.layout_audit([],[],[(100,100)])['status'],'PASS_GEOMETRY_ONLY')
    def test_cover_delegated_once(self):
        p=Painter();r=Refiner();b=Base();d=fixture()
        # Identity rows required by the four-role presentation.
        d['pages'][4]['columns']=['name','role','limit'];d['pages'][4]['rows']=[[x,'role','limit'] for x in ('Puck','OpenUI','pdfme','Typst')]
        f.render_full(p,d,{}, {},{},'external-hero',b,r)
        self.assertEqual(b.cover_calls,1);self.assertEqual(p.page,11);self.assertEqual(r.calls,['matrix','flow'])
    def test_banner_not_wordmark(self):
        p=Painter();r=Refiner();d=fixture();page=d['pages'][4]
        page['rows']=[[x,'role','limit'] for x in ('Puck','OpenUI','pdfme','Typst')]
        f.identity_page(p,page,d,{'Typst':{'role':'readme_banner','kind':'raster'}},r)
        self.assertFalse(r.calls)
    def test_favicon_source_sized(self):
        p=Painter();r=Refiner();d=fixture();page=d['pages'][4];page['rows']=[[x,'role','limit'] for x in ('Puck','OpenUI','pdfme','Typst')]
        f.identity_page(p,page,d,{'pdfme':{'role':'favicon','kind':'raster','pixel_size':[48,48]}},r)
        self.assertEqual(r.calls[0][1][-2:],(11.52,11.52))
    def test_export_eleven_chapters(self):
        out=f.export_v1(fixture(),{},Refiner(),{'providers':[{'name':x} for x in 'ABCD']})
        self.assertEqual(len(out),12);self.assertIn('schema: 1',out['docs.yml'])
    def test_export_no_brand_or_quarto_config(self):
        out=f.export_v1(fixture(),{},Refiner(),{'providers':[{'name':x} for x in 'ABCD']})
        self.assertTrue(all(k.endswith('.md') or k=='docs.yml' for k in out))
    def test_export_one_h1(self):
        out=f.export_v1(fixture(),{},Refiner(),{'providers':[{'name':x} for x in 'ABCD']})
        self.assertTrue(all(sum(l.startswith('# ') for l in v.splitlines())==1 for k,v in out.items() if k.endswith('.md')))
    def test_export_mermaid_caption(self):
        out=f.export_v1(fixture(),{},Refiner(),{'providers':[{'name':x} for x in 'ABCD']})
        self.assertIn('```mermaid',out['03-flow.md']);self.assertIn('*Abbildung:',out['03-flow.md'])
    def test_export_table_caption(self):
        out=f.export_v1(fixture(),{},Refiner(),{'providers':[{'name':x} for x in 'ABCD']})
        self.assertIn('*Tabelle:',out['01-tools.md'])
    def test_no_renderer_or_network_imports(self):
        tree=ast.parse(inspect.getsource(f));names=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):names += [x.name for x in n.names]
            elif isinstance(n,ast.ImportFrom):names.append(n.module)
        self.assertFalse(any(x.startswith(('reportlab','subprocess','requests','socket','playwright')) for x in names))
    def test_glyph_offender_not_reintroduced(self):self.assertNotIn('\u2260',inspect.getsource(f))

if __name__=='__main__':unittest.main(verbosity=2)
