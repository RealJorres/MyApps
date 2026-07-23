"""
End-to-end client-logic tests (Playwright / real headless browser).

These run each app's actual in-browser JavaScript and assert the rendered
output is correct — the layer the Python harness cannot reach. Round 1:
one representative, deterministic app per category (10 total), plus a
localStorage-persistence test and a mobile-overflow check. Round 2
(2026-07-23) doubles coverage: 10 more apps, including real file
upload/download flows (csv-viewer, pdf-merger) and browser-to-server
API round-trips (base64-tool, hash-generator).

NOT run by the default suite (they need a browser + live server). Run with:
    pytest tests/test_e2e.py            # this file
    pytest tests/ -m e2e                # the e2e marker, anywhere
Prereqs (one time):
    pip install pytest-playwright && playwright install chromium

A console-error guard (autouse) fails any test whose page raised an
uncaught JS exception or logged console.error.
"""
import re

import pytest

pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def _console_guard(page):
    """Fail the test if the page raised a JS error or console.error."""
    errors = []
    page.on('pageerror', lambda exc: errors.append(f'pageerror: {exc}'))
    page.on('console', lambda msg: errors.append(f'console.error: {msg.text}')
            if msg.type == 'error' else None)
    yield
    assert not errors, 'JS errors on page:\n  ' + '\n  '.join(errors)


# ── Developer Tools ───────────────────────────────────────────────────────────
def test_base_converter(page, base_url):
    page.goto(f'{base_url}/base-converter/')
    page.fill('#decInput', '255')
    assert page.input_value('#hexInput') == 'FF'
    assert page.input_value('#binInput') == '11111111'
    assert page.input_value('#octInput') == '377'


# ── Documents & Writing ───────────────────────────────────────────────────────
def test_word_counter(page, base_url):
    page.goto(f'{base_url}/word-counter/')
    page.fill('#mainTextarea', 'hello world foo bar')
    assert page.inner_text('#statWords') == '4'


# ── Design & Visuals ──────────────────────────────────────────────────────────
def test_color_contrast(page, base_url):
    page.goto(f'{base_url}/color-contrast/')
    page.fill('#fgHex', '#000000')
    page.fill('#bgHex', '#ffffff')
    # Black on white is the WCAG maximum, 21:1
    assert page.inner_text('#ratioDisplay') == '21.00:1'


# ── Data & Analysis ───────────────────────────────────────────────────────────
def test_statistics_calculator(page, base_url):
    page.goto(f'{base_url}/statistics-calculator/')
    page.fill('#input', '2, 4, 6, 8, 10')
    page.get_by_role('button', name='Calculate', exact=True).click()
    grid = page.inner_text('#grid').upper()
    # mean & median of {2,4,6,8,10} = 6; sum = 30; count = 5
    assert 'MEAN\n6' in grid and 'MEDIAN\n6' in grid
    assert 'SUM\n30' in grid and 'COUNT\n5' in grid


# ── Finance & Business ────────────────────────────────────────────────────────
def test_tip_calculator(page, base_url):
    page.goto(f'{base_url}/tip-calculator/')
    page.fill('#billAmount', '100')
    page.get_by_role('button', name='10%', exact=True).click()
    page.get_by_role('button', name='1', exact=True).click()  # 1 person
    assert page.inner_text('#tipAmount') == '$10.00'
    assert page.inner_text('#totalBill') == '$110.00'
    assert page.inner_text('#perPerson') == '$110.00'


# ── Productivity & Planning (+ localStorage persistence) ──────────────────────
def test_todo_add_persist_delete(page, base_url):
    page.goto(f'{base_url}/todo-list/')
    page.evaluate('localStorage.clear()')
    page.reload()

    page.fill('#taskInput', 'Buy milk')
    page.get_by_role('button', name='Add', exact=True).click()
    assert page.locator('.todo-text', has_text='Buy milk').is_visible()

    # Persistence: survives a reload (localStorage)
    page.reload()
    assert page.locator('.todo-text', has_text='Buy milk').is_visible()

    # Delete
    page.locator('.del-btn').first.click()
    assert page.locator('.todo-text').count() == 0


