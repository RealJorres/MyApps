"""
Per-app functional test harness for Jorres Apps.

Two layers:

1. Contract tests (parametrized over EVERY app in apps.json)
   Each app gets its own pass/fail line. Goes beyond "returns 200":
   asserts the served HTML wires up the shared design system correctly
   (base.css, versioned app-nav.js + footer.js, brand favicon) and is
   free of known regressions (`--primary` token, U+0008 backspace byte).

2. Known-answer functional tests (compute API endpoints)
   POST real inputs to the server-side /api/* endpoints and assert the
   OUTPUT is correct — not merely that the route responds. These exercise
   the actual tool logic (encode, hash, format, convert, generate, ...).

Network-dependent tools (DNS / IP / WHOIS / SSL / outbound proxy) are
skipped unless JORRES_NET_TESTS=1, so the suite is hermetic by default.

Run:
    pytest tests/test_functional.py -q
    pytest tests/test_functional.py -q -k contract        # just contract layer
    JORRES_NET_TESTS=1 pytest tests/test_functional.py     # include network
"""
import base64
import hashlib
import io
import json
import os
import re
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

NET_TESTS = os.environ.get('JORRES_NET_TESTS') == '1'


# ── Registry (loaded at import time so we can parametrize per app) ─────────────
def _load_registry():
    with open(os.path.join(ROOT, 'apps.json'), encoding='utf-8-sig') as f:
        return json.load(f)


REGISTRY = _load_registry()
APP_IDS = [a['id'] for a in REGISTRY]


def test_sitemap_covers_every_app_and_public_page(client):
    """sitemap.xml must list every registered app plus the homepage —
    so Google can discover and index the whole public surface."""
    import re
    _, _, xml = _get(client, '/sitemap.xml')
    locs = set(re.findall(r'<loc>(.*?)</loc>', xml))
    base = 'https://jorresapps.onrender.com'
    required = {f'{base}/{aid}/' for aid in APP_IDS}
    required |= {f'{base}/'}
    assert f'{base}/privacy' not in locs, 'retired /privacy must not be in sitemap'
    missing = sorted(required - locs)
    assert not missing, f'URLs missing from sitemap.xml: {missing}'


def test_robots_allows_crawl_and_points_to_sitemap(client):
    """robots.txt must permit indexing and advertise the sitemap; only
    /api/ and retired apps may be disallowed (never a live app)."""
    _, _, body = _get(client, '/robots.txt')
    assert 'Allow: /' in body
    assert 'Sitemap: https://jorresapps.onrender.com/sitemap.xml' in body
    assert 'Disallow: /api/' in body
    # No currently-registered app may be blocked from crawling
    disallowed = set(re.findall(r'Disallow:\s*/([a-z0-9-]+)/', body))
    blocked_live = disallowed & set(APP_IDS)
    assert not blocked_live, f'robots.txt blocks live apps: {sorted(blocked_live)}'


def test_launcher_hardcoded_ids_all_exist():
    """Every app ID hard-coded in the launcher's curated lists
    (SUBCATEGORIES, DEFAULT_QUICK_IDS, NEW_THIS_MONTH_IDS, PICKS_IDS)
    must still exist in apps.json — guards against retired-app rot."""
    import re
    reg = set(APP_IDS)
    s = open(os.path.join(ROOT, 'templates', 'index.html'), encoding='utf-8').read()
    ids = set()
    for m in re.finditer(r'ids:\s*\[([^\]]*)\]', s):
        ids |= set(re.findall(r'"([a-z0-9-]+)"', m.group(1)))
    for name in ('DEFAULT_QUICK_IDS', 'NEW_THIS_MONTH_IDS', 'PICKS_IDS'):
        m = re.search(name + r'\s*=\s*\[([^\]]*)\]', s)
        if m:
            ids |= set(re.findall(r'"([a-z0-9-]+)"', m.group(1)))
    dead = sorted(i for i in ids if i not in reg)
    assert not dead, f'Launcher references retired/unknown app IDs: {dead}'


@pytest.fixture(scope='session')
def client():
    """Full WSGI-stack test client (exercises the lazy dispatcher + middleware)."""
    from werkzeug.test import Client
    import app as launcher
    return Client(launcher.app)


def _get(client, path):
    """GET helper returning (status, raw_bytes, text)."""
    r = client.get(path)
    raw = r.get_data()
    return r.status_code, raw, raw.decode('utf-8', 'replace')


