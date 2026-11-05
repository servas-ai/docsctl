# Build03-Rücklauf und Anwendung auf den bestehenden Vollbericht

**DESIGN_REJECTED / REWORK_REQUIRED bleibt bis zur passenden Nutzerabnahme bestehen.**
Die gezielten Build03-Reparaturen sind kein globaler Design-, Produkt- oder Produktions-PASS.

## Belegter Rücklauf

Rückpaket: 5.517.166 Bytes; SHA256 `264b3f8cc3ae732b558af4fcc4c5836a626ca3136029356cbfb7f8abdf5e69af`.
Unverändertes Receipt: `5fbeff4cb321b8ea17c27a85d73df3784e533f71db2cc43b12f04a9422e06374`.
Separater Wrapperbeleg: `ed2ffeeca5b72cc9edfc1828caeb5c710bb9eb2dd5adc6b6de261b2bd71f7ef0`.

Alle 37 Inhaltsdateien wurden gegen das empfangene Receipt auf Bytezahl und SHA256 geprüft;
das Receipt selbst gegen den mitgeteilten Hash. Damit sind alle 38 ZIP-Mitglieder erfasst.
Das vom Relay genannte äußere Manifest lag nicht separat vor; dessen erneute Prüfung wird
nicht behauptet. Die erhaltenen Build01-/Build02-Archive wurden ebenfalls geprüft (34/33
Dateien), nicht nochmals auf der VM gelesen.

Der belegte Gastlauf dauerte vom 05.11.2026 08:07:37 bis 08:07:50 UTC, Wrapperexit 0.
Die sechs zurückgegebenen Seitenraster wurden einzeln angesehen. Fußnote, Puck-Geometrie
und korrekte Typst-Bannerrolle sind im geprüften Umfang repariert. Cover und Diagramm
sind nach dem eingegangenen RGB-Befund identisch geblieben. Globale Abnahme bleibt offen.

Das Receipt nennt unter `source_pr_base` den Vorfahren `ea74210`; die tatsächlich gebundenen
Reparaturdateien und Runnerhashes gehören zum nachfolgenden Stand `b4d8e3d`. Das originale
Receipt wird deswegen nicht umgeschrieben. Codebinding und historische Basereferenz bleiben
getrennt nachvollziehbar.

## Keine weitere isolierte Proof-Runde

Die vorhandene, elfseitige Berichtsquelle wird anhand ihrer unveränderten HTML-, Skript-
und Quellen-Hashes gebunden. Ihr **Inhalt**, nicht ihr verworfener Stil, wird weitergeführt.
Sie ist nicht die fehlende ursprüngliche 14-seitige Original-PDF.

| Vorhandenes Thema | Anwendung in der Vollfassung |
|---|---|
| Cover | Bestehende geprüfte Coverfunktion und Originalassets; nur korrekte Berichtsfußzeile |
| Arbeitsstand / Werkzeuge | Lesbare Rollenmatrix; Produktfunktion von PR-Integration getrennt |
| Branding | Belegte Profile und tatsächlich gewählte Rekonstruktion getrennt |
| Wiederverwendung | Vorhandener Prüf-/Rückweg, kein weiterer Editor |
| Icons / Logos | Originalvektoren; kleine quellengerechte Raster; Banner nicht als Wortmarke |
| Asset-Pipeline | Bestehende Collector-/Adapterrollen, kein neuer Scraper |
| Vorlagenmatrix | Alle 16 ursprünglichen Kriterien und fünf Profile erhalten |
| Wissenschaft | Methode, Befundgrenze und didaktische Textformel ohne erfundene Messdaten |
| Visual Gate | Build03-Belege getrennt von noch ausstehender Vollberichtprüfung |
| Design-Prompts | Sechs knappe Aufgaben im Bericht; Volltexte im Inhaltsübergabepaket erhalten |
| Quellen | Alle 15 bestehenden Quellen plus vier klar bezeichnete Ergänzungen |

