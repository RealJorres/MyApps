from flask import Flask, request, jsonify, render_template
import re
import concurrent.futures

app = Flask(__name__)

# Regex execution timeout — prevents ReDoS (catastrophic backtracking)
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)
_REGEX_TIMEOUT = 3.0  # seconds


def _run_regex(pattern, text, flags):
    """Execute regex in a thread so we can apply a hard timeout."""
    rx = re.compile(pattern, flags)
    matches = [
        {
            'start':  m.start(),
            'end':    m.end(),
            'match':  m.group(),
            'groups': list(m.groups()),
            'span':   f'{m.start()}–{m.end()}',
        }
        for m in rx.finditer(text)
    ]
    return matches


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/test', methods=['POST'])
def test():
    d = request.json if isinstance(request.json, dict) else {}
    pattern = d.get('pattern', '')
    text    = d.get('text', '')
    if not isinstance(pattern, str):
        pattern = ''
    if not isinstance(text, str):
        text = str(text) if text is not None else ''
    flags_in = d.get('flags', '')
    if not isinstance(flags_in, (str, list, tuple)):
        flags_in = ''
    flags   = 0
    for f, v in [('i', re.IGNORECASE), ('m', re.MULTILINE), ('s', re.DOTALL)]:
        if f in flags_in:
            flags |= v

    if not pattern:
        return jsonify({'matches': [], 'count': 0, 'error': None, 'highlighted': text})

    try:
        # Validate pattern first (cheap, no timeout needed)
        re.compile(pattern, flags)
    except re.error as e:
        return jsonify({'matches': [], 'count': 0, 'error': str(e)})

    # Run the actual match with a timeout to prevent ReDoS
    future = _EXECUTOR.submit(_run_regex, pattern, text, flags)
    try:
        matches = future.result(timeout=_REGEX_TIMEOUT)
        return jsonify({'matches': matches, 'count': len(matches), 'error': None})
    except concurrent.futures.TimeoutError:
        future.cancel()
        return jsonify({
            'matches': [], 'count': 0,
            'error': 'Regex execution timed out (possible catastrophic backtracking). '
                     'Simplify your pattern or reduce the input length.'
        }), 408
    except re.error as e:
        return jsonify({'matches': [], 'count': 0, 'error': str(e)})
    except Exception as e:
        return jsonify({'matches': [], 'count': 0, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, port=5007)
