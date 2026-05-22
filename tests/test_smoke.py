"""
Smoke tests for the Jorres Apps launcher.
Run with:  pytest tests/
These are NOT comprehensive unit tests — they verify the system
loads, routes respond, and the app registry is well-formed.
"""
import json
import os
import sys
import pytest

# Add the project root to sys.path so we can import app.py
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def registry():
    """Load and return the apps.json registry."""
    path = os.path.join(ROOT, 'apps.json')
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)


@pytest.fixture(scope='session')
def flask_client():
    """Return a Flask test client for the root app only (not sub-apps)."""
    # Import only flask_app (not the full WSGI stack) to avoid loading 128 apps
    from app import flask_app
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


# ── Registry tests ────────────────────────────────────────────────────────────

def test_registry_loads(registry):
    """apps.json must be valid JSON and non-empty."""
    assert isinstance(registry, list)
    assert len(registry) > 0, "apps.json is empty"


def test_registry_has_required_fields(registry):
    """Every entry must have id, name, description, path, entry, category."""
    required = {'id', 'name', 'description', 'path', 'entry', 'category'}
    for app in registry:
        missing = required - set(app.keys())
        assert not missing, f"App '{app.get('id', '?')}' missing fields: {missing}"


def test_registry_unique_ids(registry):
    """All app IDs must be unique."""
    ids = [a['id'] for a in registry]
    assert len(ids) == len(set(ids)), "Duplicate app IDs found in apps.json"


def test_registry_unique_ports(registry):
    """All ports must be unique."""
    ports = [a['port'] for a in registry]
    assert len(ports) == len(set(ports)), "Duplicate ports found in apps.json"


def test_registry_app_dirs_exist(registry):
    """Every app's directory and entry file must exist on disk."""
    missing = []
    for app in registry:
        path = app['path'] if os.path.isabs(app['path']) else os.path.normpath(
            os.path.join(ROOT, app['path'])
        )
        entry = os.path.join(path, app['entry'])
        template = os.path.join(path, 'templates', 'index.html')
        if not os.path.isfile(entry):
            missing.append(f"Missing entry: {entry}")
        if not os.path.isfile(template):
            missing.append(f"Missing template: {template}")
    assert not missing, "Missing app files:\n" + "\n".join(missing[:10])


def test_registry_valid_categories(registry):
    """Every app must be in one of the 10 defined categories."""
    valid = {
        'Developer Tools', 'Documents & Writing', 'Design & Visuals',
        'Data & Analysis', 'Finance & Business', 'Productivity & Planning',
        'Security & Network', 'Health & Wellness', 'Science & Learning', 'Games',
    }
    bad = [(a['id'], a['category']) for a in registry if a['category'] not in valid]
    assert not bad, f"Apps with invalid categories: {bad}"


def test_registry_icons_are_svg(registry):
    """All app icons should be SVG strings (not HTML entities or emoji)."""
    bad = [a['id'] for a in registry if not a.get('icon', '').startswith('<svg')]
    assert not bad, f"Apps with non-SVG icons: {bad}"


def test_registry_no_retired_apps(registry):
    """Retired app IDs must not appear in the registry."""
    retired = {
        'text-diff', 'jwt-decoder', 'password-strength', 'invoice-tracker',
        'quiz-maker', 'color-code-converter', 'markdown-to-pdf', 'countdown-timer',
    }
    found = [a['id'] for a in registry if a['id'] in retired]
    assert not found, f"Retired apps still in registry: {found}"


# ── Flask route tests ─────────────────────────────────────────────────────────

def test_root_returns_200(flask_client):
    """GET / must return 200."""
    resp = flask_client.get('/')
    assert resp.status_code == 200


def test_root_contains_apps(flask_client):
    """The launcher page must contain app data JSON."""
    resp = flask_client.get('/')
    assert b'apps_json' in resp.data or b'"id"' in resp.data


def test_robots_txt(flask_client):
    """GET /robots.txt must be valid and contain a Sitemap line."""
    resp = flask_client.get('/robots.txt')
    assert resp.status_code == 200
    body = resp.data.decode()
    assert 'User-agent: *' in body
    assert 'Sitemap:' in body
    assert 'Disallow: /api/' in body


def test_sitemap_xml(flask_client):
    """GET /sitemap.xml must return valid XML."""
    resp = flask_client.get('/sitemap.xml')
    assert resp.status_code == 200
    assert b'<urlset' in resp.data
    assert b'jorresapps.onrender.com' in resp.data


def test_privacy_page(flask_client):
    """GET /privacy must return 200 with privacy content."""
    resp = flask_client.get('/privacy')
    assert resp.status_code == 200
    assert b'Privacy' in resp.data


def test_static_base_css(flask_client):
    """GET /static/base.css must return CSS content."""
    resp = flask_client.get('/static/base.css')
    assert resp.status_code == 200
    assert b'--brand' in resp.data


def test_static_app_nav_js(flask_client):
    """GET /static/app-nav.js must return JS content."""
    resp = flask_client.get('/static/app-nav.js')
    assert resp.status_code == 200
    assert b'app-nav' in resp.data or b'ftOpen' in resp.data or b'Jorres' in resp.data


def test_bug_report_requires_description(flask_client):
    """POST /api/bug-report with no description must return 400."""
    resp = flask_client.post(
        '/api/bug-report',
        json={'app': 'test', 'type': 'Bug', 'desc': '', 'page': '/'},
        content_type='application/json',
    )
    assert resp.status_code == 400


def test_api_apps_endpoint(flask_client):
    """GET /api/apps must return a JSON list of apps."""
    resp = flask_client.get('/api/apps')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert len(data) > 0
    assert 'id' in data[0]
