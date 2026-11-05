"""Neutral, dependency-free document contract and v1 Markdown exporter.

V2 is an opt-in authoring format. It does not replace docsctl SPEC.md v1.
"""
from __future__ import annotations
import copy
import io
import json
import re
import zipfile
from datetime import date
from typing import Any

KINDS = ('cover','abstract','contents','chapter','method','architecture','results',
         'matrix','timeline','equations','references','figure','table','glossary',
         'appendix','limitations','reproducibility','conclusion')
MAX_BYTES = 1_048_576
MAX_PAGES = 60
DEFAULT_THEME = {'accent':'#52606d','ink':'#1a1a1a','paper':'#ffffff','font':'Arial'}
ROOT_KEYS = {'version','title','subtitle','author','date','format','theme','pages'}
PAGE_KEYS = {'id','kind','title','body','art','blur','mermaid'}
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
IDENT = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,63}$')

class InvalidDocument(ValueError):
    """Rejected input; caller must not replace the previous valid document."""

def text(value: Any, name: str, limit: int, multiline: bool = False) -> str:
    if not isinstance(value,str) or len(value)>limit:
        raise InvalidDocument(f'{name}: expected text of at most {limit} characters')
    if any(ord(c)<32 and c not in ('\n','\t') for c in value):
        raise InvalidDocument(f'{name}: control characters are not allowed')
    if not multiline and ('\n' in value or '\t' in value):
        raise InvalidDocument(f'{name}: expected a single line')
    return value

def validate(doc: Any) -> dict:
    if not isinstance(doc,dict) or set(doc)!=ROOT_KEYS or doc.get('version') != 2:
        raise InvalidDocument('Expected a version 2 document with known fields only')
    # JSON byte budget applies even when called with a dict by an adapter.
    try:
        if len(json.dumps(doc,ensure_ascii=False,allow_nan=False).encode())>MAX_BYTES:
            raise InvalidDocument('Document exceeds 1 MiB')
    except (TypeError,ValueError,RecursionError) as exc:
        raise InvalidDocument('Document is not bounded finite JSON') from exc
    out = copy.deepcopy(doc)
    for k,n in [('title',140),('subtitle',240),('author',120),('date',10)]:
        out[k]=text(doc.get(k,''),k,n)
    if not out['title'].strip(): raise InvalidDocument('Title is required')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',out['date']):
        raise InvalidDocument('Date must be YYYY-MM-DD')
    try: date.fromisoformat(out['date'])
    except ValueError as exc: raise InvalidDocument('Date must be YYYY-MM-DD') from exc
    if out.get('format') not in ('portrait','landscape'):
        raise InvalidDocument('format must be portrait or landscape')
    theme=doc.get('theme',{})
    if not isinstance(theme,dict) or set(theme)!=set(DEFAULT_THEME):
        raise InvalidDocument('Unknown theme field')
    out['theme'] = {**DEFAULT_THEME,**theme}
    for k in ('accent','ink','paper'):
        if not isinstance(out['theme'][k],str) or not HEX.fullmatch(out['theme'][k]):
            raise InvalidDocument(f'Invalid theme color: {k}')
    # Font name only, never CSS or a URL. Fonts are supplied by the portal.
    if not isinstance(out['theme']['font'],str) or not re.fullmatch(r'[\w -]{1,64}',out['theme']['font'],re.ASCII):
        raise InvalidDocument('Invalid font family')
    pages=doc.get('pages')
    if not isinstance(pages,list) or not 1<=len(pages)<=MAX_PAGES:
        raise InvalidDocument('Expected 1–60 pages')
    seen=set()
    for p in pages:
        if not isinstance(p,dict) or set(p)!=PAGE_KEYS: raise InvalidDocument('Unknown page field')
        if not isinstance(p.get('id'),str) or not IDENT.fullmatch(p['id']) or p['id'] in seen:
            raise InvalidDocument('Page IDs must be valid and unique')
        seen.add(p['id'])
        if p.get('kind') not in KINDS: raise InvalidDocument('Unknown page kind')
        text(p.get('title',''),'page.title',140)
        text(p.get('body',''),'page.body',12000,True)
        text(p.get('mermaid',''),'page.mermaid',12000,True)
        art=p.get('art',0)
        if type(art) is not int or not 0<=art<64: raise InvalidDocument('Invalid artwork index')
        blur=p.get('blur',0)
        if type(blur) not in (int,float) or not 0<=blur<=12:
            raise InvalidDocument('Blur must be 0–12')
    return out

