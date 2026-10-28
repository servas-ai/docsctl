#!/usr/bin/env python3
"""docsctl – prüft, bündelt und baut Tool-Dokumentation aus Markdown (docs/) nach der Doku-Konvention v1.

Befehle
  check   [--tool ID | --path DIR]   Konvention prüfen (SPEC.md), Bericht nach build/reports/
  bundle  [--tool ID]                llms-full.md + llms.txt je Tool erzeugen
  build                              alles: check -> Diagramme -> Web -> PDFs -> Bundles
  export  --tool ID --brand ID       eine PDF bauen
  mounts                             build/compose.sources.yml aus catalog.yml erzeugen

Zwei Verzeichnisse: ENGINE (dieses Repo: Regeln, Vorlagen, Portal-Optik, Branding "neutral") und
ROOT (Arbeitsverzeichnis: catalog.yml, eigene brands/, build/). Ohne catalog.yml baut docsctl das
Repository im Arbeitsverzeichnis allein (docs/ -> ein Tool, Branding neutral).

Läuft im Builder-Container (Quarto, Typst, mermaid-cli). `check --path` läuft
auch auf jedem Rechner mit python3 + PyYAML (+ jsonschema für Schemaprüfung).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import yaml

try:
    import jsonschema
except ImportError:  # check läuft auch ohne, dann ohne Schemaprüfung
    jsonschema = None

ENGINE = Path(os.environ.get("DOCSCTL_HOME", Path(__file__).resolve().parent.parent))
ROOT = Path(os.environ.get("DOKU_ROOT", Path.cwd()))
BUILD = Path(os.environ.get("DOKU_BUILD", ROOT / "build"))
SOURCES = Path(os.environ.get("DOKU_SOURCES", "/sources"))
SPEC_DIR = ENGINE / "spec"
PUPPETEER = os.environ.get("DOKU_PUPPETEER", "/opt/doku/puppeteer.json")

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
FENCE_RE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})\s*([^\s`]*)?(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LINK_RE = re.compile(r"(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# manuelle Nummern: "1", "6.3", "6.3.1", "A", "A.1", "Anhang A", "0.1"
NUM_RE = re.compile(r"^((?:Anhang\s+)?(?:\d+|[A-Z])(?:\.\d+)*)\s+(.+)$")
CAPTION_RE = re.compile(r"^\*(Abbildung|Tabelle)(\s+[\w.]+)?:\s*(.+)\*\s*$")
ALLOWED_DIAGRAMS = {"mermaid"}
ALLOWED_HTML = re.compile(r"^<br\s*/?>$", re.I)


# --------------------------------------------------------------------------- Modell
@dataclass
class Finding:
    level: str  # error | warning | deviation | info
    rule: str
    file: str
    line: int
    msg: str


@dataclass
class Chapter:
    rel: str
    path: Path
    part: str  # front | main | appendix
    fm: dict
    body: str  # ohne Front Matter
    body_line0: int  # Zeilennummer, an der body beginnt (1-basiert)
    h1: str | None = None
    h1_line: int = 0

    @property
    def stem(self) -> str:
        return Path(self.rel).with_suffix("").as_posix().replace("/", "-")

    @property
    def anchor(self) -> str:
        return "ch-" + re.sub(r"[^a-z0-9-]", "-", self.stem.lower())


@dataclass
class Tool:
    id: str
    src: Path
    manifest: dict
    chapters: list[Chapter]
    mode: str  # strict | compat
    numbering: str  # auto | manual
    findings: list[Finding] = field(default_factory=list)
    entry: dict = field(default_factory=dict)

    @property
    def title(self):
        return self.manifest["tool"]["title"]

    @property
    def subtitle(self):
        return self.manifest["tool"].get("subtitle", "")

    @property
    def doc(self):
        return self.manifest["document"]

    def summary(self):
        s = self.entry.get("summary") or self.manifest["tool"].get("summary")
        if s:
            return s
        for c in self.chapters:
            if c.fm.get("summary"):
                return c.fm["summary"]
        return ""


# --------------------------------------------------------------------------- Hilfen
def log(*a):
    print(*a, file=sys.stderr, flush=True)


def load_yaml(p: Path):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def split_front_matter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None, text, 1
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, text[m.end():], text[: m.end()].count("\n") + 1


def iter_lines(body: str):
    """Liefert (lineno0, line, in_code, fence_info) – erkennt Fenced Code Blocks."""
    fence = None
    for i, line in enumerate(body.split("\n")):
        m = FENCE_RE.match(line)
        if fence is None and m:
            fence = (m.group(2)[0], len(m.group(2)))
            yield i, line, "open", (m.group(3) or "") + (m.group(4) or "")
            continue
        if fence is not None:
            if m and m.group(2)[0] == fence[0] and len(m.group(2)) >= fence[1] and not (m.group(3) or "").strip() and not (m.group(4) or "").strip():
                fence = None
                yield i, line, "close", ""
            else:
                yield i, line, "code", ""
            continue
        yield i, line, "text", ""


def strip_inline_code(line: str) -> str:
    return re.sub(r"(`+)(.+?)\1", lambda m: " " * len(m.group(0)), line)


def clean_heading(text: str) -> str:
    text = re.sub(r"\s*\{[^}]*\}\s*$", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    return text.strip()


def gh_slug(text: str) -> str:
    s = clean_heading(text).lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def split_number(text: str):
    m = NUM_RE.match(text)
    return (m.group(1), m.group(2)) if m else (None, text)


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def run(cmd, **kw):
    log("  $", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        raise SystemExit(f"Befehl fehlgeschlagen ({r.returncode}): {' '.join(map(str, cmd))}")
    return r


# --------------------------------------------------------------------------- Katalog
def load_catalog():
    if (ROOT / "catalog.yml").is_file():
        cat = load_yaml(ROOT / "catalog.yml")
        # Umgebung (z. B. DOKU_ENV=prod): portal-Werte aus environments.<env> überschreiben die Grundwerte
        env = os.environ.get("DOKU_ENV")
        if env:
            if env not in cat.get("environments", {}):
                raise SystemExit(f"Umgebung '{env}' fehlt in catalog.yml (environments)")
            cat.setdefault("portal", {}).update(cat["environments"][env].get("portal", {}))
        return cat
    # Einzel-Repo (z. B. beim Partner): docs/ im Arbeitsverzeichnis ist das einzige Tool
    if not (ROOT / "docs").is_dir():
        raise SystemExit(f"Weder catalog.yml noch docs/ in {ROOT}")
    manifest = ROOT / "docs" / "docs.yml"
    rid = (load_yaml(manifest).get("tool") or {}).get("id") if manifest.is_file() else None
    rid = rid or re.sub(r"[^a-z0-9-]+", "-", ROOT.resolve().name.lower()).strip("-") or "docs"
    return {"schema": 1, "portal": {"title": "Dokumentation", "brand": "neutral", "default_brand": "neutral"},
            "brands": ["neutral"], "tools": [{"id": rid, "path": "docs"}]}


def brand_dir(bid: str) -> Path:
    """Eigenes Branding im Arbeitsverzeichnis vor dem mitgelieferten (neutral)."""
    own = ROOT / "brands" / bid
    return own if own.is_dir() else ENGINE / "brands" / bid


def tool_src(entry: dict) -> Path:
    mounted = SOURCES / entry["id"]
    if mounted.is_dir():
        return mounted
    p = Path(entry["path"])
    return p if p.is_absolute() else (ROOT / p)


def load_brand(bid: str) -> dict:
    d = brand_dir(bid)
    if not d.is_dir():
        raise SystemExit(f"Brand '{bid}' fehlt: {d}")
    b = load_yaml(d / "report-brand.yml")
    b["_brand"] = load_yaml(d / "_brand.yml")
    b["_dir"] = d
    return b


# --------------------------------------------------------------------------- Laden
def manifest_from_book_yaml(src: Path, findings: list[Finding]):
    """Kompatibilitätsregel: Altbestand mit book.yaml -> docs.yml-Modell."""
    by = load_yaml(src / "book.yaml")
    findings.append(Finding("deviation", "M001", "docs.yml", 0,
                            "kein docs.yml; book.yaml per Kompatibilitätsregel übernommen (numbering: manual)"))
    chapters = [c["file"] for c in by.get("chapters", [])]
    front = []
    # Kapitel mit 'chapter: 0' im Front Matter = Kurzfassung -> vor das Inhaltsverzeichnis
    for f in list(chapters):
        fm, _, _ = split_front_matter((src / f).read_text(encoding="utf-8"))
        if fm and str(fm.get("chapter")) == "0":
            chapters.remove(f)
            front.append(f)
            findings.append(Finding("deviation", "M002", f, 0,
                                    "Kapitel 0 wird als front_matter (vor dem Inhaltsverzeichnis) gesetzt"))
    lang = by.get("lang", "de")
    return {
        "schema": 1,
        "tool": {
            "id": None,
            "title": by.get("title", src.name),
            "subtitle": by.get("subtitle", ""),
            "repository": by.get("source_repository", ""),
            "commit": str(by.get("source_commit", "")),
        },
        "document": {
            "language": lang if "-" in lang else f"{lang}-AT",
            "version": str(by.get("version", "0.0.0")),
            "status": by.get("status", "draft"),
            "date": str(by.get("date", "")),
            "authors": [by["author"]] if by.get("author") else [],
            "numbering": "manual",
        },
        "front_matter": front,
        "chapters": chapters,
        "appendices": [a["file"] for a in by.get("appendices", [])],
    }


def expand_entries(src: Path, entries: list[str]) -> list[str]:
    out = []
    for e in entries or []:
        if e.endswith("/"):
            files = sorted((src / e).glob("*.md"))
            keyed = []
            for f in files:
                fm, _, _ = split_front_matter(f.read_text(encoding="utf-8"))
                keyed.append(((fm or {}).get("order", 10**6), f.name, f.relative_to(src).as_posix()))
            out += [k[2] for k in sorted(keyed)]
        else:
            out.append(e)
    return out


def load_tool(entry: dict, src: Path | None = None) -> Tool:
    src = src or tool_src(entry)
    findings: list[Finding] = []
    mode = entry.get("mode", "strict")
    if (src / "docs.yml").exists():
        manifest = load_yaml(src / "docs.yml")
        if jsonschema:
            schema = json.loads((SPEC_DIR / "docs-manifest.schema.json").read_text())
            for err in jsonschema.Draft202012Validator(schema).iter_errors(manifest):
                findings.append(Finding("error", "M003", "docs.yml", 0,
                                        f"{'/'.join(map(str, err.path)) or '(root)'}: {err.message}"))
    elif (src / "book.yaml").exists():
        manifest = manifest_from_book_yaml(src, findings)
        mode = "compat"
    else:
        raise SystemExit(f"{src}: weder docs.yml noch book.yaml gefunden")
    manifest["tool"]["id"] = manifest["tool"].get("id") or entry.get("id") or src.name
    for k, v in (entry.get("overrides") or {}).items():
        manifest["document"][k] = v
    numbering = manifest["document"].get("numbering", "auto")

    chapters = []
    for part, key in (("front", "front_matter"), ("main", "chapters"), ("appendix", "appendices")):
        for rel in expand_entries(src, manifest.get(key, [])):
            p = src / rel
            if not p.exists():
                findings.append(Finding("error", "M004", rel, 0, "in docs.yml gelistete Datei fehlt"))
                continue
            fm, body, l0 = split_front_matter(p.read_text(encoding="utf-8"))
            ch = Chapter(rel=rel, path=p, part=part, fm=fm or {}, body=body, body_line0=l0)
            if fm is None:
                findings.append(Finding("error", "F001", rel, 1, "YAML-Front-Matter fehlt"))
            for i, line, kind, _ in iter_lines(body):
                if kind == "text" and line.startswith("# "):
                    ch.h1 = clean_heading(line[2:])
                    ch.h1_line = l0 + i
                    break
            chapters.append(ch)
    t = Tool(id=manifest["tool"]["id"], src=src, manifest=manifest, chapters=chapters,
             mode=mode, numbering=numbering, findings=findings, entry=entry)
    return t


# --------------------------------------------------------------------------- check
def check_tool(t: Tool) -> list[Finding]:
    F = list(t.findings)
    fm_schema = None
    if jsonschema:
        fm_schema = jsonschema.Draft202012Validator(json.loads((SPEC_DIR / "frontmatter.schema.json").read_text()))
    ids = {}
    anchors_by_file: dict[str, set] = {}
    links = []
    for ch in t.chapters:
        # Front Matter
        if fm_schema is not None and ch.fm:
            for err in fm_schema.iter_errors(ch.fm):
                F.append(Finding("error", "F002", ch.rel, 1, f"Front Matter: {err.message}"))
        fid = ch.fm.get("id")
        if fid:
            if fid in ids:
                F.append(Finding("error", "F003", ch.rel, 1, f"id '{fid}' doppelt (auch in {ids[fid]})"))
            ids[fid] = ch.rel
        # Überschriften
        title = str(ch.fm.get("title", ""))
        slugs = {}
        h1_count = 0
        last_level = 0
        first_block_seen = False
        open_fence_line = None
        for i, line, kind, info in iter_lines(ch.body):
            ln = ch.body_line0 + i
            if kind == "open":
                open_fence_line = ln
                lang = info.strip()
                if lang.startswith("{") and "mermaid" in lang:
                    F.append(Finding("error", "D001", ch.rel, ln, "```{mermaid} (Quarto-Syntax) ist verboten; ```mermaid verwenden"))
                elif lang in ("mmd", "plantuml", "d2", "dot", "graphviz"):
                    F.append(Finding("error", "D001", ch.rel, ln, f"Diagrammsprache '{lang}' (noch) nicht erlaubt; nur mermaid"))
                elif not lang:
                    F.append(Finding("warning", "C001", ch.rel, ln, "Codeblock ohne Sprache (```text, ```bash, …)"))
                first_block_seen = True
                continue
            if kind == "close":
                open_fence_line = None
            if kind != "text":
                continue
            if line.strip() and not first_block_seen and not line.startswith("# "):
                F.append(Finding("error", "H001", ch.rel, ln, "erste Zeile nach dem Front Matter muss die H1 sein"))
            if line.strip():
                first_block_seen = True
            m = HEADING_RE.match(line)
            if m:
                level = len(m.group(1))
                text = clean_heading(m.group(2))
                s = gh_slug(text)
                n = slugs.get(s, 0)
                slugs[s] = n + 1
                anchors_by_file.setdefault(ch.rel, set()).add(s if n == 0 else f"{s}-{n}")
                if level == 1:
                    h1_count += 1
                    num, rest = split_number(text)
                    ok = text == title or (t.numbering == "manual" and rest == title)
                    if title and not ok:
                        F.append(Finding("error", "H002", ch.rel, ln, f"H1 '{text}' passt nicht zu title '{title}'"))
                if last_level and level > last_level + 1:
                    F.append(Finding("warning", "H003", ch.rel, ln, f"Überschrift springt von H{last_level} auf H{level}"))
                last_level = level
                num, _ = split_number(text)
                if t.numbering == "auto" and num and level <= 4:
                    F.append(Finding("warning", "H004", ch.rel, ln, f"manuelle Nummer '{num}' in Überschrift, numbering ist auto"))
                if t.numbering == "manual" and not num and ch.part != "front":
                    F.append(Finding("warning", "H004", ch.rel, ln, f"Überschrift ohne Nummer, numbering ist manual: '{text}'"))
            plain = strip_inline_code(line)
            for tag in re.findall(r"</?[A-Za-z][A-Za-z0-9-]*[^>]*>", plain):
                if not ALLOWED_HTML.match(tag) and not re.match(r"^<https?://", tag):
                    F.append(Finding("warning", "R001", ch.rel, ln, f"rohes HTML {tag[:40]} (nur <br> in Tabellen erlaubt)"))
            if "{{<" in plain or re.match(r"^\s*(import|export)\s", plain) or re.match(r"^:::", plain):
                F.append(Finding("error", "R002", ch.rel, ln, "renderer-spezifisches Konstrukt (Shortcode/MDX/Div) verboten"))
            for m in LINK_RE.finditer(plain):
                links.append((ch, ln, m.group(1) == "!", m.group(3)))
        if open_fence_line:
            F.append(Finding("error", "C002", ch.rel, open_fence_line, "Codeblock nicht geschlossen"))
        if h1_count == 0:
            F.append(Finding("error", "H001", ch.rel, 1, "keine H1"))
        elif h1_count > 1:
            F.append(Finding("error", "H001", ch.rel, 1, f"{h1_count} H1 in einer Datei (genau eine erlaubt)"))
        F += check_captions(ch)
    # Links
    for ch, ln, is_img, url in links:
        if re.match(r"^[a-z][a-z0-9+.-]*:", url) or url.startswith("mailto:"):
            continue
        target, _, frag = url.partition("#")
        if not target:
            tf = ch.rel
        else:
            tp = (ch.path.parent / target).resolve()
            try:
                tf = tp.relative_to(t.src.resolve()).as_posix()
            except ValueError:
                F.append(Finding("warning", "L003", ch.rel, ln, f"Link zeigt aus docs/ hinaus: {url}"))
                continue
            if not tp.exists():
                F.append(Finding("error", "I001" if is_img else "L001", ch.rel, ln, f"Ziel fehlt: {url}"))
                continue
        if frag and tf.endswith(".md") and frag not in anchors_by_file.get(tf, set()):
            F.append(Finding("error", "L002", ch.rel, ln, f"Anker #{frag} in {tf} nicht gefunden (GitHub-Slug)"))
    if t.mode == "compat":
        for f in F:
            if f.level == "error" and f.rule.startswith(("F", "M", "H002")):
                f.level = "deviation"
    return F


def check_captions(ch: Chapter) -> list[Finding]:
    """Jedes Diagramm/Bild und jede Tabelle braucht eine Bildunterschrift-Zeile darunter."""
    out = []
    lines = ch.body.split("\n")
    kinds = {i: k for i, _, k, _ in iter_lines(ch.body)}
    i = 0
    n = len(lines)
    while i < n:
        k = kinds.get(i)
        line = lines[i]
        end = None
        what = None
        if k == "open" and line.strip().startswith(("```mermaid", "~~~mermaid")):
            j = i + 1
            while j < n and kinds.get(j) != "close":
                j += 1
            end, what = j, "Abbildung"
        elif k == "text" and re.match(r"^\s*!\[[^\]]*\]\([^)]*\)\s*(\{[^}]*\})?\s*$", line):
            end, what = i, "Abbildung"
        elif k == "text" and line.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            j = i + 1
            while j + 1 < n and lines[j + 1].lstrip().startswith("|"):
                j += 1
            end, what = j, "Tabelle"
        if end is not None:
            j = end + 1
            while j < n and not lines[j].strip():
                j += 1
            nxt = lines[j] if j < n else ""
            m = CAPTION_RE.match(nxt.strip())
            if m and re.search(r"(?<!\\)\*", m.group(3)):
                out.append(Finding("warning", "C003", ch.rel, ch.body_line0 + j,
                                   "Unterschrift enthält unmaskiertes * (z. B. Glob cmd/*/main.go) – als \\* schreiben; Build maskiert automatisch"))
            if not m or m.group(1) != what:
                level = "warning" if what == "Tabelle" else "warning"
                out.append(Finding(level, "D002" if what == "Abbildung" else "T001", ch.rel, ch.body_line0 + i,
                                   f"{what} ohne Unterschrift-Zeile '*{what} …: Text*' direkt darunter"))
            i = end + 1
            continue
        i += 1
    return out


def write_check_report(t: Tool, F: list[Finding]) -> dict:
    d = BUILD / "reports" / t.id
    d.mkdir(parents=True, exist_ok=True)
    counts = {}
    for f in F:
        counts.setdefault(f.level, 0)
        counts[f.level] += 1
    by_rule = {}
    for f in F:
        by_rule.setdefault((f.level, f.rule), []).append(f)
    md = [f"# docsctl check: {t.title}", "",
          f"Quelle: `{t.entry.get('path', t.src)}` · Modus: **{t.mode}** · Nummerierung: **{t.numbering}** · "
          f"Kapitel: {len(t.chapters)} · Stand: {dt.datetime.now().isoformat(timespec='seconds')}", "",
          "| Stufe | Anzahl |", "|---|---:|"]
    for lvl in ("error", "deviation", "warning", "info"):
        md.append(f"| {lvl} | {counts.get(lvl, 0)} |")
    md += ["", "Stufen: **error** bricht den Build ab · **deviation** = Abweichung von SPEC.md, die der Build-Schritt "
           "ausgleicht (Quelle bleibt unverändert) · **warning** = sollte behoben werden.", ""]
    groups = {}
    for f in F:
        groups.setdefault((f.level, f.rule, f.msg), []).append(f.file)
    if groups:
        md += ["## Zusammenfassung (gleiche Meldung zusammengefasst)", "", "| Stufe | Regel | Meldung | Dateien |", "|---|---|---|---:|"]
        for (lvl, rule, msg), files in sorted(groups.items(), key=lambda x: ("edwi".index(x[0][0][0]), x[0][1], -len(x[1]))):
            md.append(f"| {lvl} | {rule} | {msg.replace('|', '/')} | {len(set(files))} |")
        md.append("")
    for (lvl, rule), items in sorted(by_rule.items(), key=lambda x: ("edwi".index(x[0][0][0]), x[0][1])):
        md.append(f"## {lvl} {rule} ({len(items)}×)")
        md.append("")
        for f in items[:60]:
            md.append(f"- `{f.file}:{f.line}` {f.msg}")
        if len(items) > 60:
            md.append(f"- … {len(items) - 60} weitere")
        md.append("")
    (d / "check.md").write_text("\n".join(md), encoding="utf-8")
    (d / "check.json").write_text(json.dumps([f.__dict__ for f in F], ensure_ascii=False, indent=1), encoding="utf-8")
    return counts


def print_summary(t: Tool, F: list[Finding], counts: dict):
    log(f"[check] {t.id}: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) + f"  (Bericht: build/reports/{t.id}/check.md)")
    seen = {}
    for f in F:
        key = (f.level, f.rule)
        seen[key] = seen.get(key, 0) + 1
        if f.level == "error" or seen[key] <= 2:
            log(f"   {f.level:9} {f.rule} {f.file}:{f.line} {f.msg}")


# --------------------------------------------------------------------------- Normalisieren
@dataclass
class Diagram:
    code: str
    key: str  # Hash über Code


def extract_diagrams(t: Tool) -> list[Diagram]:
    out = []
    for ch in t.chapters:
        cur = None
        for i, line, kind, info in iter_lines(ch.body):
            if kind == "open" and info.strip() == "mermaid":
                cur = []
            elif kind == "code" and cur is not None:
                cur.append(line)
            elif kind == "close" and cur is not None:
                code = "\n".join(cur) + "\n"
                out.append(Diagram(code=code, key=sha(code)))
                cur = None
    return out


def normalize_body(t: Tool, ch: Chapter, target: str, diagram_ref, title_for_dedupe=True) -> str:
    """Gemeinsame Vorverarbeitung (Quelle bleibt unverändert):
    - H1 entfernen (Titel kommt aus Front Matter / wird vom Ziel gesetzt)
    - Front-Matter-Kapitel: manuelle Nummern aus Überschriften entfernen
    - Titel-/Untertitelzeilen, die das Deckblatt doppeln, entfernen
    - ```mermaid -> Bildreferenz auf vorgerenderte Grafik
    - Links auf Kapiteldateien -> Ziel-spezifisch umschreiben
    """
    lines = ch.body.split("\n")
    out = []
    cur = None
    removed_h1 = False
    dedupe = {f"**{t.title}**", f"*{t.subtitle}*"} if title_for_dedupe else set()
    chapter_files = {c.rel: c for c in t.chapters}
    for i, line, kind, info in iter_lines(ch.body):
        if kind == "open" and info.strip() == "mermaid":
            cur = []
            continue
        if cur is not None:
            if kind == "close":
                code = "\n".join(cur) + "\n"
                out.append(diagram_ref(sha(code)))
                out.append("")  # Bild und Unterschrift als getrennte Absätze
                cur = None
            else:
                cur.append(line)
            continue
        if kind != "text":
            out.append(line)
            continue
        if not removed_h1 and line.startswith("# "):
            removed_h1 = True
            continue
        if line.strip() in dedupe and ch.part == "front":
            continue
        m = HEADING_RE.match(line)
        if m and ch.part == "front" and t.numbering == "manual":
            num, rest = split_number(clean_heading(m.group(2)))
            if num:
                line = f"{m.group(1)} {rest}"
        line = rewrite_links(line, ch, chapter_files, target)
        line = fix_caption_line(line)
        out.append(line)
    text = "\n".join(out)
    if target == "web":
        text = merge_web_captions(text)
    return text.strip("\n") + "\n"


def fix_caption_line(line: str) -> str:
    """'*Tabelle 6.1: … cmd/*/main.go …*' -> innere * escapen, sonst zerfällt die Kursivsetzung."""
    m = re.match(r"^\*((?:Abbildung|Tabelle)\b.*)\*\s*$", line.strip())
    if not m:
        return line
    inner = re.sub(r"(?<!\\)\*", r"\\*", m.group(1))
    return f"*{inner}*"


def rewrite_links(line: str, ch: Chapter, chapter_files: dict, target: str) -> str:
    def repl(m):
        bang, label, url = m.group(1), m.group(2), m.group(3)
        if bang or re.match(r"^[a-z][a-z0-9+.-]*:", url):
            return m.group(0)
        tgt, _, frag = url.partition("#")
        rel = (Path(ch.rel).parent / tgt).as_posix() if tgt else ch.rel
        rel = os.path.normpath(rel)
        c = chapter_files.get(rel)
        if c is None:
            return m.group(0)
        if target == "pdf":
            return f"[{label}](#{frag or c.anchor})"
        if target == "bundle":
            return f"[{label}](#{frag or c.anchor})"
        return m.group(0)  # web: Quarto löst .md -> .html selbst auf
    # Inline-Code nicht anfassen
    parts = re.split(r"(`+[^`]*`+)", line)
    return "".join(p if p.startswith("`") else LINK_RE.sub(repl, p) for p in parts)


