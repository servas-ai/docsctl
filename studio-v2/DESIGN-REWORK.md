# Design-Rework: zurück zur akzeptierten ursprünglichen UI/UX

Stand: 2026-11-05. Ziel: bestehender PR #1, kein paralleler Neuaufbau.

**Entscheidung: REWORK_REQUIRED. Die spätere PDF-Ausgabe ist DESIGN_REJECTED.**

## 1. Was der Nutzer ausdrücklich klargestellt hat

Die erste PDF/UI-UX war die gute Richtung. Die nachfolgenden Änderungen haben das
Ergebnis massiv verschlechtert. Die letzte PDF soll nicht weiter als gelungenes
Beispiel, visuell freigegebenes Ergebnis oder neue Gestaltungsbaseline verwendet werden.

Wörtliches Nutzerfeedback zur späteren Fassung:

> Die Ursprungs-PDF war zehnmal besser. Das Logo ist gelöscht worden.

Der Nutzer verlangt, diese Kritik und den vollständigen Reparaturauftrag im bestehenden
PR zu sichern, damit ein neuer Chat ohne den bisherigen Verlauf korrekt weiterarbeiten kann.
Die positive Bewertung der ursprünglichen UI/UX ist **keine** Abnahme aller technischen
Funktionen des V2-Branches. Auch die historische PR-Beschreibung ist keine neue Designfreigabe.

## 2. Konkret festgehaltene Regressionen

| Bereich | Akzeptierte Richtung | Abgelehnte Abweichung | Reparaturkriterium |
|---|---|---|---|
| Marke | Originale Wort-Bild-Marke mit eigenem Bildzeichen | Einfacher Textschriftzug statt vollständigem Logo | Originaldatei sichtbar, vollständig und korrekt proportioniert |
| Schrift | Feinere Typografie, bewusst gewählte Gewichte und Hierarchie | Andere Schrift mit schwereren Überschriften | Ausgangshierarchie erhalten; verwendete Schrift im Export prüfen |
| Deckblatt | Große zusammenhängende Glas-Komposition und präzise gesetzter Titel | Kleines rechteckiges Bild unter zentriertem Text | Komposition als gestaltetes Cover, nicht als Bildanhang |
| Seitenrhythmus | Eigene Layouts für UI, Prozess, Daten und Bildwelt | Wiederholte Überschrift-Kasten-Tabelle-Struktur | Abwechslungsreiche, inhaltsbezogene Seitentypen |
| Informationsgewicht | Visuelle Beispiele, echte UI-Ansichten und verständliche Vergleiche | Zu viel Status-, Integrations- und Prüfdokumentation im sichtbaren Bericht | Belege und Prüfprotokolle aus dem Hauptlayout auslagern |
| Qualitätssicherung | Technisch korrekt UND gestalterisch referenztreu | Tests/Überlauffreiheit als Ersatz für Designurteil | Beide Ebenen separat prüfen und dokumentieren |

Diese Feststellungen stammen aus dem Nutzerfeedback und dem zuletzt dokumentierten
Original-/Neufassungsvergleich. Sie behaupten keinen neuen vollständigen PDF-Renderlauf.

## 3. Die spätere Farbentscheidung bleibt gültig

Die erste Vorschau zeigte dunkle und helle Seiten mit einem Lime-Akzent. Später wurden
weißer Hintergrund und orangefarbene Glasobjekte gewünscht. Das hebt die positive
Bewertung der ursprünglichen Gestaltung **nicht** auf.

Ziel ist: ursprüngliche Logo-/Typo-/Rasterqualität + gezielt angepasste helle/orange
Bildwelt. Nicht: die abgelehnte PDF weiterpolieren oder pauschal sämtliche Farben auf
Lime zurückdrehen. Website-, Angebots- und historische Figma-Profile sind getrennte
Quellen. Ein Token aus einem Generator ist nicht automatisch der aktuelle Website-Token.
Exakte Markenwerte und Logos nur aus dem freigegebenen externen Brand-Paket übernehmen.

## 4. Bildsprache und Icons

Deckblatt: ein zentrales, thematisch erkennbares Glasobjekt, wenige unterstützende
geometrische Formen, transparenter und satinierter Glascharakter, weiches Studiolicht,
weißes Umfeld. Genügend ruhige Fläche für echte Textebenen. Keine seitliche Icon-Spalte.
Schärfevarianten dürfen den Fokus verändern, aber nicht die Erkennbarkeit zerstören.

