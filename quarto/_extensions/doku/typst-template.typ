// doku-report – zentrale "Dokumentklasse" für alle Tool-Handbücher.
// Inhalt kommt unverändert aus Markdown; alles Optische kommt aus brand.typ
// (generiert aus brands/<id>/_brand.yml + report-brand.yml). Layout-Varianten:
// brand.layout = "stripe" (Farbstreifen oben, Linien) | "framed" (Titelkopf, farbige Überschriften, Tabellenrahmen) | "neutral".

#import "brand.typ": brand

#let doku-part = state("doku-part", "title")

#let status-label = (
  draft: "Entwurf", review: "In Prüfung", reviewed: "Geprüft", released: "Freigegeben",
  deprecated: "Veraltet",
)

// Inhalt -> reiner Text (für Kopfzeile / Nummernerkennung)
#let plain(c) = {
  if c == none { "" }
  else if type(c) == str { c }
  else if c.has("text") { c.text }
  else if c.has("children") { c.children.map(plain).join("") }
  else if c.has("body") { plain(c.body) }
  else if c.func() == [ ].func() { " " }
  else { "" }
}

// Kurz-Unterschrift im Abbildungs-/Tabellenverzeichnis, lange im Text
#let in-outline = state("in-outline", false)
#let doku-cap(long, short) = context if in-outline.get() { short } else { long }

#let num-re = regex("^((?:Anhang\s+)?(?:\d+|[A-Z])(?:\.\d+)*)\s+(.+)$$")

#let split-num(c) = {
  let s = plain(c)
  let m = s.match(num-re)
  if m == none { (none, c) } else { (m.captures.at(0), m.captures.at(1)) }
}

#let wordmark(size: 12pt) = {
  if brand.wordmark.len() > 0 {
    text(font: brand.fonts.heading, weight: "bold", size: size, tracking: -0.01em)[
      #for (t, c) in brand.wordmark { text(fill: rgb(c), t) }
    ]
  } else if brand.name != "" and brand.layout != "neutral" {
    text(weight: "bold", size: size, brand.name)
  }
}

#let page-label() = context {
  let cur = counter(page).display()
  let part = doku-part.get()
  if part in ("main", "appendix") {
    let total = counter(page).final().first()
    brand.page-label.replace("{page}", cur).replace("{pages}", str(total))
  } else {
    cur
  }
}

#let current-chapter() = {
  let p = here().page()
  let h1s = query(heading.where(level: 1))
  if h1s.any(h => h.location().page() == p) { return none }
  let prev = h1s.filter(h => h.location().page() < p)
  if prev.len() == 0 { none } else { prev.last().body }
}

#let doku-header() = context {
  let part = doku-part.get()
  if part == "title" and brand.layout != "framed" { return }
  let ch = current-chapter()
  set text(size: 7.5pt, fill: brand.colors.muted, hyphenate: false)
  set par(justify: false)
  if brand.layout == "framed" {
    grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
      wordmark(size: 13pt), brand.header-right)
    v(-4pt)
    line(length: 100%, stroke: 0.5pt + rgb("#C9CDD3"))
  } else if brand.layout == "stripe" {
    grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
      if ch != none { upper(text(tracking: 0.12em, weight: "semibold", ch)) },
      wordmark(size: 10pt))
    v(-4pt)
    line(length: 100%, stroke: 0.5pt + brand.colors.rule)
  } else {
    if ch != none { emph(ch) }
    v(-5pt)
    line(length: 100%, stroke: 0.4pt + brand.colors.rule)
  }
}

#let doku-footer() = context {
  let part = doku-part.get()
  if part == "title" and brand.layout != "framed" { return }
  if part == "title" { return text(size: 7pt, fill: brand.colors.muted, brand.footer-lines.join(linebreak())) }
  set text(size: 7pt, fill: brand.colors.muted, hyphenate: false)
  set par(justify: false, leading: 0.45em)
  if brand.layout == "neutral" {
    align(center, text(size: 9pt, fill: brand.colors.fg, page-label()))
  } else {
    if brand.layout == "stripe" { line(length: 100%, stroke: 0.5pt + brand.colors.rule); v(-2pt) }
    grid(columns: (1fr, auto), align: (left + top, right + top), column-gutter: 1em,
      brand.footer-lines.join(linebreak()),
      text(size: 7.5pt, page-label()))
  }
}

