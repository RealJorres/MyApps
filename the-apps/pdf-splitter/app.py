from flask import Flask, request, send_file, jsonify, render_template
import fitz, io, zipfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def info():
    f = request.files.get('file')
    if not f: return jsonify({'error': 'No file'}), 400
    try:
        doc = fitz.open(stream=f.read(), filetype='pdf')
        return jsonify({'pages': len(doc), 'title': doc.metadata.get('title','')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/split', methods=['POST'])
def split():
    f = request.files.get('file')
    mode = request.form.get('mode', 'all')
    ranges = request.form.get('ranges', '')
    if not f: return jsonify({'error': 'No file'}), 400
    try:
        data = f.read()
        src = fitz.open(stream=data, filetype='pdf')
        total = len(src)
        pages_to_extract = []
        if mode == 'all':
            pages_to_extract = list(range(total))
        elif mode == 'range':
            for part in ranges.split(','):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-', 1)
                    pages_to_extract += list(range(int(a)-1, min(int(b), total)))
                elif part.isdigit():
                    pages_to_extract.append(int(part)-1)
        pages_to_extract = [p for p in pages_to_extract if 0 <= p < total]
        if not pages_to_extract: return jsonify({'error': 'No valid pages selected'}), 400
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for pg in pages_to_extract:
                out = fitz.open()
                out.insert_pdf(src, from_page=pg, to_page=pg)
                pb = io.BytesIO(); out.save(pb); pb.seek(0)
                zf.writestr(f'page_{pg+1}.pdf', pb.read())
                out.close()
        src.close(); buf.seek(0)
        return send_file(buf, mimetype='application/zip', as_attachment=True, download_name='split_pages.zip')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5086)
