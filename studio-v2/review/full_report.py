"""Assemble the existing report's eleven topics with an external reviewed Painter.

No brand files, fonts, browser, network, subprocesses, model calls or PDF engine
are created here. The owner supplies the verified renderer, assets and data.
The central docsctl/Quarto/Typst pipeline is not modified by this adapter.
"""
from __future__ import annotations
import copy
import json
import math
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

PAGE_IDS = ('cover','tools','brand','flow','identity','assets','templates',
            'science','quality','prompts','sources')
LIMIT = 150_000


def validate(content):
    if not isinstance(content, dict) or set(content) != {'schema','date','title','template','pages','sources','facts'}:
        raise ValueError('Invalid report root')
    if content['schema'] != 1 or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', content['date']):
        raise ValueError('Invalid schema/date')
    if len(json.dumps(content, ensure_ascii=False).encode()) > LIMIT:
        raise ValueError('Content limit exceeded')
    pages = content['pages']
    if not isinstance(pages,list) or tuple(p.get('id') for p in pages) != PAGE_IDS:
        raise ValueError('Preserve the eleven report topics and their order')
    if set(content['template']) != {'html_sha256','script_sha256','sources_sha256','sections'} or content['template']['sections'] != 11:
        raise ValueError('Original report binding required')
    for key in ('html_sha256','script_sha256','sources_sha256'):
        if not re.fullmatch('[0-9a-f]{64}',content['template'][key]):
            raise ValueError('Invalid template hash')
    src = content['sources']
    if not isinstance(src,list) or not 1 <= len(src) <= 22:
        raise ValueError('Source count')
    ids = set()
    for s in src:
        if set(s) != {'id','title','url','provenance'} or not re.fullmatch(r'S\d\d', s['id']) or s['id'] in ids:
            raise ValueError('Invalid source')
        ids.add(s['id']);u=urlsplit(s['url'])
        if u.scheme != 'https' or not u.hostname or u.username or u.password or u.port not in (None,443):
            raise ValueError('Invalid source URL')
    for i,p in enumerate(pages,1):
        if set(p) != {'id','title','kicker','note','source_ids','rows','columns','legacy_section','change'} or p['legacy_section'] != i:
            raise ValueError('Page binding or fields')
        if not isinstance(p['source_ids'],list) or any(s not in ids for s in p['source_ids']):
            raise ValueError('Unresolved page source')
        if not isinstance(p['rows'],list) or len(p['rows']) > 18:
            raise ValueError('Row limit')
        if not isinstance(p['columns'],list) or len(p['columns']) > 6:
            raise ValueError('Column limit')
        if any(not isinstance(row,list) or len(row) != len(p['columns']) for row in p['rows']):
            raise ValueError('Ragged table')
    def strings(v):
        if isinstance(v,str):
            if len(v)>1000 or any(ord(c)<32 and c not in '\n\t' for c in v):
                raise ValueError('Text limit/control character')
            if '<script' in v.lower() or '{{<' in v or '```' in v:
                raise ValueError('Executable markup not accepted')
        elif isinstance(v,dict):
            for x in v.values():strings(x)
        elif isinstance(v,list):
            for x in v:strings(x)
        elif v is not None and type(v) not in (int,bool):raise ValueError('Unsupported value')
    strings(content)
    return copy.deepcopy(content)


class TemplateHeadings(HTMLParser):
    def __init__(self):
        super().__init__();self.sections=0;self.in_h1=False;self.headings=[]
    def handle_starttag(self,tag,attrs):
        if tag == 'section' and 'page' in dict(attrs).get('class','').split():self.sections+=1
        if tag=='h1':self.in_h1=True;self.headings.append('')
    def handle_endtag(self,tag):
        if tag=='h1':self.in_h1=False
    def handle_data(self,data):
        if self.in_h1:self.headings[-1]+=data


def template_inventory(html):
    """Parse inert source only. Never execute or render its CSS/JS/asset locators."""
    parser=TemplateHeadings();parser.feed(html)
    if parser.sections != 11 or len(parser.headings) != 11:
        raise ValueError('Unexpected existing full report')
    return {'section_count':parser.sections,'headings':[' '.join(t.split()) for t in parser.headings]}