#let meta-grid(meta, date) = {
  let items = (
    ("Version", meta.version),
    ("Status", status-label.at(meta.status, default: meta.status)),
    ("Stand", date),
    ("Quelle", meta.repository),
  )
  if brand.layout == "stripe" {
    grid(columns: (1fr, 1fr, 1fr, 1.6fr), column-gutter: 12pt,
      ..items.map(((k, val)) => [
        #text(size: 6.5pt, weight: "bold", tracking: 0.18em, fill: brand.colors.muted, upper(k)) \
        #v(-4pt)
        #text(size: 10pt, weight: "medium", val)
      ]))
  } else if brand.layout == "framed" {
    set text(size: 10pt)
    line(length: 100%, stroke: 0.5pt + rgb("#C9CDD3"))
    v(-2pt)
    grid(columns: (auto, 1fr, auto, 1fr), column-gutter: 8pt, row-gutter: 6pt,
      ..items.map(((k, val)) => ([*#k:*], val)).flatten())
    v(-2pt)
    line(length: 100%, stroke: 0.5pt + rgb("#C9CDD3"))
  } else {
    set text(size: 10.5pt)
    align(center, grid(columns: (auto, auto), column-gutter: 14pt, row-gutter: 7pt, align: (right, left),
      ..items.map(((k, val)) => (text(fill: brand.colors.muted, k), val)).flatten()))
  }
}

#let title-page(title, subtitle, meta, date) = {
  if brand.layout == "stripe" {
    page(header: none, footer: none, margin: (x: 2.2cm, top: 2.2cm, bottom: 1.8cm),
      background: place(top, rect(width: 100%, height: 7pt, fill: brand.colors.primary)))[
      #grid(columns: (1fr, auto), [],
        if brand.logo != "" { image(brand.logo, width: brand.logo-width) } else { wordmark(size: 22pt) })
      #v(4.2cm)
      #text(size: 8.5pt, weight: "bold", tracking: 0.22em, fill: brand.colors.primary, upper(brand.eyebrow))
      #v(2pt)
      #block(text(size: 30pt, weight: "bold", fill: brand.colors.fg, hyphenate: false, title))
      #if subtitle != none {
        v(4pt)
        block(text(size: 12.5pt, fill: brand.colors.muted, hyphenate: false, subtitle))
      }
      #v(10pt)
      #line(length: 100%, stroke: 2pt + brand.colors.primary)
      #v(12pt)
      #meta-grid(meta, date)
      #v(1fr)
      #if brand.classification != "" {
        box(stroke: 1pt + brand.colors.accent, inset: (x: 7pt, y: 4pt),
          text(size: 8pt, weight: "bold", fill: rgb("#b45309"), upper(brand.classification)))
        v(12pt)
      }
      #line(length: 100%, stroke: 0.5pt + brand.colors.rule)
      #text(size: 7pt, fill: brand.colors.muted, brand.footer-lines.join(linebreak()))
    ]
  } else if brand.layout == "framed" {
    page[
      #v(2.4cm)
      #text(size: 9pt, weight: "bold", tracking: 0.32em, fill: brand.colors.accent, upper(brand.eyebrow))
      #v(6pt)
      #block(text(size: 28pt, weight: "bold", fill: brand.colors.primary, hyphenate: false, title))
      #if subtitle != none {
        v(2pt)
        block(text(size: 15pt, fill: brand.colors.muted, hyphenate: false, subtitle))
      }
      #v(14pt)
      #meta-grid(meta, date)
      #v(1fr)
      #if brand.classification != "" {
        text(size: 9pt, fill: brand.colors.muted)[Klassifizierung: *#brand.classification*]
        v(6pt)
      }
    ]
  } else {
    page(header: none, footer: none)[
      #set align(center)
      #v(2.5cm)
      #text(size: 11pt, tracking: 0.08em, smallcaps(brand.eyebrow))
      #v(1.6cm)
      #line(length: 75%, stroke: 0.6pt)
      #v(0.5cm)
      #block(text(size: 24pt, weight: "bold", hyphenate: false, title))
      #if subtitle != none {
        v(0.3cm)
        block(width: 85%, text(size: 13pt, hyphenate: false, subtitle))
      }
      #v(0.5cm)
      #line(length: 75%, stroke: 0.6pt)
      #v(1fr)
      #meta-grid(meta, date)
      #v(2cm)
    ]
  }
}

