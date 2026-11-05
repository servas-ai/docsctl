import copy, io, json, threading, unittest, urllib.request, urllib.error, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from core import validate, load_document, export_v1, validate_patch, InvalidDocument, KINDS, mermaid_safe
from server import Handler
from brand_probe import extract, Links

def fixture():
    return {'version':2,'title':'Study','subtitle':'Demo only','author':'Research team','date':'2026-11-05','format':'portrait',
            'theme':{'accent':'#52606d','paper':'#ffffff','ink':'#1a1a1a','font':'Arial'},
            'pages':[{'id':'p1','kind':'cover','title':'Study','body':'','art':0,'blur':0,'mermaid':''},
                     {'id':'p2','kind':'architecture','title':'Architecture','body':'Test source','art':0,'blur':0,'mermaid':'flowchart LR\nA[Source] --> B[Review]'}]}

class ContractTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate(fixture())['version'],2)
    def test_input_not_mutated(self):
        d=fixture();before=copy.deepcopy(d);validate(d);self.assertEqual(d,before)
    def test_unknown_root(self):
        d=fixture();d['execute']='code'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_unknown_theme(self):
        d=fixture();d['theme']['url']='https://example.org'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_color_injection(self):
        d=fixture();d['theme']['accent']='red;url(x)'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_font_injection(self):
        d=fixture();d['theme']['font']='Arial"; color:red'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_duplicate_ids(self):
        d=fixture();d['pages'][1]['id']='p1'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_unknown_page_kind(self):
        d=fixture();d['pages'][0]['kind']='javascript'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_unknown_page_key(self):
        d=fixture();d['pages'][0]['html']='<script>'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_invalid_date(self):
        d=fixture();d['date']='2026-02-31'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_compact_date_rejected(self):
        d=fixture();d['date']='20261105'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_non_string_font_rejected(self):
        d=fixture();d['theme']['font']=None
        with self.assertRaises(InvalidDocument):validate(d)
    def test_oversize_title(self):
        d=fixture();d['title']='x'*141
        with self.assertRaises(InvalidDocument):validate(d)
    def test_multiline_title(self):
        d=fixture();d['title']='x\ny'
        with self.assertRaises(InvalidDocument):validate(d)
    def test_nan_blur(self):
        d=fixture();d['pages'][0]['blur']=float('nan')
        with self.assertRaises(InvalidDocument):validate(d)
    def test_bool_art(self):
        d=fixture();d['pages'][0]['art']=True
        with self.assertRaises(InvalidDocument):validate(d)
    def test_no_pages(self):
        d=fixture();d['pages']=[]
        with self.assertRaises(InvalidDocument):validate(d)
    def test_too_many_pages(self):
        d=fixture();d['pages']=[{**d['pages'][0],'id':f'p{i}'} for i in range(61)]
        with self.assertRaises(InvalidDocument):validate(d)
    def test_all_kinds(self):
        for kind in KINDS:
            d=fixture();d['pages'][0]['kind']=kind;validate(d)
    def test_bytes_limit(self):
        with self.assertRaises(InvalidDocument):load_document(b' '*1_048_577)
    def test_bad_utf8(self):
        with self.assertRaises(InvalidDocument):load_document(b'\xff')
    def test_duplicate_keys(self):
        with self.assertRaises(InvalidDocument):load_document(b'{"version":2,"version":2}')
    def test_patch_good(self):self.assertEqual(validate_patch({'title':'New'}),{'title':'New'})
    def test_patch_bad_key(self):
        with self.assertRaises(InvalidDocument):validate_patch({'html':'<b>x</b>'})
    def test_patch_empty(self):
        with self.assertRaises(InvalidDocument):validate_patch({})
    def test_patch_limit(self):
        with self.assertRaises(InvalidDocument):validate_patch({'title':'x'*141})