Geplante Ausgabe des **noch nicht ausgeführten** serverseitigen Vollbuilds:
11 Seiten Standard-A4 quer, zwei zusätzliche A2-Matrixseiten und ein separater
Reviewanhang mit tatsächlichen Dokumentausschnitten. Die lesbare Standardfassung wird
nicht durch A2 ersetzt. Keine neue Covergestaltung oder rechte Iconleiste.

## Neutrale Implementierung

`full_report.py` übernimmt die fachliche Anordnung mit einem extern bereitgestellten,
bereits geprüften Painter. Es erzeugt keinen Renderer und greift nicht auf Netzwerk,
Browser, Modelle oder private Dateien zu. `test_full_report.py` prüft elfteilige
Themenbindung, strikte Datenfelder, Quellenzuordnung, Rastergröße, Ablaufdelegation,
Geometriekollisionen und den Inhaltsübergabevertrag.

Die geprüften `refine_pages.py`-/`repair_assets.py`-Funktionen bleiben die Grundlage.
Die private Ausführung begrenzt Favicon-/Rastergrößen zusätzlich; 48 Pixel werden nicht
als große Wortmarke vergrößert. 600-dpi-Rasterung ersetzt keine Original-Vektordetails.

## Produktionspipeline erhalten

Die zentrale docsctl-/Quarto-/Typst-Konfiguration wird **nicht geändert oder ersetzt**.
Der bestehende ReportLab-Ownerpfad erzeugt die Reviewfassung; parallel wird der gleiche
Inhalt als SPEC-v1-`docs.yml` plus elf Markdown-Kapitel, Mermaid-Quelle und Prompt-Anhang
bereitgestellt. Das ist ein Content-Handoff, keine behauptete pixelgleiche
Quarto-Konvertierung. `docsctl check`, Quarto, Typst und natives Mermaid bleiben bis zu
wirklicher Ausführung `NOT_RUN`.

## Allseitige Prüfung und Grenzen

Im Gast: vorhandene exakte Brand-/Font-/Build-Bytes prüfen, Glyphen je Textaufruf prüfen,
tatsächlich verwendete PDF-Fonts kontrollieren und alle 14 neuen PDF-Seiten rasterisieren.
Layoutprüfung verwendet reale Schriftmetriken für einzelne Zeilen sowie Text/Text- und
Text/Bild-Kollisionen. Das ist eine Geometrieprüfung, kein automatischer Designrichter.

Coververgleich maskiert **nur die ausdrücklich geänderte Fußzeile**; er behauptet keine
Gleichheit der ganzen Seite. Beim Diagramm sind zusätzlich zwei präzise Beschriftungszonen
für den aktuellen Buildstand und Ausgabedateinamen ausgenommen. Geometrie und Bildsprache
bleiben dieselben. Elf Originalbericht/Vollbericht-Paare und drei Build03/Vollbericht-Paare
binden den Vorher/Nachher-Vergleich an tatsächliche Rasterhashes.

Die ursprünglichen 14-Seiten-Originalbytes, 300-dpi-Heromotiv, Anbieterrechte,
Produktintegration, native Mermaid-Ausführung, Produktionsbuild und finale Nutzerabnahme
bleiben separate offene Gates. Markenbilder, Fonts, Runtimepfade, Originaldateien und
Binärnachweise werden nicht in den öffentlichen Core hochgeladen.

## Tests

```bash
cd studio-v2/review
python -m unittest test_refine_pages test_repair_assets test_full_report -v
```

123 reine Tests bestanden: 85 vorhandene Reparaturverträge plus 38 neue Vollberichtverträge.
Kein lokaler PDF-, Font-, Raster- oder Browserbuild. Der Test-Painter zeichnet nur Aufrufe
auf; echte Glyphenmetriken und der allseitige Export werden ausschließlich im Gast geprüft.

Status: Build03 `SCOPED_REPAIRS_CONFIRMED`; Vollbericht `PAYLOAD_READY / SERVER_EXECUTION_NOT_RUN`.
Kein Merge, Deployment, neuer Worker oder zusätzlicher Modellaufruf.