def raster_box(pixel_size, box, scale=1, min_dpi=300):
    if len(pixel_size)!=2 or any(type(v) is not int or v<=0 for v in pixel_size):raise ValueError('Pixel size')
    if len(box)!=2 or any(not math.isfinite(v) or v<=0 for v in box) or scale<=0 or min_dpi<72:raise ValueError('Display box')
    factor=min(box[0]/pixel_size[0],box[1]/pixel_size[1],72/(min_dpi*scale))
    return tuple(v*factor for v in pixel_size)


def source_line(p, page, content, top=524):
    lookup={s['id']:s for s in content['sources']}
    sources=[lookup[k] for k in page['source_ids']]
    x=44
    for s in sources:
        p.text(s['id'],x,top,34,7.2,color='muted',max_height=12)
        p.c.linkURL(s['url'],(x*p.scale,(p.h-top-12)*p.scale,(x+30)*p.scale,(p.h-top+2)*p.scale),relative=0,thickness=0)
        x+=39
    p.text('Quellenstand '+content['date']+' · keine automatische Freigabe',x+10,top,790-x-10,7.0,color='muted',max_height=12)


def start(p,page,num):
    names={'brand':'Branding','identity':'Anbieterzeichen','assets':'Asset-Pipeline','templates':'Vorlagenkatalog','science':'Wissenschaft','quality':'Visuelle Abnahme','prompts':'Design-Prompts','sources':'Quellen'}
    p.begin();p.header(names.get(page['id'],page['id'])+' / Bericht',f'{num:02d} / 11');p.kicker(page['kicker'])
    p.text(page['title'],44,98,750,30,'400',leading=32,max_height=78,tracking=-.5)
    p.text(page['note'],44,171,754,8.4,color='muted',max_height=26)


def table(p,page,widths,top=218,row_h=33,size=8.6,head_h=25):
    if abs(sum(widths)-754)>.01 or len(widths)!=len(page['columns']):raise ValueError('Table geometry')
    x=44
    for j,(label,w) in enumerate(zip(page['columns'],widths)):
        p.rect(x,top,w,head_h,['peach','pale_blue','pale_teal','pale_violet','surface','surface'][j])
        p.text(label,x+7,top+6,w-14,8.0,'450',max_height=head_h-8);x+=w
    for i,row in enumerate(page['rows']):
        y=top+head_h+i*row_h
        if y+row_h>509:raise ValueError('Table crosses caption zone')
        if i%2==0:p.rect(44,y,754,row_h,'surface')
        x=44
        for j,(text,w) in enumerate(zip(row,widths)):
            p.text(text,x+7,y+5,w-14,size,'450' if j==0 else '400',max_height=row_h-7);x+=w


def brand_page(p,page,content):
    start(p,page,3)
    table(p,page,[136,175,232,211],top=216,row_h=45,size=8.5)
    # Actual logo stays at original/native reading size, never a large crop.
    p.image(p.logo,44,443,108,21,'original_wordmark_small')
    p.text('Markenidentität bleibt erhalten.',174,443,250,10,'450',max_height=16)
    p.text('Aspekta 400 / 450 / 600. Kein stiller Fontwechsel.',174,464,430,8.6,max_height=16)
    for i,key in enumerate(('orange','blue','teal','violet')):
        p.rect(613+i*47,446,32,12,key,radius=2)
    p.text('Akzent + semantische Vergleichsfarben',570,470,228,7.1,color='muted',max_height=13)
    source_line(p,page,content);p.end()


def identity_page(p,page,content,assets,refine):
    start(p,page,5)
    for i,name in enumerate(('Puck','OpenUI','pdfme','Typst')):
        y=215+i*65;p.line(44,y+57,798,y+57)
        p.text(name,44,y+8,112,12,'450',max_height=20)
        a=assets.get(name)
        if a:
            if a['role']=='readme_banner':
                p.text('Typst',172,y+6,174,13,'450',max_height=21)
                p.text('Banner nicht als Logo eingesetzt',172,y+29,200,7.4,color='muted',max_height=14)
            elif a['kind']=='raster':
                # 48 px favicon <= 11.52 pt at 300 dpi; no large soft proof image.
                size=raster_box(a['pixel_size'],(140,34),p.scale)
                refine.draw_provider(p,a,172,y+7,size[0],size[1])
            else:refine.draw_provider(p,a,172,y+5,150,31)
        else:p.text('Kein Zeichen eingesetzt',172,y+8,200,9,color='muted',max_height=17)
        row=page['rows'][i]
        p.text(row[1],390,y+7,190,8.7,'450',max_height=27)
        p.text(row[2],584,y+7,210,8.3,max_height=34)
    p.text('Vektormarken bleiben Vektoren. Rasterqualität hängt von den Originalpixeln ab, nicht von höherer Render-dpi.',44,489,754,8.0,color='muted',max_height=24)
    source_line(p,page,content);p.end()


