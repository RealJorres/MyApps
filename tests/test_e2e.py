"""
End-to-end client-logic tests (Playwright / real headless browser).

These run each app's actual in-browser JavaScript and assert the rendered
output is correct — the layer the Python harness cannot reach. One
representative, deterministic app per category (10 total), plus a
localStorage-persistence test and a mobile-overflow check.

NOT run by the default suite (they need a browser + live server). Run with:
    pytest tests/test_e2e.py            # this file
    pytest tests/ -m e2e                # the e2e marker, anywhere
Prereqs (one time):
    pip install pytest-playwright && playwright install chromium

A console-error guard (autouse) fails any test whose page raised an
uncaught JS exception or logged console.error.
"""
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


# ── Cross-cutting: mobile viewport must not overflow horizontally ─────────────
def test_no_horizontal_overflow_mobile(page, base_url):
    page.set_viewport_size({'width': 375, 'height': 800})
    page.goto(f'{base_url}/bmi-calculator/')
    overflow = page.evaluate(
        'document.documentElement.scrollWidth - document.documentElement.clientWidth'
    )
    assert overflow <= 1, f'horizontal overflow of {overflow}px at 375w'
