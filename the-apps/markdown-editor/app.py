from flask import Flask, request, jsonify, render_template
import markdown

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/render', methods=['POST'])
def render_md():
    d = request.json or {}
    try:
        html = markdown.markdown(d.get('text', ''),
               extensions=['fenced_code', 'tables', 'nl2br'])
        return jsonify({'html': html})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5008)
