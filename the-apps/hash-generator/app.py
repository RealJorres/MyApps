from flask import Flask, request, jsonify, render_template
import hashlib

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALGOS = ['md5', 'sha1', 'sha256', 'sha512']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/hash-text', methods=['POST'])
def hash_text():
    d = request.json or {}
    text = d.get('text', '')
    enc  = d.get('encoding', 'utf-8')
    try:
        data = text.encode(enc, errors='replace')
        return jsonify({algo: hashlib.new(algo, data).hexdigest() for algo in ALGOS})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/hash-file', methods=['POST'])
def hash_file():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    try:
        data = f.read()
        return jsonify({algo: hashlib.new(algo, data).hexdigest() for algo in ALGOS})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5006)