def load_document(raw: bytes) -> dict:
    if len(raw)>MAX_BYTES: raise InvalidDocument('Document exceeds 1 MiB')
    def unique_pairs(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise InvalidDocument('Duplicate JSON key')
            out[k]=v
        return out
    try:
        return validate(json.loads(raw.decode('utf-8'),object_pairs_hook=unique_pairs))
    except (UnicodeDecodeError,json.JSONDecodeError,RecursionError) as exc:
        raise InvalidDocument('Invalid JSON') from exc

def plain_markdown(value: str) -> str:
    """Export untrusted field text as prose, never executable Markdown syntax."""
    value=value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    value=re.sub(r'([\\`*_{}\[\]#!|])',r'\\\1',value)
    return '\n\n'.join(line.strip() for line in value.splitlines() if line.strip())

def mermaid_safe(source: str) -> str:
    if '```' in source or re.search(r'(?i)(%%\{|click\s|javascript:|<script|<iframe)',source):
        raise InvalidDocument('Mermaid directives, callbacks and HTML are not allowed')
    if source and not re.match(r'^\s*(flowchart|graph|sequenceDiagram|stateDiagram-v2|classDiagram|erDiagram|gantt|pie|mindmap|timeline)\b',source):
        raise InvalidDocument('Unsupported Mermaid diagram type')
    return source

def heading_text(value: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'[^\w .,:;()/+–—-]', ' ', value)).strip() or 'Untitled'

def catalog_markdown(kind: str) -> list[str]:
    """Preserve the fixed, explicitly synthetic catalog examples in the v1 handoff."""
    if kind == 'matrix':
        rows=['Lokale Verarbeitung','PDF-Ausgabe','Editierbare Quellen','Versionierte Vorlagen','Farbsemantik','Bildunterschriften','Literaturverzeichnis','Formelsatz','Export-Prüfung','Modell-Freigabe','Browser-Vorschau','Offline-Inhalte']
        lines=['| Kriterium | Profil A | Profil B | Profil C | Profil D | Profil E |','|---|---|---|---|---|---|']
        for i,row in enumerate(rows):
            cells=[['Ja','Ja','Teilweise','Nein'][(i+j*3)%4] for j in range(5)]
            lines.append('| '+row+' | '+' | '.join(cells)+' |')
        return lines+['','*Tabelle: Synthetische Profile, keine Produktbewertung*','']
    if kind == 'table':
        lines=['| Versuch | n | Mittelwert | Std.-Abw. | Status |','|---|---|---|---|---|']
        for i in range(9): lines.append(f"| Demo {i+1:02d} | {20+i*5} | {4.1+i*.3:.2f} | {.21+i*.02:.2f} | {'Teilweise' if i%3==0 else 'Ja'} |")
        return lines+['','*Tabelle: Synthetische Datensätze auf einer beliebigen Demo-Skala*','']
    if kind == 'results':
        return ['**Nur Demowerte; keine Forschungsdaten.**','','| Profil | Wert |','|---|---|','| A | 48 |','| B | 75 |','| C | 61 |','| D | 92 |','| E | 68 |','','*Tabelle: Frei gewählte Beispielwerte auf einer Skala von 0 bis 100*','']
    if kind == 'equations':
        return ['```text','F₁ = 2 · (P · R) / (P + R)','x̄ = (x₁ + ··· + xₙ) / n','```','','P: Präzision. R: Recall. F₁: harmonisches Mittel. Didaktische Beispiele, keine Messdaten.','']
    if kind == 'references':
        return [f'- [{title}]({url})' for title,url in [('Puck','https://github.com/puckeditor/puck'),('OpenUI','https://github.com/thesysdev/openui'),('Penpot','https://github.com/penpot/penpot'),('Ollama','https://docs.ollama.com/capabilities/structured-outputs'),('pdfme','https://github.com/pdfme/pdfme')]]+['']
    if kind == 'abstract':
        return ['Illustrative Kennzahlen: 3 Perspektiven, 12 Demo-Kriterien, 1 gemeinsames System. Keine gemessenen Ergebnisse.','']
    if kind == 'figure':
        return ['Die illustrative Grafik ist Bestandteil des separat verwalteten Portal-Brand-Pakets und wird nicht in das neutrale Inhaltsarchiv kopiert.','']
    return []

