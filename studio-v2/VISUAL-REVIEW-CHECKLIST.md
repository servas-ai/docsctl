# Visuelle Abnahme — Referenztreue ist ein eigenes Gate

Status dieser Datei: dokumentierter Prüfvertrag, **keine bereits installierte
Laufzeitprüfung und kein neuer Test-PASS**. Gilt für die Wiederherstellung aus PR #1.

## Evidenz pro Review

Zu jeder Prüfung gehören tatsächlicher UTC-Zeitpunkt, Input-/PDF-Hash,
Referenzdatei mit Hash, geprüfter Commit, Seitenbereich, Renderer, Prüferrolle,
Befunde und offene Fehler. Ein Zeitstempel aus einem alten Chat ersetzt keinen Lauf.

## Harte Abbruchbedingungen

| Gate | PASS nur bei | Sonst |
|---|---|---|
| Referenz | Akzeptierte Vorschau tatsächlich geöffnet und identifiziert | BLOCKED_REFERENCE |
| Originalstatus | Originaldatei oder Rekonstruktion eindeutig bezeichnet | FAIL_PROVENANCE |
| Logo | Freigegebene Originaldatei vollständig sichtbar, korrekt proportioniert | FAIL_BRAND |
| Schrift | Gewollte Familie/Gewichte geprüft, kein stiller Fallback | FAIL_TYPE |
| Cover | Zentrale zusammenhängende Komposition und echte Textebenen; keine seitlichen Icons | FAIL_COVER |
| Layout | Referenzqualität, lesbare Informationsdichte, passende Seitentypen | FAIL_DESIGN |
| Daten | Echte Belege versus DEMO klar getrennt, Diagramme korrekt beschriftet | FAIL_CONTENT |
| Gesamte PDF | Jede finale Seite gerendert und angesehen; keine Clip-/Footerfehler | FAIL_RENDER |
| Unabhängige Prüfung | Separater Prüferlauf mit eigenem Befundnachweis, falls gefordert | NOT_RUN oder BLOCKED |
| Artefakt | PDF und Quelle wirklich vorhanden, Links geöffnet, Remote-Datei zurückgelesen | FAIL_DELIVERY |

Ein technisches PASS kann ein FAIL_BRAND, FAIL_TYPE oder FAIL_DESIGN nicht ausgleichen.
Ohne Referenzzugriff darf kein Referenzvergleich als bestanden eingetragen werden.

## Zweistufige Prüfung

**Gestaltung:** Logo, Typohierarchie, Raster, Bildgewicht, ruhige Coverfläche,
Seitendramaturgie, Tabellenfarben, sinnvolle Icons und Original-Anbieterlogos.
Original und Kandidat nebeneinander bei vergleichbarer Größe betrachten.

**Technik/Inhalt:** Vektortext, tatsächlich benutzte Schrift, Tabellen/Diagramme,
Links, Seitenformat, Überläufe, Quellenprovenienz, echte Asset-Rollen und
Kennzeichnung synthetischer Werte. Bestehende Pipelineprüfungen weiterverwenden.

Nicht nur HTML prüfen: PDF selbst rendern. Eine generierte UI-Collage ist kein
Screenshot einer ausgeführten Oberfläche. Ein schöner Screenshot ist kein Beleg
für alle Seiten oder einen funktionierenden Editor.

## Befundvorlage

```json
{
  "document_status": "REWORK_REQUIRED",
  "reference_status": "NOT_RUN",
  "brand_gate": "NOT_RUN",
  "typography_gate": "NOT_RUN",
  "design_gate": "NOT_RUN",
  "technical_gate": "NOT_RUN",
  "self_review": "NOT_RUN",
  "independent_review": "NOT_RUN",
  "user_acceptance": "REJECTED_PREVIOUS_OUTPUT",
  "pdf_sha256": null,
  "reference_sha256": null,
  "commit_sha": null,
  "reviewed_pages": [],
  "findings": [],
  "open_blockers": ["Original PDF/generator not recovered; use verified preview only"]
}
```

Diese Vorlage enthält absichtlich keine Erfolgswerte. Ein verantwortlicher Prüfer
trägt nur tatsächlich beobachtete Ergebnisse ein. Menschliche Bewertung bleibt
notwendig; eine Checkliste garantiert keine gute Gestaltung.
