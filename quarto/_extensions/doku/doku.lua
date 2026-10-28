-- doku.lua – PDF-Feinschliff für die Doku-Konvention v1 (läuft vor Quarto).
--  * <br> in Tabellen -> echter Zeilenumbruch
--  * Bild/Diagramm + "*Abbildung …*"-Zeile -> Typst-figure (Abbildungsverzeichnis)
--  * Tabelle + "*Tabelle …*"-Zeile        -> Typst-figure kind:table (Tabellenverzeichnis)
--  * Codeblöcke -> natives Typst-raw (Typst-Syntaxhervorhebung, keine Skylighting-Makros)
local numbering = 'manual'

local function tstr(s)
  s = s:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\r', ''):gsub('\n', '\\n'):gsub('\t', '    ')
  return '"' .. s .. '"'
end

local function to_typst(inlines)
  local s = pandoc.write(pandoc.Pandoc({ pandoc.Plain(inlines) }), 'typst')
  return (s:gsub('%s+$', ''))
end

local function caption_of(blk, kind)
  if not blk or blk.t ~= 'Para' or #blk.content ~= 1 or blk.content[1].t ~= 'Emph' then return nil end
  local inl = blk.content[1].content
  local s = pandoc.utils.stringify(inl)
  if s:sub(1, #kind) ~= kind then return nil end
  local rest = s:sub(#kind + 1)
  if not rest:match('^%s*[%w%.]*%s*:') then return nil end
  local typ = to_typst(inl)
  -- Kurzform fürs Verzeichnis: Quellenangabe "(… Quellen: …)" am Ende weglassen
  local short = s:gsub('%s*%([^()]*Quellen?:[^()]*%)%s*$', '')
  local styp = to_typst({ pandoc.Str(short) })
  if numbering == 'auto' then
    typ = typ:gsub('^' .. kind .. '%s*:%s*', '')
    styp = styp:gsub('^' .. kind .. '%s*:%s*', '')
  end
  return '#doku-cap([' .. typ .. '], [' .. styp .. '])'
end

local function lone_image(blk)
  if blk and (blk.t == 'Para' or blk.t == 'Plain') and #blk.content == 1 and blk.content[1].t == 'Image' then
    return blk.content[1]
  end
  return nil
end

local function num()
  if numbering == 'auto' then return '"1"' else return 'none' end
end

function Meta(meta)
  if meta.doku and meta.doku.numbering then
    numbering = pandoc.utils.stringify(meta.doku.numbering)
  end
end

function RawInline(el)
  if el.format:match('html') and el.text:match('^<[bB][rR]%s*/?>$') then
    return pandoc.LineBreak()
  end
end

function CodeBlock(el)
  if not FORMAT:match('typst') then return nil end
  local lang = el.classes[1]
  local args = 'block: true'
  if lang and lang ~= '' then args = args .. ', lang: ' .. tstr(lang) end
  return pandoc.RawBlock('typst', '#raw(' .. args .. ', ' .. tstr(el.text) .. ')')
end

function Blocks(blocks)
  if not FORMAT:match('typst') then return nil end
  local out = pandoc.List()
  local i = 1
  while i <= #blocks do
    local b, nxt = blocks[i], blocks[i + 1]
    local img = lone_image(b)
    local cap
    if img then cap = caption_of(nxt, 'Abbildung') end
    if img and cap then
      local w = img.attributes.width
      local args = tstr(img.src)
      if w then args = args .. ', width: ' .. w end
      local fig = '#figure(image(' .. args .. '), kind: image, supplement: [Abbildung], numbering: ' .. num() ..
        ', caption: figure.caption(position: bottom, [' .. cap .. ']))'
      if img.attributes['doku-landscape'] then
        -- eigene Querformatseite; Kopf-/Fußzeile bleiben
        fig = '#page(flipped: true)[#v(1fr)\n' .. fig .. '\n#v(1fr)]'
      end
      out:insert(pandoc.RawBlock('typst', fig))
      i = i + 2
    elseif b.t == 'Table' and caption_of(nxt, 'Tabelle') then
      cap = caption_of(nxt, 'Tabelle')
      out:insert(pandoc.RawBlock('typst',
        '#figure(kind: table, supplement: [Tabelle], numbering: ' .. num() ..
        ', caption: figure.caption(position: bottom, [' .. cap .. ']))['))
      out:insert(b)
      out:insert(pandoc.RawBlock('typst', ']'))
      i = i + 2
    elseif img then
      local w = img.attributes.width
      local args = tstr(img.src)
      if w then args = args .. ', width: ' .. w end
      out:insert(pandoc.RawBlock('typst', '#align(center, image(' .. args .. '))'))
      i = i + 1
    else
      out:insert(b)
      i = i + 1
    end
  end
  return out
end

return {
  { Meta = Meta },
  { RawInline = RawInline, CodeBlock = CodeBlock },
  { Blocks = Blocks },
}