def merge_web_captions(text: str) -> str:
    """Web: Bild + folgende '*Abbildung …*'-Zeile -> ![Unterschrift](bild) (HTML-<figure>)."""
    pat = re.compile(r"^!\[\]\(([^)]+)\)(\{[^}]*\})?\n(?:[ \t]*\n)+\*(Abbildung[^*\n]*)\*[ \t]*$", re.M)

    def repl(m):
        cap = m.group(3).replace("[", "\\[").replace("]", "\\]")
        return f"![{cap}]({m.group(1)}){{fig-alt=\"{html.escape(m.group(3), quote=True)}\"}}"
    return pat.sub(repl, text)


# --------------------------------------------------------------------------- Diagramme
def mermaid_config(brand_id: str) -> Path:
    return brand_dir(brand_id) / "mermaid.json"


def render_diagrams(diagrams: list[Diagram], brand_id: str, fmt: str) -> Path:
    """Rendert alle Diagramme eines Brands in ein Cache-Verzeichnis (Hash über Code+Config)."""
    cfg = mermaid_config(brand_id)
    cfg_hash = sha(cfg.read_text() + fmt)
    cache = BUILD / "cache" / "diagrams" / f"{brand_id}-{fmt}-{cfg_hash}"
    cache.mkdir(parents=True, exist_ok=True)
    todo = []
    seen = set()
    for d in diagrams:
        if d.key in seen or (cache / f"{d.key}.{fmt}").exists():
            continue
        seen.add(d.key)
        todo.append(d)
    if not todo:
        log(f"[diagramme] {brand_id}/{fmt}: {len(diagrams)} aus Cache")
        return cache
    tmp = BUILD / "tmp" / f"mmd-{brand_id}-{fmt}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    src = tmp / "in.md"
    src.write_text("".join(f"```mermaid\n{d.code}```\n\n" for d in todo), encoding="utf-8")
    log(f"[diagramme] {brand_id}/{fmt}: rendere {len(todo)} Diagramme")
    cmd = ["mmdc", "-q", "-p", PUPPETEER, "-c", str(cfg), "-i", str(src), "-o", str(tmp / "out.md"), "-e", fmt]
    if fmt == "svg":
        cmd += ["-b", "white"]
    run(cmd)
    for n, d in enumerate(todo, start=1):
        f = tmp / f"out-{n}.{fmt}"
        if not f.exists():
            raise SystemExit(f"Diagramm {n} ({d.key}) wurde nicht gerendert")
        shutil.move(str(f), cache / f"{d.key}.{fmt}")
    return cache


