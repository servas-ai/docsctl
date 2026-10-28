# Doku-Konvention v1 (verbindlich für Menschen und Agenten)

Gilt für jedes Repository, dessen Dokumentation im Portal und als PDF erscheinen soll.
Prüfung: `bin/docsctl check --path docs` (Exit 0 = ok, siehe `README.md`). Schemas: `spec/frontmatter.schema.json`,
`spec/docs-manifest.schema.json`. Beispiel: `spec/examples/docs.yml` und `docs/` dieses Repos (das Handbuch von docsctl hält sich selbst an diese Regeln).

## 1. Ablage

```text
<repo>/
├── AGENTS.md            # verweist auf diese Regel ("docs/ pflegen, docsctl check muss grün sein")
└── docs/
    ├── docs.yml         # Manifest: Tool, Dokument, Reihenfolge
    ├── index.md         # Überblick (kind: overview)
    ├── 10-architecture/ # arc42 (kind: architecture, arc42_section 01–12), ADRs in adr/ (MADR, kind: adr)
    ├── 20-explanation/  # Diátaxis: Erklärung
    ├── 30-how-to/       # Diátaxis: Anleitung für eine Aufgabe
    ├── 40-tutorials/    # Diátaxis: Lernpfad
    ├── 50-reference/    # Diátaxis: Nachschlagen (CLI, API, Konfiguration)
    ├── 60-operations/   # Betrieb, Runbooks
    └── assets/          # Bilder (SVG/PNG), nur relativ verlinkt
```

Unterordner sind optional; kleine Tools dürfen flach bleiben. **Keine** Quarto-, Typst-, Branding-
oder Web-Konfiguration ins Repo – das liegt zentral in docsctl bzw. im Portal, das die Repos einsammelt.

## 2. `docs.yml`

```yaml
schema: 1
tool: { id: mein-tool, title: "Mein Tool", subtitle: "…", summary: "…", repository: firma/mein-tool }
document: { language: de-AT, version: "1.2.0", status: draft, date: 2026-10-26, numbering: auto }
front_matter: [00-kurzfassung.md]     # optional: vor dem Inhaltsverzeichnis
chapters: [index.md, 10-architecture/, 30-how-to/]   # Dateien oder Ordner (Ordner: nach order, dann Name)
appendices: [90-glossar.md]           # optional
```

Die Reihenfolge kommt **nur** aus `docs.yml` (und `order` bei Ordnern), nie aus Zufall.

## 3. Kapiteldatei

```markdown
---
doc_schema: 1
id: howto.lokal-starten          # stabil, repo-weit eindeutig
title: Lokal starten             # ohne Nummer
summary: Ein Satz für llms.txt.  # empfohlen
kind: how-to                     # overview|tutorial|how-to|reference|explanation|architecture|adr|operations|glossary|appendix
status: draft                    # draft|review|reviewed|released|deprecated
---

# Lokal starten

Text …
```

Regeln:

1. Genau **eine H1**, direkt nach dem Front Matter, Text = `title`. Keine Ebene überspringen (H2 → H4 verboten).
2. **Nummerierung macht die Pipeline** (`numbering: auto`): keine Nummern in Überschriften, Abbildungen,
   Tabellen. `numbering: manual` nur für Altbestand, dann überall Nummern („# 3 Titel“, „## 3.1 …“).
3. Markdown-Dialekt: CommonMark/GFM – Absätze, Listen, Pipe-Tabellen, Fenced Code **mit Sprache**
   (` ```bash `, ` ```text `), Links, Bilder. Verboten: MDX/JSX, `<script>`, Quarto-Shortcodes `{{< >}}`,
   Pandoc-Divs `:::`, `{mermaid}`-Syntax. Rohes HTML nur `<br>` in Tabellenzellen.
4. **Diagramme** als ` ```mermaid ` (flowchart, sequenceDiagram, stateDiagram-v2, …), Quelltext bleibt im Markdown.
5. **Unterschriften**: direkt unter jedem Diagramm/Bild eine Zeile `*Abbildung: Text*`, unter jeder
   Tabelle `*Tabelle: Text*` (bei `manual`: `*Abbildung 4.1: Text*`). Sternchen im Text als `\*`.
   Quellenangaben am Ende in Klammern `(Quellen: pfad, pfad)` – sie fallen im Verzeichnis automatisch weg.
6. **Links** relativ auf `.md`-Dateien (`[Betrieb](60-operations/betrieb.md#backup)`), Anker im
   GitHub-Slug-Stil. Keine Links aus `docs/` hinaus; Code-Belege als Text in `sources:` oder im Satz.
7. Keine Geheimnisse, keine echten Kundendaten, Platzhalter wie `<api-key>`.

## 4. Was daraus entsteht (nicht von Hand pflegen)

| Ausgabe | Pfad im Portal |
|---|---|
| Web-Seiten (Wiki, Suche) | `/tools/<id>/…html` |
| PDF je Branding | `/artifacts/<id>/<id>-<brand>.pdf` |
| Agenten-Gesamtfassung | `/tools/<id>/llms-full.md`, `/tools/<id>/llms.txt`, `/llms.txt` |
| Prüfbericht | `/tools/<id>/check.md` |

*Tabelle: Ausgaben der Pipeline*

`llms.txt`/`llms-full.md` werden generiert – nie im Repo pflegen.

## 5. Prüfstufen von `docsctl check`

- **error** (Build bricht ab): fehlende Datei/H1, kaputter Link/Anker, fehlendes Bild, verbotenes Konstrukt,
  ungültiges Front Matter/Manifest (im Modus `strict`).
- **deviation**: Altbestand im Modus `compat` (z. B. `book.yaml` statt `docs.yml`); der Build gleicht aus,
  die Quelle bleibt unverändert. Ziel: auf `strict` migrieren.
- **warning**: Codeblock ohne Sprache, fehlende Unterschrift, unmaskiertes `*`, Überschriftensprung.
