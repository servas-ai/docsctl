---
doc_schema: 1
id: reference.befehle
title: Befehle
summary: docsctl-Befehle, Aufruf über Docker und Umgebungsvariablen.
kind: reference
status: draft
---

# Befehle

Aufruf über das Skript `bin/docsctl`: es startet das Builder-Image mit dem aktuellen Verzeichnis als
`/work`, als eigener Benutzer und ohne Netz.

| Befehl | Wirkung |
|---|---|
| `docsctl check --path docs` | Konvention prüfen, Bericht nach `build/reports/<tool>/check.md` |
| `docsctl check --tool ID` | ein Tool aus `catalog.yml` prüfen |
| `docsctl build` | alles: Prüfung, Diagramme, Web, PDFs je Branding, Agentenfassungen nach `build/site` |
| `docsctl build --web-only` | nur Web neu, vorhandene PDFs bleiben |
| `docsctl build --brands a,b` | nur diese Brands als PDF |
| `docsctl export --tool ID --brand ID` | eine PDF bauen |
| `docsctl bundle` | nur `llms-full.md` und `llms.txt` |
| `docsctl mounts` | `build/compose.sources.yml` aus `catalog.yml` erzeugen |

*Tabelle: docsctl-Befehle*

| Variable | Standard | Bedeutung |
|---|---|---|
| `DOCSCTL_IMAGE` | `docsctl:2026.10` | Builder-Image für `bin/docsctl` |
| `DOKU_ROOT` | Arbeitsverzeichnis | Projekt mit `catalog.yml`, `brands/`, `build/` |
| `DOCSCTL_HOME` | Verzeichnis von docsctl | Engine: Regeln, Vorlagen, Portal-Optik |
| `DOKU_SOURCES` | `/sources` | eingebundene Repositories je Tool-ID |

*Tabelle: Umgebungsvariablen*

`check --path` läuft auch ohne Docker mit `python3`, `PyYAML` und optional `jsonschema`:

```bash
python3 ~/docsctl/docsctl/docsctl.py check --path docs
```
