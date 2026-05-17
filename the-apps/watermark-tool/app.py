from flask import Flask, request, send_file, jsonify, render_template
from PIL import Image, ImageDraw, ImageFont
import io, os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

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
    opacity = max(10, min(100, int(request.form.get('opacity', 40)))) / 100
    size = max(10, min(200, int(request.form.get('size', 48))))
    color = request.form.get('color', '#ffffff')
    fmt = request.form.get('format', 'PNG').upper()
    try:
        img = Image.open(f.stream).convert('RGBA')
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
        r = int(int(color[1:3],16))
        g = int(int(color[3:5],16))
        b = int(int(color[5:7],16))
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5036)
