from flask import Flask, request, send_file, jsonify, render_template
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import os
import re

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/pdf-to-images', methods=['POST'])
def pdf_to_images():
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No PDF files provided'}), 400

    dpi = min(max(int(request.form.get('dpi', 150)), 36), 600)
    fmt = request.form.get('format', 'png').lower()
    if fmt not in ('png', 'jpeg'):
        fmt = 'png'

    results = []
    total_pages = 0

    try:
        for f in files:
            if not f.filename.lower().endswith('.pdf'):
                return jsonify({'error': f'"{f.filename}" is not a PDF file'}), 400

            doc = fitz.open(stream=f.read(), filetype='pdf')
            if doc.is_encrypted:
                return jsonify({'error': f'"{f.filename}" is password-protected'}), 400

            base = re.sub(r'[^\w\-]', '_', os.path.splitext(os.path.basename(f.filename))[0])
            scale = dpi / 72
            pages = []
            for i in range(len(doc)):
                pix = doc[i].get_pixmap(matrix=fitz.Matrix(scale, scale))
                img_bytes = pix.tobytes(fmt)
                pages.append({
                    'page': i + 1,
                    'data': base64.b64encode(img_bytes).decode(),
                    'format': fmt,
                    'filename': f'page_{i + 1}.{fmt}',
                })

            results.append({
                'filename': os.path.basename(f.filename),
                'base_name': base,
                'total': len(doc),
                'pages': pages,
            })
            total_pages += len(doc)

        return jsonify({'files': results, 'total_pages': total_pages, 'file_count': len(results)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/images-to-pdf', methods=['POST'])
def images_to_pdf():
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No images provided'}), 400

    try:
        pil_images = []
        for f in files:
            img = Image.open(f.stream)
            if img.mode == 'RGBA':
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            pil_images.append(img)

        buf = io.BytesIO()
        pil_images[0].save(
            buf,
            format='PDF',
            save_all=True,
            append_images=pil_images[1:],
            resolution=150.0,
        )
        buf.seek(0)
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='output.pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print('\n  PDF ↔ Image Converter')
    print('  Open http://localhost:5001 in your browser\n')
    app.run(debug=False, port=5001)
