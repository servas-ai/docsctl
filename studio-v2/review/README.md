# Build02 geprüft — gezielte Build03-Reparatur

**Kein neuer Editor, kein neuer Stil, keine finale Designfreigabe.** Cover, Aspekta,
Original-Wortbildlogo, Diagramm und Seitenraster des bestehenden Proofs bleiben
maßgeblich. Die hier gespeicherten neutralen Funktionen enthalten keine Brandbilder,
Fontdateien, privaten PDF-Raster oder Runtimepfade. Der externe Owner-Runner bleibt
für tatsächliche PDF-Ausgabe und echte Poppler-Raster zuständig.

## Belegter Rücklauf

| Prüfung | Beobachtung |
|---|---|
| Build02-ZIP | 5.855.498 Bytes; SHA256 `d33f0b2f65a5b53c688e0be19a3507061b8fd691340c2e2c128135fecc23ef01` |
| Originalreceipt | SHA256 `4cd949351dc8eb090d855f9c1ea9b7c8991632d3a0130dc22c8c4bec695a725c` |
| Manifest | Alle 33 Ausgaben byte-/hashgleich geprüft |
| Erhaltene Baseline | Alle 34 Dateien des vorhandenen Build01-Rücklaufs erneut geprüft; keine erneute Live-VM-Prüfung behauptet |
| Seiten | Vier A4-, eine A2- und eine Anbieterprüfseite einzeln anhand der gelieferten echten Serverraster angesehen |
| Cover | Build01-/Build02-PNGs bytegleich; SHA256 `a6d79cae52581a6862e41491f808af03f18d7c2c5d3466ab7099a5f9bd6ad6e0` |

Das eingegangene Receipt berichtet erfolgreichen Serverbuild mit eingebetteter
Aspekta und Poppler. Ein technischer oder Coverpixel-PASS ist kein globales Designurteil.
Der aktuelle Befund lautet **OWNER_REVIEW_CHANGES_REQUESTED**.

## Exakte Restfehler und begrenzte Korrektur

| Befund | Ursache / Änderung |
|---|---|
| Schwarzes Kästchen in Matrixfußnote | Im Quelltext steht U+2260; aus der gelieferten PDF wird an dieser Stelle U+0000 extrahiert. Neuer Wortlaut: „Produktfunktion bedeutet nicht: im PR integriert oder getestet.“ Kein Ersatzfont. Der Guest-Runner prüft vor jeder Textausgabe die tatsächliche Aspekta-Glyphenmap und dokumentiert zusätzlich die U+2260-Abdeckung aller drei Gewichte. |
| Typst fälschlich als Wortmarke | Das gelieferte Bild ist ein README-Banner. Rolle jetzt `readme_banner`; im Matrixkopf steht der normale Textname, im separaten Herkunftsbeleg „README-Banner; keine freistehende Wortmarke“. Keine neue Marke nachgebaut. |
| Puck blieb unbenutzt | Der Abruf war erfolgreich. Der alte Flat-Path-Parser scheitert an der XML-Deklaration; außerdem enthält die unveränderte Quelle vier Gruppen, sechs Pfade und ein Polygon. Die begrenzte Normalisierung entfernt nur inerte Metadaten, flacht transformlose Gruppen ab und schließt die originalen Polygonpunkte exakt. CSS, Transformationen, Skripte, DTD, Entitäten, Bilder und Links bleiben ausgeschlossen. |
| Vergrößerte Logo-Crops unscharf | Derselbe Ausschnitt wird im Gast aus den vorhandenen, hashgeprüften PDFs gerastert: Identität mit 600 dpi, Tabellen mit 300 dpi. Die Platzierung hält mindestens 300 dpi gesampelte Auflösung ein; bei fehlendem PDF/Renderer wird ausschließlich der vorhandene Crop kleiner gezeigt. Keine Retusche, keine erfundene Vorher-Abbildung. |