def assets_page(p,page,content):
    start(p,page,6)
    steps=[('Quelle','document'),('Rolle','layers'),('Bytes','document'),('Identität','check'),('Einsatz','table')]
    for i,(label,kind) in enumerate(steps):
        x=44+i*155;p.icon(kind,x,211,'ink',17);p.text(label,x+24,212,118,10,'450',max_height=20)
        if i<4:p.line(x+118,219,x+143,219,'orange',1.2)
    table(p,page,[173,228,353],top=253,row_h=43,size=8.5)
    p.text('Ein verifizierter Hash belegt die Bytes. Er belegt weder Markenidentität noch Nutzungsrecht.',44,492,754,8.2,color='muted',max_height=22)
    source_line(p,page,content);p.end()


def templates_page(p,page,content,expanded=False):
    start(p,page,7)
    widths=[224,106,106,106,106,106];x=44;top=214
    for j,(h,w) in enumerate(zip(page['columns'],widths)):
        p.rect(x,top,w,29,['surface','peach','pale_blue','pale_teal','pale_violet','surface'][j]);p.text(h,x+7,top+8,w-14,8.2,'450',max_height=15);x+=w
    role={'Standard':'native','Optional':'adapter','Bei Marke':'unknown','Pflicht':'native'}
    for i,row in enumerate(page['rows']):
        y=top+29+i*15
        if i%2==0:p.rect(44,y,754,15,'surface')
        p.text(row[0],51,y+3,207,7.2,'450',max_height=12);x=44+224
        for word in row[1:]:
            if word not in role:raise ValueError('Unknown catalog state')
            p.symbol(role[word],x+9,y+7.2,4.5)
            p.text(word,x+19,y+3,82,6.9,max_height=12);x+=106
    p.text('Standard / Optional / Bei Marke = Vorlagenvorschlag. Keine Aussage über bereits integrierte Produktfunktionen.',44,497,754,7.6,color='muted',max_height=21)
    source_line(p,page,content);p.end()


def science_page(p,page,content):
    start(p,page,8)
    table(p,page,[130,290,334],top=218,row_h=41,size=8.8)
    p.rect(44,426,365,70,'surface',radius=7)
    p.text('F1 = 2 * P * R / (P + R)',58,440,336,19,'400',max_height=28)
    p.text('Didaktisch: P = Präzision; R = Recall. Keine Messdaten.',58,475,336,7.7,color='muted',max_height=15)
    p.icon('document',434,431,'ink',19)
    p.text('Text bleibt Text.',461,432,320,15,'450',max_height=24)
    p.text('Formel, Einheit, Unsicherheit und Quelle getrennt setzen. Ein Glasbild ist eine Illustration, kein Forschungsbeleg.',434,463,357,8.8,max_height=34)
    source_line(p,page,content);p.end()


def quality_page(p,page,content):
    start(p,page,9)
    table(p,page,[169,137,448],top=216,row_h=34,size=8.5)
    p.text('Technischer Befund, gezielte Sichtprüfung und finale Nutzerabnahme sind getrennte Zustände.',44,498,754,8.0,color='muted',max_height=21)
    source_line(p,page,content);p.end()


def prompts_page(p,page,content):
    start(p,page,10)
    table(p,page,[130,242,382],top=216,row_h=43,size=8.7)
    p.text('Volltexte bleiben in der vorhandenen UX-DESIGN-PROMPTS.md. Hier: präzise Eingaben und Grenzen statt Textwänden.',44,501,754,7.8,color='muted',max_height=18)
    source_line(p,page,content);p.end()


