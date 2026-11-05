"""Inspect public HTML/CSS, recording evidence instead of guessing brand colors.

Usage: python studio-v2/brand_probe.py https://example.org/ --out brand-evidence.json
A caller may allow additional CSS hosts with repeated --css-host arguments.
This tool never downloads fonts, images, scripts, cookies or authenticated data.
"""
from __future__ import annotations
import argparse, collections, hashlib, ipaddress, json, re, socket, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

MAX_BYTES=2_097_152
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.css=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='link' and 'stylesheet' in a.get('rel','').split() and a.get('href'):
            self.css.append(a['href'])

def extract(text,url):
    hexes=collections.Counter(m.group().upper() for m in re.finditer(r'#[0-9a-fA-F]{3,8}\b',text) if len(m.group()) in (4,5,7,9))
    rgb=collections.Counter(re.findall(r'rgba?\([^)]{1,100}\)',text))
    families=[]
    for m in re.finditer(r'font-family\s*:\s*([^;}<>]{1,180})',text,re.I):
        family=m.group(1).strip().strip('"\'')
        if family not in families: families.append(family)
    variables=[]
    for m in re.finditer(r'(--[\w-]+)\s*:\s*([^;}<>]{1,160})',text):
        if re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(',m.group(2)):
            variables.append({'name':m.group(1),'value':m.group(2).strip()})
    return {'url':url,'sha256':hashlib.sha256(text.encode()).hexdigest(),
            'hex_candidates':[{'value':k,'count':v} for k,v in hexes.most_common(80)],
            'rgb_candidates':[{'value':k,'count':v} for k,v in rgb.most_common(80)],
            'font_families':families[:80],'css_variables':variables[:160]}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**k): raise ValueError('Redirect rejected; inspect the destination explicitly')

def fetch_public(url,allowed_hosts):
    u=urlsplit(url)
    if u.scheme!='https' or u.username or u.password or u.port not in (None,443) or u.hostname not in allowed_hosts:
        raise ValueError('Only explicitly allowed public HTTPS hosts are supported')
    addresses={info[4][0] for info in socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError('Non-public address rejected')
    # No credentials/cookies/proxy credentials are forwarded. Redirects are disabled.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(urllib.request.Request(url,headers={'User-Agent':'docsctl-brand-probe/2'}),timeout=15) as r:
        content_type=r.headers.get_content_type()
        if content_type not in ('text/html','text/css','text/plain'): raise ValueError('Not HTML or CSS')
        raw=r.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES: raise ValueError('Source exceeds 2 MiB')
        return raw.decode(r.headers.get_content_charset() or 'utf-8',errors='strict')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('url');p.add_argument('--css-host',action='append',default=[])
    p.add_argument('--out',default='brand-evidence.json');a=p.parse_args()
    host=urlsplit(a.url).hostname
    report={'observed_at':datetime.now(timezone.utc).isoformat(),'requested_url':a.url,
            'sources':[],'errors':[],'interpretation':'Candidates only. Frequency does not identify an official primary color. Inspect selectors and rendered elements before selecting tokens.'}
    try:
        source=fetch_public(a.url,{host});report['sources'].append(extract(source,a.url))
        links=Links();links.feed(source)
        for href in list(dict.fromkeys(links.css))[:10]:
            url=urljoin(a.url,href)
            try: report['sources'].append(extract(fetch_public(url,{host,*a.css_host}),url))
            except Exception as exc: report['errors'].append({'url':url,'error':str(exc)[:200]})
    except Exception as exc: report['errors'].append({'url':a.url,'error':str(exc)[:200]})
    from pathlib import Path
    Path(a.out).write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(f"Sources: {len(report['sources'])}; errors: {len(report['errors'])}; {a.out}")
    return 0 if report['sources'] else 1
if __name__=='__main__': raise SystemExit(main())
