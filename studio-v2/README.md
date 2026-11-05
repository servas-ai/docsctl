# Studio v2 — lokales Authoring, bestehende Produktionspipeline

Ein **experimenteller, opt-in Dokument-Editor** für docsctl. Der öffentliche Kern bleibt neutral. Eigene Marken, Kundeninhalte, Bilder und Schriften gehören ins jeweilige Portalprojekt, nicht in dieses Repository.

V2 bezeichnet das Authoring-Format, **keine Änderung der verbindlichen Doku-Konvention v1**. `SPEC.md`, der vorhandene CLI-Aufruf und Quarto/Typst bleiben unverändert.

## Start

Python 3.10 oder neuer genügt; keine Installation und keine Cloud-Verbindung nötig:

```bash
python studio-v2/server.py --port 8765
```

Die ausgegebene Loopback-Adresse im Browser öffnen. Für eine bereits installierte lokale Ollama-Modellversion:

```bash
python studio-v2/server.py --port 8765 --model YOUR_INSTALLED_MODEL
```

Ollama muss separat auf Port 11434 laufen. Es wird **kein Modell automatisch geladen, gekauft oder installiert**. `--ollama-port` ändert nur den lokalen Port, nicht den Zielhost. Ohne Modell bleiben Vorlagen, Bearbeitung und Export nutzbar.

## Was funktioniert

- Sechs Vorlagen; 18 Seitentypen von Deckblatt, Kurzfassung und Methodik bis Literatur, Glossar und Anhang.
- Visuelle Seitenauswahl, Umordnung, Duplizieren, Löschen, Undo/Redo, Zoom und responsive Oberfläche.
- Bearbeitbare Titel/Texte, Farbwahl, Artwork-Auswahl und Blur-Regler. Die eingebauten Vergleichszahlen sind ausdrücklich synthetisch.
- Lokale Speicherung, JSON-Import/-Export, Prüfung gegen einen begrenzten Datenvertrag.
- Druckvorschau mit durchsuchbarem Text. Der Export-Button prüft zuvor alle Seiten auf Überlauf.
- Lokale KI schlägt eine kleine JSON-Änderung vor. Vorschau, ausdrückliche Übernahme und Prüfung auf zwischenzeitlich geänderte Dokumente.
- V1-Markdown-ZIP mit Manifest, Kapitelmetadaten und unveränderter, editierbarer Mermaid-Quelle.
- Evidence-Probe für öffentliches HTML/CSS: Kandidaten, Quellen-URL, Zeit und SHA-256, **keine automatische Behauptung einer offiziellen Markenfarbe**.

## Architektur

```text
Lokales Modell → begrenzter JSON-Vorschlag → menschliche Prüfung
                                             ↓
                                Studio-v2-Dokument / Puck-Adapter
                                             ↓
                              Markdown + docs.yml (SPEC v1)
                                             ↓
                            bestehender docsctl / Quarto / Typst
```

Browserdruck ist eine **Layout-Demo**, kein Ersatz für die Produktionspipeline. Fixed-page-Templates führen keinen automatischen Langtext-Umbruch aus; überfüllte Seiten werden vor dem Export gemeldet. Der native Browser-Menüpunkt „Drucken“ kann nicht zuverlässig blockiert werden — den Studio-Export-Button verwenden.

## V1-Export: bewusste Grenze

Der ZIP-Export übernimmt editierte Überschriften und Texte sowie Mermaid-Quellen. Die fest eingebauten Demo-Matrizen, Ergebnistabellen, Kennzahlen, Formelbeispiele und Quellen werden als gekennzeichnete Inhalte erhalten. **Artwork und das genaue Seitenlayout werden nicht konvertiert.** Das ist ein Content-Handoff, keine verlustfreie Layout-Konvertierung. Die Vergleichsdaten sind momentan Katalogbeispiele, keine pro Zelle editierbaren Forschungsdatensätze; dafür folgen echte strukturierte Datenblöcke. Überschriften werden für den strikten Markdown-Vertrag normalisiert. V1-Branding wird weiterhin ausschließlich durch `brands/<id>/` und die zentrale Typst-Vorlage bestimmt.

## Puck und OpenUI

`puck-bridge.mjs` ist ein getesteter, reiner Datenadapter. Er wandelt einen geprüften V2-Dokumentstand in Puck-Daten und zurück; unbekannte Komponenten und verschachtelte Zonen werden nicht stillschweigend übernommen.

