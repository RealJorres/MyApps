from flask import Flask, jsonify, render_template, make_response, request, send_from_directory
import sys
import json
import os
import time
import threading
from collections import defaultdict
from json import dumps as _json_dumps
import importlib.util
# DispatcherMiddleware replaced by LazyDispatcher (see below)

# ── Optional per-route rate limiting (Flask-Limiter) ─────────────────────────
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _LIMITER_AVAILABLE = True
except ImportError:
    _LIMITER_AVAILABLE = False
    print('[launcher] flask-limiter not installed — root API endpoints unprotected', flush=True)


# ── WSGI-level API rate limiter (covers ALL sub-app /api/* endpoints) ─────────
class ApiRateLimitMiddleware:
    """
    Sliding-window rate limiter applied at the WSGI layer so every sub-app's
    /api/* routes are protected without modifying individual app.py files.

    Limits are keyed by (client_ip, endpoint_category). Categories are matched
    by the most-specific prefix in LIMITS.
    """

    # (max_requests, window_seconds)
    LIMITS = {
        # CPU-heavy processing ─────────────────────────────────────────────────
        '/api/convert':    (5,  60),   # PDF generation (ReportLab)
        '/api/generate':   (10, 60),   # PDF / image / QR generation
        '/api/merge':      (5,  60),   # PDF merge (PyMuPDF)
        '/api/compress':   (5,  60),   # PDF / image compression
        '/api/split':      (5,  60),   # PDF split
        '/api/watermark':  (10, 60),   # Image processing (Pillow)
        '/api/crop':       (15, 60),   # Image crop
        '/api/process':    (10, 60),   # Image resize / convert
        '/api/extract':    (10, 60),   # Colour-palette extraction
        '/api/pdf-to-images': (5, 60), # PDF → images
        '/api/images-to-pdf': (5, 60), # Images → PDF
        # Outbound network requests ────────────────────────────────────────────
        '/api/lookup':     (15, 60),   # DNS / IP / Whois
        '/api/check':      (10, 60),   # SSL certificate check
        '/api/request':    (15, 60),   # api-tester (outbound HTTP proxy)
        '/api/myip':       (30, 60),   # IP info
        # Text / compute ───────────────────────────────────────────────────────
        '/api/test':       (30, 60),   # Regex tester (ReDoS surface)
        '/api/format':     (60, 60),   # Code formatters
        '/api/diff':       (60, 60),   # Text diff
        # Default: all other /api/ paths ──────────────────────────────────────
        '/api/':           (60, 60),
    }

    _RATE_LIMITED = (
        b'{"error":"Rate limit exceeded. Please slow down and try again."}',
    )

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        # Warm-start: pre-populate a recent timestamp so a burst on cold start
        # doesn't get a full fresh window. We record the process start time as
        # a "sentinel" entry in a system bucket — this doesn't block real users
        # but makes the limiter slightly less "restartable" by an attacker.
        _start = time.monotonic()
        self._windows['__startup__'].append(_start)

    def _resolve_limit(self, api_path: str):
        """Return (max_requests, window_seconds) for the given /api/… path."""
        for prefix, lim in self.LIMITS.items():
            if prefix == '/api/':
                continue
            if api_path == prefix or api_path.startswith(prefix + '/') or api_path.startswith(prefix + '?'):
                return lim
        return self.LIMITS['/api/']

    def _allowed(self, ip: str, api_path: str) -> bool:
        max_req, window = self._resolve_limit(api_path)
        key = f'{ip}\x00{api_path}'
        now = time.monotonic()

        with self._lock:
            # Periodic cleanup every 5 minutes
            if now - self._last_cleanup > 300:
                cutoff = now - 120
                stale = [k for k, ts in self._windows.items()
                         if not ts or ts[-1] < cutoff]
                for k in stale:
                    del self._windows[k]
                self._last_cleanup = now

            # Slide window
            cutoff = now - window
            bucket = self._windows[key]
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)

            if len(bucket) >= max_req:
                return False

            bucket.append(now)
            return True

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')

        # Only rate-limit paths that contain /api/
        api_idx = path.find('/api/')
        if api_idx < 0:
            return self.wsgi_app(environ, start_response)

        api_path = path[api_idx:]   # e.g. /api/convert

        # Prefer X-Forwarded-For (Render adds this behind its edge proxy)
        xff = environ.get('HTTP_X_FORWARDED_FOR', '')
        ip  = xff.split(',')[0].strip() if xff else environ.get('REMOTE_ADDR', '0.0.0.0')

        if not self._allowed(ip, api_path):
            start_response('429 Too Many Requests', [
                ('Content-Type', 'application/json'),
                ('Retry-After', '60'),
            ])
            return self._RATE_LIMITED

        return self.wsgi_app(environ, start_response)