class ExportTests(unittest.TestCase):
    def test_deterministic_zip(self):self.assertEqual(export_v1(fixture()),export_v1(fixture()))
    def test_v1_manifest(self):
        with zipfile.ZipFile(io.BytesIO(export_v1(fixture()))) as z:
            self.assertIn('docs/docs.yml',z.namelist());self.assertIn('schema: 1',z.read('docs/docs.yml').decode())
    def test_mermaid_and_caption(self):
        with zipfile.ZipFile(io.BytesIO(export_v1(fixture()))) as z:
            text=z.read('docs/01-architecture.md').decode()
            self.assertIn('```mermaid',text);self.assertIn('*Abbildung:',text)
    def test_matrix_preserved(self):
        d=fixture();d['pages'][1]['kind']='matrix';d['pages'][1]['mermaid']=''
        with zipfile.ZipFile(io.BytesIO(export_v1(d))) as z:
            body=z.read('docs/01-matrix.md').decode();self.assertIn('Offline-Inhalte',body);self.assertIn('*Tabelle:',body)
    def test_references_preserved(self):
        d=fixture();d['pages'][1]['kind']='references';d['pages'][1]['mermaid']=''
        with zipfile.ZipFile(io.BytesIO(export_v1(d))) as z:self.assertIn('https://github.com/puckeditor/puck',z.read('docs/01-references.md').decode())
    def test_cover_only(self):
        d=fixture();d['pages']=d['pages'][:1]
        with zipfile.ZipFile(io.BytesIO(export_v1(d))) as z:self.assertIn('docs/index.md',z.namelist())
    def test_no_brand_fonts_or_images_exported(self):
        with zipfile.ZipFile(io.BytesIO(export_v1(fixture()))) as z:
            self.assertTrue(all(n.endswith(('.md','.yml')) for n in z.namelist()))
            self.assertNotIn('#52606d',z.read('docs/docs.yml').decode())
    def test_script_escaped(self):
        d=fixture();d['pages'][1]['body']='<script>alert(1)</script>'
        with zipfile.ZipFile(io.BytesIO(export_v1(d))) as z:self.assertNotIn('<script>',z.read('docs/01-architecture.md').decode())
    def test_mermaid_directive_rejected(self):
        with self.assertRaises(InvalidDocument):mermaid_safe('flowchart LR\n%%{init: {}}%%')
    def test_mermaid_click_rejected(self):
        with self.assertRaises(InvalidDocument):mermaid_safe('flowchart LR\nclick A javascript:alert(1)')
    def test_mermaid_fence_rejected(self):
        with self.assertRaises(InvalidDocument):mermaid_safe('flowchart LR\n```html')
    def test_mermaid_unknown_rejected(self):
        with self.assertRaises(InvalidDocument):mermaid_safe('<script>x</script>')

