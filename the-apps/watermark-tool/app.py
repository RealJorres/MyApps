from flask import Flask, request, send_file, jsonify, render_template
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import io, os, re

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

FORMATS = {'PNG', 'JPEG', 'WEBP'}


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_hex(color):
    """Accept #rgb and #rrggbb; return (r, g, b) or None."""
    m = re.fullmatch(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})', color or '')
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/watermark', methods=['POST'])
def watermark():
    f = request.files.get('image')
    if not f:
        return jsonify({'error': 'No image provided'}), 400
    text = request.form.get('text', 'WATERMARK')
    position = request.form.get('position', 'center')
    opacity = _int(request.form.get('opacity', 40))
    if opacity is None:
        return jsonify({'error': 'opacity must be a number'}), 400
    opacity = max(10, min(100, opacity)) / 100
    size = _int(request.form.get('size', 48))
    if size is None:
        return jsonify({'error': 'size must be a number'}), 400
    size = max(10, min(200, size))
    rgb = _parse_hex(request.form.get('color', '#ffffff'))
    if rgb is None:
        return jsonify({'error': 'color must be a hex value like #fff or #ffffff'}), 400
    fmt = request.form.get('format', 'PNG').upper()
    if fmt not in FORMATS:
        return jsonify({'error': f'format must be one of: {", ".join(sorted(FORMATS))}'}), 400
    try:
        try:
            img = Image.open(f.stream).convert('RGBA')
        except UnidentifiedImageError:
            return jsonify({'error': 'Invalid or unsupported image file.'}), 400
        overlay = Image.new('RGBA', img.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype('arial.ttf', size)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        w, h = img.size
        positions = {
            'center': ((w-tw)//2, (h-th)//2),
            'top-left': (20, 20),
            'top-right': (w-tw-20, 20),
            'bottom-left': (20, h-th-20),
            'bottom-right': (w-tw-20, h-th-20),
            'top-center': ((w-tw)//2, 20),
            'bottom-center': ((w-tw)//2, h-th-20),
        }
        x, y = positions.get(position, ((w-tw)//2, (h-th)//2))
        r, g, b = rgb
        a = int(opacity * 255)
        draw.text((x, y), text, font=font, fill=(r, g, b, a))
        result = Image.alpha_composite(img, overlay)
        buf = io.BytesIO()
        mime_map = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}
        ext_map = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp'}
        if fmt == 'JPEG':
            result = result.convert('RGB')
        result.save(buf, format=fmt)
        buf.seek(0)
        return send_file(buf, mimetype=mime_map.get(fmt,'image/png'), as_attachment=True, download_name=f'watermarked.{ext_map.get(fmt,"png")}')
    except Exception:
        return jsonify({'error': 'Could not watermark this image. Please try a different file.'}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5036)
