-- Web: "*Tabelle …*"-Zeilen unter Tabellen als Bildunterschrift auszeichnen; <br> bleibt HTML.
function Para(el)
  if #el.content == 1 and el.content[1].t == 'Emph' then
    local s = pandoc.utils.stringify(el.content[1])
    if s:match('^Tabelle[%s%w%.]*:') then
      return pandoc.Div({ pandoc.Plain(el.content[1].content) }, pandoc.Attr('', { 'doku-caption' }))
    end
  end
end