class ProbeTests(unittest.TestCase):
    def test_colors(self):self.assertEqual(extract(':root{--accent:#123ABC} body{color:#fff}','https://example.org')['hex_candidates'][0]['value'],'#123ABC')
    def test_family(self):self.assertIn('Example Sans',extract("font-family:'Example Sans';",'x')['font_families'])
    def test_fingerprint(self):self.assertEqual(len(extract('abc','x')['sha256']),64)
    def test_css_only(self):
        p=Links();p.feed('<link rel="stylesheet" href="a.css"><script src="a.js"></script><link rel="preload" href="font.woff2">');self.assertEqual(p.css,['a.css'])

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.server.csrf='test-only';cls.server.model='';cls.server.ollama_port=11434
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,data=None,headers=None):
        req=urllib.request.Request(self.base+path,data=data,headers=headers or {})
        try:
            with urllib.request.urlopen(req,timeout=3) as r:return r.status,r.read(),dict(r.headers)
        except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
    def headers(self):return {'Origin':self.base,'X-Studio-Token':'test-only','Content-Type':'application/json'}
    def test_index(self):self.assertEqual(self.request('/')[0],200)
    def test_config(self):self.assertEqual(json.loads(self.request('/api/config')[1])['csrf'],'test-only')
    def test_denies_path_traversal(self):self.assertEqual(self.request('/../core.py')[0],404)
    def test_denies_source_read(self):self.assertEqual(self.request('/server.py')[0],404)
    def test_denies_foreign_host(self):self.assertEqual(self.request('/',headers={'Host':'attacker.invalid'})[0],403)
    def test_denies_foreign_origin(self):
        h=self.headers();h['Origin']='https://attacker.invalid';self.assertEqual(self.request('/api/export',json.dumps(fixture()).encode(),h)[0],403)
    def test_denies_missing_token(self):
        h=self.headers();del h['X-Studio-Token'];self.assertEqual(self.request('/api/export',b'{}',h)[0],403)
    def test_denies_non_json(self):
        h=self.headers();h['Content-Type']='text/plain';self.assertEqual(self.request('/api/export',b'{}',h)[0],415)
    def test_export_works(self):self.assertEqual(self.request('/api/export',json.dumps(fixture()).encode(),self.headers())[0],200)
    def test_invalid_document(self):self.assertEqual(self.request('/api/export',b'{}',self.headers())[0],400)
    def test_model_not_configured(self):self.assertEqual(self.request('/api/propose',b'{"prompt":"Shorten","context":{}}',self.headers())[0],503)
    def test_no_url_injection(self):self.assertEqual(self.request('/api/propose',b'{"prompt":"x","context":{},"url":"http://example.org"}',self.headers())[0],400)
    def test_no_sniff_header(self):self.assertEqual(self.request('/')[2]['X-Content-Type-Options'],'nosniff')
    def test_no_external_csp(self):self.assertIn("connect-src 'self'",self.request('/')[2]['Content-Security-Policy'])


class MockModel(BaseHTTPRequestHandler):
    reply='{"title":"Local proposal"}'
    captured=None
    def log_message(self,*args):pass
    def do_POST(self):
        type(self).captured=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.reply=='HTTP_ERROR':self.send_error(500);return
        body=json.dumps({'message':{'content':self.reply}}).encode()
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

class ModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=ThreadingHTTPServer(('127.0.0.1',0),MockModel)
        cls.mt=threading.Thread(target=cls.model.serve_forever,daemon=True);cls.mt.start()
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.server.csrf='model-test-only';cls.server.model='mock-not-a-real-model';cls.server.ollama_port=cls.model.server_port
        cls.st=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.st.start();cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.model.shutdown();cls.model.server_close();cls.st.join();cls.mt.join()
    def call(self,reply):
        MockModel.reply=reply
        req=urllib.request.Request(self.base+'/api/propose',data=b'{"prompt":"Improve the title","context":{"title":"Example"}}',headers={'Content-Type':'application/json','Origin':self.base,'X-Studio-Token':'model-test-only'})
        try:
            with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
    def test_valid_patch_requires_approval(self):
        status,data=self.call('{"title":"Better title"}');self.assertEqual(status,200);self.assertTrue(data['requiresApproval']);self.assertEqual(data['patch']['title'],'Better title')
    def test_structured_schema_sent(self):
        self.call('{"title":"Better title"}');self.assertFalse(MockModel.captured['format']['additionalProperties']);self.assertFalse(MockModel.captured['stream'])
    def test_unknown_model_field_rejected(self):self.assertEqual(self.call('{"html":"<script>evil</script>"}')[0],400)
    def test_invalid_model_json_rejected(self):self.assertEqual(self.call('not json')[0],400)
    def test_model_http_error(self):self.assertEqual(self.call('HTTP_ERROR')[0],502)
    def test_large_model_response_rejected(self):self.assertEqual(self.call('x'*132000)[0],400)
    def test_prompt_not_system_message(self):
        self.call('{"title":"Better title"}');self.assertEqual(MockModel.captured['messages'][1]['role'],'user');self.assertIn('Never invent research results',MockModel.captured['messages'][0]['content'])

if __name__=='__main__':unittest.main(verbosity=2)
