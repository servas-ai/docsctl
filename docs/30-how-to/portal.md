---
doc_schema: 1
id: howto.portal
title: Portal aufsetzen
summary: Mehrere Repositories über catalog.yml zu einem Portal mit eigenem Branding zusammenführen.
kind: how-to
status: draft
order: 30
---

# Portal aufsetzen

Ein Portal ist ein eigenes Projekt (meist ein privates Repository) mit dieser Ablage:

```text
mein-portal/
├── catalog.yml        # welche Repositories, welche Brands, Portal-Angaben
├── brands/<id>/       # eigene Brands (optional)
├── portal/assets/     # eigene Ergänzungen zur Portal-Optik (optional, überschreibt gleichnamige Dateien)
└── build/             # Ausgabe (gitignored)
```

Minimales `catalog.yml`:

```yaml
schema: 1
portal:
  title: "Firma Doku"
  navbar_title: "Doku"
  brand: neutral            # Branding der Web-Ansicht
  default_brand: neutral    # Vorauswahl im PDF-Export
  intro: Technische Dokumentation unserer Tools.
brands: [neutral]
tools:
  - id: mein-tool
    path: /pfad/zu/mein-tool/docs
    short: Mein Tool
```

Mit `portal.operator` (Name, Adresse, E-Mail, Register) erzeugt docsctl zusätzlich Impressum,
Datenschutzseite und einen Footer mit Kontakt. `portal.group_brands` ordnet Gruppen aus dem Login
einem vorausgewählten Branding im PDF-Export zu.

Unterscheiden sich lokale Vorschau und Produktion nur in Adressen, stehen die abweichenden Werte unter
`environments.<name>.portal`; `DOKU_ENV=<name>` wählt sie beim Bauen, `DOKU_BUILD` trennt die Ausgabe:

```yaml
environments:
  prod:
    portal:
      site_url: https://docs.example.com
      logout_redirect: https://login.example.com/api/oidc/end-session
```

Gebaut wird mit dem Builder-Image, das Projektverzeichnis ist `/work`, jedes Repository wird
schreibgeschützt unter `/sources/<id>` eingebunden (`docsctl mounts` erzeugt dafür eine Compose-Datei).
`build/site` ist statisch und kann hinter jeden Webserver mit Login gestellt werden, zum Beispiel
nginx hinter oauth2-proxy. Die Seiten lesen den angemeldeten Nutzer unter `/oauth2/userinfo` und
zeigen ihn im Kopf an; ohne Login-Proxy bleibt diese Stelle leer.
