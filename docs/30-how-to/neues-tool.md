---
doc_schema: 1
id: howto.neues-tool
title: Repository dokumentieren
summary: In einem Repository docs/ nach der Konvention anlegen, prüfen und als Web und PDF bauen.
kind: how-to
status: draft
order: 10
---

# Repository dokumentieren

Voraussetzung ist Docker. docsctl einmal klonen und das Builder-Image bauen:

```bash
git clone https://github.com/servas-ai/docsctl.git ~/docsctl
make -C ~/docsctl image
```

1. Im eigenen Repository `docs/docs.yml` und die Kapiteldateien nach `SPEC.md` anlegen. Vorlage:
   `spec/examples/docs.yml` und das Verzeichnis `docs/` von docsctl.
2. In `AGENTS.md` des Repositories einen Satz ergänzen, damit Agenten die Regeln kennen:

   ```text
   Dokumentation liegt in docs/ nach der Doku-Konvention v1 (servas-ai/docsctl, SPEC.md);
   `docsctl check --path docs` muss ohne Fehler durchlaufen.
   ```

3. Prüfen, im Wurzelverzeichnis des Repositories:

   ```bash
   ~/docsctl/bin/docsctl check --path docs
   ```

   Der Bericht steht danach in `build/reports/<tool>/check.md`. Exit-Code 0 heißt: keine Fehler.

4. Bauen:

   ```bash
   ~/docsctl/bin/docsctl build
   ```

   Ergebnis in `build/site/`: Web-Seiten (`index.html`), die PDF unter `artifacts/<tool>/` und die
   Agentenfassung unter `tools/<tool>/llms-full.md`. `build/` gehört in `.gitignore`.

Ohne `catalog.yml` im Arbeitsverzeichnis nimmt docsctl `docs/` als einziges Tool und das Branding
`neutral`. Altbestand ohne `docs.yml` (zum Beispiel ein `book.yaml`) läuft im Modus `compat`:
Abweichungen stehen im Prüfbericht, der Build gleicht sie aus.