def pdf_size(p: Path):
    data = p.read_bytes()
    m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", data)
    if not m:
        return None
    x0, y0, x1, y1 = map(float, m.groups())
    return x1 - x0, y1 - y0


# --------------------------------------------------------------------------- Bundle (llms-full.md)
def bundle_tool(t: Tool, outdir: Path, base_url: str):
    outdir.mkdir(parents=True, exist_ok=True)
    d = t.doc
    parts = [f"# {t.title}", ""]
    if t.subtitle:
        parts += [f"> {t.subtitle}", ""]
    meta = [("Tool-ID", t.id), ("Version", d.get("version")), ("Status", d.get("status")), ("Datum", d.get("date")),
            ("Repository", t.manifest["tool"].get("repository")), ("Commit", t.manifest["tool"].get("commit")),
            ("Erzeugt", dt.date.today().isoformat()), ("Erzeugt von", "docsctl bundle (Doku-Konvention v1)")]
    parts += [f"- {k}: {v}" for k, v in meta if v] + [""]
    parts += ["Diese Datei ist die vollständige Fassung für Agenten: alle Kapitel in Lesereihenfolge, "
              "Front Matter entfernt, Diagramme als Mermaid-Quelltext, Kapitel-Links als Anker in dieser Datei.", ""]
    parts += ["## Inhalt", ""]
    for ch in t.chapters:
        parts.append(f"- [{ch.h1 or ch.fm.get('title')}](#{ch.anchor})")
    parts.append("")
    chapter_files = {c.rel: c for c in t.chapters}
    for ch in t.chapters:
        parts.append(f"<!-- source: {ch.rel} -->")
        body = []
        for i, line, kind, info in iter_lines(ch.body):
            if kind == "text":
                if line.startswith("# "):
                    line = f"# {clean_heading(line[2:])} {{#{ch.anchor}}}"
                line = rewrite_links(line, ch, chapter_files, "bundle")
            body.append(line)
        parts.append("\n".join(body).strip("\n"))
        parts.append("")
    full = "\n".join(parts)
    (outdir / "llms-full.md").write_text(full, encoding="utf-8")
    # llms.txt (llmstxt.org-Format)
    lt = [f"# {t.title}", "", f"> {t.summary() or t.subtitle}", "",
          f"Technische Dokumentation des Tools `{t.id}` (Version {d.get('version')}, Status {d.get('status')}). "
          f"Vollständige Fassung in einer Datei: {base_url}/llms-full.md", "", "## Kapitel", ""]
    for ch in t.chapters:
        title = ch.h1 or ch.fm.get("title")
        summ = ch.fm.get("summary", "")
        lt.append(f"- [{title}]({base_url}/{Path(ch.rel).with_suffix('.html').as_posix()}): {summ}".rstrip(": "))
    lt += ["", "## Optional", "", f"- [Gesamtfassung Markdown]({base_url}/llms-full.md)",
           f"- [PDF (Brands siehe /artifacts/index.json)](/artifacts/{t.id}/)", ""]
    (outdir / "llms.txt").write_text("\n".join(lt), encoding="utf-8")
    return outdir / "llms-full.md"