def export_v1(doc: dict) -> bytes:
    """Return a deterministic ZIP containing only v1-compatible Markdown/YAML.

    Brand tokens and generated pictures intentionally stay in the portal, not
    the neutral content repository. No model-supplied filenames are accepted.
    """
    d=validate(doc)
    files={}
    chapters=[]
    yaml_str=lambda s: json.dumps(s,ensure_ascii=False)
    for i,p in enumerate(d['pages']):
        if p['kind'] in ('cover','contents'): continue
        filename=f'{i:02d}-{p["kind"]}.md'
        chapters.append(filename)
        title=heading_text(p.get('title') or p['kind'].title())
        kind='overview' if len(chapters)==1 else ('appendix' if p['kind']=='appendix' else 'explanation')
        lines=['---','doc_schema: 1',f'id: studio.{p["id"]}',f'title: {yaml_str(title)}',
               f'summary: {yaml_str("Illustrative authoring demo; not research evidence.")}',
               f'kind: {kind}','status: draft','---','',f'# {title}','',
               plain_markdown(p.get('body','')),'']
        lines += catalog_markdown(p['kind'])
        if p.get('mermaid'):
            source=mermaid_safe(p['mermaid'])
            lines+=['```mermaid',source,'```','', '*Abbildung: Editable architecture diagram*','']
        files[filename]='\n'.join(lines).encode()
    if not chapters:
        chapters=['index.md']
        files['index.md']=(f'---\ndoc_schema: 1\nid: studio.overview\ntitle: {yaml_str(heading_text(d["title"]))}\nkind: overview\nstatus: draft\n---\n\n# {heading_text(d["title"])}\n\n{plain_markdown(d["subtitle"])}\n').encode()
    manifest=f'''schema: 1\ntool:\n  id: studio-demo\n  title: {yaml_str(d['title'])}\n  subtitle: {yaml_str(d['subtitle'])}\n  summary: "Illustrative document authored in Studio v2"\ndocument:\n  language: de-AT\n  version: "2.0-demo"\n  status: draft\n  date: {d['date']}\n  numbering: auto\nchapters:\n'''+''.join(f'  - {name}\n' for name in chapters)
    files['docs.yml']=manifest.encode()
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for path,body in sorted(files.items()):
            info=zipfile.ZipInfo('docs/'+path,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,body)
    return buf.getvalue()

# AI may propose a small replacement set, not arbitrary executable UI/code.
PATCH_FIELDS={'title':140,'subtitle':240,'pageTitle':140,'pageBody':12000}
PATCH_SCHEMA={'type':'object','additionalProperties':False,'properties':{
    k:{'type':'string','maxLength':n} for k,n in PATCH_FIELDS.items()}}

def validate_patch(value: Any) -> dict:
    if not isinstance(value,dict) or not value or set(value)-set(PATCH_FIELDS):
        raise InvalidDocument('Model must return a non-empty allowed patch')
    return {k:text(v,k,PATCH_FIELDS[k],k=='pageBody') for k,v in value.items()}
