// Portal-Chrome: Projekt-Umschalter, Nutzer-Badge, PDF-Knopf im Header.
// Daten: window.DOKU (vom Build in assets/doku-data.html geschrieben), Nutzer: /oauth2/userinfo (oauth2-proxy).
(function () {
  const D = window.DOKU || { tools: [], portal: {} };
  const m = location.pathname.match(/\/tools\/([^\/]+)\//);
  const current = m ? D.tools.find(t => t.id === m[1]) : null;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function el(html) { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstChild; }

  function switcher() {
    const items = D.tools.map(t =>
      `<li><a class="dropdown-item doku-sw-item${current && t.id === current.id ? ' active' : ''}" href="/tools/${esc(t.id)}/start.html">
         <span class="doku-sw-mark">${esc(t.short.slice(0, 2).toUpperCase())}</span>
         <span class="doku-sw-text"><span class="doku-sw-title">${esc(t.title)}</span>
         <span class="doku-sw-meta">${esc(t.meta)}</span></span></a></li>`).join('');
    return el(`<div class="dropdown doku-switcher">
      <button class="doku-switcher-btn" type="button" data-bs-toggle="dropdown" aria-expanded="false" aria-label="Projekt wechseln">
        <span class="doku-switcher-name">${esc(current ? current.short : (matchMedia('(max-width: 575.98px)').matches ? 'Projekte' : 'Alle Projekte'))}</span>
        <i class="bi bi-chevron-expand"></i>
      </button>
      <ul class="dropdown-menu doku-switcher-menu">
        <li><h6 class="dropdown-header">Projekt wechseln</h6></li>
        ${items}
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item doku-sw-all${current ? '' : ' active'}" href="/index.html"><i class="bi bi-grid"></i> Alle Projekte</a></li>
      </ul></div>`);
  }

  function initials(name) {
    const p = String(name || '?').split(/[\s._@-]+/).filter(Boolean);
    return ((p[0] || '?')[0] + (p[1] ? p[1][0] : '')).toUpperCase();
  }

  function userBadge(u) {
    const name = u.preferredUsername || u.user || u.email || 'Angemeldet';
    const groups = (u.groups || []).map(g => `<span class="doku-chip">${esc(g)}</span>`).join(' ');
    return el(`<div class="dropdown doku-user">
      <button class="doku-user-btn" type="button" data-bs-toggle="dropdown" aria-expanded="false" aria-label="Konto">
        <span class="doku-avatar">${esc(initials(name))}</span><span class="doku-user-name">${esc(name)}</span>
        <i class="bi bi-chevron-down"></i>
      </button>
      <ul class="dropdown-menu dropdown-menu-end doku-user-menu">
        <li class="doku-user-head"><span class="doku-avatar doku-avatar-lg">${esc(initials(name))}</span>
          <span><strong>${esc(name)}</strong><span class="doku-user-mail">${esc(u.email || '')}</span></span></li>
        ${groups ? `<li class="doku-user-groups">Gruppen ${groups}</li>` : ''}
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item" href="${esc(D.portal.signout)}"><i class="bi bi-box-arrow-right"></i> Abmelden</a></li>
      </ul></div>`);
  }

  function mount() {
    const brand = document.querySelector('.navbar-brand-container');
    if (brand && D.tools.length) brand.after(switcher());
    const tools = document.querySelector('.quarto-navbar-tools') ||
      document.querySelector('.navbar-container').appendChild(el('<div class="quarto-navbar-tools"></div>'));
    tools.classList.add('doku-navtools');
    if (current) {
      tools.appendChild(el(`<button class="btn btn-sm doku-nav-export doku-export-btn" data-tool="${esc(current.id)}" type="button">
        <i class="bi bi-file-earmark-arrow-down"></i><span>PDF</span></button>`));
    }
    const side = document.querySelector('#quarto-sidebar .sidebar-menu-container');
    if (current && side) {
      side.prepend(el(`<div class="doku-side-head"><div class="doku-side-kicker">Projekt</div>
        <a class="doku-side-title" href="/tools/${esc(current.id)}/start.html">${esc(current.title)}</a>
        <div class="doku-side-meta">${esc(current.meta)}</div></div>`));
    }
    const slot = el('<div class="doku-user-slot"></div>');
    tools.appendChild(slot);
    fetch('/oauth2/userinfo', { credentials: 'same-origin' })
      .then(r => r.ok ? r.json() : null)
      .then(u => { if (u) slot.replaceWith(userBadge(u)); })
      .catch(() => { /* lokale Vorschau ohne Login-Proxy */ });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
