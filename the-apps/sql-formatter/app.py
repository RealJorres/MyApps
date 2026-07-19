from flask import Flask, request, jsonify, render_template
import sqlparse

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/format', methods=['POST'])
def format_sql():
    d = request.json if isinstance(request.json, dict) else {}
    sql = d.get('sql', '')
    if not isinstance(sql, str):
        return jsonify({'error': 'SQL input must be text.'}), 400
    try:
        indent = int(d.get('indent', 2))
    except (ValueError, TypeError):
        indent = 2
    keyword_case = d.get('keyword_case', 'upper')
    if keyword_case not in ('upper', 'lower', 'capitalize'):
        keyword_case = 'upper'
    try:
        result = sqlparse.format(sql, reindent=True, indent_width=indent,
                                  keyword_case=keyword_case, strip_comments=False,
                                  use_space_around_operators=True)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/minify', methods=['POST'])
def minify_sql():
    d = request.json if isinstance(request.json, dict) else {}
    sql = d.get('sql', '')
    if not isinstance(sql, str):
        return jsonify({'error': 'SQL input must be text.'}), 400
    try:
        result = sqlparse.format(sql, strip_whitespace=True)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5028)
