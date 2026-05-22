/**
 * Jorres Apps — Persistent In-App Navigation Bar
 * Served at /static/app-nav.js
 */
(function () {
  'use strict';

  var FAV_KEY   = 'jorresApps_favorites';
  var RECENT_KEY = 'jorres_recent_v1';

  // ── Related tools map (IIFE-level scope, no conflicts) ─────────────────────
  var RELATED = {
    'json-formatter':    ['json-to-yaml','diff-checker','regex-tester'],
    'markdown-editor':   ['diff-checker','word-counter','markdown-table-generator'],
    'password-generator':['hash-generator','jwt-generator','cipher-tool'],
    'color-picker':      ['color-contrast','color-palette-extractor','color-gradient-generator'],
    'csv-viewer':        ['csv-json-converter','pivot-table','chart-visualizer'],
    'gantt-chart':       ['okr-tracker','kanban-board','decision-matrix'],
    'okr-tracker':       ['gantt-chart','kanban-board','swot-analysis'],
    'kanban-board':      ['todo-list','gantt-chart','okr-tracker'],
    'invoice-generator': ['budget-tracker','expense-splitter','roi-calculator'],
    'tip-calculator':    ['loan-calculator','vat-calculator','currency-converter'],
    'hash-generator':    ['password-generator','cipher-tool','jwt-generator'],
    'api-tester':        ['jwt-generator','url-parser','diff-checker'],
    'resume-builder':    ['certificate-generator','business-letter','word-counter'],
    'bmi-calculator':    ['tdee-calculator','sleep-calculator','habit-tracker'],
    'chart-visualizer':  ['statistics-calculator','pivot-table','csv-viewer'],
    'survey-builder':    ['meeting-agenda','survey-builder','okr-tracker'],
  };

  function buildRelatedBar(currentAppId) {
    var ids = RELATED[currentAppId];
    if (!ids || ids.length === 0) return null;
    // Hide on small screens via CSS (bar has display:none at <600px)
    var relDiv = document.createElement('div');
    relDiv.id = 'app-rel-bar';
    var lbl = document.createElement('span');
    lbl.className = 'app-rel-label';
    lbl.textContent = 'Related:';
    relDiv.appendChild(lbl);
    ids.forEach(function (id) {
      var a = document.createElement('a');
      a.href = '/' + id + '/';
      a.className = 'app-nav-rel';
      a.textContent = id.replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
      a.setAttribute('aria-label', 'Related tool: ' + a.textContent);
      relDiv.appendChild(a);
    });
    return relDiv;
  }

  // ── Utility helpers ─────────────────────────────────────────────────────────
  function getAppId() {
    var parts = window.location.pathname.replace(/^\/|\/$/g, '').split('/');
    return parts[0] || '';
  }

  function getAppName() {
    // Strip " | Jorres Apps" suffix and "— Moved" variants
    return document.title
      .replace(/ \| Jorres Apps$/i, '')
      .replace(/ [—–-] ?(Moved|Redirecting).*$/i, '')
      .trim() || 'App';
  }

  function getFavorites() {
    try { return new Set(JSON.parse(localStorage.getItem(FAV_KEY)) || []); }
    catch (e) { return new Set(); }
  }

  function saveFavorites(set) {
    localStorage.setItem(FAV_KEY, JSON.stringify(Array.from(set)));
  }

  function trackRecent(id) {
    if (!id) return;
    try {
      var r = JSON.parse(localStorage.getItem(RECENT_KEY)) || [];
      r = r.filter(function (x) { return x !== id; });
      r.unshift(id);
      r = r.slice(0, 8);
      localStorage.setItem(RECENT_KEY, JSON.stringify(r));
    } catch (e) { /* ignore */ }
  }

  // ── Main build function ─────────────────────────────────────────────────────
  function build() {
    var appId   = getAppId();
    var appName = getAppName();
    var favs    = getFavorites();
    var isFav   = favs.has(appId);

    // Track this visit
    trackRecent(appId);

    // Skip-to-content link (accessibility)
    var skip = document.createElement('a');
    skip.className   = 'skip-link';
    skip.href        = '#app-main-content';
    skip.textContent = 'Skip to main content';

    // Nav bar container
    var navBar = document.createElement('div');
    navBar.id = 'app-nav-bar';
    navBar.setAttribute('role', 'navigation');
    navBar.setAttribute('aria-label', 'App navigation');

    // Back link
    var back = document.createElement('a');
    back.className = 'app-nav-back';
    back.href = '/';
    back.setAttribute('aria-label', 'Back to Jorres Apps');
    back.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M19 12H5M12 5l-7 7 7 7"/></svg> Jorres Apps';

    // Title
    var titleSpan = document.createElement('span');
    titleSpan.className = 'app-nav-title';
    titleSpan.setAttribute('aria-current', 'page');
    titleSpan.textContent = appName;

    // Favourite star
    var star = document.createElement('button');
    star.className = 'app-nav-star' + (isFav ? ' fav-active' : '');
    star.setAttribute('aria-label',   isFav ? 'Remove from favorites' : 'Add to favorites');
    star.setAttribute('aria-pressed', isFav ? 'true' : 'false');
    star.textContent = isFav ? '★' : '☆'; // ★ / ☆

    star.addEventListener('click', function () {
      var f2 = getFavorites();
      if (f2.has(appId)) {
        f2.delete(appId);
        star.textContent = '☆';
        star.classList.remove('fav-active');
        star.setAttribute('aria-pressed', 'false');
        star.setAttribute('aria-label', 'Add to favorites');
      } else {
        f2.add(appId);
        star.textContent = '★';
        star.classList.add('fav-active');
        star.setAttribute('aria-pressed', 'true');
        star.setAttribute('aria-label', 'Remove from favorites');
      }
      saveFavorites(f2);
    });

    navBar.appendChild(back);
    navBar.appendChild(titleSpan);
    navBar.appendChild(star);

    // Related tools bar (optional)
    var relBar = buildRelatedBar(appId);

    // Skip-link anchor target
    var anchor = document.createElement('a');
    anchor.id        = 'app-main-content';
    anchor.tabIndex  = -1;
    anchor.setAttribute('aria-hidden', 'true');
    anchor.style.cssText = 'position:absolute;top:0;left:0;width:0;height:0;overflow:hidden';

    // Insert into DOM: skip → navBar → [relBar] → anchor → [existing content]
    var body = document.body;
    if (body) {
      body.insertBefore(anchor, body.firstChild);
      if (relBar) { body.insertBefore(relBar, anchor); }
      body.insertBefore(navBar, relBar || anchor);
      body.insertBefore(skip, navBar);
    } else {
      document.addEventListener('DOMContentLoaded', function () {
        document.body.insertBefore(anchor, document.body.firstChild);
        if (relBar) { document.body.insertBefore(relBar, anchor); }
        document.body.insertBefore(navBar, relBar || anchor);
        document.body.insertBefore(skip, navBar);
      });
    }
  }

  // Run immediately if body exists, otherwise wait for DOM
  if (document.body) {
    build();
  } else {
    document.addEventListener('DOMContentLoaded', build);
  }

})();
