from flask import Flask, request, jsonify, render_template
import re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/test', methods=['POST'])
def test():
    d = request.json or {}
    pattern = d.get('pattern', '')
    text    = d.get('text', '')
    flags   = 0
    for f, v in [('i', re.IGNORECASE), ('m', re.MULTILINE), ('s', re.DOTALL)]:
        if f in d.get('flags', []):
            flags |= v
    if not pattern:
        return jsonify({'matches': [], 'count': 0, 'error': None, 'highlighted': text})
    try:
        rx = re.compile(pattern, flags)
        matches = [{'start': m.start(), 'end': m.end(), 'match': m.group(),
                    'groups': list(m.groups()), 'span': f'{m.start()}–{m.end()}'}
                   for m in rx.finditer(text)]
        return jsonify({'matches': matches, 'count': len(matches), 'error': None})
    except re.error as e:
        return jsonify({'matches': [], 'count': 0, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=False, port=5007)
