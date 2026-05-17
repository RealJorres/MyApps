from flask import Flask, request, jsonify, render_template
import difflib

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/diff', methods=['POST'])
def diff():
    d = request.json or {}
    a = d.get('a', '').splitlines(keepends=True)
    b = d.get('b', '').splitlines(keepends=True)
    mode = d.get('mode', 'unified')
    try:
        if mode == 'unified':
            result = list(difflib.unified_diff(a, b, lineterm='', fromfile='Original', tofile='Modified'))
        else:
            result = list(difflib.ndiff(a, b))
        return jsonify({'diff': result, 'mode': mode})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5016)