# --------------------------------------------------------------------------- PDF
def brand_typst(b: dict, bid: str, tool: Tool) -> str:
    """report-brand.yml + _brand.yml -> brand.typ (Typst-Dictionary)."""
    br = b["_brand"]
    pal = br.get("color", {}).get("palette", {})

    def col(v, default="#000000"):
        if v is None:
            return f'rgb("{default}")'
        v = pal.get(v, v)
        return f'rgb("{v}")'

    colors = br.get("color", {})
    typo = br.get("typography", {})

    def fam(x, d):
        v = typo.get(x, d)
        if isinstance(v, dict):
            v = v.get("family", d)
        return v

    def s(v):
        return json.dumps("" if v is None else str(v), ensure_ascii=False)

    tp = b.get("title_page", {})
    hd = b.get("header", {})
    ft = b.get("footer", {})
    docb = b.get("document", {})
    logo = (br.get("logo", {}) or {}).get("medium")
    lines = [
        "#let brand = (",
        f"  id: {s(bid)},",
        f"  name: {s(b.get('display_name', bid))},",
        f"  legal-name: {s(b.get('legal_name', ''))},",
        f"  layout: {s(b.get('layout', 'neutral'))},",
        "  colors: (",
        f"    fg: {col(colors.get('foreground'), '#1a1a1a')},",
        f"    bg: {col(colors.get('background'), '#ffffff')},",
        f"    primary: {col(colors.get('primary'), '#1a1a1a')},",
        f"    secondary: {col(colors.get('secondary'), '#606060')},",
        f"    accent: {col(pal.get('accent') and 'accent', '#606060')},",
        f"    muted: {col(pal.get('muted') and 'muted', '#606060')},",
        f"    rule: {col(pal.get('rule') and 'rule', '#e6e6e6')},",
        f"    code-bg: {col(pal.get('code-bg') and 'code-bg', '#f5f5f4')},",
        f"    table-head: {col(pal.get('table-head') and 'table-head', '#ffffff')},",
        f"    table-head-fg: {col(pal.get('table-head-fg') and 'table-head-fg', '#1a1a1a')},",
        f"    link: {col(colors.get('link') or colors.get('primary'), '#1a1a1a')},",
        "  ),",
        "  fonts: (",
        f"    body: {s(fam('base', 'Libertinus Serif'))},",
        f"    heading: {s(fam('headings', fam('base', 'Libertinus Serif')))},",
        f"    mono: {s(fam('monospace', 'DejaVu Sans Mono'))},",
        "  ),",
        f"  body-size: {b.get('body_size', '10pt')},",
        f"  logo: {s('brand-assets/' + Path(logo).name if logo else '')},",
        f"  logo-width: {b.get('logo_width', '4cm')},",
        f"  wordmark: {json.dumps(b.get('wordmark') or [], ensure_ascii=False).replace('[', '(').replace(']', ',)') if b.get('wordmark') else '()'},",
        f"  eyebrow: {s(tp.get('eyebrow', 'Technische Dokumentation'))},",
        f"  claim: {s(tp.get('claim', ''))},",
        f"  header-right: {s(hd.get('right', ''))},",
        f"  footer-lines: ({''.join(s(x) + ', ' for x in ft.get('lines', []))}),",
        f"  page-label: {s(ft.get('page_label', 'Seite {page} / {pages}'))},",
        f"  classification: {s(docb.get('classification', ''))},",
        f"  disclaimer: {s(docb.get('disclaimer', ''))},",
        f"  table-style: {s(b.get('table_style', 'booktabs'))},",
        f"  heading-rule: {s(b.get('heading_rule', 'none'))},",
        ")",
    ]
    return "\n".join(lines) + "\n"