# ── Security & Network ────────────────────────────────────────────────────────
def test_password_generator_length(page, base_url):
    page.goto(f'{base_url}/password-generator/')
    page.fill('#countInput', '1')
    page.get_by_role('button', name='Generate Passwords', exact=True).click()
    assert page.locator('#resultsCard').is_visible()
    # Default length is 16; the first password renders in #pw0
    pw = page.locator('#pw0').text_content()
    assert len(pw) == 16, f'expected 16-char password, got {len(pw)}: {pw!r}'


# ── Health & Wellness ─────────────────────────────────────────────────────────
def test_bmi_calculator(page, base_url):
    page.goto(f'{base_url}/bmi-calculator/')
    page.fill('#weightKg', '75')
    page.fill('#heightCm', '180')
    # 75 / 1.80^2 = 23.1
    assert page.inner_text('#bmiValue') == '23.1'
    assert 'Normal' in page.inner_text('#categoryBadge')


# ── Science & Learning ────────────────────────────────────────────────────────
def test_prime_factorizer(page, base_url):
    page.goto(f'{base_url}/prime-factorizer/')
    page.fill('#num', '12')
    page.get_by_role('button', name='Factorize', exact=True).click()
    fact = page.inner_text('#factStr')
    assert fact.startswith('12 =') and '3' in fact and '2' in fact


# ── Games ─────────────────────────────────────────────────────────────────────
def test_tic_tac_toe_move(page, base_url):
    page.goto(f'{base_url}/tic-tac-toe/')
    first = page.locator('.cell').first
    first.click()
    assert first.inner_text() == 'X'              # move placed
    assert 'O' in page.inner_text('#turnIndicator')  # turn advanced


# ══════════════════════════════════════════════════════════════════════════════
# Round 2 — broader per-app coverage (2026-07-23)
# ══════════════════════════════════════════════════════════════════════════════
from playwright.sync_api import expect


# ── Developer Tools ───────────────────────────────────────────────────────────
def test_json_formatter(page, base_url):
    page.goto(f'{base_url}/json-formatter/')
    page.fill('#inputArea', '{"b":1,"a":[1,2]}')
    page.get_by_role('button', name='Format', exact=True).click()
    out = page.inner_text('#outputPane')
    assert '"b": 1' in out and '"a": [' in out


def test_base64_tool_ui_roundtrip(page, base_url):
    """Text tab exercises the browser → Flask API → browser round-trip."""
    page.goto(f'{base_url}/base64-tool/')
    page.fill('#plainText', 'Hello, World!')
    page.locator('button', has_text='Encode').first.click()
    expect(page.locator('#b64Text')).to_have_value('SGVsbG8sIFdvcmxkIQ==')
    page.fill('#plainText', '')
    page.locator('button', has_text='Decode').first.click()
    expect(page.locator('#plainText')).to_have_value('Hello, World!')


# ── Documents & Writing ───────────────────────────────────────────────────────
def test_text_case_converter(page, base_url):
    page.goto(f'{base_url}/text-case-converter/')
    page.fill('#inputText', 'hello world')
    expect(page.locator('#result-uppercase')).to_have_text('HELLO WORLD')
    expect(page.locator('#result-snakecase')).to_have_text('hello_world')


def test_markdown_editor_preview(page, base_url):
    page.goto(f'{base_url}/markdown-editor/')
    page.fill('#editorArea', '# Title\n\nSome **bold** text.')
    expect(page.locator('#previewContent h1')).to_have_text('Title')
    expect(page.locator('#previewContent strong')).to_have_text('bold')


