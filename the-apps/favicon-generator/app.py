from flask import Flask, request, send_file, jsonify, render_template
from PIL import Image
import io, zipfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

SIZES = [16, 32, 48, 64, 96, 128, 180, 192, 256, 512]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    fmt = request.form.get('format', 'png').lower()
    sizes_raw = request.form.get('sizes', '')
    try:
        sizes = [int(s) for s in sizes_raw.split(',') if s.strip().isdigit()] if sizes_raw else SIZES
        img = Image.open(f.stream).convert('RGBA')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for size in sizes:
                resized = img.resize((size, size), Image.LANCZOS)
                img_buf = io.BytesIO()
                if fmt == 'ico' and size <= 256:
                    resized.save(img_buf, format='ICO')
                    zf.writestr(f'favicon-{size}x{size}.ico', img_buf.getvalue())
                else:
                    out = resized if fmt == 'png' else resized.convert('RGB')
                    out.save(img_buf, format='PNG' if fmt == 'png' else 'JPEG')
                    zf.writestr(f'favicon-{size}x{size}.{"png" if fmt=="png" else "jpg"}', img_buf.getvalue())
        buf.seek(0)
        return send_file(buf, mimetype='application/zip', as_attachment=True, download_name='favicons.zip')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5023)
