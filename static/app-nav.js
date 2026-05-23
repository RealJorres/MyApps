/**
 * Jorres Apps — Persistent In-App Navigation Bar
 * Served at /static/app-nav.js
 */
(function () {
  'use strict';

  var FAV_KEY   = 'jorresApps_favorites';
  var RECENT_KEY = 'jorres_recent_v1';

  // ── Related tools map — full 130-app graph ─────────────────────────────────
  var RELATED = {
    // Developer Tools
    'json-formatter':          ['json-to-yaml','diff-checker','regex-tester'],
    'json-to-yaml':            ['json-formatter','diff-checker','code-beautifier'],
    'diff-checker':            ['json-formatter','code-beautifier','regex-tester'],
    'code-beautifier':         ['css-formatter','sql-formatter','diff-checker'],
    'css-formatter':           ['code-beautifier','html-previewer','json-formatter'],
    'sql-formatter':           ['code-beautifier','diff-checker','json-formatter'],
    'html-previewer':          ['css-formatter','code-beautifier','markdown-editor'],
    'markdown-editor':         ['diff-checker','word-counter','markdown-table-generator'],
    'markdown-table-generator':['markdown-editor','csv-json-converter','json-formatter'],
    'regex-tester':            ['diff-checker','json-formatter','code-beautifier'],
    'base64-tool':             ['hash-generator','url-parser','cipher-tool'],
    'base-converter':          ['ascii-table','hash-generator','base64-tool'],
    'ascii-table':             ['base-converter','html-entity-encoder','hash-generator'],
    'html-entity-encoder':     ['markdown-editor','code-beautifier','regex-tester'],
    'url-parser':              ['api-tester','diff-checker','base64-tool'],
    'uuid-generator':          ['hash-generator','random-data-generator','password-generator'],
    'random-data-generator':   ['uuid-generator','json-formatter','csv-json-converter'],
    'timestamp-converter':     ['world-clock','meeting-time-planner','cron-builder'],
    'cron-builder':            ['timestamp-converter','meeting-timer','gitignore-generator'],
    'gitignore-generator':     ['cron-builder','chmod-calculator','code-beautifier'],
    'chmod-calculator':        ['cidr-calculator','ssl-checker','hash-generator'],
    'cidr-calculator':         ['dns-lookup','ip-info','whois-lookup'],
    'ip-info':                 ['dns-lookup','whois-lookup','cidr-calculator'],
    'dns-lookup':              ['ip-info','whois-lookup','ssl-checker'],
    'whois-lookup':            ['dns-lookup','ip-info','ssl-checker'],
    'ssl-checker':             ['dns-lookup','http-status-codes','ip-info'],
    'http-status-codes':       ['api-tester','ssl-checker','url-parser'],
    'api-tester':              ['jwt-generator','url-parser','diff-checker'],
    'jwt-generator':           ['hash-generator','api-tester','password-generator'],
    'ascii-art-generator':     ['text-case-converter','word-counter','markdown-editor'],
    // Documents & Writing
    'word-counter':            ['markdown-editor','text-case-converter','readability-analyzer'],
    'text-case-converter':     ['word-counter','regex-tester','lorem-ipsum'],
    'lorem-ipsum':             ['markdown-editor','word-counter','text-case-converter'],
    'readability-analyzer':    ['word-counter','text-case-converter','markdown-editor'],
    'notepad':                 ['todo-list','markdown-editor','sticky-notes'],
    'sticky-notes':            ['notepad','todo-list','journal'],
    'journal':                 ['sticky-notes','notepad','habit-tracker'],
    'reading-list':            ['todo-list','flashcards','notepad'],
    'resume-builder':          ['certificate-generator','business-letter','word-counter'],
    'business-letter':         ['resume-builder','email-signature','word-counter'],
    'certificate-generator':   ['resume-builder','business-letter','image-tools'],
    'email-signature':         ['business-letter','resume-builder','word-counter'],
    'speech-to-text':          ['text-to-speech','word-counter','notepad'],
    'text-to-speech':          ['speech-to-text','word-counter','markdown-editor'],
    'ocr-tool':                ['speech-to-text','image-filters','image-tools'],
    'pdf-merger':              ['pdf-splitter','pdf-to-image','pdf-compressor'],
    'pdf-splitter':            ['pdf-merger','pdf-to-image','pdf-compressor'],
    'pdf-compressor':          ['pdf-merger','pdf-splitter','image-tools'],
    'pdf-to-image':            ['image-tools','image-filters','pdf-merger'],
    'survey-builder':          ['meeting-agenda','decision-matrix','okr-tracker'],
    // Design & Visuals
    'color-picker':            ['color-contrast','color-palette-extractor','color-gradient-generator'],
    'color-contrast':          ['color-picker','color-palette-extractor','color-gradient-generator'],
    'color-palette-extractor': ['color-picker','color-contrast','image-filters'],
    'color-gradient-generator':['color-picker','color-contrast','css-formatter'],
    'image-filters':           ['image-tools','image-cropper','color-palette-extractor'],
    'image-tools':             ['image-filters','image-cropper','watermark-tool'],
    'image-cropper':           ['image-tools','image-filters','watermark-tool'],
    'image-comparison':        ['image-filters','image-tools','image-cropper'],
    'watermark-tool':          ['image-tools','image-filters','pdf-merger'],
    'exif-viewer':             ['image-tools','image-filters','ocr-tool'],
    'favicon-generator':       ['image-tools','svg-to-png','color-picker'],
    'svg-to-png':              ['image-tools','image-filters','favicon-generator'],
    'paint':                   ['pixel-art-maker','image-tools','color-picker'],
    'pixel-art-maker':         ['paint','color-picker','favicon-generator'],
    'meme-generator':          ['image-tools','image-filters','watermark-tool'],
    'barcode-generator':       ['qr-generator','image-tools','url-parser'],
    'qr-generator':            ['barcode-generator','url-parser','image-tools'],
    // Data & Analysis
    'csv-viewer':              ['csv-json-converter','pivot-table','chart-visualizer'],
    'csv-json-converter':      ['json-formatter','csv-viewer','diff-checker'],
    'chart-visualizer':        ['statistics-calculator','pivot-table','csv-viewer'],
    'pivot-table':             ['csv-viewer','chart-visualizer','statistics-calculator'],
    'statistics-calculator':   ['chart-visualizer','pivot-table','prime-factorizer'],
    // Finance & Business
    'tip-calculator':          ['loan-calculator','vat-calculator','currency-converter'],
    'loan-calculator':         ['compound-interest','tip-calculator','salary-calculator'],
    'compound-interest':       ['loan-calculator','roi-calculator','inflation-calculator'],
    'vat-calculator':          ['tip-calculator','salary-calculator','inflation-calculator'],
    'currency-converter':      ['vat-calculator','tip-calculator','inflation-calculator'],
    'roi-calculator':          ['compound-interest','break-even-calculator','invoice-generator'],
    'invoice-generator':       ['budget-tracker','expense-splitter','roi-calculator'],
    'budget-tracker':          ['expense-splitter','invoice-generator','kanban-board'],
    'expense-splitter':        ['budget-tracker','tip-calculator','invoice-generator'],
    'salary-calculator':       ['vat-calculator','loan-calculator','roi-calculator'],
    'break-even-calculator':   ['roi-calculator','compound-interest','budget-tracker'],
    'depreciation-calculator': ['compound-interest','roi-calculator','break-even-calculator'],
    'inflation-calculator':    ['currency-converter','compound-interest','salary-calculator'],
    // Productivity & Planning
    'todo-list':               ['kanban-board','habit-tracker','notepad'],
    'kanban-board':            ['todo-list','gantt-chart','okr-tracker'],
    'gantt-chart':             ['okr-tracker','kanban-board','decision-matrix'],
    'okr-tracker':             ['gantt-chart','kanban-board','swot-analysis'],
    'pomodoro-timer':          ['meeting-timer','habit-tracker','todo-list'],
    'meeting-timer':           ['pomodoro-timer','meeting-agenda','meeting-time-planner'],
    'meeting-agenda':          ['survey-builder','meeting-timer','meeting-time-planner'],
    'meeting-time-planner':    ['world-clock','meeting-agenda','meeting-timer'],
    'world-clock':             ['meeting-time-planner','timestamp-converter','meeting-agenda'],
    'habit-tracker':           ['todo-list','water-tracker','calorie-tracker'],
    'water-tracker':           ['habit-tracker','calorie-tracker','tdee-calculator'],
    'calorie-tracker':         ['water-tracker','tdee-calculator','habit-tracker'],
    'swot-analysis':           ['decision-matrix','okr-tracker','gantt-chart'],
    'decision-matrix':         ['swot-analysis','okr-tracker','survey-builder'],
    'flashcards':              ['reading-list','todo-list','notepad'],
    'mind-map':                ['okr-tracker','gantt-chart','decision-matrix'],
    'org-chart':               ['kanban-board','decision-matrix','survey-builder'],
    // Health & Wellness
    'bmi-calculator':          ['tdee-calculator','sleep-calculator','habit-tracker'],
    'tdee-calculator':         ['bmi-calculator','sleep-calculator','calorie-tracker'],
    'sleep-calculator':        ['bmi-calculator','habit-tracker','water-tracker'],
    'age-calculator':          ['bmi-calculator','sleep-calculator','habit-tracker'],
    // Science & Learning
    'periodic-table':          ['unit-converter','graph-plotter','prime-factorizer'],
    'unit-converter':          ['periodic-table','graph-plotter','tip-calculator'],
    'graph-plotter':           ['statistics-calculator','unit-converter','prime-factorizer'],
    'prime-factorizer':        ['hash-generator','statistics-calculator','unit-converter'],
    // Security & Network
    'password-generator':      ['hash-generator','jwt-generator','cipher-tool'],
    'hash-generator':          ['password-generator','cipher-tool','jwt-generator'],
    'cipher-tool':             ['hash-generator','password-generator','base64-tool'],
    // Games (grouped by style)
    'chess':                   ['tic-tac-toe','connect-four','battleship'],
    'tic-tac-toe':             ['chess','connect-four','battleship'],
    'connect-four':            ['chess','tic-tac-toe','battleship'],
    'battleship':              ['connect-four','chess','number-guessing'],
    'sudoku':                  ['minesweeper','number-guessing','hangman'],
    'minesweeper':             ['sudoku','number-guessing','wordle'],
    'wordle':                  ['hangman','typing-speed-test','number-guessing'],
    'hangman':                 ['wordle','typing-speed-test','number-guessing'],
    'number-guessing':         ['hangman','wordle','dice-roller'],
    'typing-speed-test':       ['hangman','wordle','notepad'],
    'memory-card-game':        ['simon-says','game-2048','dice-roller'],
    'simon-says':              ['memory-card-game','game-2048','dice-roller'],
    'game-2048':               ['tetris','simon-says','memory-card-game'],
    'tetris':                  ['game-2048','snake-game','flappy-bird'],
    'snake-game':              ['tetris','flappy-bird','game-2048'],
    'flappy-bird':             ['snake-game','tetris','dice-roller'],
    'dice-roller':             ['number-guessing','simon-says','memory-card-game'],
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
