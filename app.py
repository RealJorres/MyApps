from flask import Flask, jsonify, render_template
import sys
import json
import os
import importlib.util
from werkzeug.middleware.dispatcher import DispatcherMiddleware

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
app = _slash_redirect(
    DispatcherMiddleware(flask_app, mounts),
    set(mounts.keys()),
)


@flask_app.route('/')
def index():
    return render_template('index.html')


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
            'status':      'running' if loaded else 'error',
            'url':         f"/{a['id']}/",
        })
    return jsonify(result)


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    print('\n  App Library — http://localhost:5000\n')
    run_simple('0.0.0.0', 5000, app, use_reloader=False)
