from flask import Flask, request, jsonify, render_template
import json, re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/format', methods=['POST'])
def format_code():
    d = request.json or {}
    code = d.get('code', '')
    lang = d.get('lang', 'json')
    indent = int(d.get('indent', 2))
    try:
        if lang == 'json':
            parsed = json.loads(code)
            result = json.dumps(parsed, indent=indent, ensure_ascii=False)
        elif lang == 'python':
            try:
                import autopep8
                result = autopep8.fix_code(code, options={'max_line_length': 100, 'indent_size': indent})
            except ImportError:
                return jsonify({'error': 'autopep8 not installed'}), 500
        elif lang == 'javascript':
            try:
                import jsbeautifier
                opts = jsbeautifier.default_options()
                opts.indent_size = indent
                result = jsbeautifier.beautify(code, opts)
            except ImportError:
                return jsonify({'error': 'jsbeautifier not installed'}), 500
        elif lang == 'css':
            try:
                import cssbeautifier
                opts = cssbeautifier.default_options()
                opts.indent_size = indent
                result = cssbeautifier.beautify(code, opts)
            except ImportError:
                return jsonify({'error': 'cssbeautifier not installed'}), 500
        elif lang == 'html':
            result = re.sub(r'>\s*<', '>\n<', code)
            lines = result.split('\n')
            indent_str = ' ' * indent
            level = 0; out = []
            for line in lines:
                line = line.strip()
                if not line: continue
                if re.match(r'</(div|p|ul|ol|li|table|tr|td|th|section|article|header|footer|main|nav|aside|form|fieldset)', line):
                    level = max(0, level-1)
                out.append(indent_str * level + line)
                if re.match(r'<(div|p|ul|ol|li|table|tr|td|th|section|article|header|footer|main|nav|aside|form|fieldset)[^/]*>(?!.*</(div|p|ul|ol|li|table|tr|td|th|section|article|header|footer|main|nav|aside|form|fieldset))', line):
                    level += 1
            result = '\n'.join(out)
        else:
            result = code
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5089)
