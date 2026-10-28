# docsctl

Werkzeug und Regelwerk für technische Dokumentation im Repository. Markdown in `docs/` nach einer
einzigen Konvention ([`SPEC.md`](SPEC.md)) wird zu:

- **Web-Seiten** mit Suche, Projekt-Navigation und Diagrammen,
- **PDFs je Branding** im Stil einer technischen Abschlussarbeit (Deckblatt, Verzeichnisse, nummerierte Kapitel),
- **Agentenfassungen** (`llms.txt`, `llms-full.md`).

Die Quelle bleibt unverändert; Optik, Satz und Branding liegen zentral hier und nicht in den Repositories.

## Schnellstart (ein Repository)

Voraussetzung: Docker.

```bash
git clone https://github.com/servas-ai/docsctl.git ~/docsctl
make -C ~/docsctl image                 # Builder-Image (Quarto, Typst, mermaid-cli), einmalig

cd mein-repo                            # enthält docs/docs.yml + Kapitel nach SPEC.md
~/docsctl/bin/docsctl check --path docs # Konvention prüfen, Bericht: build/reports/<tool>/check.md
~/docsctl/bin/docsctl build             # build/site: Web, PDF (artifacts/), llms-full.md
```

Ohne `catalog.yml` baut docsctl das Repository im Arbeitsverzeichnis als einziges Tool mit dem
Branding `neutral`. Der Build läuft ohne Netz und als eigener Benutzer.

## Was im Repository stehen muss

```text
mein-repo/
├── AGENTS.md            # Satz: "docs/ nach Doku-Konvention v1 (servas-ai/docsctl) pflegen, docsctl check muss grün sein"
└── docs/
    ├── docs.yml         # Manifest: Tool, Dokument, Reihenfolge der Kapitel
    ├── index.md         # Überblick
    └── …                # Kapitel (arc42 / Diátaxis-Ordner, siehe SPEC.md)
```

Verbindlich ist [`SPEC.md`](SPEC.md); maschinenlesbar in [`spec/`](spec/) (JSON-Schemas für `docs.yml`
und das Front Matter jeder Kapiteldatei). Ein vollständiges Beispiel ist [`docs/`](docs/) – das Handbuch
von docsctl selbst, gebaut mit `make build`.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `SPEC.md`, `spec/` | Regelwerk und Schemas |
| `docsctl/docsctl.py` | Prüfen, Normalisieren, Bauen, Bündeln |
| `quarto/_extensions/doku/` | Dokumentklasse für PDFs (Typst-Template, Lua-Filter) |
| `portal/assets/` | Optik und Bedienelemente der Web-Seiten |
| `brands/neutral/` | mitgeliefertes Branding |
| `Dockerfile`, `builder/` | Builder-Image mit gepinnten Versionen |
| `bin/docsctl` | Aufruf über Docker |
| `docs/` | Handbuch (nach der eigenen Konvention) |

## Portal über viele Repositories

Ein eigenes Projekt mit `catalog.yml`, eigenen `brands/` und Betreiberangaben sammelt mehrere
Repositories ein; `build/site` ist statisch und kann hinter jeden Login-Proxy gestellt werden.
Anleitung: [`docs/30-how-to/portal.md`](docs/30-how-to/portal.md).

## Lizenz

Apache-2.0, siehe [`LICENSE`](LICENSE). © servas.ai FlexCo.
