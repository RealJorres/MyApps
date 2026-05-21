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

    // Insert at top of body
    var body = document.body;
    if (body) {
      body.insertBefore(bar, body.firstChild);
    } else {
      document.addEventListener('DOMContentLoaded', function () {
        document.body.insertBefore(bar, document.body.firstChild);
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