def _post_json(client, path, payload):
    """POST JSON helper returning (status, parsed_json_or_None, text)."""
    r = client.post(
        path,
        data=json.dumps(payload),
        content_type='application/json',
    )
    raw = r.get_data()
    text = raw.decode('utf-8', 'replace')
    try:
        data = json.loads(text)
    except Exception:
        data = None
    return r.status_code, data, text


# ══════════════════════════════════════════════════════════════════════════════
# Layer 1 — Per-app contract tests (one parametrized case per app)
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.contract
@pytest.mark.parametrize('app_id', APP_IDS)
def test_app_contract(client, app_id):
    """Each app must load and correctly wire the shared design system."""
    status, raw, text = _get(client, f'/{app_id}/')

    assert status == 200, f'{app_id}: expected 200, got {status}'
    assert len(raw) > 400, f'{app_id}: body suspiciously small ({len(raw)} bytes)'
    assert '<title' in text.lower(), f'{app_id}: missing <title>'

    # Shared design system wiring (these are the assets app-nav/footer rely on)
    assert '/static/base.css' in text, f'{app_id}: base.css not linked'
    assert 'app-nav.js?v=' in text, f'{app_id}: versioned app-nav.js missing'
    assert 'footer.js?v=' in text, f'{app_id}: versioned footer.js missing'

    # Brand favicon (either quote style)
    assert ("viewBox='0 0 64 64'" in text or 'viewBox="0 0 64 64"' in text), \
        f'{app_id}: brand favicon missing'

    # Regression guards (project standards)
    assert '--primary' not in text, f'{app_id}: leftover --primary token (use --brand)'
    assert 0x08 not in raw, f'{app_id}: U+0008 backspace byte in served HTML'


# ══════════════════════════════════════════════════════════════════════════════
# Layer 2 — Known-answer functional tests (server-side compute endpoints)
# ══════════════════════════════════════════════════════════════════════════════
def test_base64_roundtrip(client):
    s, d, _ = _post_json(client, '/base64-tool/api/encode-text', {'text': 'Hello, World!'})
    assert s == 200 and d['result'] == base64.b64encode(b'Hello, World!').decode()
    s, d, _ = _post_json(client, '/base64-tool/api/decode-text', {'text': d['result']})
    assert s == 200 and d['result'] == 'Hello, World!'


def test_base64_invalid_decode_is_handled(client):
    s, d, _ = _post_json(client, '/base64-tool/api/decode-text', {'text': '!!!not-base64!!!'})
    # Must not crash the worker: returns a JSON error, not an unhandled 500 stacktrace
    assert d is not None and ('error' in d or 'result' in d)


def test_hash_known_vectors(client):
    s, d, _ = _post_json(client, '/hash-generator/api/hash-text', {'text': 'abc'})
    assert s == 200
    assert d['md5'] == '900150983cd24fb0d6963f7d28e17f72'
    assert d['sha256'] == hashlib.sha256(b'abc').hexdigest()


def test_css_format(client):
    s, d, _ = _post_json(client, '/css-formatter/api/format', {'css': 'a{color:red;margin:0}'})
    assert s == 200 and 'color' in d['result'] and 'red' in d['result']


def test_sql_format_uppercases_keywords(client):
    s, d, _ = _post_json(client, '/sql-formatter/api/format', {'sql': 'select id from users where id=1'})
    assert s == 200 and 'SELECT' in d['result'] and 'FROM' in d['result']


def test_csv_to_json(client):
    s, d, _ = _post_json(client, '/csv-json-converter/api/csv-to-json',
                         {'text': 'name,age\nAlice,30\nBob,25'})
    assert s == 200 and d['count'] == 2
    rows = json.loads(d['result'])
    assert rows[0]['name'] == 'Alice' and rows[1]['age'] == '25'


def test_regex_counts_matches(client):
    s, d, _ = _post_json(client, '/regex-tester/api/test',
                         {'pattern': r'\d+', 'text': 'a1 bb 22 ccc 333'})
    assert s == 200 and d['count'] == 3 and d['error'] is None


def test_regex_invalid_pattern_is_handled(client):
    s, d, _ = _post_json(client, '/regex-tester/api/test', {'pattern': '(', 'text': 'x'})
    assert d is not None and d.get('error')  # bad regex reported, not crashed


def test_jwt_roundtrip(client):
    s, d, _ = _post_json(client, '/jwt-generator/api/generate',
                         {'secret': 'topsecret', 'algorithm': 'HS256', 'payload': {'sub': '42'}})
    assert s == 200 and d['token'].count('.') == 2
    s, d2, _ = _post_json(client, '/jwt-generator/api/decode',
                          {'token': d['token'], 'secret': 'topsecret'})
    assert s == 200 and d2['payload']['sub'] == '42' and d2['verified'] is True