Die Puck-Quelldatei wurde am tatsächlich zurückgegebenen Bytebestand geprüft:
`6d8c23f5202cbc14bac53c81668886b1b9d17ebc6cf9ec724542942fb6707c98`.
Die normalisierte SVG-Struktur besteht aus sieben gefüllten Pfaden; Geometrie,
Reihenfolge und Farben bleiben erhalten. **Das ist ein Parsernachweis, noch kein
neuer Rendering- oder Markenidentitäts-PASS.** OpenUI bleibt unverändert; pdfme bleibt
als Favicon/Bildzeichen bezeichnet. Quelle und Markenrechte sind getrennte Prüfungen.

Die Evidenzseite bleibt ein **Reviewanhang**, keine neu getestete Produktansicht.
Der Hinweis auf unterschiedliche Tabelleninhalte bleibt sichtbar. Ihr Rahmen und
ihre Beschriftungspositionen bleiben erhalten; nur die Bilder werden auflösungsbewusst
eingepasst. Höhere Raster-dpi können keine fehlenden Details in einer Quelle erzeugen.

## Code und Prüfung

- `refine_pages.py`: gleiche Seitengeometrie; lesbare Fußnote, korrekte Asset-Rollen,
  begrenzte Bitmapplatzierung. Kein Coverrenderer, kein Netzwerk.
- `repair_assets.py`: reine Funktionen für Glyphenabdeckung, genaue SVG-Normalisierung,
  Crop-Koordinaten und DPI-Untergrenze; keine automatischen Assetabrufe.
- `provider-assets.json`: dieselben vier Quellen, nun mit allen zurückgelesenen
  SHA256-Pins und korrekter Bannerrolle; Build03 nutzt ausschließlich vorhandene Bytes.
- `refinement.json`: unveränderte Vergleichs-/Flussdaten; PR-Snapshot `ea74210`.
- `test_refine_pages.py`, `test_repair_assets.py`: reine Verträge und Fake-Painter-Aufrufe.

```bash
cd studio-v2/review
python -m unittest test_refine_pages test_repair_assets -v
```

**85 Tests ausgeführt: 85 bestanden.** Kein lokaler PDF-Build, keine lokale
Rasterisierung, kein Browser- oder Modellstart. Die Tests messen keine echten
Fontmetriken. Die Prüfung echter Fontdateien, Ausgabe und Poppler-Crops erfolgt erst
im bereits zugeordneten Guest-Runner; er substituiert keine Schrift und lädt nichts nach.

## Nächster abgegrenzter Lauf

Ein einzelnes privates, hashgebundenes Reparaturpaket verwendet exakt die bestehenden
Build01-/Build02-Quellen, Receipts und Assets. Es ändert keine Baseline-Datei und
prüft nach dem Lauf beide Manifeste erneut. Alle sechs neuen Seiten müssen als echte
PDF-Raster zurückgegeben werden. Cover und unverändertes Diagramm bekommen jeweils
einen exakten Pixelvergleich mit Build02; die anderen Seiten Vorher/Nachher-Paare.

**Build03: PAYLOAD_READY / SERVER_EXECUTION_NOT_RUN / VISUAL_REVIEW_NOT_RUN.**
Der bestandene Build02 ist keine Ausführung dieses Patches. 300-dpi-Heromotiv,
vollständige Originalbytes, native Mermaid-Ausführung, Produktionsabnahme,
Anbieter-/Markenrechte und finale Nutzerfreigabe bleiben getrennte offene Gates.
Kein Netzwerk, keine Installation, kein zusätzlicher Worker, kein Merge oder Deployment.

Historische Build01-/Build02-Vorbereitung und deren frühere 40 Tests bleiben unter
Commit `ea74210641327c95e0c6ffaf7be9653d6c5e82fe` nachvollziehbar; sie werden nicht
als neue Build03-Abnahme ausgegeben.