# ── Data & Analysis (file upload → server parse → rendered table) ─────────────
def test_csv_viewer_upload_renders_table(page, base_url, tmp_path):
    csv = tmp_path / 'people.csv'
    csv.write_text('name,age\nAlice,30\nBob,25\n', encoding='utf-8')
    page.goto(f'{base_url}/csv-viewer/')
    page.set_input_files('#fileInput', str(csv))
    expect(page.locator('#tableCard')).to_be_visible()
    table = page.inner_text('#dataTable')
    assert 'Alice' in table and 'Bob' in table
    assert page.inner_text('#infoFileName') == 'people.csv'


# ── Documents & Writing (file upload → server merge → file download) ──────────
def test_pdf_merger_merges_and_downloads(page, base_url, tmp_path):
    import fitz
    paths = []
    for i in (1, 2):
        doc = fitz.open()
        doc.new_page().insert_text((72, 72), f'document {i}')
        p = tmp_path / f'doc{i}.pdf'
        doc.save(str(p))
        doc.close()
        paths.append(str(p))
    page.goto(f'{base_url}/pdf-merger/')
    page.set_input_files('#fileInput', paths)
    with page.expect_download() as dl:
        page.click('#mergeBtn')
    merged_path = tmp_path / 'merged.pdf'
    dl.value.save_as(str(merged_path))
    merged = fitz.open(str(merged_path))
    assert len(merged) == 2, f'expected 2 pages in merged PDF, got {len(merged)}'
    merged.close()


# ── Finance & Business ────────────────────────────────────────────────────────
def test_loan_calculator(page, base_url):
    page.goto(f'{base_url}/loan-calculator/')
    # Defaults: $250,000 at 6.5% over 30 years → $1,580.17/month
    page.fill('#loanAmount', '250000')
    expect(page.locator('#monthly')).to_contain_text(re.compile(r'1,?580\.17'))


# ── Security & Network ────────────────────────────────────────────────────────
def test_cidr_calculator(page, base_url):
    page.goto(f'{base_url}/cidr-calculator/')
    page.fill('#cidr', '192.168.1.0/24')
    page.press('#cidr', 'Enter')
    grid = page.inner_text('#grid')
    assert '255.255.255.0' in grid       # netmask
    assert '192.168.1.255' in grid       # broadcast


def test_hash_generator_known_answer(page, base_url):
    """Browser → Flask hash API round-trip with a known SHA-256 answer."""
    page.goto(f'{base_url}/hash-generator/')
    page.fill('#textInput', 'abc')
    page.click('#hashTextBtn')
    body = page.locator('#resultsBody')
    expect(body).to_contain_text(
        'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')  # SHA-256
    expect(body).to_contain_text('900150983cd24fb0d6963f7d28e17f72')          # MD5


# ── Science & Learning ────────────────────────────────────────────────────────
def test_unit_converter(page, base_url):
    page.goto(f'{base_url}/unit-converter/')
    # Default category Length: 1 mm → 0.1 cm
    page.fill('#fromVal', '1')
    expect(page.locator('#toVal')).to_have_value('0.1')
    assert page.inner_text('#formula') == '1 mm = 0.1 cm'


# ── Games ─────────────────────────────────────────────────────────────────────
def test_connect_four_alternating_moves(page, base_url):
    page.goto(f'{base_url}/connect-four/')
    page.locator('.arrow-btn').first.click()
    expect(page.locator('.cell.p1')).to_have_count(1)
    page.locator('.arrow-btn').first.click()
    expect(page.locator('.cell.p2')).to_have_count(1)


# ── Cross-cutting: mobile viewport must not overflow horizontally ─────────────
def test_no_horizontal_overflow_mobile(page, base_url):
    page.set_viewport_size({'width': 375, 'height': 800})
    page.goto(f'{base_url}/bmi-calculator/')
    overflow = page.evaluate(
        'document.documentElement.scrollWidth - document.documentElement.clientWidth'
    )
    assert overflow <= 1, f'horizontal overflow of {overflow}px at 375w'