def sources_page(p,page,content):
    start(p,page,11)
    for i,s in enumerate(content['sources']):
        col=i//11;row=i%11;x=44+col*384;y=213+row*25
        p.text(s['id'],x,y,31,8.1,'450',max_height=14)
        p.text(s['title'],x+37,y,332,8.1,max_height=20)
        p.c.linkURL(s['url'],(x*p.scale,(p.h-y-22)*p.scale,(x+370)*p.scale,(p.h-y+1)*p.scale),relative=0,thickness=0)
        p.line(x,y+23,x+370,y+23)
    p.text('Quellenbasis: bestehende Berichtsvorlage + geprüfte Build-Rückläufe. Keine neue Anbieter-/Produktabnahme.',44,503,754,7.7,color='muted',max_height=18)
    p.text('Zentrale Quarto-/Typst-Konfiguration unverändert. Inhaltsübergabe als SPEC v1; Produktionslauf noch nicht ausgeführt.',44,524,754,7.0,color='muted',max_height=14)
    p.end()


def render_full(p,content,data,spec,assets,hero,base,refine):
    c=validate(content);by={x['id']:x for x in c['pages']}
    base.page_cover(p,data,hero)
    refine.page_matrix(p,data,spec,assets)
    brand_page(p,by['brand'],c)
    refine.page_architecture(p,spec)
    identity_page(p,by['identity'],c,assets,refine)
    assets_page(p,by['assets'],c)
    templates_page(p,by['templates'],c)
    science_page(p,by['science'],c)
    quality_page(p,by['quality'],c)
    prompts_page(p,by['prompts'],c)
    sources_page(p,by['sources'],c)


def layout_audit(lines,images,page_sizes):
    """Audit physical page-point boxes with a top-left origin, fail closed.

    Raster and vector producers must report their actual fitted placement.
    Missing geometry is a schema failure, never zero-filled or exempted.
    """
    failures=[]
    def number(v):
        return type(v) in (int,float) and math.isfinite(v)
    def page_ok(n):
        return type(n) is int and 1 <= n <= len(page_sizes)
    for size in page_sizes:
        if len(size)!=2 or not all(number(v) and v>0 for v in size):
            raise ValueError('Invalid physical page size')
    valid_lines=[]
    for i,a in enumerate(lines):
        if not isinstance(a,dict) or not page_ok(a.get('page')) or 'call' not in a:
            failures.append({'gate':'TEXT_RECORD_SCHEMA','record':i});continue
        box=a.get('bbox')
        if not isinstance(box,(list,tuple)) or len(box)!=4 or not all(number(v) for v in box) or box[2]<box[0] or box[3]<box[1]:
            failures.append({'gate':'TEXT_RECORD_SCHEMA','record':i,'page':a['page']});continue
        n=a['page'];w,h=page_sizes[n-1]
        valid_lines.append(a)
        if box[0]<-.1 or box[1]<-.1 or box[2]>w+.1 or box[3]>h+.1:
            failures.append({'gate':'TEXT_OUTSIDE_PAGE','page':n,'call':a['call']})
    image_boxes=[]
    keys=('x_pt','y_top_pt','width_pt','height_pt')
    for i,im in enumerate(images):
        if not isinstance(im,dict) or not page_ok(im.get('page')) or not isinstance(im.get('role'),str):
            failures.append({'gate':'IMAGE_RECORD_SCHEMA','record':i});continue
        missing=[k for k in keys if k not in im]
        if missing or not all(number(im[k]) for k in keys if k in im):
            failures.append({'gate':'IMAGE_RECORD_SCHEMA','record':i,'page':im['page'],'role':im['role'],'missing':missing});continue
        x,y,w,h=(im[k] for k in keys)
        if w<=0 or h<=0 or not math.isfinite(x+w) or not math.isfinite(y+h):
            failures.append({'gate':'IMAGE_RECORD_SCHEMA','record':i,'page':im['page'],'role':im['role']});continue
        box=(x,y,x+w,y+h);pw,ph=page_sizes[im['page']-1]
        image_boxes.append((im,box))
        if x<-.1 or y<-.1 or box[2]>pw+.1 or box[3]>ph+.1:
            failures.append({'gate':'IMAGE_OUTSIDE_PAGE','record':i,'page':im['page'],'role':im['role']})
    def overlaps(a,b):
        return min(a[2],b[2])-max(a[0],b[0])>.7 and min(a[3],b[3])-max(a[1],b[1])>.7
    for i,a in enumerate(valid_lines):
        for b in valid_lines[i+1:]:
            if a['page']==b['page'] and a['call']!=b['call'] and overlaps(a['bbox'],b['bbox']):
                failures.append({'gate':'TEXT_COLLISION','page':a['page'],'calls':[a['call'],b['call']]})
        for im,box in image_boxes:
            if im['page']==a['page'] and overlaps(a['bbox'],box):
                failures.append({'gate':'TEXT_IMAGE_COLLISION','page':a['page'],'call':a['call'],'role':im['role']})
    return {'status':'PASS_GEOMETRY_ONLY' if not failures else 'FAIL_GEOMETRY','failures':failures,
            'pages':len(page_sizes),'checked_lines':len(lines),'checked_images':len(images),
            'validated_image_boxes':len(image_boxes),'coordinate_space':'physical_page_points_top_left',
            'scope':'schema, font-metric bounds, text/text and text/image; not visual approval'}


