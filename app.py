from flask import Flask, jsonify, render_template, request, Response, redirect
import subprocess
import sys
import json
import os
import time
import requests as req_lib

app = Flask(__name__)

LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))


def load_registry():
    with open(os.path.join(LAUNCHER_DIR, 'apps.json'), encoding='utf-8') as f:
        apps = json.load(f)
    for a in apps:
        if not os.path.isabs(a['path']):
            a['path'] = os.path.normpath(os.path.join(LAUNCHER_DIR, a['path']))
    return apps


REGISTRY = load_registry()
procs = {}


def is_running(app_id):
    p = procs.get(app_id)
    return p is not None and p.poll() is None


def start_silent(cfg):
    kwargs = {'cwd': cfg['path']}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen([sys.executable, cfg['entry']], **kwargs)


def ensure_running(cfg):
    if is_running(cfg['id']):
        return
    procs[cfg['id']] = start_silent(cfg)
    for _ in range(20):
        try:
            req_lib.get(f"http://localhost:{cfg['port']}/", timeout=0.3)
            return
        except Exception:
            time.sleep(0.3)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/apps')
def list_apps():
    result = []
    for a in REGISTRY:
        result.append({
            'id':          a['id'],
            'name':        a['name'],
            'description': a['description'],
            'icon':        a['icon'],
            'color':       a['color'],
            'tags':        a.get('tags', []),
            'status':      'running' if is_running(a['id']) else 'stopped',
            'url':         f"/{a['id']}/",
        })
    return jsonify(result)


@app.route('/api/apps/<app_id>/stop', methods=['POST'])
def stop_app(app_id):
    p = procs.get(app_id)
    if not p or p.poll() is not None:
        procs.pop(app_id, None)
        return jsonify({'status': 'not_running'})
    p.terminate()
    procs.pop(app_id, None)
    return jsonify({'status': 'stopped'})


@app.route('/<app_id>')
def app_redirect(app_id):
    if not any(a['id'] == app_id for a in REGISTRY):
        return jsonify({'error': 'App not found'}), 404
    return redirect(f'/{app_id}/')


@app.route('/<app_id>/', defaults={'subpath': ''})
@app.route('/<app_id>/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(app_id, subpath):
    cfg = next((a for a in REGISTRY if a['id'] == app_id), None)
    if not cfg:
        return jsonify({'error': 'App not found'}), 404

    ensure_running(cfg)

    url = f"http://localhost:{cfg['port']}/{subpath}"
    if request.query_string:
        url += '?' + request.query_string.decode()

    headers = {k: v for k, v in request.headers if k.lower() not in ('host', 'content-length')}

    resp = req_lib.request(
        method=request.method,
        url=url,
        headers=headers,
        data=request.get_data(),
        allow_redirects=False,
        timeout=120,
        stream=True,
    )

    excluded = {'content-encoding', 'content-length', 'transfer-encoding', 'connection'}
    resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}

    return Response(resp.iter_content(chunk_size=8192), status=resp.status_code, headers=resp_headers)


if __name__ == '__main__':
    print('\n  App Library — http://localhost:5000\n')
    app.run(debug=False, port=5000)