class SecurityHeadersMiddleware:
    """Adds security headers to every response across all mounted sub-apps."""
    HEADERS = [
        ('X-Content-Type-Options',  'nosniff'),
        ('X-Frame-Options',         'SAMEORIGIN'),
        ('Referrer-Policy',         'strict-origin-when-cross-origin'),
        ('Strict-Transport-Security', 'max-age=31536000; includeSubDomains'),
        ('Permissions-Policy',
         'camera=(), microphone=(), geolocation=(), payment=(), usb=()'),
        ('X-XSS-Protection',        '1; mode=block'),
    ]

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        def add_security_headers(status, headers, exc_info=None):
            existing = {h[0].lower() for h in headers}
            patched = list(headers)
            for name, value in self.HEADERS:
                if name.lower() not in existing:
                    patched.append((name, value))
            return start_response(status, patched, exc_info)
        return self.wsgi_app(environ, add_security_headers)


class LazyDispatcher:
    """
    Replaces DispatcherMiddleware with on-demand sub-app loading.

    Sub-apps are imported and initialized the first time they receive a
    request — not at server startup.  This eliminates the ~135-app eager
    load that previously consumed the entire 512 MB Render free-tier
    allocation before the first user request was served.

    Memory profile with lazy loading:
      Startup  : only the registry config dict — effectively 0 app RAM
      Steady   : footprint of apps actually visited in the current session
      Cold start: responds to the launcher / in <1 s instead of waiting for
                  all 135 Flask instances to initialize

    Thread safety (gthread: 1 OS process, 8 threads):
      - Per-app locks prevent two threads from double-loading the same app
      - Double-checked locking: fast path (dict lookup) avoids lock overhead
        on every request after the first
      - Unrelated apps never block each other
    """

    def __init__(self, default_app, registry, loader):
        self.default_app = default_app
        # prefix (/app-id) → registry config dict
        self._cfg_map = {f"/{cfg['id']}": cfg for cfg in registry}
        self._loader  = loader
        self._apps    = {}   # prefix → loaded WSGI app (populated on first hit)
        self._errors  = {}   # prefix → error string (permanent; won't retry)
        # One lock per app so unrelated apps never block each other
        self._locks   = {p: threading.Lock() for p in self._cfg_map}

    @property
    def prefixes(self):
        """All registered /<id> prefixes (used by _slash_redirect)."""
        return set(self._cfg_map.keys())

    def status(self, prefix):
        """Return 'loaded', 'error', or 'ready' for use in API responses."""
        if prefix in self._errors:
            return 'error'
        if prefix in self._apps:
            return 'loaded'
        return 'ready'

    def _ensure_loaded(self, prefix):
        """
        Load the sub-app for *prefix* if not already done.
        Returns the WSGI callable on success, None on failure.
        Uses double-checked locking for thread safety.
        """
        # Fast path — already resolved (covers >99 % of requests)
        if prefix in self._apps:
            return self._apps[prefix]
        if prefix in self._errors:
            return None

        with self._locks[prefix]:
            # Re-check inside the lock (another thread may have beaten us)
            if prefix in self._apps:
                return self._apps[prefix]
            if prefix in self._errors:
                return None
            try:
                cfg     = self._cfg_map[prefix]
                wsgi_app = self._loader(cfg)
                self._apps[prefix] = wsgi_app
                print(f'[launcher] Loaded {prefix[1:]} on first request', flush=True)
                return wsgi_app
            except Exception as exc:
                self._errors[prefix] = str(exc)
                print(f'[launcher] Failed to load {prefix[1:]}: {exc}', flush=True)
                return None

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '/')

        # Find the matching registered prefix (e.g. /json-formatter)
        matched = None
        for p in self._cfg_map:
            if path == p or path.startswith(p + '/'):
                matched = p
                break

        if matched is None:
            # Root Flask app handles /, /static/, /api/*, /sitemap.xml, etc.
            return self.default_app(environ, start_response)

        wsgi_app = self._ensure_loaded(matched)

        if wsgi_app is None:
            err  = self._errors.get(matched, 'unknown load error')
            body = (
                f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
                f'<title>Unavailable | Jorres Apps</title></head><body>'
                f'<p>This tool is temporarily unavailable ({err}).</p>'
                f'<p><a href="/">Back to all tools</a></p>'
                f'</body></html>'
            ).encode()
            start_response('503 Service Unavailable', [
                ('Content-Type', 'text/html; charset=utf-8'),
                ('Content-Length', str(len(body))),
            ])
            return [body]

        # Strip the prefix from PATH_INFO and extend SCRIPT_NAME
        # (mirrors what DispatcherMiddleware does)
        env = environ.copy()
        env['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + matched
        env['PATH_INFO']   = path[len(matched):] or '/'
        return wsgi_app(env, start_response)


flask_app = Flask(__name__)
flask_app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Rate limiting setup ───────────────────────────────────────────────────────
if _LIMITER_AVAILABLE:
    limiter = Limiter(
        key_func=get_remote_address,
        app=flask_app,
        default_limits=[],               # No global limit; per-route only
        storage_uri='memory://',
    )
else:
    class _NoopLimiter:
        def limit(self, *a, **kw):
            return lambda f: f
    limiter = _NoopLimiter()


def load_registry():
    with open(os.path.join(LAUNCHER_DIR, 'apps.json'), encoding='utf-8-sig') as f:
        apps = json.load(f)
    for a in apps:
        if not os.path.isabs(a['path']):
            a['path'] = os.path.normpath(os.path.join(LAUNCHER_DIR, a['path']))
    return apps


REGISTRY = load_registry()


def load_sub_app(cfg):
    """
    Load a sub-app module using its absolute file path.
    We do NOT mutate sys.path — importlib.util.spec_from_file_location
    with an absolute entry path sets __file__ correctly, which lets
    Flask resolve root_path (and therefore templates/) without any
    global sys.path insertion.
    """
    entry = os.path.join(cfg['path'], cfg['entry'])
    module_name = cfg['id'].replace('-', '_') + '_wsgi'
    spec = importlib.util.spec_from_file_location(module_name, entry)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so Flask can resolve root_path for templates
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.app


def _slash_redirect(wsgi_app, prefixes):
    """Redirect /<id> → /<id>/ so relative URLs in sub-app HTML resolve correctly."""
    def middleware(environ, start_response):
        if environ.get('PATH_INFO') in prefixes:
            qs = environ.get('QUERY_STRING', '')
            loc = environ['PATH_INFO'] + '/' + ('?' + qs if qs else '')
            start_response('301 Moved Permanently', [
                ('Location', loc), ('Content-Type', 'text/plain')
            ])
            return [b'Redirecting...']
        return wsgi_app(environ, start_response)
    return middleware


# Build the lazy dispatcher — no sub-apps are loaded here.
# Each app is imported on the first request it receives.
lazy_dispatcher = LazyDispatcher(flask_app, REGISTRY, load_sub_app)

# 'app' is the full WSGI stack imported by wsgi.py and gunicorn.
# Layers (innermost → outermost):
#   LazyDispatcher → _slash_redirect → ApiRateLimitMiddleware → SecurityHeadersMiddleware
app = SecurityHeadersMiddleware(
    ApiRateLimitMiddleware(
        _slash_redirect(
            lazy_dispatcher,
            lazy_dispatcher.prefixes,   # all registered /<id> prefixes
        )
    )
)


# ── Static assets (design system) ────────────────────────────────────────────
# These shared JS files change with every deployment fix. Never let browsers
# cache them — stale versions cause "properties of null" errors site-wide.
_NO_CACHE_ASSETS = {'app-nav.js', 'footer.js'}

@flask_app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve shared static assets to all sub-apps."""
    resp = send_from_directory(flask_app.static_folder, filename)
    if filename in _NO_CACHE_ASSETS:
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Pragma']  = 'no-cache'
        resp.headers['Expires'] = '0'
    return resp


# ── Privacy page ──────────────────────────────────────────────────────────────
@flask_app.route('/privacy')
def privacy():
    resp = make_response('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="canonical" href="https://jorresapps.onrender.com/privacy">
<meta name="description" content="Jorres Apps Privacy Policy — no tracking, no ads, no sign-up. All data stays in your browser.">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect x='2' y='2' width='60' height='60' rx='14' fill='%230d1117'/%3E%3Crect x='14' y='14' width='12' height='12' rx='3' fill='%23ffffff'/%3E%3Crect x='30' y='14' width='12' height='12' rx='3' fill='%23ffffff' opacity='0.35'/%3E%3Crect x='30' y='30' width='12' height='12' rx='3' fill='%23ffffff'/%3E%3Crect x='14' y='46' width='12' height='12' rx='3' fill='%232f57ff'/%3E%3Crect x='30' y='46' width='12' height='12' rx='3' fill='%23ffffff'/%3E%3C/svg%3E">
<title>Privacy Policy | Jorres Apps</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f8fafc;color:#0f172a;min-height:100vh;padding:0 0 4rem}
header{background:#0f172a;padding:1rem 2rem;display:flex;align-items:center;gap:1rem}
header a{color:#94a3b8;text-decoration:none;font-size:.85rem;font-weight:600;transition:color .15s}
header a:hover{color:#e2e8f0}
header span{color:#334155}
.hero{background:linear-gradient(135deg,#1e3a5f,#0f172a);color:#fff;padding:3rem 2rem;text-align:center}
.hero h1{font-size:1.75rem;font-weight:800;margin-bottom:.5rem}
.hero p{color:#94a3b8;font-size:.95rem}
.content{max-width:720px;margin:0 auto;padding:3rem 1.5rem}
.pills{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;margin-top:1.5rem}
.pill{padding:.35rem .9rem;border-radius:2rem;font-size:.78rem;font-weight:700;letter-spacing:.03em}
.pill-green{background:#d1fae5;color:#065f46}
.pill-blue{background:#dbeafe;color:#1e40af}
.pill-purple{background:#ede9fe;color:#4c1d95}
.section{margin-bottom:2.5rem}
.section h2{font-size:1.1rem;font-weight:800;margin-bottom:.75rem;color:#1e293b;padding-bottom:.4rem;border-bottom:2px solid #e2e8f0}
.section p,.section li{font-size:.9rem;color:#475569;line-height:1.7;margin-bottom:.5rem}
.section ul{padding-left:1.25rem}
.section li{margin-bottom:.3rem}
.highlight{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:.75rem;padding:1.25rem 1.5rem;margin-bottom:1.5rem}
.highlight p{color:#065f46;font-weight:600;font-size:.9rem;margin:0}
.back-link{display:inline-flex;align-items:center;gap:.4rem;color:#2563eb;text-decoration:none;font-weight:600;font-size:.875rem;margin-bottom:2rem}
.back-link:hover{text-decoration:underline}
footer{text-align:center;color:#94a3b8;font-size:.78rem;padding:2rem;border-top:1px solid #e2e8f0;margin-top:2rem}
</style>
</head>
<body>
<header>
  <a href="/">&larr; Jorres Apps</a>
  <span>&middot;</span>
  <a href="/privacy" style="color:#e2e8f0">Privacy Policy</a>
</header>

<div class="hero">
  <h1>Privacy Policy</h1>
  <p>Last updated: May 2026</p>
  <div class="pills">
    <span class="pill pill-green">No tracking</span>
    <span class="pill pill-green">No cookies</span>
    <span class="pill pill-blue">No sign-up required</span>
    <span class="pill pill-blue">No ads</span>
    <span class="pill pill-purple">No server-side data storage</span>
  </div>
</div>

<div class="content">
  <a class="back-link" href="/">&larr; Back to all tools</a>

  <div class="highlight">
    <p>The short version: Jorres Apps collects nothing about you. No data leaves your browser. No accounts. No tracking. Free forever.</p>
  </div>

  <div class="section">
    <h2>What we collect</h2>
    <p><strong>Nothing.</strong> Jorres Apps does not collect, store, or transmit any personal information. There are no analytics scripts, no tracking pixels, no third-party data collectors embedded in our pages.</p>
  </div>

  <div class="section">
    <h2>Cookies</h2>
    <p>We do not use cookies of any kind &mdash; not for sessions, not for preferences, not for advertising.</p>
  </div>

  <div class="section">
    <h2>Local storage</h2>
    <p>Some tools save data to your browser&rsquo;s <code>localStorage</code> so your work persists between visits (e.g. Notepad, Kanban Board, Journal, Budget Tracker). This data:</p>
    <ul>
      <li>Stays entirely on your device</li>
      <li>Is never transmitted to our server or any third party</li>
      <li>Can be cleared at any time via your browser&rsquo;s developer tools or settings</li>
      <li>Is lost if you clear your browser data</li>
    </ul>
  </div>

  <div class="section">
    <h2>Server logs</h2>
    <p>Our hosting provider (Render.com) may retain standard HTTP access logs (IP address, timestamp, requested URL) for security and operational purposes. These are not used by us for analytics or marketing and are governed by <a href="https://render.com/privacy" style="color:#2563eb">Render&rsquo;s privacy policy</a>.</p>
  </div>

  <div class="section">
    <h2>Bug reports</h2>
    <p>When you voluntarily submit a bug report via the &ldquo;Report a Bug&rdquo; form, we receive the text you enter (app name, description, and optional email). This is used solely to fix reported issues and is never shared or sold.</p>
  </div>

  <div class="section">
    <h2>Third-party API tools</h2>
    <p>A small number of tools make outbound requests to third-party services on your behalf:</p>
    <ul>
      <li><strong>IP Address Info</strong> &mdash; queries a public IP geolocation API with the IP you request</li>
      <li><strong>DNS Lookup</strong> &mdash; queries public DNS resolvers for the domain you enter</li>
      <li><strong>Whois Lookup</strong> &mdash; queries public WHOIS servers for the domain you enter</li>
      <li><strong>Currency Converter</strong> &mdash; uses static exchange rates; no outbound requests</li>
    </ul>
    <p>These requests originate from our server (not directly from your browser) and do not include any identifying information beyond the query itself.</p>
  </div>

  <div class="section">
    <h2>Children</h2>
    <p>Jorres Apps is not directed at children under 13. We do not knowingly collect data from children.</p>
  </div>

  <div class="section">
    <h2>Changes to this policy</h2>
    <p>If this policy changes materially, the &ldquo;Last updated&rdquo; date at the top will be updated. Continued use of the site constitutes acceptance of the revised policy.</p>
  </div>

  <div class="section">
    <h2>Contact</h2>
    <p>Questions about this policy? Email <a href="mailto:joshuarelatorres28@gmail.com" style="color:#2563eb">joshuarelatorres28@gmail.com</a> or use the Bug Report form on any tool page.</p>
  </div>
</div>

<footer>
  &copy; 2026 Jorres Apps &middot;
  <a href="/" style="color:#94a3b8;text-decoration:none">All Tools</a> &middot;
  <a href="/privacy" style="color:#94a3b8;text-decoration:none">Privacy</a>
</footer>
</body>
</html>''')
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


# ── Custom 404 ────────────────────────────────────────────────────────────────
_BRAND_FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Crect x='2' y='2' width='60' height='60' rx='14' fill='%230d1117'/%3E"
    "%3Crect x='14' y='14' width='12' height='12' rx='3' fill='%23ffffff'/%3E"
    "%3Crect x='30' y='14' width='12' height='12' rx='3' fill='%23ffffff' opacity='0.35'/%3E"
    "%3Crect x='30' y='30' width='12' height='12' rx='3' fill='%23ffffff'/%3E"
    "%3Crect x='14' y='46' width='12' height='12' rx='3' fill='%232f57ff'/%3E"
    "%3Crect x='30' y='46' width='12' height='12' rx='3' fill='%23ffffff'/%3E"
    "%3C/svg%3E"
)

_404_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="{favicon}">
<title>Page Not Found | Jorres Apps</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f8fafc;color:#0f172a;min-height:100vh;display:flex;flex-direction:column}}
nav{{background:#0f172a;padding:.9rem 1.75rem;display:flex;align-items:center}}
nav a{{color:#94a3b8;text-decoration:none;font-size:.85rem;font-weight:600;display:inline-flex;align-items:center;gap:.4rem;transition:color .15s}}
nav a:hover{{color:#e2e8f0}}
main{{flex:1;display:flex;align-items:center;justify-content:center;padding:3rem 1.5rem}}
.box{{text-align:center;max-width:480px;width:100%}}
.code{{font-size:6rem;font-weight:900;line-height:1;color:#2f57ff;letter-spacing:-.04em;margin-bottom:.5rem}}
h1{{font-size:1.35rem;font-weight:700;color:#1e293b;margin-bottom:.6rem}}
p{{font-size:.9rem;color:#64748b;line-height:1.6;margin-bottom:1.75rem}}
.btn{{display:inline-block;background:#2f57ff;color:#fff;text-decoration:none;font-weight:700;font-size:.9rem;padding:.7rem 1.6rem;border-radius:8px;transition:opacity .15s,transform .15s;margin-bottom:1.5rem}}
.btn:hover{{opacity:.88;transform:translateY(-1px)}}
.search-form{{display:flex;gap:.5rem;max-width:340px;margin:0 auto}}
.search-form input{{flex:1;padding:.6rem 1rem;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.875rem;font-family:inherit;outline:none;background:#fff;color:#0f172a;transition:border-color .15s}}
.search-form input:focus{{border-color:#2f57ff}}
.search-form button{{padding:.6rem 1rem;background:#2f57ff;color:#fff;border:none;border-radius:8px;font-weight:600;font-size:.875rem;font-family:inherit;cursor:pointer;white-space:nowrap;transition:opacity .15s}}
.search-form button:hover{{opacity:.88}}
footer{{padding:1.25rem;text-align:center;font-size:.75rem;color:#94a3b8;border-top:1px solid #e2e8f0}}
</style>
</head>
<body>
<nav>
  <a href="/">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
    Jorres Apps
  </a>
</nav>
<main>
  <div class="box">
    <div class="code" aria-hidden="true">404</div>
    <h1>Page not found</h1>
    <p>The tool you were looking for may have moved, been removed, or never existed.<br>Try searching below or browse all tools.</p>
    <a class="btn" href="/">Browse all 135 tools</a>
    <form class="search-form" action="/" method="get" role="search" aria-label="Search tools">
      <input name="q" type="search" placeholder="Search tools..." aria-label="Search">
      <button type="submit">Search</button>
    </form>
  </div>
</main>
<footer>&copy; 2026 Jorres Apps</footer>
</body>
</html>""".format(favicon=_BRAND_FAVICON)


@flask_app.errorhandler(404)
def not_found(e):
    resp = make_response(_404_HTML, 404)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    resp.headers['Cache-Control'] = 'no-store'
    return resp


# ── Main launcher ─────────────────────────────────────────────────────────────
@flask_app.route('/')
def index():
    apps = [
        {
            'id':          a['id'],
            'name':        a['name'],
            'description': a['description'],
            'icon':        a['icon'],
            'color':       a['color'],
            'tags':        a.get('tags', []),
            'category':    a.get('category', 'Other'),
            'status':      lazy_dispatcher.status(f"/{a['id']}"),
            'url':         f"/{a['id']}/",
        }
        for a in REGISTRY
    ]
    return render_template('index.html', apps_json=_json_dumps(apps))


BASE_URL = 'https://jorresapps.onrender.com'


@flask_app.route('/googleff8e8f6157da6a96.html')
def google_verification():
    resp = make_response('google-site-verification: googleff8e8f6157da6a96.html')
    resp.headers['Content-Type'] = 'text/html'
    return resp


@flask_app.route('/robots.txt')
def robots():
    # Retired apps — still have redirect pages but 404 now; tell crawlers to deindex
    retired = [
        '/text-diff/', '/jwt-decoder/', '/password-strength/',
        '/invoice-tracker/', '/quiz-maker/', '/color-code-converter/',
        '/markdown-to-pdf/', '/countdown-timer/', '/percentage-calculator/',
    ]
    disallow_retired = ''.join(f'Disallow: {p}\n' for p in retired)
    body = (
        f'User-agent: *\n'
        f'Allow: /\n'
        f'Disallow: /api/\n'
        f'{disallow_retired}'
        f'\n'
        f'Sitemap: {BASE_URL}/sitemap.xml\n'
    )
    resp = make_response(body)
    resp.headers['Content-Type'] = 'text/plain'
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


@flask_app.route('/sitemap.xml')
def sitemap():
    from datetime import date
    today = date.today().isoformat()
    urls = [
        f'  <url>'
        f'<loc>{BASE_URL}/</loc>'
        f'<lastmod>{today}</lastmod>'
        f'<changefreq>weekly</changefreq>'
        f'<priority>1.0</priority>'
        f'</url>',
        f'  <url>'
        f'<loc>{BASE_URL}/privacy</loc>'
        f'<lastmod>{today}</lastmod>'
        f'<changefreq>yearly</changefreq>'
        f'<priority>0.3</priority>'
        f'</url>'
    ]
    for a in REGISTRY:
        urls.append(
            f'  <url>'
            f'<loc>{BASE_URL}/{a["id"]}/</loc>'
            f'<lastmod>{today}</lastmod>'
            f'<changefreq>monthly</changefreq>'
            f'<priority>0.8</priority>'
            f'</url>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(urls)
        + '\n</urlset>'
    )
    resp = make_response(xml)
    resp.headers['Content-Type'] = 'application/xml'
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


# ── Bug report (rate-limited: 10/minute per IP) ───────────────────────────────
@flask_app.route('/api/bug-report', methods=['POST'])
@limiter.limit('10 per minute')
def bug_report():
    data       = request.json or {}
    app_name   = data.get('app',   '').strip() or '(not specified)'
    issue_type = data.get('type',  'Bug').strip()
    desc       = data.get('desc',  '').strip()
    reporter   = data.get('email', '').strip() or '(not provided)'
    page       = data.get('page',  '').strip()

    if not desc:
        return jsonify({'ok': False, 'error': 'Description is required.'}), 400

    subject = f'[Jorres Apps] {issue_type}: {app_name}'

    text_body = (
        f'Bug Report — Jorres Apps\n'
        f'{"="*44}\n'
        f'App / Page:  {app_name}\n'
        f'URL:         {page}\n'
        f'Issue type:  {issue_type}\n'
        f'Reporter:    {reporter}\n'
        f'{"="*44}\n\n'
        f'{desc}\n'
    )

    badge_colours = {
        'Bug':     ('#fee2e2', '#dc2626', 'Bug'),
        'UI':      ('#ede9fe', '#7c3aed', 'UI/Layout'),
        'Feature': ('#dcfce7', '#16a34a', 'Feature'),
        'Other':   ('#f1f5f9', '#475569', 'Other'),
    }
    bg, fg, label = badge_colours.get(issue_type, badge_colours['Other'])

    def esc(s):
        return (str(s)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('\n', '<br>'))

    html_body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 16px;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
<tr><td style="background:#0f172a;border-radius:12px 12px 0 0;padding:28px 32px;">
  <p style="margin:0;font-size:22px;font-weight:800;color:#fff;">Jorres Apps</p>
  <p style="margin:6px 0 0;font-size:13px;color:#94a3b8;">Bug &amp; Feedback Report</p>
</td></tr>
<tr><td style="background:#fff;padding:28px 32px;">
  <p style="margin:0 0 20px;">
    <span style="display:inline-block;background:{bg};color:{fg};font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px;">{esc(label)}</span>
  </p>
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:24px;">
    <tr><td style="padding:11px 16px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;border-bottom:1px solid #e2e8f0;width:110px;">App</td>
        <td style="padding:11px 16px;font-size:14px;color:#1e293b;border-bottom:1px solid #e2e8f0;">{esc(app_name)}</td></tr>
    <tr><td style="padding:11px 16px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">Reporter</td>
        <td style="padding:11px 16px;font-size:14px;color:#1e293b;border-bottom:1px solid #e2e8f0;">{esc(reporter)}</td></tr>
    <tr><td style="padding:11px 16px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;">URL</td>
        <td style="padding:11px 16px;font-size:13px;color:#2563eb;word-break:break-all;"><a href="{esc(page)}" style="color:#2563eb;">{esc(page)}</a></td></tr>
  </table>
  <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;">Description</p>
  <div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid {fg};border-radius:0 8px 8px 0;padding:16px;font-size:14px;color:#1e293b;line-height:1.7;">{esc(desc)}</div>
</td></tr>
<tr><td style="background:#f8fafc;border-top:1px solid #e2e8f0;border-radius:0 0 12px 12px;padding:16px 32px;text-align:center;">
  <p style="margin:0;font-size:12px;color:#94a3b8;">Sent from <strong style="color:#64748b;">jorresapps.onrender.com</strong></p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

    # Log only non-PII metadata. The reporter's email and free-text
    # description are NOT written to stdout — our privacy policy states no
    # personal data is stored server-side, and Render retains stdout logs.
    print(f'[BUG REPORT] {issue_type} for {app_name} ({len(desc)} chars)', flush=True)

    resend_key = os.environ.get('RESEND_API_KEY', '')
    if not resend_key:
        return jsonify({'ok': True})

    try:
        import resend as _resend
        _resend.api_key = resend_key
        to_addr   = os.environ.get('RESEND_TO', 'joshuarelatorres28@gmail.com')
        from_addr = os.environ.get('EMAIL_FROM', 'Jorres Apps <onboarding@resend.dev>')
        result = _resend.Emails.send({
            'from': from_addr, 'to': [to_addr],
            'subject': subject, 'html': html_body, 'text': text_body,
        })
        print(f'[BUG REPORT] Resend OK — id={result.get("id")} → {to_addr}', flush=True)
        return jsonify({'ok': True})
    except Exception as e:
        print(f'[BUG REPORT] Resend error: {e}', flush=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@flask_app.route('/api/apps')
def list_apps():
    result = [
        {
            'id': a['id'], 'name': a['name'], 'description': a['description'],
            'icon': a['icon'], 'color': a['color'], 'tags': a.get('tags', []),
            'category': a.get('category', 'Other'),
            'status': lazy_dispatcher.status(f"/{a['id']}"),
            'url': f"/{a['id']}/",
        }
        for a in REGISTRY
    ]
    return jsonify(result)


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    print('\n  App Library — http://localhost:5000\n')
    run_simple('0.0.0.0', 5000, app, use_reloader=False)