#let info-page(title, meta, date) = {
  // Rückseite des Deckblatts: Dokumentinformation (wie Impressum einer Abschlussarbeit)
  page[
    #v(1fr)
    #set text(size: 8.5pt)
    #set par(justify: false)
    #text(size: 10pt, weight: "bold", fill: brand.colors.primary)[Dokumentinformation]
    #v(4pt)
    #set table(fill: none, stroke: none)
    #show table.cell.where(y: 0): set text(fill: brand.colors.fg, weight: "regular")
    #table(columns: (auto, 1fr), stroke: none, inset: (x: 0pt, y: 3pt), column-gutter: 12pt,
      [Titel], title,
      [Version], meta.version,
      [Status], status-label.at(meta.status, default: meta.status),
      [Stand], date,
      [Quelle], [#meta.repository #if plain(meta.commit) != "" [ \@ #meta.commit]],
      ..if brand.legal-name != "" { ([Herausgeber], brand.legal-name) } else { () },
      ..if brand.classification != "" { ([Vertraulichkeit], brand.classification) } else { () },
      [Branding], brand.name,
      [Erzeugt mit], [docsctl · Quarto · Typst (Doku-Konvention v1)],
    )
    #if brand.disclaimer != "" {
      v(8pt)
      text(fill: brand.colors.muted, brand.disclaimer)
    }
  ]
}

// ---- Gliederung: wird aus dem Markdown-Body per Raw-Typst aufgerufen
#let doku-mainmatter() = {
  pagebreak(weak: true)
  doku-part.update("toc")
  outline(title: "Inhaltsverzeichnis", depth: 3, indent: auto)
  pagebreak(weak: true)
  outline(title: "Abbildungsverzeichnis", target: figure.where(kind: image))
  v(1.2cm)
  outline(title: "Tabellenverzeichnis", target: figure.where(kind: table))
}

#let doku-start-main() = doku-part.update("main")
#let doku-appendix() = doku-part.update("appendix")

