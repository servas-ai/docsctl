# AGENTS.md – docsctl

Werkzeug und Regelwerk der Doku-Konvention v1. Öffentliches Repository.

- Regeln für Dokumentation in anderen Repos: `SPEC.md` (verbindlich), Schemas in `spec/`.
- Das eigene Handbuch `docs/` hält sich an `SPEC.md`; `make check` muss ohne Fehler durchlaufen.
- Image: `make image`; Aufruf: `bin/docsctl …` (Docker, ohne Netz).
- Keine kunden- oder firmenspezifischen Inhalte hier: keine eigenen Brands außer `neutral`, keine
  internen Hostnamen, Pfade, Zugangsdaten. Portal-Projekte mit `catalog.yml` liegen in eigenen Repos.
- Optik der PDFs nur über `brands/<id>/` und `quarto/_extensions/doku/typst-template.typ`.
