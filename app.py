from flask import Flask, jsonify, render_template, make_response, request, send_from_directory
import sys
import json
import os
from json import dumps as _json_dumps
import importlib.util
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# ── Optional rate limiting ────────────────────────────────────────────────────
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _LIMITER_AVAILABLE = True
except ImportError:
    _LIMITER_AVAILABLE = False
    print('[launcher] flask-limiter not installed — API endpoints unprotected', flush=True)


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


mounts = {}
for _cfg in REGISTRY:
    try:
        mounts[f"/{_cfg['id']}"] = load_sub_app(_cfg)
    except Exception as _e:
        print(f"[launcher] Could not load {_cfg['id']}: {_e}")


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


# 'app' is the full WSGI stack imported by wsgi.py and gunicorn
app = SecurityHeadersMiddleware(
    _slash_redirect(
        DispatcherMiddleware(flask_app, mounts),
        set(mounts.keys()),
    )
)


# ── Static assets (design system) ────────────────────────────────────────────
@flask_app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve shared static assets to all sub-apps."""
    return send_from_directory(flask_app.static_folder, filename)


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
            'status':      'running' if f"/{a['id']}" in mounts else 'error',
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
    body = (
        f'User-agent: *\n'
        f'Allow: /\n'
        f'Disallow: /api/\n'
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

    print(f'[BUG REPORT] {subject}\n{text_body}', flush=True)

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
            'status': 'running' if f"/{a['id']}" in mounts else 'error',
            'url': f"/{a['id']}/",
        }
        for a in REGISTRY
    ]
    return jsonify(result)


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    print('\n  App Library — http://localhost:5000\n')
    run_simple('0.0.0.0', 5000, app, use_reloader=False)
