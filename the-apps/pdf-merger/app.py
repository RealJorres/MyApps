from flask import Flask, request, send_file, jsonify, render_template
import fitz
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/merge', methods=['POST'])
def merge():
    files = request.files.getlist('files')
    if len(files) < 2:
        return jsonify({'error': 'Upload at least 2 PDF files'}), 400
    try:
        merged = fitz.open()
        for f in files:
            doc = fitz.open(stream=f.read(), filetype='pdf')
            merged.insert_pdf(doc)
            doc.close()
        buf = io.BytesIO()
        merged.save(buf)
        merged.close()
        buf.seek(0)
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='merged.pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5035)