def build_pdf(t: Tool, bid: str, diagrams: list[Diagram]) -> Path:
    b = load_brand(bid)
    cache = render_diagrams(diagrams, bid, "pdf")
    wd = BUILD / "pdf" / t.id / bid
    shutil.rmtree(wd, ignore_errors=True)
    (wd / "diagrams").mkdir(parents=True)
    shutil.copytree(ENGINE / "quarto" / "_extensions", wd / "_extensions")
    shutil.copytree(b["_dir"] / "assets", wd / "brand-assets")
    (wd / "brand.typ").write_text(brand_typst(b, bid, t), encoding="utf-8")
    text_w, max_h = 453.0, 610.0  # pt, A4 mit Satzspiegel aus dem Template

    def ref(key):
        src = cache / f"{key}.pdf"
        shutil.copy(src, wd / "diagrams" / src.name)
        size = pdf_size(src)
        attr = ""
        if size:
            w, h = size
            scale = min(1.0, text_w / w, max_h / h)
            land = min(1.0, 700.0 / w, 400.0 / h)  # Querformat-Satzspiegel
            if scale < 0.62 and land > scale * 1.25:
                # sehr breite Diagramme: eigene Querformatseite statt Briefmarke
                attr = f'{{width="{w * land:.1f}pt" doku-landscape="true"}}'
            else:
                attr = f'{{width="{w * scale:.1f}pt"}}'
        return f"![](diagrams/{key}.pdf){attr}"

    d = t.doc
    fm = {
        "title": t.title,
        "subtitle": t.subtitle,
        "lang": d.get("language", "de-AT").split("-")[0],
        "region": (d.get("language", "de-AT").split("-") + ["AT"])[1],
        "date": d.get("date") or dt.date.today().isoformat(),
        "doku": {
            "tool-id": t.id,
            "version": d.get("version", ""),
            "status": d.get("status", ""),
            "numbering": t.numbering,
            "repository": t.manifest["tool"].get("repository", ""),
            "commit": t.manifest["tool"].get("commit", ""),
            "authors": ", ".join(d.get("authors", [])),
            "brand": bid,
        },
        "format": {"doku-typst": {"keep-typ": True, "font-paths": ["brand-assets/fonts"]}},
    }
    MAINMATTER = ["```{=typst}", "#doku-mainmatter()", '#set page(numbering: "1")', "#counter(page).update(1)",
                  "#doku-start-main()", "```", ""]
    if t.numbering == "auto":
        fm["format"]["doku-typst"]["number-sections"] = True
    parts = ["---", yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip(), "---", ""]
    state = "front"
    for ch in t.chapters:
        if ch.part != state:
            if ch.part in ("main", "appendix") and state == "front":
                parts += MAINMATTER
            if ch.part == "appendix":
                parts += ["```{=typst}", "#doku-appendix()"] + (
                    ['#set heading(numbering: "A.1")', "#counter(heading).update(0)"] if t.numbering == "auto" else []) + ["```", ""]
            state = ch.part
        title = ch.h1 or ch.fm.get("title", ch.stem)
        if ch.part == "front" and t.numbering == "manual":
            title = split_number(title)[1]
        cls = " .unnumbered" if (t.numbering == "manual" or ch.part == "front") else ""
        parts.append(f"# {title} {{#{ch.anchor}{cls}}}")
        parts.append("")
        parts.append(normalize_body(t, ch, "pdf", ref))
    if state == "front":
        parts += MAINMATTER
    src = wd / f"{t.id}.md"
    src.write_text("\n".join(parts), encoding="utf-8")
    log(f"[pdf] {t.id} × {bid}: quarto render")
    run(["quarto", "render", src.name, "--to", "doku-typst"], cwd=wd)
    pdf = wd / f"{t.id}.pdf"
    out = BUILD / "site" / "artifacts" / t.id
    out.mkdir(parents=True, exist_ok=True)
    final = out / f"{t.id}-{bid}.pdf"
    shutil.copy(pdf, final)
    log(f"[pdf] -> {final.relative_to(BUILD)} ({final.stat().st_size // 1024} KB)")
    return final


