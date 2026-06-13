from flask import Flask, request, send_file, jsonify, render_template
import fitz, io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/compress', methods=['POST'])
def compress():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file provided'}), 400
    try:
        data = f.read()
        original_size = len(data)
        src = fitz.open(stream=data, filetype='pdf')
        buf = io.BytesIO()
        src.save(buf, garbage=4, deflate=True, clean=True, deflate_images=True, deflate_fonts=True)
        src.close()
        buf.seek(0)
        compressed_size = len(buf.getvalue())
        buf.seek(0)
        savings = round((1 - compressed_size / original_size) * 100, 1)
        resp = send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='compressed.pdf')
        resp.headers['X-Original-Size'] = str(original_size)
        resp.headers['X-Compressed-Size'] = str(compressed_size)
        resp.headers['X-Savings'] = str(savings)
        resp.headers['Access-Control-Expose-Headers'] = 'X-Original-Size, X-Compressed-Size, X-Savings'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5059)