`puck-adapter.tsx` ist eine optionale React-Integrationsvorlage für `@puckeditor/core`. Der Host liefert Validator, Page-Renderer und Speichern-Funktion. Sie ist **nicht die Laufzeit der eigenständig lauffähigen HTML-Demo** und wurde in dieser Umgebung nicht gegen installierte Puck/React-Pakete kompiliert. Vor Integration im Host dessen Versionen locken, typechecken und echte Drag-and-drop-Tests ausführen.

Puck Core und Puck AI/Cloud nicht gleichsetzen: Die offizielle AI-Dokumentation beschreibt ein Cloud-Angebot. Für einen vollständig lokalen Weg verwendet diese Demo einen eigenen Ollama-Adapter. OpenUI kann darüber als Chat-/Eingabeoberfläche stehen; ein nativer OpenUI-Lang-Parser ist hier **noch nicht implementiert**.

Quellen: https://puckeditor.com/docs/getting-started · https://puckeditor.com/docs/ai/overview · https://github.com/thesysdev/openui · https://docs.ollama.com/capabilities/structured-outputs

## Marke und Artwork extern einbinden

Ein **vertrauenswürdiger Portalentwickler** kann neben `index.html` eine lokale `brand-pack.js` bereitstellen. Diese Datei ist absichtlich gitignored. Sie ist ausführbarer Host-Code, kein Modell- oder Uploadformat.

```javascript
window.DOCSCTL_BRAND = {
  name: 'Example Studio',
  accent: '#52606d',
  font: 'Example Sans',
  note: 'Tokenquelle und Prüfstatus hier dokumentieren.',
  artworks: [{ title: 'Architecture', src: 'data:image/png;base64,...' }]
};
```

Keine Fonts werden mitgeliefert oder automatisch geladen. Eine gewünschte Familie wird lokal verwendet, sonst folgt ein System-Fallback. Generierte Bilder bleiben Illustrationen, nie Belege für Forschungsergebnisse oder Screenshots eines tatsächlich ausgeführten Produkts. Die Bildprompts stehen in `COVER-PROMPTS.md`.

Mermaid: Ohne vom Host lokal bereitgestellte `window.mermaid`-Runtime zeigt die Demo eine **ausdrücklich beschriftete statische SVG-Vorschau**. Eine bereitgestellte Runtime wird mit `securityLevel: 'strict'` verwendet. Der v1-Export enthält die originale `.mmd`-Quelle; der bestehende Produktionsrenderer bleibt zuständig. Keine heimliche CDN-Abhängigkeit.

## Sicherheitsgrenzen

Loopback-Bindung; strikte Host- und Origin-Prüfung; CSRF-Token; Content-Type-Prüfung; 1-MiB-Dokumentbudget; begrenzte Textfelder; 60-Seiten-Limit; nur feste statische Dateipfade; keine beliebigen URLs für Modelle; keine Redirects; keine Proxy-Credentials; keine Prompt-Logs; kein `eval`; kein unkontrolliertes HTML im Renderer. Modelldaten sind Daten, keine Ausführungsanweisungen. Der lokale Server ist eine Demo und nicht für öffentliche Exposition ausgelegt.

## Tests

```bash
cd studio-v2
python -m unittest test_core -v
node --test test-bridge.mjs
```

Die zusätzlichen Browser-/PDF-Prüfungen können mit Playwright, Chromium und PyMuPDF ausgeführt werden. Die ausgelieferten Nachweise unterscheiden explizit Offline-DOM-Tests, lokale HTTP-Vertragstests und **nicht ausgeführte Live-Modellinferenz**.

## Release-Gates — vor einem produktiven V2-Release

1. Host-integrierten Puck-Adapter kompilieren, testen und Abhängigkeiten locken.
2. Echte Tabellen/KPIs/Formeln als Schema-Daten statt Beispieldaten führen; verlustfreien Block-Export ergänzen.
3. Native Mermaid-Rendering-Abnahme, Typst-Integration, `make check` und vollständiger PDF-Produktionsbuild.
4. Live-Inferenz mit dem tatsächlich ausgewählten lokalen Modell einschließlich Fehler- und Timeoutfällen.
5. Lizenz-/Markenfreigabe für Assets und Fonts; PDF/UA bzw. PDF/A nur nach einem eigenen Compliance-Test behaupten.

Diese offenen Gates sind der Grund für den Draft-Status des V2-PRs.