Innenseiten: sinnvolle UI-Icons, originale Anbieterlogos, farbige Status- und
Vergleichsmatrizen sowie echte Screenshots mit Herkunft. Ein Favicon ist nicht pauschal
ein Wortlogo; ein Open-Graph-Bild ist kein Logo. Bildquelle, Asset-Rolle, Identität,
Rechte und Sichtprüfung getrennt dokumentieren. Keine frei erfundenen Anbieterzeichen.

Mermaid soll aus editierbarer Quelle nativ gerendert werden; eine beschriftete statische
Vorschau ist kein Ersatz für eine getestete native Renderingstrecke. Wissenschaftliche
Seitentypen brauchen lesbare Formeln, Bildlegenden, Tabellen, Literatur und klare
Unsicherheiten, nicht bloß zusätzliche Dekoration.

## 5. Was existiert — und was nicht gesichert ist

- Erster V2-Code: Commit `75780f415e426d5dac485cbeb3a8a816483bd706`.
- Vor diesem Rework-Auftrag geprüfter Head: `f6e8018659b89f886053997d12d68c8f9b1042e6`.
  Dieser enthält zusätzliche UX-Vorschläge und einen statischen Wireframe. Beides erhalten;
  weder die Vorschläge noch der Wireframe als bereits implementierte Oberfläche ausgeben.
- Eine ursprüngliche Vorschau mit sechs Seitenansichten und ein Original-/Neufassungsvergleich
  sind als Gesprächsartefakte vorhanden. Sie sind **nicht die vollständige Original-PDF**.
- Ursprüngliche 14-seitige PDF und ursprüngliches Generator-ZIP sind in der aktuellen
  Arbeitsumgebung nicht wiedergefunden. Eine neue Rekonstruktion darf nicht als Original gelten.
- Später gelieferte PDF, Paket und Visual-Gate-Patch sind getrennte Artefakte. Die PDF wurde
  verworfen. Der Patch wird durch diesen Dokumentationscommit nicht automatisch angewandt.
- Historisch genannte 132 Tests und spätere 21 Tests beziehen sich auf verschiedene
  Lieferstände. In diesem Sicherungsschritt nicht erneut ausgeführt; kein Design-PASS daraus.
- Kein hier nachgewiesener globaler Startup-Hook, keine abgeschlossene Puck-/OpenUI-Integration,
  keine neue Live-Modellprüfung und kein neuer Produktions-PDF-Build.

Die detaillierten Markenquellen, Artefaktnamen und Prüfsummen gehören zum bestehenden
privaten Projektcheckpoint. Der PR-Kommentar verlinkt diesen. Verlinkte Evidenz ist
nicht mit ins öffentliche Repository hochgeladenen PDF-/Bilddateien gleichzusetzen.

## 6. Konkreter Wiederanlauf

1. Aktuellen PR-Head und vorhandene Arbeiten lesen, keine fremden Änderungen überschreiben.
2. Akzeptierte Vorschau, Vergleich und vorhandene Originalassets tatsächlich öffnen.
3. Ursprüngliche PDF/Generatorquelle über vorhandene Artefakte und berechtigte Ablage suchen.
   Fehlende Quellen als Blocker dokumentieren; den Originalfund nicht vortäuschen.
4. Bestehende Generator-/Brand-/Puck-/OpenUI-Bausteine auf Wiederverwendung prüfen, ohne
   aus einem Adapter eine fertig integrierte Laufzeit zu machen.
5. Zuerst drei repräsentative Seiten überarbeiten: Cover, große Vergleichsmatrix,
   Diagramm-/UI-Seite. Jede neben der Referenz prüfen, bevor der Rest ausgeweitet wird.
6. Logo-, Schrift- und Cover-Regressionsprüfungen in den tatsächlichen Exportweg integrieren.
7. Vollständige PDF rendern; alle Seiten visuell prüfen; unabhängige Prüfung nur mit
   tatsächlichem Prüferlauf und Befunden melden.
8. Reviewbare Änderung im selben PR sichern. Konkrete PDF-/Quelllinks und offene Punkte
   nennen; ohne erfüllte Designabnahme weder fertig melden noch mergen.

## 7. Definition of Done

Alle harten Bedingungen aus `VISUAL-REVIEW-CHECKLIST.md` müssen erfüllt sein. Eine
vorhandene Prüfdatei oder ein schöner Mockup ist kein Wirkungsnachweis. Eine unverändert
hässliche PDF mit mehr Test-PASSs ist weiterhin ein abgelehntes Ergebnis.
