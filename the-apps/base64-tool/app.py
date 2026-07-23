from flask import Flask, request, jsonify, send_file, render_template
import base64, io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

def _str(d, key, default=''):
    v = d.get(key, default)
    return v if isinstance(v, str) else default

@app.route('/api/encode-text', methods=['POST'])
def encode_text():
    d = request.json or {}
    text = _str(d, 'text')
    enc = _str(d, 'encoding', 'utf-8')
    try:
        result = base64.b64encode(text.encode(enc)).decode('ascii')
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/decode-text', methods=['POST'])
def decode_text():
    d = request.json or {}
    b64 = _str(d, 'text').strip()
    enc = _str(d, 'encoding', 'utf-8')
    try:
        result = base64.b64decode(b64).decode(enc)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/encode-file', methods=['POST'])
def encode_file():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    try:
        result = base64.b64encode(f.read()).decode('ascii')
        return jsonify({'result': result, 'filename': f.filename})
    except Exception:
        return jsonify({'error': 'Could not encode this file. Please try again.'}), 500

@app.route('/api/decode-file', methods=['POST'])
def decode_file():
    d = request.json or {}
    b64 = _str(d, 'text').strip()
    filename = _str(d, 'filename', 'output.bin') or 'output.bin'
    try:
        data = base64.b64decode(b64)
        return send_file(io.BytesIO(data), as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=False, port=5017)
