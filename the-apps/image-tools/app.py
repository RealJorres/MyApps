from flask import Flask, request, send_file, jsonify, render_template
from PIL import Image, UnidentifiedImageError
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Cap resize targets: one oversized request must never be able to exhaust
# the server's memory (a 30000x30000 RGBA image alone is ~3.4 GB).
MAX_DIMENSION = 10000
MAX_PIXELS = 25_000_000

FORMATS = {'PNG', 'JPEG', 'WEBP', 'BMP'}


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def info():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    try:
        img = Image.open(f.stream)
        return jsonify({'width': img.width, 'height': img.height, 'mode': img.mode, 'format': img.format or 'unknown'})
    except UnidentifiedImageError:
        return jsonify({'error': 'Invalid or unsupported image file.'}), 400
    except Exception:
        return jsonify({'error': 'Could not read this image. Please try a different file.'}), 500

@app.route('/api/process', methods=['POST'])
def process():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    op = request.form.get('op', 'convert')
    fmt = request.form.get('format', 'PNG').upper()
    if fmt not in FORMATS:
        return jsonify({'error': f'format must be one of: {", ".join(sorted(FORMATS))}'}), 400
    quality = _int(request.form.get('quality', 85))
    if quality is None:
        return jsonify({'error': 'quality must be a number'}), 400
    quality = max(1, min(100, quality))
    try:
        try:
            img = Image.open(f.stream)
        except UnidentifiedImageError:
            return jsonify({'error': 'Invalid or unsupported image file.'}), 400
        if op == 'resize':
            mode = request.form.get('resize_mode', 'percent')
            if mode == 'percent':
                p = _int(request.form.get('percent', 100))
                if p is None:
                    return jsonify({'error': 'percent must be a number'}), 400
                p = max(1, min(500, p)) / 100
                tw, th = max(1, int(img.width * p)), max(1, int(img.height * p))
            else:
                w = _int(request.form.get('width', '').strip() or None)
                h = _int(request.form.get('height', '').strip() or None)
                raw_w = request.form.get('width', '').strip()
                raw_h = request.form.get('height', '').strip()
                if (raw_w and w is None) or (raw_h and h is None):
                    return jsonify({'error': 'width and height must be numbers'}), 400
                if w and h:
                    tw, th = w, h
                elif w:
                    tw, th = w, max(1, int(img.height * w / img.width))
                elif h:
                    tw, th = max(1, int(img.width * h / img.height)), h
                else:
                    tw, th = img.width, img.height
                if tw < 1 or th < 1:
                    return jsonify({'error': 'width and height must be positive'}), 400
            if tw > MAX_DIMENSION or th > MAX_DIMENSION or tw * th > MAX_PIXELS:
                return jsonify({'error': f'Target size too large (max {MAX_DIMENSION}px per side, {MAX_PIXELS // 1_000_000} megapixels total)'}), 400
            if (tw, th) != (img.width, img.height):
                img = img.resize((tw, th), Image.LANCZOS)
        if fmt == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            src = img.convert('RGBA') if img.mode == 'P' else img
            bg.paste(src, mask=src.split()[-1])
            img = bg
        elif fmt not in ('JPEG',) and img.mode == 'P':
            img = img.convert('RGBA')
        buf = io.BytesIO()
        mime = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp', 'BMP': 'image/bmp'}
        ext  = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp', 'BMP': 'bmp'}
        kw = {'quality': quality} if fmt in ('JPEG', 'WEBP') else {}
        img.save(buf, format=fmt, **kw)
        buf.seek(0)
        return send_file(buf, mimetype=mime.get(fmt, 'image/png'), as_attachment=True, download_name=f'output.{ext.get(fmt,"png")}')
    except Exception:
        return jsonify({'error': 'Could not process this image. Please try a different file.'}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5002)
