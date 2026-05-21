from flask import Flask, jsonify, render_template, make_response, request
import sys
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from json import dumps as _json_dumps
import importlib.util
from werkzeug.middleware.dispatcher import DispatcherMiddleware


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
LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))


def load_registry():
    with open(os.path.join(LAUNCHER_DIR, 'apps.json'), encoding='utf-8') as f:
        apps = json.load(f)
    for a in apps:
        if not os.path.isabs(a['path']):
            a['path'] = os.path.normpath(os.path.join(LAUNCHER_DIR, a['path']))
    return apps


REGISTRY = load_registry()


def load_sub_app(cfg):
    entry = os.path.join(cfg['path'], cfg['entry'])
    module_name = cfg['id'].replace('-', '_') + '_wsgi'
    if cfg['path'] not in sys.path:
        sys.path.insert(0, cfg['path'])
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
    body = f'User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n'
    resp = make_response(body)
    resp.headers['Content-Type'] = 'text/plain'
    return resp


@flask_app.route('/sitemap.xml')
def sitemap():
    urls = [f'  <url><loc>{BASE_URL}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>']
    for a in REGISTRY:
        urls.append(
            f'  <url><loc>{BASE_URL}/{a["id"]}/</loc>'
            f'<changefreq>monthly</changefreq><priority>0.8</priority></url>'
        )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(urls)
           + '\n</urlset>')
    resp = make_response(xml)
    resp.headers['Content-Type'] = 'application/xml'
    return resp


@flask_app.route('/api/bug-report', methods=['POST'])
def bug_report():
    data = request.json or {}
    app_name  = data.get('app',   '').strip() or '(not specified)'
    issue_type = data.get('type', 'Bug').strip()
    desc      = data.get('desc',  '').strip()
    reporter  = data.get('email', '').strip() or '(not provided)'

    if not desc:
        return jsonify({'ok': False, 'error': 'Description is required.'}), 400

    mail_user = os.environ.get('MAIL_USER', '')
    mail_pass = os.environ.get('MAIL_PASS', '')

    if not mail_user or not mail_pass:
        # Env vars not configured — still return success so the user isn't
        # blocked, but log to server console so the dev can see the report.
        print(f'[BUG REPORT] App={app_name} | Type={issue_type} | Reporter={reporter}\n{desc}')
        return jsonify({'ok': True})

    try:
        subject = f'[Jorres Apps] Bug Report – {issue_type}: {app_name}'
        body = (
            f'Bug Report from Jorres Apps\n'
            f'{"="*40}\n'
            f'App:         {app_name}\n'
            f'Issue type:  {issue_type}\n'
            f'Reporter:    {reporter}\n'
            f'{"="*40}\n\n'
            f'{desc}\n'
        )
        msg = MIMEMultipart()
        msg['From']    = mail_user
        msg['To']      = 'joshuarelatorres28@gmail.com'
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(mail_user, mail_pass)
            server.sendmail(mail_user, 'joshuarelatorres28@gmail.com', msg.as_string())

        return jsonify({'ok': True})
    except Exception as e:
        print(f'[BUG REPORT] Email failed: {e}')
        return jsonify({'ok': False, 'error': 'Failed to send email. Please try again later.'}), 500


@flask_app.route('/api/apps')
def list_apps():
    result = []
    for a in REGISTRY:
        loaded = f"/{a['id']}" in mounts
        result.append({
            'id':          a['id'],
            'name':        a['name'],
            'description': a['description'],
            'icon':        a['icon'],
            'color':       a['color'],
            'tags':        a.get('tags', []),
            'category':    a.get('category', 'Other'),
            'status':      'running' if loaded else 'error',
            'url':         f"/{a['id']}/",
        })
    return jsonify(result)


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    print('\n  App Library — http://localhost:5000\n')
    run_simple('0.0.0.0', 5000, app, use_reloader=False)