# --------------------------------------------------------------------------- Web
def web_build(tools: list[Tool], cat: dict, diagrams_by_tool: dict):
    portal = cat.get("portal", {})
    pbrand = portal.get("brand", "neutral")
    b = load_brand(pbrand)
    wd = BUILD / "web"
    shutil.rmtree(wd, ignore_errors=True)
    wd.mkdir(parents=True)
    # Brand für die Web-Ansicht (_brand.yml + Assets)
    shutil.copytree(b["_dir"] / "assets", wd / "brand")
    brand_yml = dict(b["_brand"])
    brand_yml = json.loads(json.dumps(brand_yml).replace('"assets/', '"brand/'))
    (wd / "_brand.yml").write_text(yaml.safe_dump(brand_yml, allow_unicode=True, sort_keys=False), encoding="utf-8")
    shutil.copytree(ENGINE / "portal" / "assets", wd / "assets")
    if (ROOT / "portal" / "assets").is_dir():  # eigene Portal-Ergänzungen überschreiben gleichnamige Dateien
        shutil.copytree(ROOT / "portal" / "assets", wd / "assets", dirs_exist_ok=True)
    all_diagrams = [d for ds in diagrams_by_tool.values() for d in ds]
    cache = render_diagrams(all_diagrams, pbrand, "svg") if all_diagrams else None

    sidebars = []
    for t in tools:
        td = wd / "tools" / t.id
        (td / "diagrams").mkdir(parents=True)

        def ref(key, td=td, depth=None):
            shutil.copy(cache / f"{key}.svg", td / "diagrams" / f"{key}.svg")
            return f"![](DIAGRAM_PREFIX/diagrams/{key}.svg)"

        contents = [f"tools/{t.id}/start.qmd"]
        for ch in t.chapters:
            out = td / ch.rel
            out.parent.mkdir(parents=True, exist_ok=True)
            depth = len(Path(ch.rel).parts) - 1
            prefix = "/".join([".."] * depth) or "."
            body = normalize_body(t, ch, "web", ref).replace("DIAGRAM_PREFIX", prefix)
            title = ch.h1 or ch.fm.get("title", ch.stem)
            if ch.part == "front" and t.numbering == "manual":
                title = split_number(title)[1]
            fm = {"title": title}
            if ch.fm.get("summary"):
                fm["description"] = ch.fm["summary"]
            fm["doku-tool"] = t.id
            out.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
            contents.append(f"tools/{t.id}/{ch.rel}")
        (td / "start.qmd").write_text(tool_index_page(t, cat), encoding="utf-8")
        bundle_tool(t, td, f"/tools/{t.id}")  # damit Links beim Rendern auflösen; nach dem Build erneut geschrieben
        sections = []
        front = [f"tools/{t.id}/{c.rel}" for c in t.chapters if c.part == "front"]
        main = [f"tools/{t.id}/{c.rel}" for c in t.chapters if c.part == "main"]
        app = [f"tools/{t.id}/{c.rel}" for c in t.chapters if c.part == "appendix"]
        sections = [{"text": "Start", "href": f"tools/{t.id}/start.qmd"}] + front + main
        if app:
            sections.append({"section": "Anhang", "contents": app})
        sidebars.append({"id": t.id, "title": t.title, "style": "docked", "collapse-level": 1, "contents": sections})
    (wd / "assets" / "doku-data.html").write_text(portal_data(tools, portal), encoding="utf-8")
    legal = []
    if portal.get("operator"):  # Impressum/Datenschutz nur mit Betreiberangaben (catalog.yml portal.operator)
        (wd / "impressum.qmd").write_text(imprint_page(portal), encoding="utf-8")
        (wd / "datenschutz.qmd").write_text(privacy_page(portal), encoding="utf-8")
        legal = ["impressum.qmd", "datenschutz.qmd"]
    (wd / "index.qmd").write_text(home_page(tools, cat), encoding="utf-8")
    qy = {
        "project": {"type": "website", "output-dir": "../site", "render": ["index.qmd", *legal, "tools/**/*.qmd", "tools/**/*.md"],
                    "resources": ["assets/*", "brand/*", "tools/*/llms-full.md", "tools/*/llms.txt"]},
        "lang": "de",
        "website": {
            "title": portal.get("title", "Dokumentation"),
            "site-url": portal.get("site_url", "http://localhost:8470"),
            "favicon": "brand/favicon.png" if (wd / "brand" / "favicon.png").exists() else None,
            "search": {"location": "navbar", "type": "overlay", "limit": 50,
                       "copy-button": False},
            "navbar": {
                "background": "#ffffff", "foreground": "#1a1a1a", "pinned": True,
                "logo": "brand/" + Path((b["_brand"].get("logo") or {}).get("medium", "logo.png")).name,
                "title": portal.get("navbar_title", "Doku"),
            },
            "page-footer": page_footer(portal),
            "sidebar": sidebars,
            "page-navigation": True,
            "llms-txt": True,
            "reader-mode": False,
        },
        "format": {"html": {
            "from": "markdown+gfm_auto_identifiers",
            "toc": True, "toc-depth": 3, "toc-title": "Auf dieser Seite",
            "css": ["assets/portal.css"],
            "include-in-header": ["assets/doku-data.html"],
            "include-after-body": ["assets/export.html", "assets/portal-js.html"],
            "grid": {"sidebar-width": "290px", "body-width": "820px", "margin-width": "260px", "gutter-width": "2.5rem"},
            "filters": ["assets/doku-web.lua"],
            "anchor-sections": True,
            "smooth-scroll": True,
            "link-external-newwindow": True,
            "lightbox": "auto",
        }},
    }
    if not qy["website"]["favicon"]:
        del qy["website"]["favicon"]
    (wd / "_quarto.yml").write_text(yaml.safe_dump(qy, allow_unicode=True, sort_keys=False), encoding="utf-8")
    site = BUILD / "site"
    keep = site / "artifacts"
    tmp_keep = BUILD / "tmp" / "artifacts-keep"
    if keep.exists():
        shutil.rmtree(tmp_keep, ignore_errors=True)
        shutil.move(str(keep), tmp_keep)
    shutil.rmtree(site, ignore_errors=True)
    log("[web] quarto render (Website)")
    run(["quarto", "render"], cwd=wd)
    if tmp_keep.exists():
        shutil.move(str(tmp_keep), keep)


STATUS_DE = {"draft": "Entwurf", "review": "In Prüfung", "released": "Freigegeben"}
PART_DE = {"front": "Vorspann", "main": "Kapitel", "appendix": "Anhang"}


def tool_short(t: Tool) -> str:
    return t.entry.get("short", t.id)


def tool_mark(t: Tool) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", tool_short(t))[:2].upper() or "?"


def tool_meta(t: Tool) -> str:
    d = t.doc
    return f"v{d.get('version')} · {STATUS_DE.get(d.get('status'), d.get('status'))} · {len(t.chapters)} Kapitel"


def chapter_rows(t: Tool):
    """(Teil, Nummer, Titel, Kurzfassung, relativer Pfad) je Kapitel; Nummern bei auto-Nummerierung berechnet."""
    n = 0
    for c in t.chapters:
        title = c.h1 or c.fm.get("title") or c.stem
        num, rest = split_number(title)
        if c.part == "main":
            n += 1
            num = num or str(n)
        elif c.part == "appendix":
            num = num or ""
        else:
            num = ""
        yield c.part, num, rest, c.fm.get("summary", ""), c.rel


def signout_url(portal: dict) -> str:
    return "/oauth2/sign_out" + ("?rd=" + urllib.parse.quote(portal["logout_redirect"], safe="")
                                 if portal.get("logout_redirect") else "")


def portal_data(tools: list[Tool], portal: dict) -> str:
    data = {"portal": {"title": portal.get("title", "Dokumentation"), "signout": signout_url(portal)},
            "tools": [{"id": t.id, "title": t.title, "short": tool_short(t), "meta": tool_meta(t)} for t in tools]}
    return "<script>window.DOKU = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";</script>\n"


