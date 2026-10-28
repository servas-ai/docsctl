#show: doc => doku-report(
  title: [$title$],
$if(subtitle)$
  subtitle: [$subtitle$],
$endif$
  date: "$date$",
  lang: "$if(lang)$$lang$$else$de$endif$",
  region: "$if(region)$$region$$else$AT$endif$",
  meta: (
    version: [$doku.version$],
    status: "$doku.status$",
    tool: "$doku.tool-id$",
    numbering: "$doku.numbering$",
    repository: [$doku.repository$],
    commit: [$doku.commit$],
    authors: [$doku.authors$],
  ),
$if(section-numbering)$
  sectionnumbering: "$section-numbering$",
$endif$
  doc,
)
