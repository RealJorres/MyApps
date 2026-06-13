from flask import Flask, request, send_file, jsonify, render_template
import io
import os
import tempfile
import logging

import fitz  # PyMuPDF — used only to sniff whether the PDF has real text
from pdf2docx import Converter

# pdf2docx is extremely chatty at INFO level; keep production logs clean.
logging.getLogger('pdf2docx').setLevel(logging.ERROR)

app = Flask(__name__)
# Conversion is CPU/memory heavy and the deploy is a single 512 MB worker,
# so cap uploads well below the larger file apps.
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25 MB

# Below this many extractable characters the PDF is almost certainly a scan
# (image-only) and there is no selectable text to turn into editable Word.
_MIN_TEXT_CHARS = 10


@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(413)
def too_large(_e):
    return jsonify({'error': 'File is too large. The maximum size is 25 MB.'}), 413


@app.route('/api/convert', methods=['POST'])
def convert():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file was provided.'}), 400

    data = f.read()
    if not data:
        return jsonify({'error': 'The uploaded file is empty.'}), 400
    if not data.startswith(b'%PDF'):
        return jsonify({'error': 'That does not look like a valid PDF file.'}), 400

    # Inspect the PDF: page count + how much real text it contains.
    try:
        doc = fitz.open(stream=data, filetype='pdf')
        page_count = doc.page_count
        text_chars = sum(len(page.get_text().strip()) for page in doc)
        doc.close()
    except Exception:
        return jsonify({'error': 'Could not read this PDF. It may be corrupted '
                                 'or password-protected.'}), 400

    if page_count == 0:
        return jsonify({'error': 'This PDF has no pages.'}), 400

    if text_chars < _MIN_TEXT_CHARS:
        # Scanned / image-only PDF — honest message instead of an empty .docx.
        return jsonify({
            'error': 'This PDF looks scanned (image-only), so it has no '
                     'selectable text to convert into an editable Word document. '
                     'Run it through the OCR Tool first, then convert the result.',
            'scanned': True,
        }), 422

    pdf_path = docx_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(data)
            pdf_path = tmp.name
        docx_path = pdf_path[:-4] + '.docx'

        cv = Converter(pdf_path)
        try:
            cv.convert(docx_path)
        finally:
            cv.close()

        with open(docx_path, 'rb') as fh:
            out = io.BytesIO(fh.read())
        out.seek(0)

        base = os.path.splitext(os.path.basename(f.filename or 'document'))[0] or 'document'
        return send_file(
            out,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=base + '.docx',
        )
    except Exception as e:
        return jsonify({'error': 'Conversion failed: ' + str(e)}), 500
    finally:
        for p in (pdf_path, docx_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


if __name__ == '__main__':
    app.run(debug=False, port=5145)