def page_footer(portal: dict) -> dict:
    op = portal.get("operator", {})
    dot = '<span class="doku-dot">·</span>'
    left = f"© {dt.date.today().year} {op['name']}" if op.get("name") else portal.get("title", "Dokumentation")
    if op.get("address"):
        left += dot + ", ".join(op["address"][:2])
    links = ["[Impressum](/impressum.html)", "[Datenschutz](/datenschutz.html)"] if op else []
    if op.get("email"):
        links.append(f"[Kontakt](mailto:{op['email']})")
    links.append("[Für Agenten: llms.txt](/llms.txt)")
    return {"left": left, "right": dot.join(links)}


def imprint_page(portal: dict) -> str:
    op = portal.get("operator", {})
    md = ["---", 'title: "Impressum"', "toc: false", "---", "",
          "Informationen gemäß § 5 E-Commerce-Gesetz und Offenlegung gemäß § 25 Mediengesetz.", "",
          f"**{op.get('name', '')}**  ", *(f"{line}  " for line in op.get("address", [])), ""]
    if op.get("purpose"):
        md += [f"Unternehmensgegenstand: {op['purpose']}", ""]
    if op.get("register"):
        md += ["```{=html}", '<dl class="doku-dl">', *(f"<dt>{html.escape(k)}</dt><dd>{html.escape(str(v))}</dd>"
                                                       for k, v in op["register"].items()), "</dl>", "```", ""]
    contact = []
    if op.get("email"):
        contact.append(f"E-Mail: <{op['email']}>")
    if op.get("web"):
        contact.append(f"Web: <{op['web']}>")
    if contact:
        md += ["## Kontakt", "", *(f"{c}  " for c in contact), ""]
    md += ["## Inhalte", "",
           "Dieses Portal ist ein internes Arbeitswerkzeug für angemeldete Nutzer. Die Dokumente sind technische "
           "Beschreibungen im jeweils angegebenen Stand (Version, Status, Datum) und keine zugesicherten Eigenschaften.", ""]
    return "\n".join(md)


# Standardzeilen der Datenschutzseite; ein Portal ersetzt sie über catalog.yml portal.privacy_rows.
PRIVACY_ROWS = [
    {"zweck": "Anmeldung", "daten": "Benutzername, Name, E-Mail, Gruppen", "dauer": "solange das Konto besteht"},
    {"zweck": "Sitzung im Portal", "daten": "verschlüsseltes Sitzungs-Cookie mit Benutzerkennung und Gruppen",
     "dauer": "bis zum Abmelden"},
    {"zweck": "Betrieb", "daten": "Zugriffsprotokolle des Webservers (Zeit, Pfad, Statuscode)", "dauer": "kurzfristig zur Fehlersuche"},
]


def privacy_page(portal: dict) -> str:
    op = portal.get("operator", {})
    return "\n".join([
        "---", 'title: "Datenschutz"', "toc: false", "---", "",
        f"Verantwortlich: **{op.get('name', '')}**, {', '.join(op.get('address', []))}"
        + (f", <{op['email']}>" if op.get("email") else "") + ".", "",
        "## Welche Daten anfallen", "",
        "| Zweck | Daten | Speicherdauer |", "|---|---|---|",
        *(f"| {r['zweck']} | {r['daten']} | {r['dauer']} |" for r in portal.get("privacy_rows", PRIVACY_ROWS)), "",
        "Es gibt keine Analyse- oder Werbe-Cookies, keine Einbindung externer Dienste und keine Weitergabe an Dritte. "
        "Rechtsgrundlage ist die Durchführung der Zusammenarbeit (Art. 6 Abs. 1 lit. b DSGVO) und das berechtigte "
        "Interesse an einem sicheren Betrieb (lit. f).", "",
        "## Ihre Rechte", "",
        "Auskunft, Berichtigung, Löschung, Einschränkung, Datenübertragbarkeit und Widerspruch: formlos per E-Mail an "
        + (f"<{op['email']}>" if op.get("email") else "den Betreiber") + ". Beschwerden: Österreichische Datenschutzbehörde.", "",
    ])


def tool_index_page(t: Tool, cat: dict) -> str:
    d = t.doc
    repo = t.manifest["tool"].get("repository", "")
    if t.manifest["tool"].get("commit"):
        repo += f" @ {t.manifest['tool']['commit']}"
    facts = [("Version", d.get("version")), ("Status", STATUS_DE.get(d.get("status"), d.get("status"))),
             ("Stand", d.get("date")), ("Umfang", f"{len(t.chapters)} Kapitel"), ("Quelle", repo)]
    rows = list(chapter_rows(t))
    first = next((r[4] for r in rows if r[0] == "main"), rows[0][4] if rows else "")
    md = ["---", yaml.safe_dump({"title": t.title, "subtitle": t.subtitle, "doku-tool": t.id, "toc": False},
                                allow_unicode=True, sort_keys=False).strip(), "---", "", "```{=html}"]
    if t.summary():
        md.append(f'<p class="lead doku-lead">{html.escape(t.summary())}</p>')
    md.append(
        '<div class="doku-actions">'
        f'<button class="btn btn-primary doku-export-btn" data-tool="{t.id}" type="button">'
        '<i class="bi bi-file-earmark-arrow-down"></i> PDF exportieren</button>'
        f'<a class="btn btn-outline-secondary" href="{Path(first).with_suffix(".html").as_posix()}">Lesen beginnen <i class="bi bi-arrow-right"></i></a>'
        '<div class="dropdown"><button class="btn btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" type="button">'
        '<i class="bi bi-robot"></i> Für Agenten</button><ul class="dropdown-menu">'
        f'<li><a class="dropdown-item" href="/tools/{t.id}/llms-full.md">llms-full.md – ganzes Dokument</a></li>'
        f'<li><a class="dropdown-item" href="/tools/{t.id}/llms.txt">llms.txt – Index</a></li>'
        f'<li><a class="dropdown-item" href="/tools/{t.id}/check.html">Prüfbericht ({t.mode})</a></li>'
        '</ul></div></div>')
    md.append('<div class="doku-facts">' + "".join(
        f'<div class="doku-fact"><span>{k}</span><span>{html.escape(str(v))}</span></div>' for k, v in facts if v) + "</div>")
    md.append('<p class="doku-section-label">Inhalt</p><ul class="doku-chapters">')
    part = None
    for p, num, title, summ, rel in rows:
        if p != part and p != "main":
            md.append(f'<li class="doku-ch-part">{PART_DE[p]}</li>')
        elif p != part and part is not None:
            md.append(f'<li class="doku-ch-part">{PART_DE[p]}</li>')
        part = p
        href = Path(rel).with_suffix(".html").as_posix()
        md.append(f'<li><a href="{href}"><span class="doku-ch-no">{html.escape(num)}</span>'
                  f'<span class="doku-ch-title">{html.escape(title)}</span>'
                  + (f'<span class="doku-ch-sum">{html.escape(summ)}</span>' if summ else "") + "</a></li>")
    md += ["</ul>", "```", ""]
    return "\n".join(md)


def home_page(tools: list[Tool], cat: dict) -> str:
    portal = cat.get("portal", {})
    cards = []
    for t in tools:
        d = t.doc
        chips = [f"v{d.get('version')}", STATUS_DE.get(d.get("status"), d.get("status")), f"{len(t.chapters)} Kapitel"]
        cards.append(
            '<article class="doku-card">'
            f'<div class="doku-card-top"><span class="doku-card-mark">{html.escape(tool_mark(t))}</span>'
            f'<h3><a href="tools/{t.id}/start.html">{html.escape(t.title)}</a></h3></div>'
            f'<p class="doku-card-sub">{html.escape(t.subtitle or t.summary()[:200])}</p>'
            '<div class="doku-card-foot"><div class="doku-card-meta">'
            + "".join(f'<span class="doku-chip">{html.escape(str(c))}</span>' for c in chips) +
            f'</div><button class="btn btn-sm btn-outline-secondary doku-export-btn" data-tool="{t.id}" type="button">'
            '<i class="bi bi-file-earmark-arrow-down"></i> PDF</button></div></article>')
    intro = html.escape(" ".join(portal.get("intro", "").split())).replace("`docs/`", "<code>docs/</code>")
    return "\n".join([
        "---", f"title: \"{portal.get('title', 'Dokumentation')}\"", "page-layout: full", "toc: false", "---", "",
        "```{=html}",
        f'<div class="doku-hero"><p>{intro}</p></div>',
        f'<p class="doku-section-label">Projekte ({len(tools)})</p>',
        '<div class="doku-grid doku-tools">', *cards, "</div>",
        '<section class="doku-panel"><h2>Für Agenten</h2><ul>'
        '<li><a href="llms.txt"><code>/llms.txt</code></a> – Einstieg nach llmstxt.org, verweist auf alle Projekte</li>'
        '<li><code>/tools/&lt;projekt&gt;/llms-full.md</code> – vollständige Fassung eines Projekts in einer Markdown-Datei</li>'
        '<li><a href="artifacts/index.json"><code>/artifacts/index.json</code></a> – alle PDFs je Projekt und Branding</li>'
        "</ul></section>",
        "```", "",
    ])