def _cell(s):
    return str(s).replace('\\','\\\\').replace('|','\\|').replace('\n',' / ').replace('*','\\*').replace('<','&lt;').replace('>','&gt;')


def export_v1(content,data,refine,spec):
    """Stage content only; no brand files, Quarto config or replacement renderer."""
    c=validate(content);files={};chapter_names=[]
    source_map={s['id']:s for s in c['sources']}
    for i,p in enumerate(c['pages']):
        name='index.md' if i==0 else f'{i:02d}-{p["id"]}.md';chapter_names.append(name)
        title=' '.join(p['title'].split())
        if any(s in title for s in ('#','*','[',']')):raise ValueError('Unsafe heading')
        lines=['---','doc_schema: 1',f'id: report.{p["id"]}',f'title: {json.dumps(title,ensure_ascii=False)}',
               f'summary: {json.dumps(p["note"],ensure_ascii=False)}',f'kind: {"overview" if i==0 else "reference"}',
               'status: draft','---','',f'# {title}','',_cell(p['note']),'']
        rows=p['rows'];cols=p['columns']
        if p['id']=='tools':
            cols=['Kriterium']+[x['name'] for x in spec['providers']]
            rows=[[x['label']]+[cell['text']+' ('+refine.STATUS_LABELS[cell['status']]+')' for cell in x['cells']] for x in refine.matrix_rows(data,spec)]
        if rows:
            lines += ['| '+' | '.join(_cell(x) for x in cols)+' |','| '+' | '.join('---' for _ in cols)+' |']
            lines += ['| '+' | '.join(_cell(x) for x in r)+' |' for r in rows]
            lines += ['',f'*Tabelle: {_cell(title)}*','']
        if p['id']=='flow':lines += ['```mermaid',refine.architecture_mmd(spec).strip(),'```','','*Abbildung: Prüfweg mit Korrekturrückweg; native Ausführung nicht abgenommen*','']
        if p['id']=='science':lines += ['```text','F1 = 2 * P * R / (P + R)','```','','Didaktische Formel; keine Messdaten.','']
        if p['id']=='sources':
            lines += [f'- [{_cell(s["id"]+" "+s["title"])}]({s["url"]})' for s in c['sources']]+['']
        else:
            lines += [f'- [{_cell(source_map[k]["id"]+" "+source_map[k]["title"])}]({source_map[k]["url"]})' for k in p['source_ids']]+['']
        files[name]='\n'.join(lines)
    manifest='schema: 1\ntool:\n  id: studio-report\n  title: '+json.dumps(c['title'],ensure_ascii=False)+'\n  summary: "Bestehender Report mit referenzgebundener Reparatur"\ndocument:\n  language: de-AT\n  version: "full-report-review"\n  status: draft\n  date: '+c['date']+'\n  numbering: auto\nchapters:\n'+''.join('  - '+x+'\n' for x in chapter_names)
    files['docs.yml']=manifest
    return files
