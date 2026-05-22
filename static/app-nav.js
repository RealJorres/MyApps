/**
 * Jorres Apps — Persistent In-App Navigation Bar
 * Served at /static/app-nav.js
 *
 * Injects a sticky 40px dark nav bar at the top of every sub-app with:
 *   - Back to Jorres Apps link
 *   - Current app name (read from <title>)
 *   - Favorite star toggle (synced with launcher's favorites localStorage)
 *
 * Include in every sub-app just before </body>:
 *   <script src="/static/app-nav.js"></script>
 */
(function () {
  'use strict';

  var FAV_KEY = 'jorresApps_favorites';
  var RECENT_KEY = 'jorres_recent_v1';

  // Derive app ID from URL path (/app-id/ -> 'app-id')
  function getAppId() {
    var parts = window.location.pathname.replace(/^\/|\/$/g, '').split('/');
    return parts[0] || '';
  }

  // Derive app name from <title>, stripping ' — Moved' suffixes etc.
  function getAppName() {
    return document.title.replace(/ [—–-] ?(Moved|Redirecting).*$/i, '').trim() || 'App';
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

  function build() {
    var appId = getAppId();
    var appName = getAppName();
    var favs = getFavorites();
    var isFav = favs.has(appId);

    // ── Cross-app recommendations ─────────────────────────
  // Shows 2-3 related tools below the nav bar (hidden on small screens)
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
    'survey-builder':    ['meeting-agenda','form-builder','okr-tracker'],
  };

  function buildRelatedBar(appId) {
    var ids = RELATED[appId];
    if (!ids || window.innerWidth < 600) return null;
    // Build chips using app registry from localStorage cache (best-effort)
    var chips = ids.map(function(id) {
      var a = document.createElement('a');
      a.href = '/' + id + '/';
      a.className = 'app-nav-rel';
      a.textContent = id.replace(/-/g,' ').replace(/\b\w/g,function(c){return c.toUpperCase();});
      a.setAttribute('aria-label', 'Related tool: ' + a.textContent);
      return a;
    });
    if (!chips.length) return null;
    var bar = document.createElement('div');
    bar.id = 'app-rel-bar';
    var lbl = document.createElement('span');
    lbl.className = 'app-rel-label';
    lbl.textContent = 'Related:';
    bar.appendChild(lbl);
    chips.forEach(function(c){ bar.appendChild(c); });
    return bar;
  }

  // ── Skip-to-content link (accessibility) ──────────────
    var skip = document.createElement('a');
    skip.className = 'skip-link';
    skip.href = '#app-main-content';
    skip.textContent = 'Skip to main content';

    // Track this visit
    trackRecent(appId);

    // Create bar
    var bar = document.createElement('div');
    bar.id = 'app-nav-bar';
    bar.setAttribute('role', 'navigation');
    bar.setAttribute('aria-label', 'App navigation');

    // Back link
    var back = document.createElement('a');
    back.className = 'app-nav-back';
    back.href = '/';
    back.setAttribute('aria-label', 'Back to Jorres Apps');
    back.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M19 12H5M12 5l-7 7 7 7"/></svg> Jorres Apps';

    // Title
    var title = document.createElement('span');
    title.className = 'app-nav-title';
    title.setAttribute('aria-current', 'page');
    title.textContent = appName;

    // Star button
    var star = document.createElement('button');
    star.className = 'app-nav-star' + (isFav ? ' fav-active' : '');
    star.setAttribute('aria-label', isFav ? 'Remove from favorites' : 'Add to favorites');
    star.setAttribute('aria-pressed', isFav ? 'true' : 'false');
    star.textContent = isFav ? '★' : '☆'; // ★ or ☆

    star.addEventListener('click', function () {
      var favs2 = getFavorites();
      if (favs2.has(appId)) {
        favs2.delete(appId);
        star.textContent = '☆';
        star.classList.remove('fav-active');
        star.setAttribute('aria-pressed', 'false');
        star.setAttribute('aria-label', 'Add to favorites');
      } else {
        favs2.add(appId);
        star.textContent = '★';
        star.classList.add('fav-active');
        star.setAttribute('aria-pressed', 'true');
        star.setAttribute('aria-label', 'Remove from favorites');
      }
      saveFavorites(favs2);
    });

    bar.appendChild(back);
    bar.appendChild(title);
    bar.appendChild(star);

    // ── Related tools bar ────────────────────────────────
    var relBar = buildRelatedBar(appId);

    // ── Main content anchor (skip link target) ───────────
    var anchor = document.createElement('a');
    anchor.id = 'app-main-content';
    anchor.tabIndex = -1;
    anchor.setAttribute('aria-hidden', 'true');
    anchor.style.cssText = 'position:absolute;top:0;left:0;width:0;height:0;overflow:hidden';

    // Insert: skip → nav-bar → related-bar (optional) → anchor → rest
    var body = document.body;
    if (body) {
      body.insertBefore(anchor, body.firstChild);
      if (relBar) body.insertBefore(relBar, anchor);
      body.insertBefore(bar, relBar || anchor);
      body.insertBefore(skip, bar);
    } else {
      document.addEventListener('DOMContentLoaded', function () {
        document.body.insertBefore(anchor, document.body.firstChild);
        document.body.insertBefore(bar, anchor);
        document.body.insertBefore(skip, bar);
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
