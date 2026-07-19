from flask import Flask, request, send_file, jsonify, render_template
from PIL import Image, UnidentifiedImageError
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process():
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file'}), 400
    op = request.form.get('op', 'convert')
    fmt = request.form.get('format', 'PNG').upper()
    quality = max(1, min(100, int(request.form.get('quality', 85))))
    try:
        try:
            img = Image.open(f.stream)
        except UnidentifiedImageError:
            return jsonify({'error': 'Invalid or unsupported image file.'}), 400
        if op == 'resize':
            mode = request.form.get('resize_mode', 'percent')
            if mode == 'percent':
                p = max(1, min(500, int(request.form.get('percent', 100)))) / 100
                img = img.resize((max(1, int(img.width * p)), max(1, int(img.height * p))), Image.LANCZOS)
            else:
                w = request.form.get('width', '').strip()
                h = request.form.get('height', '').strip()
                if w and h:
                    img = img.resize((int(w), int(h)), Image.LANCZOS)
                elif w:
                    r = int(w) / img.width
                    img = img.resize((int(w), max(1, int(img.height * r))), Image.LANCZOS)
                elif h:
                    r = int(h) / img.height
                    img = img.resize((max(1, int(img.width * r)), int(h)), Image.LANCZOS)
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5002)