def write_site_index(tools: list[Tool], cat: dict, pdfs: dict):
    site = BUILD / "site"
    portal = cat.get("portal", {})
    brands = {}
    for bid in cat.get("brands", []):
        b = load_brand(bid)
        brands[bid] = {"label": b.get("display_name", bid), "description": b.get("description", "")}
    idx = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "default_brand": portal.get("default_brand", "neutral"),
        "group_brands": portal.get("group_brands", {}),
        "brands": brands,
        "tools": {t.id: {"title": t.title, "pdfs": {bid: f"/artifacts/{t.id}/{p.name}" for bid, p in pdfs.get(t.id, {}).items()},
                          "default_brand": t.doc.get("default_brand")} for t in tools},
    }
    (site / "artifacts").mkdir(parents=True, exist_ok=True)
    (site / "artifacts" / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    # Root llms.txt (überschreibt Quartos generische Variante, verweist aber auf deren .llms.md-Seiten)
    lt = [f"# {portal.get('title', 'Dokumentation')}", "",
          "> " + " ".join(portal.get("intro", "Technische Dokumentation, erzeugt aus Markdown in den Repositories (docs/).").split()), "",
          "Jedes Tool hat eine vollständige Einzeldatei (llms-full.md) und eine eigene llms.txt. "
          "Zu jeder HTML-Seite gibt es eine bereinigte Markdown-Fassung unter gleichem Pfad mit Endung .llms.md.", "",
          "## Tools", ""]
    for t in tools:
        lt.append(f"- [{t.title}](/tools/{t.id}/llms-full.md): {t.summary()[:200]}")
    lt += ["", "## Optional", ""] + [f"- [{t.id} llms.txt](/tools/{t.id}/llms.txt)" for t in tools] + \
          ["- [PDF-Index](/artifacts/index.json)", ""]
    (site / "llms.txt").write_text("\n".join(lt), encoding="utf-8")


# --------------------------------------------------------------------------- Befehle
def selected_tools(cat, tool_id=None) -> list[Tool]:
    entries = [e for e in cat["tools"] if not tool_id or e["id"] == tool_id]
    if not entries:
        raise SystemExit(f"Tool '{tool_id}' nicht in catalog.yml")
    return [load_tool(e) for e in entries]


def cmd_check(args) -> int:
    if args.path:
        p = Path(args.path)
        t = load_tool({"id": p.resolve().parent.name if p.name == "docs" else p.name, "path": str(p)}, src=p)
        tools = [t]
    else:
        tools = selected_tools(load_catalog(), args.tool)
    rc = 0
    for t in tools:
        F = check_tool(t)
        counts = write_check_report(t, F)
        print_summary(t, F, counts)
        if counts.get("error"):
            rc = 1
    return rc


def cmd_bundle(args) -> int:
    for t in selected_tools(load_catalog(), args.tool):
        p = bundle_tool(t, BUILD / "site" / "tools" / t.id, f"/tools/{t.id}")
        log(f"[bundle] {t.id}: {p.relative_to(BUILD)}")
    return 0


def cmd_export(args) -> int:
    t = selected_tools(load_catalog(), args.tool)[0]
    build_pdf(t, args.brand, extract_diagrams(t))
    return 0


def cmd_build(args) -> int:
    cat = load_catalog()
    tools = selected_tools(cat, None)
    rc = 0
    for t in tools:
        F = check_tool(t)
        counts = write_check_report(t, F)
        print_summary(t, F, counts)
        if counts.get("error"):
            rc = 1
    if rc and not args.keep_going:
        log("[build] Abbruch: check meldet Fehler (siehe build/reports/*/check.md)")
        return rc
    diagrams = {t.id: extract_diagrams(t) for t in tools}
    for t in tools:
        log(f"[build] {t.id}: {len(t.chapters)} Kapitel, {len(diagrams[t.id])} Diagramme")
    web_build(tools, cat, diagrams)
    pdfs = {}
    brands = cat.get("brands", [])
    only = args.brands.split(",") if args.brands else brands
    for t in tools:
        for bid in only:
            if args.web_only:  # vorhandene PDFs weiterverwenden
                f = BUILD / "site" / "artifacts" / t.id / f"{t.id}-{bid}.pdf"
                if f.exists():
                    pdfs.setdefault(t.id, {})[bid] = f
                continue
            pdfs.setdefault(t.id, {})[bid] = build_pdf(t, bid, diagrams[t.id])
    for t in tools:
        bundle_tool(t, BUILD / "site" / "tools" / t.id, f"/tools/{t.id}")
        rep = BUILD / "reports" / t.id / "check.md"
        if rep.exists():
            shutil.copy(rep, BUILD / "site" / "tools" / t.id / "check.md")
            (BUILD / "site" / "tools" / t.id / "check.html").write_text(simple_md_page(rep.read_text(encoding="utf-8"), t.title), encoding="utf-8")
    write_site_index(tools, cat, pdfs)
    (BUILD / "site" / "build-info.json").write_text(json.dumps({
        "built": dt.datetime.now().isoformat(timespec="seconds"),
        "versions": Path("/opt/doku/VERSIONS").read_text().splitlines() if Path("/opt/doku/VERSIONS").exists() else [],
        "tools": [t.id for t in tools], "brands": only}, indent=1), encoding="utf-8")
    log("[build] fertig: build/site")
    return 0


def simple_md_page(md: str, title: str) -> str:
    body = html.escape(md)
    return (f"<!doctype html><meta charset='utf-8'><title>Prüfbericht – {html.escape(title)}</title>"
            f"<link rel='stylesheet' href='/assets/portal.css'><body style='max-width:60rem;margin:2rem auto;padding:0 1rem'>"
            f"<p><a href='index.html'>← zurück</a> · <a href='check.md'>check.md</a></p><pre style='white-space:pre-wrap'>{body}</pre></body>")


def cmd_mounts(args) -> int:
    cat = load_catalog()
    vols = []
    for e in cat["tools"]:
        p = Path(e["path"])
        host = p if p.is_absolute() else Path(os.environ.get("DOKU_HOST_ROOT", ROOT)) / p
        vols.append(f"      - \"{host}:/sources/{e['id']}:ro\"")
    out = "# generiert von `docsctl mounts` aus catalog.yml – nicht von Hand ändern\nservices:\n  builder:\n    volumes:\n" + "\n".join(vols) + "\n"
    (BUILD).mkdir(exist_ok=True)
    (BUILD / "compose.sources.yml").write_text(out, encoding="utf-8")
    log(out)
    return 0


def main():
    ap = argparse.ArgumentParser(prog="docsctl", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--tool"); c.add_argument("--path")
    c = sub.add_parser("bundle"); c.add_argument("--tool")
    c = sub.add_parser("export"); c.add_argument("--tool", required=True); c.add_argument("--brand", required=True)
    c = sub.add_parser("build"); c.add_argument("--keep-going", action="store_true"); c.add_argument("--brands"); c.add_argument("--web-only", action="store_true", help="nur Web-Portal, vorhandene PDFs behalten")
    sub.add_parser("mounts")
    args = ap.parse_args()
    return {"check": cmd_check, "bundle": cmd_bundle, "export": cmd_export, "build": cmd_build, "mounts": cmd_mounts}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