def test_code_beautifier_json(client):
    s, d, _ = _post_json(client, '/code-beautifier/api/format',
                         {'code': '{"a":1,"b":[2,3]}', 'lang': 'json', 'indent': 2})
    assert s == 200 and '"a"' in d['result'] and '\n' in d['result']


def test_qr_generate_returns_image(client):
    s, d, _ = _post_json(client, '/qr-generator/api/generate', {'text': 'https://example.com'})
    assert s == 200 and isinstance(d.get('image'), str) and len(d['image']) > 100


def test_qr_empty_input_rejected(client):
    s, d, _ = _post_json(client, '/qr-generator/api/generate', {'text': ''})
    assert s == 400 and 'error' in d


def test_cron_describe_valid(client):
    s, d, _ = _post_json(client, '/cron-builder/api/describe', {'expr': '*/5 * * * *'})
    assert s == 200 and d.get('valid') is True and d.get('next_runs')


def test_cron_rejects_wrong_field_count(client):
    s, d, _ = _post_json(client, '/cron-builder/api/describe', {'expr': '* * *'})
    assert s == 400 and 'error' in d


# ── Edge cases: long input & special chars should not crash compute endpoints ──
def test_hash_long_input(client):
    s, d, _ = _post_json(client, '/hash-generator/api/hash-text', {'text': 'x' * 200_000})
    assert s == 200 and d['sha256'] == hashlib.sha256(b'x' * 200_000).hexdigest()


def test_base64_unicode(client):
    s, d, _ = _post_json(client, '/base64-tool/api/encode-text', {'text': 'café ☕ 日本語'})
    assert s == 200
    s, d, _ = _post_json(client, '/base64-tool/api/decode-text', {'text': d['result']})
    assert s == 200 and d['result'] == 'café ☕ 日本語'


# ── PDF to Word (file-upload conversion) ──────────────────────────────────────
def _make_pdf(text=None):
    """Build a tiny in-memory PDF; text=None yields a blank (no-text) page."""
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    if text:
        c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buf.getvalue()


def _post_file(client, path, file_bytes, filename):
    r = client.post(path, data={'file': (io.BytesIO(file_bytes), filename)},
                    content_type='multipart/form-data')
    return r


def test_pdf_to_word_converts_text_pdf(client):
    pdf = _make_pdf('Hello Jorres Apps. This is a convertible paragraph.')
    r = _post_file(client, '/pdf-to-word/api/convert', pdf, 'sample.pdf')
    assert r.status_code == 200
    out = r.get_data()
    # Output must be a real .docx (zip containing word/document.xml)
    assert zipfile.is_zipfile(io.BytesIO(out))
    assert 'word/document.xml' in zipfile.ZipFile(io.BytesIO(out)).namelist()


def test_pdf_to_word_flags_scanned_pdf(client):
    blank = _make_pdf(None)  # a page with no extractable text
    r = _post_file(client, '/pdf-to-word/api/convert', blank, 'scan.pdf')
    assert r.status_code == 422
    assert r.get_json().get('scanned') is True


def test_pdf_to_word_rejects_non_pdf(client):
    r = _post_file(client, '/pdf-to-word/api/convert', b'this is not a pdf', 'notes.txt')
    assert r.status_code == 400 and 'error' in r.get_json()


# ══════════════════════════════════════════════════════════════════════════════
# Layer 3 — Network-dependent tools (hermetic by default; opt-in via env)
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.skipif(not NET_TESTS, reason='set JORRES_NET_TESTS=1 to run network tests')
def test_dns_lookup_live(client):
    s, d, _ = _post_json(client, '/dns-lookup/api/lookup', {'domain': 'example.com', 'type': 'A'})
    assert s == 200 and d.get('records')


@pytest.mark.skipif(not NET_TESTS, reason='set JORRES_NET_TESTS=1 to run network tests')
def test_api_tester_blocks_internal_ssrf(client):
    # SSRF guard must reject loopback regardless of network availability
    s, d, _ = _post_json(client, '/api-tester/api/request',
                         {'url': 'http://127.0.0.1/', 'method': 'GET'})
    assert s == 403 and 'error' in d


# This SSRF-guard assertion needs no outbound network, so it always runs:
def test_api_tester_ssrf_guard_always_on(client):
    s, d, _ = _post_json(client, '/api-tester/api/request',
                         {'url': 'http://169.254.169.254/latest/meta-data/', 'method': 'GET'})
    assert s == 403 and 'error' in d, 'cloud-metadata address must be blocked'
