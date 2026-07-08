from flask import Flask, request, jsonify, render_template
import cssbeautifier

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/format', methods=['POST'])
def format_css():
    d = request.json or {}
    css = d.get('css', '')
    indent = d.get('indent', '  ')
    try:
        opts = cssbeautifier.default_options()
        opts.indent_char = ' '
        opts.indent_size = int(indent) if str(indent).isdigit() else 2
        result = cssbeautifier.beautify(css, opts)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/minify', methods=['POST'])
def minify_css():
    d = request.json or {}
    css = d.get('css', '')
    try:
        import re
        result = re.sub(r'\s+', ' ', css)
        result = re.sub(r'\s*([{}:;,>~+])\s*', r'\1', result)
        result = re.sub(r';(?=\s*})', '', result)
        result = re.sub(r'/\*.*?\*/', '', result, flags=re.DOTALL)
        result = result.strip()
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5039)
