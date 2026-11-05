# Studio v2 — Design erhalten, Regression beheben

Gilt innerhalb von `studio-v2/`; die Root-Regeln bleiben bestehen.

## Aktueller Auftrag

**REWORK_REQUIRED / DESIGN_REJECTED — Stand 2026-11-05.**
Die ursprüngliche UI/UX gefiel dem Nutzer. Die spätere PDF hat diese Qualität
massiv verschlechtert. Sie ist keine neue Designbaseline und kein akzeptiertes Release.

Vor jeder Fortsetzung lesen:
1. `DESIGN-REWORK.md` — Nutzerentscheidung, Regression und Abnahmekriterien.
2. `START-NEW-CHAT.md` — vollständiger projektbezogener Startauftrag.
3. `VISUAL-REVIEW-CHECKLIST.md` — getrennte technische und gestalterische Prüfung.
4. Bestehenden PR #1 samt aktuellen Kommentaren und seinem aktuellen Head prüfen.

## Nicht verhandelbar

- Akzeptierte Originalvorschau tatsächlich ansehen, nicht aus einer Beschreibung nachbauen.
- Originale Wort-Bild-Marke einschließlich ihres Bildzeichens erhalten. Kein Text-Ersatz,
  kein als Logo ausgegebenes Favicon, kein abgeschnittenes oder unsichtbares Markenzeichen.
- Originale Typohierarchie und passende Schriftgewichte erhalten. Fehlende Schrift nicht
  still durch eine andere ersetzen und anschließend als markenkonform abnehmen.
- Die später gewünschten hellen/orangefarbenen Glas-Cover sind eine gezielte Variation,
  keine Erlaubnis, gleichzeitig Typografie, Raster und gesamte Bildsprache auszutauschen.
- Cover: eine ruhige zentrale Glas-Komposition, großzügige Fläche für separat gesetzten
  Vektortext; keine rechten Icon-Leisten, Badges, Kontaktbögen oder eingebrannten Labels.
- Innenseiten: viele sinnvolle Icons, Original-Anbieterlogos und farbige Vergleiche;
  keine dekorative Überladung, mikroskopischen Begleittexte oder monotone Kastenserie.
- Bestehende Generatoren und UI-Komponenten zuerst prüfen und wiederverwenden.
  Kein weiterer eigenständiger Editor als Ersatz für eine offene Puck-/OpenUI-Integration.
- Generierte Moodboards sind keine Screenshots, keine Testbelege und keine echten PRs.
- Firmenassets bleiben im autorisierten Portal/privaten Evidenzbereich. Keine Fontdateien,
  Secrets, vertraulichen Rohquellen oder fremden Designreferenzen öffentlich kopieren.

## Freigabe

Jede finale PDF-Seite aus der tatsächlichen PDF rendern und gegen die Referenz ansehen.
Logo, Typografie, Bildkomposition, Informationsdichte, Diagramme, Tabellen und Quellen
prüfen. `PASS_SELF_REVIEW` ist nicht `PASS_INDEPENDENT_REVIEW` und nicht Nutzerfreigabe.
Ein nicht gestarteter Reviewer bleibt `NOT_RUN`; eine fehlende Voraussetzung `BLOCKED`.
Keine fertige oder verbesserte PDF behaupten, solange wesentliche Designbefunde offen sind.

Dieses Update speichert den Reparaturauftrag. Es implementiert selbst weder einen
Startup-Hook noch neue Tests, einen automatischen Designrichter oder eine reparierte PDF.
