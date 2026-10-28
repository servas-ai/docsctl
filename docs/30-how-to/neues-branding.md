---
doc_schema: 1
id: howto.neues-branding
title: Neues Branding
summary: Ein weiteres Brand-Paket (Farben, Schriften, Logo, Deckblatt) anlegen.
kind: how-to
status: draft
order: 20
---

# Neues Branding

Ein Branding ist ein Verzeichnis `brands/<id>/` mit vier Teilen:

| Datei | Inhalt |
|---|---|
| `_brand.yml` | Farben, Logo, Schriften (Quarto-brand.yml-Format) |
| `report-brand.yml` | PDF-Metadaten: Layout-Variante, Deckblatt-Kicker, Kopf-/Fußzeile, Disclaimer |
| `mermaid.json` | Diagrammfarben und -schrift |
| `assets/` | Logo, Schriften (`assets/fonts/*.ttf`, nur freie Lizenzen) |

*Tabelle: Bestandteile eines Brand-Pakets*

Eigene Brands liegen im Projekt, das docsctl aufruft (`brands/<id>/` neben `catalog.yml`), nicht in
docsctl selbst. Ein gleichnamiges Verzeichnis im Projekt hat Vorrang vor dem mitgelieferten.

Vorgehen: `brands/neutral/` aus docsctl kopieren, Werte ersetzen, die ID in `catalog.yml` unter
`brands` ergänzen, bauen. Das Template kennt drei Layout-Varianten (`report-brand.yml`, Feld `layout`):

| Layout | Wirkung |
|---|---|
| `neutral` | schlicht, ohne Farbflächen |
| `stripe` | Farbstreifen am Seitenkopf, Linien unter Kopf- und Fußzeile |
| `framed` | Titelkopf auf jeder Seite, farbige Überschriften, Tabellenrahmen |

*Tabelle: Layout-Varianten im Typst-Template*

Braucht das Deckblatt eine ganz neue Anordnung, kommt in `quarto/_extensions/doku/typst-template.typ`
eine weitere Variante dazu.