#let doku-report(
  title: none,
  subtitle: none,
  date: none,
  lang: "de",
  region: "AT",
  meta: (:),
  sectionnumbering: none,
  doc,
) = {
  let c = brand.colors
  set document(title: plain(title), author: if brand.legal-name != "" { brand.legal-name } else { () })
  set page(
    paper: "a4",
    margin: (left: 2.5cm, right: 2.3cm, top: 2.6cm, bottom: 2.4cm),
    header: doku-header(),
    footer: doku-footer(),
    header-ascent: 35%,
    footer-descent: 30%,
    numbering: "i",
    background: if brand.layout == "stripe" { place(top, rect(width: 100%, height: 3pt, fill: c.primary)) },
  )
  set text(font: brand.fonts.body, size: brand.body-size, lang: lang, region: region,
    hyphenate: true, fill: c.fg, fallback: true)
  set par(justify: true, leading: 0.62em, spacing: 1.05em)
  set heading(numbering: sectionnumbering)
  show raw: set text(font: brand.fonts.mono)
  show raw.where(block: true): it => block(
    width: 100%, fill: c.code-bg, inset: (x: 8pt, y: 7pt), radius: 2pt,
    stroke: if brand.layout == "framed" { 0.5pt + rgb("#E5E7EB") } else { none },
    { set text(size: 0.8em); set par(justify: false); it })
  // Inline-Code: Umbruchstellen nach / . _ : = - einfügen, damit lange Pfade nicht überlaufen
  show raw.where(block: false): it => text(font: brand.fonts.mono, size: 0.86em,
    it.text.replace(regex("([/._:=-])"), m => m.text + "\u{200B}"))
  show link: it => if type(it.dest) in (str, label) { text(fill: c.link, it) } else { it }
  set list(marker: (text(fill: c.accent)[•], text(fill: c.accent)[–]), indent: 0.4em)
  set enum(indent: 0.2em)
  show quote.where(block: true): it => block(
    stroke: (left: 2pt + c.accent), inset: (left: 10pt, y: 3pt), width: 100%,
    text(fill: c.muted, it.body))

  // Tabellen
  set table(inset: (x: 5pt, y: 4pt), align: left)
  show table: set par(justify: false)
  show table: set align(left)
  show table: set text(size: 0.86em, hyphenate: true)
  show table.cell.where(y: 0): set text(weight: "bold")
  set table(
    stroke: if brand.table-style == "header-fill" { 0.5pt + rgb("#D7DADF") }
      else if brand.table-style == "rules" { (x, y) => (bottom: 0.5pt + c.rule) }
      else { (x, y) => if y == 0 { (top: 1pt + c.fg) } else { none } },
    fill: if brand.table-style == "header-fill" { (x, y) => if y == 0 { c.table-head } } else { none },
  )
  show table.cell.where(y: 0): set text(fill: c.table-head-fg)
  show table.hline: it => if brand.table-style == "header-fill" { table.hline(stroke: 0pt) } else { table.hline(stroke: 0.8pt + c.fg) }
  show figure.where(kind: table): set block(breakable: true)
  show figure.caption: it => {
    set text(size: 0.85em, fill: c.muted)
    set par(justify: false)
    it
  }
  show figure: set block(spacing: 1.4em)

  // Überschriften
  show heading: set text(font: brand.fonts.heading, fill: if brand.layout == "framed" { c.primary } else { c.fg }, hyphenate: false)
  show heading: set par(justify: false)
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    let (n, rest) = split-num(it.body)
    if it.numbering != none {
      n = counter(heading).display(it.numbering)
      rest = it.body
    }
    if brand.layout == "stripe" {
      v(1.2cm)
      if n != none { text(size: 11pt, weight: "bold", tracking: 0.18em, fill: c.primary, upper(if n.starts-with("Anhang") { n } else { "Kapitel " + n })); v(-2pt) }
      block(text(size: 22pt, weight: "bold", rest))
      v(-4pt)
      line(length: 100%, stroke: 1.5pt + c.primary)
      v(0.6cm)
    } else if brand.layout == "framed" {
      v(0.8cm)
      block(text(size: 20pt, weight: "bold")[#if n != none [#text(fill: c.accent, n)#h(0.4em)]#rest])
      v(-6pt)
      line(length: 100%, stroke: 1.2pt + c.accent)
      v(0.5cm)
    } else {
      v(1.6cm)
      if n != none { text(size: 13pt, smallcaps(if n.starts-with("Anhang") { n } else { "Kapitel " + n })); v(0pt) }
      block(text(size: 22pt, weight: "bold", rest))
      v(0.8cm)
    }
  }
  show heading.where(level: 2): it => {
    v(0.9em)
    if brand.layout == "stripe" {
      block(stroke: (left: 3pt + c.accent), inset: (left: 7pt, y: 1pt), below: 0.8em,
        text(size: 13pt, weight: "bold", it))
    } else if brand.layout == "framed" {
      block(below: 0.8em, {
        text(size: 14pt, weight: "bold", it)
        v(-7pt)
        line(length: 100%, stroke: 0.7pt + c.accent)
      })
    } else {
      block(below: 0.8em, text(size: 14pt, weight: "bold", it))
    }
  }
  show heading.where(level: 3): it => block(above: 1.1em, below: 0.7em, text(size: 11.5pt, weight: "bold", it))
  show heading.where(level: 4): it => block(above: 1em, below: 0.6em, text(size: 1em, weight: "bold", style: "italic", it))

  // Verzeichnisse
  set outline(indent: auto)
  set outline.entry(fill: repeat(text(fill: c.muted)[.], gap: 0.25em))
  show outline.entry.where(level: 1): it => {
    if it.element.func() == heading {
      v(0.55em, weak: true)
      strong(it)
    } else { it }
  }
  show outline: it => {
    show heading: h => block(below: 1em, text(size: 20pt, weight: "bold", fill: if brand.layout == "framed" { c.primary } else { c.fg }, h.body))
    in-outline.update(true)
    it
    in-outline.update(false)
  }

  // Deckblatt + Dokumentinformation
  title-page(title, subtitle, meta, date)
  info-page(title, meta, date)
  doku-part.update("front")
  doc
}
