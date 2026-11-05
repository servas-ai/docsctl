# AGENTS.md – docsctl

Werkzeug und Regelwerk der Doku-Konvention v1. Öffentliches Repository.

- Regeln für Dokumentation in anderen Repos: `SPEC.md` (verbindlich), Schemas in `spec/`.
- Das eigene Handbuch `docs/` hält sich an `SPEC.md`; `make check` muss ohne Fehler durchlaufen.
- Image: `make image`; Aufruf: `bin/docsctl …` (Docker, ohne Netz).
- Keine kunden- oder firmenspezifischen Inhalte hier: keine eigenen Brands außer `neutral`, keine
  internen Hostnamen, Pfade, Zugangsdaten. Portal-Projekte mit `catalog.yml` liegen in eigenen Repos.
- Optik der PDFs nur über `brands/<id>/` und `quarto/_extensions/doku/typst-template.typ`.

## Studio v2 / PDF-Gestaltung: zuerst den Rework-Auftrag lesen

Vor Änderungen an Studio v2, PDF-Layouts, Markenanbindung oder visueller Abnahme:
[Studio-Regeln](studio-v2/AGENTS.md), [Design-Rework](studio-v2/DESIGN-REWORK.md)
und [Startbrief für neue Chats](studio-v2/START-NEW-CHAT.md) lesen.
Die spätere PDF-Ausgabe wurde vom Nutzer ausdrücklich abgelehnt. Ein technischer
Test-PASS ist keine Designfreigabe. Die ursprünglich akzeptierte UI/UX ist die
Gestaltungsreferenz; fehlende Originaldateien dürfen nicht als wiederhergestellt gelten.
Diese Regeln sind projektbezogene Anweisungen, kein global installierter Chat-Systemprompt.
